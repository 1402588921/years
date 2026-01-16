import traceback
from typing import Callable

from years.responses import PlainTextResponse


class DebugMiddleware:
    def __init__(self, endpoint: Callable):
        self.endpoint = endpoint

    async def __call__(self, scope, receive, send):
        try:
            await self.endpoint(scope, receive, send)
        except Exception:
            err_stack = traceback.format_exc()
            response = PlainTextResponse(err_stack)
            await response(scope, send)
