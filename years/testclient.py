import httpx


def TestClient(app, base_url: str = "http://testserver"):
    transport = httpx.ASGITransport(app=app)
    params = dict(transport=transport, base_url=base_url)
    return httpx.AsyncClient(**params)
