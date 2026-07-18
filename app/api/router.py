from fastapi import APIRouter

from app.api import auth, captions, health, images, products, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(products.router)
api_router.include_router(captions.router)
api_router.include_router(images.router)
