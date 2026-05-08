from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import api_router
from core.config import get_settings
from core.errors import setup_exception_handlers
from core.logging import setup_logging
from jobs.registry import start_scheduler


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)
    setup_logging(app)
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    def on_startup() -> None:
        start_scheduler()

    return app
