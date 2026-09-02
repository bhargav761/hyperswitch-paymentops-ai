from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dashboard import router as dashboard_router
from app.api.incidents import router as incidents_router
from app.api.payments import router as payments_router
from app.api.recovery import router as recovery_router
from app.config.settings import APP_NAME, APP_VERSION
from app.database.base import Base
from app.database.connection import engine
from app.services.logging_service import (
    configure_logging,
    get_logger,
)

configure_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application.starting")
    Base.metadata.create_all(bind=engine)
    logger.info("database.initialized")
    yield
    logger.info("application.stopping")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "status": "running",
        "version": APP_VERSION,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "paymentops-ai",
    }


app.include_router(payments_router)
app.include_router(dashboard_router)
app.include_router(incidents_router)
app.include_router(recovery_router)
