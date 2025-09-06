"""
마법옷장 인증 모듈
JWT 인증 및 권한 관리
"""

from .middleware import (
    auth_middleware,
    get_current_user_optional,
    get_current_user_required,
    get_admin_user_required,
    get_approved_user_required,
    AuthMiddleware
)

__all__ = [
    "auth_middleware",
    "get_current_user_optional",
    "get_current_user_required", 
    "get_admin_user_required",
    "get_approved_user_required",
    "AuthMiddleware"
]