#!/usr/bin/env bash
# A fixed, disposable rootless PostgreSQL target; never uses development volumes.
set -euo pipefail
cd "$(dirname "$0")/../.."
endpoint="unix:///run/user/$(id -u)/docker.sock"
docker_cmd=(env -u DOCKER_CONTEXT -u DOCKER_HOST -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH docker --host "$endpoint")
if [[ "$("${docker_cmd[@]}" info --format '{{json .SecurityOptions}}')" != *'name=rootless'* ]]; then
    echo 'Refusing a daemon without rootless security.' >&2
    exit 1
fi
image='pgvector/pgvector:pg17'
"${docker_cmd[@]}" image inspect "$image" >/dev/null
run_id="cvmatcher-test-$(date +%s)-$$"
cleanup() {
    if [[ "$("${docker_cmd[@]}" inspect --format '{{index .Config.Labels "cvmatcher.test-run"}}' "$run_id" 2>/dev/null)" == "$run_id" ]]; then
        "${docker_cmd[@]}" rm -fv "$run_id" >/dev/null
    fi
}
trap cleanup EXIT
"${docker_cmd[@]}" run --detach --name "$run_id" --pull never \
    --label "cvmatcher.test-run=$run_id" --label 'cvmatcher.project=esw3_cvmatcher' \
    --memory 512m --cpus 1 --pids-limit 128 \
    --publish 127.0.0.1::5432 \
    --env POSTGRES_USER=cvmatch --env POSTGRES_PASSWORD=synthetic-test-only \
    --env POSTGRES_DB=cvmatch_test \
    "$image" -c shared_buffers=64MB -c max_connections=20 >/dev/null
ready=false
for ((attempt=0; attempt<30; attempt++)); do
    if "${docker_cmd[@]}" exec "$run_id" pg_isready -h 127.0.0.1 -U cvmatch -d cvmatch_test >/dev/null; then
        ready=true
        break
    fi
    sleep 1
done
if [[ "$ready" != true ]]; then
    echo 'Disposable PostgreSQL did not become ready.' >&2
    exit 1
fi
port="$("${docker_cmd[@]}" port "$run_id" 5432/tcp)"
port="${port##*:}"
export TEST_DATABASE_URL="postgresql://cvmatch:synthetic-test-only@127.0.0.1:${port}/cvmatch_test"
"${PYTHON:-python3}" -m pytest "$@"
