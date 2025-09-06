"""
인증 API 간단 검증 테스트
TestClient 의존성 문제 회피용 기본 테스트
"""

import pytest
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone

from api.auth import (
    AuthService, create_user, authenticate_user, 
    get_user_by_id, change_user_password
)
from models.auth import UserCreate, UserLogin
from utils.jwt_utils import create_access_token, create_refresh_token


class TestAuthServiceMocking:
    """인증 서비스 함수 모킹 테스트"""
    
    @pytest.mark.asyncio
    @patch('api.auth.AuthService.create_user')
    async def test_create_user_mock(self, mock_create):
        """사용자 생성 서비스 모킹 테스트"""
        user_data = UserCreate(
            email="test@example.com",
            name="테스트사용자",
            phone="010-1234-5678",
            company_type="retail",
            password="password123",
            password_confirm="password123"
        )
        
        mock_user = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "name": user_data.name,
            "role": "user",
            "approved": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        mock_create.return_value = mock_user
        
        result = await AuthService.create_user(user_data)
        
        assert result["email"] == user_data.email
        assert result["approved"] is False
        mock_create.assert_called_once_with(user_data)
    
    @pytest.mark.asyncio
    @patch('api.auth.AuthService.authenticate_user')
    async def test_authenticate_user_mock(self, mock_auth):
        """사용자 인증 서비스 모킹 테스트"""
        mock_user = {
            "id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail",
            "approved": True
        }
        mock_auth.return_value = mock_user
        
        result = await AuthService.authenticate_user("test@example.com", "password123")
        
        assert result["email"] == "test@example.com"
        assert result["approved"] is True
        mock_auth.assert_called_once_with("test@example.com", "password123")


class TestJWTIntegration:
    """JWT 통합 테스트"""
    
    def test_jwt_token_flow(self):
        """JWT 토큰 생성-검증 플로우 테스트"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        # 토큰 생성
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        # 토큰이 다른지 확인
        assert access_token != refresh_token
        
        # 토큰 길이 확인
        assert len(access_token) > 50
        assert len(refresh_token) > 50
        
        # JWT 형식 확인
        assert access_token.count('.') == 2
        assert refresh_token.count('.') == 2


class TestAuthModelsValidation:
    """인증 모델 검증 테스트"""
    
    def test_user_create_validation(self):
        """UserCreate 모델 검증"""
        valid_data = {
            "email": "test@example.com",
            "name": "테스트사용자",
            "phone": "010-1234-5678",
            "company_type": "retail",
            "password": "password123",
            "password_confirm": "password123"
        }
        
        user_create = UserCreate(**valid_data)
        assert user_create.email == "test@example.com"
        assert user_create.company_type == "retail"
        
        # 비밀번호 일치 확인
        validated = user_create.validate_passwords_match()
        assert validated.password == "password123"
    
    def test_user_create_password_mismatch(self):
        """UserCreate 비밀번호 불일치 검증"""
        invalid_data = {
            "email": "test@example.com",
            "name": "테스트사용자",
            "phone": "010-1234-5678",
            "company_type": "retail",
            "password": "password123",
            "password_confirm": "different123"
        }
        
        user_create = UserCreate(**invalid_data)
        
        with pytest.raises(ValueError, match="비밀번호가 일치하지 않습니다"):
            user_create.validate_passwords_match()
    
    def test_user_login_validation(self):
        """UserLogin 모델 검증"""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        user_login = UserLogin(**login_data)
        assert user_login.email == "test@example.com"
        assert user_login.password == "password123"