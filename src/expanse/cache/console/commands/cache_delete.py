from typing import ClassVar

from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.cache.asynchronous.cache_manager import CacheManager
from expanse.console.commands.command import Command


class CacheDeleteCommand(Command):
    name: str = "cache delete"
    description: str = "Remove specific items from the cache."

    arguments: ClassVar[list[Argument]] = [
        Argument(
            "keys",
            description="The keys of the cache items to delete.",
            is_list=True,
        ),
    ]

    options: ClassVar[list[Option]] = [
        Option(
            "store",
            description="The name of the cache store to delete items from.",
            flag=False,
        )
    ]

    async def handle(self, cache_manager: CacheManager) -> int:
        store: str = self.option("store") or cache_manager.get_default_store_name()

        cache = await cache_manager.cache(store)

        keys: list[str] = self.argument("keys")

        if await cache.delete_many(keys):
            self.line(
                f"Deleted keys '{', '.join(keys)}' from cache '{store}'.",
                style="success",
            )
            return 0
        else:
            self.line_error(
                f"Failed to delete keys '{', '.join(keys)}' from cache '{store}'.",
                style="error",
            )
            return 1
