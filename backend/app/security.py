from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sent on every HTTP response. The API serves JSON only, so it is never framed or sniffed.
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
}


class SecurityHeadersMiddleware:
    """Pure ASGI middleware (no BaseHTTPMiddleware) so it also covers error responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._headers = [(k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *self._headers]
            await send(message)

        await self.app(scope, receive, send_with_headers)
