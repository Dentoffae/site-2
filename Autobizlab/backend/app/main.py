"""
Точка входа FastAPI: подключение роутов и инициализация таблиц в PostgreSQL.

В Docker сервис слушает 0.0.0.0:8080 только во внутренней сети compose; снаружи — через Nginx /api/.
"""

from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI

from app.core.database import Base, engine
from app.models import admin_site_config, lead_application, lead_behavior_metrics  # noqa: F401
from app.routes import admin_site_config as admin_routes
from app.routes import lead_application as lead_routes
from app.routes import lead_behavior_metrics as metrics_routes


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(Base.metadata.create_all, engine)
    yield


app = FastAPI(
    title="Autobizlab API",
    description="Приватный API контура Autobizlab (заявки, метрики, админ-конфиг).",
    lifespan=lifespan,
    version="1.0.0",
)

app.include_router(lead_routes.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(metrics_routes.router, prefix="/api/v1/lead-metrics", tags=["lead-metrics"])
app.include_router(admin_routes.router, prefix="/api/v1/admin-config", tags=["admin-config"])


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
