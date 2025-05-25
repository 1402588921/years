import json
import typing

from years import MutableHeaders


class Response:
    media_type = None
    charset = "utf-8"

    def __init__(
        self,
        content,
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
    ):
        self.body = self.render(content)
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.raw_kwargs = self.init_headers(headers)

    def render(self, content):
        if isinstance(content, bytes):
            return content
        return content.encode(self.charset)

    def init_headers(self, headers: typing.Mapping):
        if headers is None:
            raw_kwargs = []
            populate_content_length = True
            populate_content_type = True
        else:
            raw_kwargs = [
                (key.lower().encode("latin-1"), value.encode("latin-1"))
                for key, value in headers.items()
            ]
            keys = set(item[0] for item in raw_kwargs)
            populate_content_length = "content_length" in keys
            populate_content_type = "content_type" in keys

        body = getattr(self, "body", None)
        if body is not None and populate_content_length:
            raw_kwargs.append(
                (b"content_length", str(len(self.body)).encode("latin-1"))
            )

        context_type = self.media_type
        if populate_content_type and context_type is not None:
            if context_type.startswith("text/"):
                context_type = self.media_type + "; charset=%s" % self.charset
            raw_kwargs.append((b"context_type", context_type.encode()))

        return raw_kwargs

    @property
    def headers(self):
        if not hasattr(self, "_headers"):
            self._headers = MutableHeaders(self.raw_kwargs)
        return self._headers

    async def __call__(self, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_kwargs,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": self.body,
            }
        )


class HTMLResponse(Response):
    media_type = "text/html"


class PlainTextResponse(Response):
    media_type = "text/plain"


class JSONResponse(Response):
    media_type = "application/json"

    def render(self, content):
        return json.dumps(content).encode(self.charset)


class StreamingResponse(Response):
    media_type = "application/octet-stream"

    def __init__(self, content, status_code=200, headers=None, media_type=None):
        self.body_iterator = content
        self.status_code = status_code
        if media_type:
            self.media_type = media_type
        self.raw_kwargs = self.init_headers(headers)

    async def __call__(self, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_kwargs,
            }
        )

        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode()

            await send(
                {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                }
            )

        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )
