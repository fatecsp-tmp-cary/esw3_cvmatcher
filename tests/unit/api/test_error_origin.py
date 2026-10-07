from src.api.errors import _origin


def test_origin_names_file_line_and_function() -> None:
    def fail() -> None:
        raise ValueError("candidate value")

    try:
        fail()
    except ValueError as exc:
        origin = _origin(exc)

    assert origin.startswith("test_error_origin.py:")
    assert origin.endswith(" in fail")
    assert "candidate value" not in origin


def test_origin_of_exception_never_raised() -> None:
    assert _origin(ValueError("not raised")) == "unknown location"
