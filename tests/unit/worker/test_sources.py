import pytest

from src.worker.sources import main


@pytest.mark.parametrize(
    "arguments",
    [["register", "gupy"], ["register", "apibr", "--polling-mode", "HOURLY"], []],
)
def test_command_rejects_invalid_arguments_before_any_database_access(arguments):
    def forbidden():
        pytest.fail("argument validation must not open a database")

    with pytest.raises(SystemExit) as exit_info:
        main(arguments, sessions=forbidden)
    assert exit_info.value.code == 2


def test_command_failure_is_safe_and_does_not_leak_exception_text(caplog, capsys):
    def failing():
        raise RuntimeError("postgresql://user:secret@host/db is unavailable")

    assert main(["register", "apibr"], sessions=failing) == 1
    assert "source_registration_failed" in caplog.text
    assert "secret" not in caplog.text
    assert capsys.readouterr().out == ""
