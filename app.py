from years import Request, JSONResponse


async def app(scope, receive, send):
    request = Request(scope, receive)
    body = await request.json()
    data = dict(json=body)
    response = JSONResponse(data)
    await response(receive, send)
