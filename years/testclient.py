import io
import typing
import asyncio
import requests
import requests.adapters

from urllib.parse import urlparse, unquote, urljoin


class _HeaderDict(requests.packages.urllib3._collections.HTTPHeaderDict):
    def get_all(self, key, default):
        return self.getheaders(key)


class _MockOriginalResponse(object):
    def __init__(self, headers):
        self.msg = _HeaderDict(headers)
        self.closed = False

    def isclosed(self):
        return self.closed


class _ASGIAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, app: typing.Callable):
        self.app = app

    def send(self, request, *args, **kwargs):
        uscheme, netloc, url, params, query, fragment = urlparse(request.url)
        if ":" in netloc:
            host, port = netloc.split(":", 1)
            port = int(port)
        else:
            host = netloc
            port = dict(http=80, https=443)[uscheme]

        if "host" in request.headers:
            headers = []
        elif port == 80:
            headers = [[b"host", host.encode()]]
        else:
            headers = [[b"host", ("%s:%s" % (host, port)).encode()]]

        headers += [
            [key.lower().encode(), value.encode()]
            for key, value in request.headers.items()
        ]

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "root_path": "",
            "path": unquote(url),
            "scheme": uscheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": ["testclient", 50000],
            "server": [host, port],
        }

        async def receive():
            body = request.body
            if body is None:
                body_bytes = b""
            elif isinstance(body, str):
                body_bytes = body.encode()
            else:
                body_bytes = body
            return dict(type="http.request", body=body_bytes)

        async def send(message):
            if message["type"] == "http.response.start":
                raw_kwargs["version"] = 11
                raw_kwargs["status"] = message["status"]
                raw_kwargs["headers"] = [
                    (key.decode(), value.decode()) for key, value in message["headers"]
                ]
                raw_kwargs["preload_content"] = False
                raw_kwargs["original_response"] = _MockOriginalResponse(
                    message["headers"]
                )
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                raw_kwargs["body"].write(body)

                if not more_body:
                    raw_kwargs["body"].seek(0)

        raw_kwargs = dict(body=io.BytesIO())
        connect = self.app(scope)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
        loop.run_until_complete(connect(receive, send))

        raw = requests.packages.urllib3.HTTPResponse(**raw_kwargs)
        return self.build_response(request, raw)


class _TestClient(requests.Session):
    def __init__(self, app, base_url: str):
        super().__init__()
        app = _ASGIAdapter(app)
        self.mount("http://", app)
        self.mount("https://", app)
        self.headers.update({"user-agent": "testclient"})
        self.app = app
        self.base_url = base_url

    def request(self, method, url, **kwargs):
        url = urljoin(self.base_url, url)
        return super().request(method, url, **kwargs)


def TestClient(app: typing.Callable, base_url: str = "http://testserver"):
    return _TestClient(app, base_url)
