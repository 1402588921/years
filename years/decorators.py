from years import Request


def asgi_application(func):
    def app(scope):
        async def asgi(receive, send):
            request = Request(scope, receive)
            response = func(request)
            await response(receive, send)

        return asgi

    return app
