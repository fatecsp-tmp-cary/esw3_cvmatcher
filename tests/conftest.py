from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).parent

# First directory under tests/ -> marker applied to every test inside it.
DIRECTORY_MARKERS = {
    "unit": "unit",
    "integration": "integration",
    "api": "api",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative = item.path.relative_to(TESTS_ROOT)
        marker = DIRECTORY_MARKERS.get(relative.parts[0])
        if marker is not None:
            item.add_marker(marker)
