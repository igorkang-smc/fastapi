from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CustomMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Perform actions before the request is processed
        print("Before request")

        # Forward the request to the next middleware or route handler
        response = await call_next(request)

        # Perform actions after the request is processed
        print("After request")

        return response