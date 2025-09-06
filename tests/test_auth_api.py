"""
인증 API 엔드포인트 테스트
TDD 기반 인증 시스템 API 통합 테스트
"""

import pytest
import json
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from main import app
from models.auth import UserCreate, UserLogin, TokenRefresh, PasswordChange
from utils.jwt_utils import create_access_token, create_refresh_token


client = TestClient(app)


class TestUserRegistration:
    """사용자 회원가입 API 테스트"""
    
    def test_register_success(self):
        """회원가입 성공"""
        registration_data = {
            "email": "newuser@example.com",
            "name": "새로운사용자",
            "phone": "010-1234-5678",
            "company_type": "retail",
            "password": "newpassword123",
            "password_confirm": "newpassword123"
        }
        
        with patch('api.auth.create_user') as mock_create_user:
            mock_user = {
                "id": str(uuid.uuid4()),
                "email": registration_data["email"],
                "name": registration_data["name"],
                "role": "user",
                "approved": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            mock_create_user.return_value = mock_user
            
            response = client.post("/api/auth/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "승인 대기 중입니다" in data["message"]
            assert data["user"]["email"] == registration_data["email"]
            assert data["user"]["approved"] is False
    
    def test_register_password_mismatch(self):
        """비밀번호 불일치로 회원가입 실패"""
        registration_data = {
            "email": "test@example.com",
            "name": "테스트사용자",
            "phone": "010-1234-5678",
            "company_type": "wholesale",
            "password": "password123",
            "password_confirm": "different123"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "비밀번호가 일치하지 않습니다" in data["detail"]
    
    def test_register_duplicate_email(self):
        """중복 이메일로 회원가입 실패"""
        registration_data = {
            "email": "existing@example.com",
            "name": "기존사용자",
            "phone": "010-1234-5678",
            "company_type": "retail",
            "password": "password123",
            "password_confirm": "password123"
        }
        
        with patch('api.auth.create_user') as mock_create_user:
            mock_create_user.side_effect = ValueError("이미 존재하는 이메일입니다")
            
            response = client.post("/api/auth/register", json=registration_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "이미 존재하는 이메일입니다" in data["detail"]
    
    def test_register_invalid_phone(self):
        """잘못된 전화번호 형식으로 회원가입 실패"""
        registration_data = {
            "email": "test@example.com",
            "name": "테스트사용자",
            "phone": "123-456-7890",  # 잘못된 형식
            "company_type": "retail",
            "password": "password123",
            "password_confirm": "password123"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """사용자 로그인 API 테스트"""
    
    def test_login_success_approved_user(self):
        """승인된 사용자 로그인 성공"""
        login_data = {
            "email": "approved@example.com",
            "password": "password123"
        }
        
        with patch('api.auth.authenticate_user') as mock_auth:
            mock_user = {
                "id": str(uuid.uuid4()),
                "email": login_data["email"],
                "name": "승인된사용자",
                "role": "user",
                "company_type": "retail",
                "approved": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            mock_auth.return_value = mock_user
            
            response = client.post("/api/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 900  # 15분 = 900초
            assert data["user"]["email"] == login_data["email"]
            
            # 쿠키 설정 확인
            cookies = response.cookies
            assert "access_token" in cookies
            assert "refresh_token" in cookies
    
    def test_login_failed_wrong_password(self):
        """잘못된 비밀번호로 로그인 실패"""
        login_data = {
            "email": "user@example.com",
            "password": "wrongpassword"
        }
        
        with patch('api.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            response = client.post("/api/auth/login", json=login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False
            assert "이메일 또는 비밀번호가 일치하지 않습니다" in data["message"]
    
    def test_login_failed_not_approved_user(self):
        """미승인 사용자 로그인 실패"""
        login_data = {
            "email": "notapproved@example.com",
            "password": "password123"
        }
        
        with patch('api.auth.authenticate_user') as mock_auth:
            mock_user = {
                "id": str(uuid.uuid4()),
                "email": login_data["email"],
                "name": "미승인사용자",
                "role": "user",
                "company_type": "retail",
                "approved": False,  # 미승인 상태
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            mock_auth.return_value = mock_user
            
            response = client.post("/api/auth/login", json=login_data)
            
            assert response.status_code == 403
            data = response.json()
            assert data["success"] is False
            assert "관리자 승인 대기 중입니다" in data["message"]
    
    def test_login_invalid_email_format(self):
        """잘못된 이메일 형식으로 로그인 실패"""
        login_data = {
            "email": "invalid-email-format",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error


class TestTokenRefresh:
    """토큰 갱신 API 테스트"""
    
    def test_refresh_token_success(self):
        """유효한 Refresh 토큰으로 갱신 성공"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        refresh_token = create_refresh_token(user_data)
        
        with patch('api.auth.get_user_by_id') as mock_get_user:
            mock_user = {
                "id": user_data["user_id"],
                "email": user_data["email"],
                "name": "테스트사용자",
                "role": user_data["role"],
                "company_type": user_data["company_type"],
                "approved": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            mock_get_user.return_value = mock_user
            
            response = client.post(
                "/api/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self):
        """잘못된 Refresh 토큰으로 갱신 실패"""
        invalid_refresh_token = "invalid.refresh.token"
        
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": invalid_refresh_token}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "잘못된 토큰입니다" in data["detail"]
    
    def test_refresh_token_expired(self):
        """만료된 Refresh 토큰으로 갱신 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        # 만료된 토큰 생성
        with patch('utils.jwt_utils.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            past_time = datetime.now(timezone.utc) - timedelta(days=31)
            mock_datetime.now.return_value = past_time
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            expired_token = create_refresh_token(user_data)
        
        response = client.post(
            "/api/auth/refresh", 
            json={"refresh_token": expired_token}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "토큰이 만료되었습니다" in data["detail"]


class TestUserLogout:
    """사용자 로그아웃 API 테스트"""
    
    def test_logout_success(self):
        """로그아웃 성공"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        with patch('utils.jwt_utils.revoke_token') as mock_revoke:
            mock_revoke.return_value = True
            
            response = client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "로그아웃되었습니다" in data["message"]
    
    def test_logout_without_token(self):
        """토큰 없이 로그아웃 요청"""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 401
        data = response.json()
        assert "인증이 필요합니다" in data["detail"]


class TestPasswordChange:
    """비밀번호 변경 API 테스트"""
    
    def test_change_password_success(self):
        """비밀번호 변경 성공"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        change_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        
        with patch('api.auth.change_user_password') as mock_change:
            mock_change.return_value = True
            
            response = client.post(
                "/api/auth/change-password",
                json=change_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "비밀번호가 성공적으로 변경되었습니다" in data["message"]
    
    def test_change_password_wrong_current(self):
        """현재 비밀번호 틀림으로 변경 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        change_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        
        with patch('api.auth.change_user_password') as mock_change:
            mock_change.side_effect = ValueError("현재 비밀번호가 일치하지 않습니다")
            
            response = client.post(
                "/api/auth/change-password",
                json=change_data,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "현재 비밀번호가 일치하지 않습니다" in data["detail"]
    
    def test_change_password_new_password_mismatch(self):
        """새 비밀번호 불일치로 변경 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        change_data = {
            "current_password": "currentpassword123",
            "new_password": "newpassword123",
            "new_password_confirm": "different123"
        }
        
        response = client.post(
            "/api/auth/change-password",
            json=change_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 422  # Validation error


class TestPasswordReset:
    """비밀번호 재설정 API 테스트"""
    
    def test_password_reset_request_success(self):
        """비밀번호 재설정 요청 성공"""
        reset_data = {
            "email": "user@example.com"
        }
        
        with patch('api.auth.send_password_reset_email') as mock_send:
            mock_send.return_value = True
            
            response = client.post("/api/auth/password-reset", json=reset_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "재설정 링크를 이메일로 전송했습니다" in data["message"]
    
    def test_password_reset_confirm_success(self):
        """비밀번호 재설정 확인 성공"""
        confirm_data = {
            "token": "valid_reset_token",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        
        with patch('api.auth.reset_user_password') as mock_reset:
            mock_reset.return_value = True
            
            response = client.post("/api/auth/password-reset/confirm", json=confirm_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "비밀번호가 성공적으로 재설정되었습니다" in data["message"]
    
    def test_password_reset_invalid_token(self):
        """잘못된 재설정 토큰으로 실패"""
        confirm_data = {
            "token": "invalid_reset_token",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123"
        }
        
        with patch('api.auth.reset_user_password') as mock_reset:
            mock_reset.side_effect = ValueError("유효하지 않은 재설정 토큰입니다")
            
            response = client.post("/api/auth/password-reset/confirm", json=confirm_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "유효하지 않은 재설정 토큰입니다" in data["detail"]


class TestUserApproval:
    """사용자 승인 API 테스트 (관리자 전용)"""
    
    def test_approve_user_success(self):
        """사용자 승인 성공 (관리자)"""
        admin_data = {
            "user_id": str(uuid.uuid4()),
            "email": "admin@example.com",
            "role": "admin",
            "company_type": "wholesale"
        }
        
        admin_token = create_access_token(admin_data)
        
        approval_data = {
            "user_id": str(uuid.uuid4()),
            "approved": True,
            "reason": "정상적인 업체로 확인됨"
        }
        
        with patch('api.auth.approve_user') as mock_approve:
            mock_user = {
                "id": approval_data["user_id"],
                "email": "pending@example.com",
                "name": "대기중사용자",
                "approved": True,
                "approved_at": datetime.now(timezone.utc)
            }
            mock_approve.return_value = mock_user
            
            response = client.post(
                "/api/auth/approve",
                json=approval_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "사용자가 승인되었습니다" in data["message"]
    
    def test_approve_user_unauthorized(self):
        """일반 사용자가 승인 시도 시 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "user@example.com",
            "role": "user",  # 일반 사용자
            "company_type": "retail"
        }
        
        user_token = create_access_token(user_data)
        
        approval_data = {
            "user_id": str(uuid.uuid4()),
            "approved": True,
            "reason": "승인 시도"
        }
        
        response = client.post(
            "/api/auth/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "관리자 권한이 필요합니다" in data["detail"]


class TestCSRFProtection:
    """CSRF 보호 API 테스트"""
    
    def test_get_csrf_token(self):
        """CSRF 토큰 발급"""
        response = client.get("/api/auth/csrf-token")
        
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0
        
        # CSRF 토큰이 쿠키에도 설정되는지 확인
        assert "csrf_token" in response.cookies
    
    def test_login_with_csrf_protection(self):
        """CSRF 토큰과 함께 로그인"""
        # 먼저 CSRF 토큰 발급
        csrf_response = client.get("/api/auth/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        
        login_data = {
            "email": "user@example.com",
            "password": "password123"
        }
        
        with patch('api.auth.authenticate_user') as mock_auth:
            mock_user = {
                "id": str(uuid.uuid4()),
                "email": login_data["email"],
                "name": "테스트사용자",
                "role": "user",
                "company_type": "retail",
                "approved": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            mock_auth.return_value = mock_user
            
            response = client.post(
                "/api/auth/login",
                json=login_data,
                headers={"X-CSRF-Token": csrf_token},
                cookies={"csrf_token": csrf_token}
            )
            
            assert response.status_code == 200


class TestAuthAPIErrorHandling:
    """인증 API 오류 처리 테스트"""
    
    def test_invalid_json_request(self):
        """잘못된 JSON 형식 요청"""
        response = client.post(
            "/api/auth/login",
            data="invalid json data",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """필수 필드 누락"""
        incomplete_data = {
            "email": "test@example.com"
            # password 누락
        }
        
        response = client.post("/api/auth/login", json=incomplete_data)
        
        assert response.status_code == 422
    
    def test_rate_limiting_simulation(self):
        """Rate Limiting 시뮬레이션"""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        # 여러 번 요청하여 Rate Limit 테스트
        # 실제로는 Nginx에서 처리되지만 API 레벨에서도 확인
        responses = []
        for _ in range(20):  # 20번 연속 요청
            response = client.post("/api/auth/login", json=login_data)
            responses.append(response.status_code)
        
        # 대부분은 401 (인증 실패)이지만 429 (Too Many Requests)가 있을 수 있음
        assert any(status in [401, 429] for status in responses)


class TestAuthMiddleware:
    """인증 미들웨어 테스트"""
    
    def test_protected_route_with_valid_token(self):
        """유효한 토큰으로 보호된 라우트 접근"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        # 보호된 라우트 예시 (나중에 실제 라우트로 교체)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # 라우트가 아직 구현되지 않았으므로 404가 예상됨
        # 인증은 통과해야 함 (401이 아닌 404)
        assert response.status_code == 404
    
    def test_protected_route_without_token(self):
        """토큰 없이 보호된 라우트 접근"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "인증이 필요합니다" in data["detail"]
    
    def test_protected_route_with_expired_token(self):
        """만료된 토큰으로 보호된 라우트 접근"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        # 만료된 토큰 생성
        with patch('utils.jwt_utils.datetime') as mock_datetime:
            from datetime import datetime, timezone, timedelta
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = past_time
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            expired_token = create_access_token(user_data)
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "토큰이 만료되었습니다" in data["detail"]