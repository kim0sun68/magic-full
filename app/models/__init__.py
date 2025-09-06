"""
마법옷장 데이터 모델 패키지
Pydantic 모델 및 스키마 정의
"""

from .auth import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserInDB,
    TokenData,
    TokenResponse,
    TokenRefresh,
    AuthResponse,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    CSRFToken,
    UserApproval,
    UserUpdate,
    LoginHistory,
)

__all__ = [
    "UserBase",
    "UserCreate", 
    "UserLogin",
    "UserResponse",
    "UserInDB",
    "TokenData",
    "TokenResponse",
    "TokenRefresh",
    "AuthResponse",
    "PasswordChange",
    "PasswordReset",
    "PasswordResetConfirm",
    "CSRFToken",
    "UserApproval",
    "UserUpdate",
    "LoginHistory",
]