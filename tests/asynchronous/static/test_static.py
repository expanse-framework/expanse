from pathlib import Path

from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.static.static import Static


FIXTURES_DIR = Path(__file__).parent / "fixtures"


async def test_get_returns_file_content_if_file_exists(app: Application) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    response = await static.get("foo.txt")

    assert response.status_code == 200


async def test_get_returns_404_not_found_if_file_does_not_exist(
    app: Application,
) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    response = await static.get("bar.txt")

    assert response.status_code == 404
