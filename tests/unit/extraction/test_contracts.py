import pytest

from src.extraction.contracts import SpanEvidence, chunks


def test_chunk_coverage_preserves_offsets_and_bounds():
    text = "Título\nCompetências\n" + "ação 🦉 " * 200
    result = chunks(text, size=100, overlap=20)
    assert result[0].start == 0
    assert result[-1].end == len(text)
    assert all(
        chunk.text == text[chunk.start : chunk.end] and len(chunk.text) <= 100 for chunk in result
    )
    assert all(a.end - b.start == 20 for a, b in zip(result, result[1:], strict=False))
    assert set().union(*(set(range(c.start, c.end)) for c in result)) == set(range(len(text)))
    assert chunks("") == ()


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, -1), (10, 10), (10, 11)])
def test_invalid_chunk_policy(size, overlap):
    with pytest.raises(ValueError):
        chunks("text", size=size, overlap=overlap)


def test_span_confidence_never_implies_mandatory_requirement():
    assert (
        SpanEvidence(0, 6, "skill", 1.0).serialize("Python requerido")["requirement_class"] is None
    )


@pytest.mark.parametrize(
    "span",
    [
        SpanEvidence(-1, 2, "skill", 0.8),
        SpanEvidence(0, 10, "skill", 0.8),
        SpanEvidence(1, 1, "skill", 0.8),
        SpanEvidence(True, 2, "skill", 0.8),
        SpanEvidence(0, 2, "", 0.8),
        SpanEvidence(0, 2, "skill", float("nan")),
        SpanEvidence(0, 2, "skill", 1.1),
        SpanEvidence(0, 2, "skill", True),
    ],
)
def test_invalid_span_rejected(span):
    with pytest.raises(ValueError):
        span.serialize("text")
