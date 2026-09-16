from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import api_router
from core.config import get_settings
from core.errors import setup_exception_handlers
from core.logging import setup_logging
from db.session import engine
from jobs.registry import start_scheduler
from modules.system.audit import setup_audit_middleware
from modules.system.audit_config import load_database_field_labels
from modules.system.audit_coverage import warn_unclassified_write_routes


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        load_database_field_labels(engine)
        warn_unclassified_write_routes(app)
        if settings.should_start_scheduler:
            start_scheduler()
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)
    setup_logging(app)
    setup_audit_middleware(app)
    app.include_router(api_router, prefix="/api")

    return app
