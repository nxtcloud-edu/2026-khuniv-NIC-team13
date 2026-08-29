from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.routes import router as legacy_router
from app.core.config import get_settings
from app.core.cors import configure_cors
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import configure_middlewares
from app.schemas.common import error_response

OPENAPI_TAGS = [
    {"name": "Health", "description": "Runtime health checks."},
    {"name": "Setup", "description": "Static setup/autocomplete data for companies, positions, universities, and majors."},
    {"name": "Auth", "description": "Email verification and analysis credit APIs."},
    {"name": "Session", "description": "Member session start and extension APIs."},
    {"name": "Parsing", "description": "Resume/self-introduction parsing helpers."},
    {"name": "Analysis", "description": "Self-introduction analysis stream APIs."},
    {"name": "Notice", "description": "Notice CRUD APIs."},
    {"name": "Admin", "description": "Legacy admin HTML endpoints."},
]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, debug=settings.debug, openapi_tags=OPENAPI_TAGS)

    configure_cors(app, settings)
    configure_middlewares(app)
    register_exception_handlers(app)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "success" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content=error_response("ERROR", str(exc.detail)))

    app.include_router(health_router)
    app.include_router(legacy_router)
    return app


app = create_app()
