-- pgvector validation (issue #24, parent #4).
--
-- Usage:   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/validate_pgvector.sql
-- Effects: creates and drops its own table (pgvector_validation); touches nothing else.
-- Data:    deterministic synthetic 384-d vectors (384 = dimension of MiniLM-class models),
--          grouped in three clusters, so the expected neighbours are known in advance.

\echo '== 1. Enable extension'
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extversion AS pgvector_version FROM pg_extension WHERE extname = 'vector';

\echo '== 2. Sample vector column'
DROP TABLE IF EXISTS pgvector_validation;
CREATE TABLE pgvector_validation (
    id        integer PRIMARY KEY,
    cluster   text NOT NULL,
    embedding vector(384) NOT NULL
);

-- Cluster base frequency: backend=1, data=3, kitchen=7; the id adds a small deterministic jitter.
INSERT INTO pgvector_validation (id, cluster, embedding)
SELECT g,
       c.name,
       (SELECT array_agg(sin(c.freq * d / 10.0) + 0.05 * sin(g * d))::real[]
          FROM generate_series(1, 384) AS d)::vector(384)
FROM generate_series(1, 30) AS g
JOIN LATERAL (
    SELECT CASE (g - 1) % 3 WHEN 0 THEN 'backend' WHEN 1 THEN 'data' ELSE 'kitchen' END AS name,
           CASE (g - 1) % 3 WHEN 0 THEN 1 WHEN 1 THEN 3 ELSE 7 END AS freq
) AS c ON true;

SELECT count(*) AS rows, vector_dims(embedding) AS dims
FROM pgvector_validation GROUP BY 2;

\echo '== 3. Similarity queries (query vector = backend cluster, id 100)'
-- Query vector: same generator as the backend cluster, jitter seed 100.
CREATE TEMP TABLE q AS
SELECT (SELECT array_agg(sin(1 * d / 10.0) + 0.05 * sin(100 * d))::real[]
          FROM generate_series(1, 384) AS d)::vector(384) AS v;

\echo 'cosine distance (<=>): top 5, similarity = 1 - distance'
SELECT id, cluster, round((1 - (embedding <=> q.v))::numeric, 4) AS cosine_similarity
FROM pgvector_validation, q ORDER BY embedding <=> q.v, id LIMIT 5;

\echo 'L2 distance (<->): top 3'
SELECT id, cluster, round((embedding <-> q.v)::numeric, 4) AS l2
FROM pgvector_validation, q ORDER BY embedding <-> q.v, id LIMIT 3;

\echo 'negative inner product (<#>): top 3'
SELECT id, cluster, round((embedding <#> q.v)::numeric, 4) AS neg_ip
FROM pgvector_validation, q ORDER BY embedding <#> q.v, id LIMIT 3;

\echo 'ASSERT: all top-10 cosine neighbours belong to the backend cluster'
DO $$
DECLARE bad integer;
BEGIN
    SELECT count(*) INTO bad FROM (
        SELECT cluster FROM pgvector_validation, q ORDER BY embedding <=> q.v, id LIMIT 10
    ) t WHERE cluster <> 'backend';
    IF bad > 0 THEN RAISE EXCEPTION 'similarity ordering wrong: % non-backend rows in top 10', bad; END IF;
    RAISE NOTICE 'OK: top-10 are all backend';
END $$;

\echo '== 4. Indexes (HNSW and IVFFlat, cosine ops) are created and used by the planner'
-- The index is only usable when the query vector is a constant/parameter, not a join column,
-- so the plan check runs the query through dynamic SQL with the vector as a literal.
SELECT v::text AS qv FROM q \gset

CREATE OR REPLACE FUNCTION pg_temp.plan_node(expected_index text) RETURNS void
LANGUAGE plpgsql AS $f$
DECLARE r text; found boolean := false;
BEGIN
    SET LOCAL enable_seqscan = off;  -- tiny table: a seq scan is otherwise cheaper
    FOR r IN EXECUTE format(
        'EXPLAIN (COSTS OFF) SELECT id FROM pgvector_validation ORDER BY embedding <=> %L::vector LIMIT 5',
        current_setting('app.qv'))
    LOOP
        IF r LIKE '%Index Scan using ' || expected_index || '%' THEN found := true; END IF;
    END LOOP;
    IF NOT found THEN RAISE EXCEPTION 'planner did not use %', expected_index; END IF;
    RAISE NOTICE 'OK: planner uses %', expected_index;
END $f$;

SELECT set_config('app.qv', :'qv', false) IS NOT NULL AS qv_set;

CREATE INDEX pgvector_validation_hnsw ON pgvector_validation
    USING hnsw (embedding vector_cosine_ops);
SELECT pg_temp.plan_node('pgvector_validation_hnsw');
DROP INDEX pgvector_validation_hnsw;

CREATE INDEX pgvector_validation_ivfflat ON pgvector_validation
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 3);
SELECT pg_temp.plan_node('pgvector_validation_ivfflat');
DROP INDEX pgvector_validation_ivfflat;

\echo '== 5. Dimension mismatch must be rejected'
DO $$
BEGIN
    INSERT INTO pgvector_validation VALUES (999, 'bad', '[1,2,3]');
    RAISE EXCEPTION 'dimension mismatch was NOT rejected';
EXCEPTION WHEN SQLSTATE '22000' THEN
    RAISE NOTICE 'OK: rejected (%).', SQLERRM;
END $$;

\echo '== 6. NULL embedding is allowed on a nullable column (PLAN: embedding = NULL means missing)'
CREATE TEMP TABLE nullable_probe (embedding vector(384));
INSERT INTO nullable_probe VALUES (NULL);
SELECT count(*) AS null_rows FROM nullable_probe WHERE embedding IS NULL;

\echo '== cleanup'
DROP TABLE pgvector_validation;
