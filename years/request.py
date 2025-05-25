import json
from collections.abc import Mapping
from typing import Callable

from years.datastructures import URL, QueryParams, Headers


class Request(Mapping):
    def __init__(self, scope: dict, receive: Callable | None = None):
        self._scope = scope
        self._receive = receive
        self._stream_consumed = False

    def __getitem__(self, key: str):
        return self._scope[key]

    def __iter__(self):
        return iter(self._scope)

    def __len__(self):
        return len(self._scope)

    @property
    def method(self):
        return self._scope["method"]

    @property
    def url(self):
        if not hasattr(self, "_url"):
            host, port = self._scope["server"]
            scheme = self._scope["scheme"]
            path = self._scope["root_path"] + self._scope["path"]
            query_params = self._scope["query_string"].decode()

            if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
                url = "%s://%s:%s%s" % (scheme, host, port, path)
            else:
                url = "%s://%s%s" % (scheme, host, path)

            url += "?" + query_params
            self._url = URL(url)
        return self._url

    @property
    def relative_url(self):
        if not hasattr(self, "_relative_url"):
            relative_path = self._scope["path"]
            query_params = self._scope["query_string"].decode()
            relative_url = "%s?%s" % (relative_path, query_params)
            self._relative_url = relative_url

        return self._relative_url

    @property
    def query_params(self):
        if not hasattr(self, "_query_params"):
            query_params = self._scope["query_string"].decode()
            self._query_params = QueryParams(query_params)

        return self._query_params

    @property
    def headers(self):
        if not hasattr(self, "_headers"):
            self._headers = Headers(self._scope["headers"])
        return self._headers

    async def stream(self):
        if hasattr(self, "_body"):
            yield self._body
            return

        if self._stream_consumed:
            raise RuntimeError("stream customed")

        if not self._receive:
            raise RuntimeError("Receive channel has not been made available")

        self._stream_consumed = True

        while True:
            content = await self._receive()
            if content["type"] == "http.request":
                yield content.get("body", b"")
                if not content.get("more_body", False):
                    break
            break

    async def body(self):
        if not hasattr(self, "_body"):
            body = b""
            async for chunk in self.stream():
                body += chunk
            self._body = body
        return self._body

    async def json(self):
        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = json.loads(body)
        return self._json
