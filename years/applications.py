from contextlib import AsyncExitStack
from years.routing import Router, Route, Mount
from years.debug import DebugMiddleware


class Years:
    def __init__(self, router: Router = None):
        self._debug = False
        self._lifespan = None
        if router:
            self.router = router
        else:
            self.router = Router()

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, is_debug: bool):
        if is_debug:
            self.router = DebugMiddleware(self.router)

    def route(self, path: str, methods=None):
        if methods is None:
            methods = ["GET"]

        def decorate(endpoint):
            route = Route(path, endpoint, methods=methods)
            self.router.add_route(route)

        return decorate

    def get(self, path: str):
        def decorate(endpoint):
            route = Route(path, endpoint, methods=["GET"])
            self.router.add_route(route)

        return decorate

    def post(self, path: str):
        def decorate(endpoint):
            route = Route(path, endpoint, methods=["POST"])
            self.router.add_route(route)

        return decorate

    def mount(self, path, app):
        mount = Mount(path, app=app)
        self.router.add_mount(mount)

    def lifespan(self):
        def decorate(func):
            self._lifespan = func

        return decorate

    async def run_lifespan(self, scope, receive, send):
        stack = AsyncExitStack()
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await stack.enter_async_context(self._lifespan())
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                await stack.aclose()
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.run_lifespan(scope, receive, send)
        else:
            await self.router(scope, receive, send)
