from expanse.http.request import Request
from expanse.session.synchronous.stores.store import Store


class NullStore(Store):
    def read(self, session_id: str) -> str:
        return ""

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        pass

    def delete(self, session_id: str) -> None:
        pass

    def clear(self) -> int:
        return 0
