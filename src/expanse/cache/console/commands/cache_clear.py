from typing import ClassVar

from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.cache.asynchronous.cache_manager import CacheManager
from expanse.console.commands.command import Command


class CacheClearCommand(Command):
    name: str = "cache clear"
    description: str = "Remove all entries from the cache."

    arguments: ClassVar[list[Argument]] = [
        Argument(
            "store",
            description="The name of the cache store to clear. If not provided, the default store will be cleared.",
            required=False,
        ),
    ]

    options: ClassVar[list[Option]] = []

    async def handle(self, cache_manager: CacheManager) -> int:
        store: str = self.argument("store") or cache_manager.get_default_store_name()

        cache = await cache_manager.cache(store)

        if await cache.clear():
            self.line(f"Cache '{store}' cleared successfully.", style="success")
            return 0
        else:
            self.line_error(f"Failed to clear cache '{store}'.", style="error")
            return 1
