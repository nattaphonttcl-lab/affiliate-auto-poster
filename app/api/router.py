from fastapi import APIRouter

from app.api import (
    ai,
    analytics,
    auth,
    captions,
    dashboard,
    health,
    images,
    publishing,
    saas,
    products,
    scheduler,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(products.router)
api_router.include_router(ai.router)
api_router.include_router(captions.router)
api_router.include_router(images.router)
api_router.include_router(publishing.router)
api_router.include_router(publishing.social_router)
api_router.include_router(saas.router)
api_router.include_router(scheduler.router)
api_router.include_router(dashboard.router)
api_router.include_router(analytics.router)
