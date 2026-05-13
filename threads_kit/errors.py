class ThreadsAPIError(Exception):
    """Graph Threads API が error オブジェクトを返したとき。"""

    def __init__(self, message: str, *, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}
