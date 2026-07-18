from fastapi import APIRouter

from app.api import auth, captions, dashboard, health, images, products, scheduler, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(products.router)
api_router.include_router(captions.router)
api_router.include_router(images.router)
api_router.include_router(scheduler.router)
api_router.include_router(dashboard.router)
