"""
인증 미들웨어 테스트
JWT 기반 라우트 보호 및 권한 확인 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
from datetime import datetime, timezone
from fastapi import Request, HTTPException

from auth.middleware import (
    AuthMiddleware, auth_middleware,
    get_current_user_optional, get_current_user_required,
    get_admin_user_required, get_approved_user_required
)
from utils.jwt_utils import create_access_token, create_refresh_token


def create_mock_request(path: str, auth_header: str = None, cookies: dict = None) -> Request:
    """테스트용 Mock Request 생성"""
    headers = []
    
    if auth_header:
        headers.append((b"authorization", auth_header.encode()))
    
    # 쿠키가 있으면 Cookie 헤더로 변환
    if cookies:
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers.append((b"cookie", cookie_str.encode()))
    
    scope = {
        "type": "http",
        "path": path,
        "headers": headers,
        "query_string": b""
    }
    
    request = Request(scope)
    return request


class TestAuthMiddleware:
    """인증 미들웨어 테스트"""
    
    def test_middleware_initialization(self):
        """미들웨어 초기화 테스트"""
        middleware = AuthMiddleware()
        
        assert isinstance(middleware.excluded_paths, set)
        assert "/health" in middleware.excluded_paths
        assert "/api/auth/login" in middleware.excluded_paths
        assert "/api/auth/register" in middleware.excluded_paths
    
    def test_is_excluded_path(self):
        """경로 제외 확인 테스트"""
        middleware = AuthMiddleware()
        
        # 제외 경로들
        assert middleware._is_excluded_path("/health")
        assert middleware._is_excluded_path("/api/auth/login")
        assert middleware._is_excluded_path("/api/auth/register")
        assert middleware._is_excluded_path("/static/css/style.css")
        assert middleware._is_excluded_path("/docs")
        
        # 보호 경로들
        assert not middleware._is_excluded_path("/api/products")
        assert not middleware._is_excluded_path("/api/orders")
        assert not middleware._is_excluded_path("/api/auth/me")
        assert not middleware._is_excluded_path("/api/auth/logout")
    
    @pytest.mark.asyncio
    @patch('auth.middleware.AuthService.get_user_by_id')
    async def test_authenticate_request_valid_token(self, mock_get_user):
        """유효한 토큰으로 인증 요청"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        mock_user = {
            "id": user_data["user_id"],
            "email": user_data["email"],
            "name": "테스트사용자",
            "role": user_data["role"],
            "approved": True
        }
        mock_get_user.return_value = mock_user
        
        token = create_access_token(user_data)
        request = create_mock_request(
            "/api/products", 
            auth_header=f"Bearer {token}"
        )
        
        result = await auth_middleware.authenticate_request(request)
        
        assert result is not None
        assert result["email"] == user_data["email"]
        assert result["id"] == user_data["user_id"]
    
    @pytest.mark.asyncio
    async def test_authenticate_request_excluded_path(self):
        """제외 경로에 대한 인증 요청"""
        request = create_mock_request("/api/auth/login")
        
        result = await auth_middleware.authenticate_request(request)
        
        # 제외 경로는 None 반환 (인증 불필요)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_request_no_token(self):
        """토큰 없는 인증 요청"""
        request = create_mock_request("/api/products")
        
        result = await auth_middleware.authenticate_request(request)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_request_invalid_token(self):
        """잘못된 토큰으로 인증 요청"""
        request = create_mock_request(
            "/api/products",
            auth_header="Bearer invalid.token.here"
        )
        
        result = await auth_middleware.authenticate_request(request)
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('auth.middleware.AuthService.get_user_by_id')
    async def test_authenticate_request_cookie_token(self, mock_get_user):
        """쿠키 토큰으로 인증 요청"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        mock_user = {
            "id": user_data["user_id"],
            "email": user_data["email"],
            "name": "테스트사용자",
            "role": user_data["role"],
            "approved": True
        }
        mock_get_user.return_value = mock_user
        
        token = create_access_token(user_data)
        request = create_mock_request(
            "/api/products",
            cookies={"access_token": token}
        )
        
        result = await auth_middleware.authenticate_request(request)
        
        assert result is not None
        assert result["email"] == user_data["email"]


class TestAuthDependencies:
    """인증 의존성 함수 테스트"""
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_current_user_optional_success(self, mock_auth):
        """선택적 인증 성공"""
        mock_user = {
            "id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user"
        }
        mock_auth.return_value = mock_user
        
        request = create_mock_request("/api/products")
        result = await get_current_user_optional(request)
        
        assert result == mock_user
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_current_user_optional_no_auth(self, mock_auth):
        """선택적 인증 실패 (예외 없음)"""
        mock_auth.return_value = None
        
        request = create_mock_request("/api/products")
        result = await get_current_user_optional(request)
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_current_user_required_success(self, mock_auth):
        """필수 인증 성공"""
        mock_user = {
            "id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user"
        }
        mock_auth.return_value = mock_user
        
        request = create_mock_request("/api/products")
        result = await get_current_user_required(request)
        
        assert result == mock_user
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_current_user_required_no_auth(self, mock_auth):
        """필수 인증 실패 (401 예외)"""
        mock_auth.return_value = None
        
        request = create_mock_request("/api/products")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_required(request)
        
        assert exc_info.value.status_code == 401
        assert "인증이 필요합니다" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_admin_user_required_success(self, mock_auth):
        """관리자 권한 확인 성공"""
        mock_admin = {
            "id": str(uuid.uuid4()),
            "email": "admin@example.com",
            "role": "admin"
        }
        mock_auth.return_value = mock_admin
        
        request = create_mock_request("/api/admin")
        result = await get_admin_user_required(request)
        
        assert result == mock_admin
        assert result["role"] == "admin"
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_admin_user_required_not_admin(self, mock_auth):
        """관리자 권한 확인 실패 (403 예외)"""
        mock_user = {
            "id": str(uuid.uuid4()),
            "email": "user@example.com",
            "role": "user"  # 일반 사용자
        }
        mock_auth.return_value = mock_user
        
        request = create_mock_request("/api/admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user_required(request)
        
        assert exc_info.value.status_code == 403
        assert "관리자 권한이 필요합니다" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_approved_user_required_success(self, mock_auth):
        """승인된 사용자 확인 성공"""
        mock_approved_user = {
            "id": str(uuid.uuid4()),
            "email": "approved@example.com",
            "role": "user",
            "approved": True
        }
        mock_auth.return_value = mock_approved_user
        
        request = create_mock_request("/api/products")
        result = await get_approved_user_required(request)
        
        assert result == mock_approved_user
        assert result["approved"] is True
    
    @pytest.mark.asyncio
    @patch('auth.middleware.auth_middleware.authenticate_request')
    async def test_get_approved_user_required_not_approved(self, mock_auth):
        """미승인 사용자 확인 실패 (403 예외)"""
        mock_unapproved_user = {
            "id": str(uuid.uuid4()),
            "email": "unapproved@example.com",
            "role": "user",
            "approved": False  # 미승인 상태
        }
        mock_auth.return_value = mock_unapproved_user
        
        request = create_mock_request("/api/products")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_approved_user_required(request)
        
        assert exc_info.value.status_code == 403
        assert "관리자 승인이 필요합니다" in str(exc_info.value.detail)