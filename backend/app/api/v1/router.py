"""V1 API router — combines all endpoint groups."""

from fastapi import APIRouter

from app.api.v1.endpoints.admin_auth import router as admin_auth
from app.api.v1.endpoints.admin_management import router as admin_mgmt
from app.api.v1.endpoints.user_auth import router as user_auth
from app.api.v1.endpoints.user_management import router as user_mgmt

api_router = APIRouter()
api_router.include_router(user_auth)
api_router.include_router(admin_auth)
api_router.include_router(admin_mgmt)
api_router.include_router(user_mgmt)
