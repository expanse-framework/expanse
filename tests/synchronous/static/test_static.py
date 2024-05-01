from pathlib import Path

from expanse.foundation.application import Application
from expanse.static.static import Static


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_get_returns_file_content_if_file_exists(app: Application) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    response = static.get("foo.txt")

    assert response.status_code == 200


def test_get_returns_404_not_found_if_file_does_not_exist(app: Application) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    response = static.get("bar.txt")

    assert response.status_code == 404
