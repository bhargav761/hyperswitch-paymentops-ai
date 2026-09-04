from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.approvals import router as approvals_router
from app.api.dashboard import router as dashboard_router
from app.api.incidents import router as incidents_router
from app.api.payments import router as payments_router
from app.api.recovery import router as recovery_router
from app.api.webhooks import router as webhooks_router
from app.api.health import router as health_router
from app.config.settings import APP_NAME, APP_VERSION, CORS_ORIGINS
from app.database.base import Base
from app.models.approval import RecoveryApproval
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(webhooks_router)
app.include_router(health_router)
app.include_router(approvals_router)
