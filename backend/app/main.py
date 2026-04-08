import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.dependencies import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    logger.info("Starting SwarmScope backend (env=%s)", settings.app_env)
    engine = get_engine(settings)
    yield
    logger.info("Shutting down — disposing database engine")
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="SwarmScope API",
        version="0.1.0",
        description="Scenario Simulation Lab",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router (populated from Session 04 onwards)
    try:
        from app.api.router import router as api_router
        application.include_router(api_router, prefix="/api/v1")
    except ImportError:
        logger.warning("API router not yet implemented — skipping mount")

    # Webhook receiver — no JWT auth, uses HMAC verification
    try:
        from app.api.ingestion import webhook_router
        application.include_router(webhook_router, prefix="/api/v1")
    except ImportError:
        logger.warning("Webhook router not yet implemented — skipping mount")

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": type(exc).__name__,
                "detail": str(exc),
                "status_code": 500,
            },
        )

    @application.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return application


app = create_app()
