"""
JWT 토큰 유틸리티 함수 테스트
TDD 기반 JWT 인증 시스템 단위 테스트
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import uuid

from utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    is_token_expired,
    get_token_payload,
    revoke_token,
    TokenValidationError
)
from models.auth import TokenData
import config


class TestJWTTokenCreation:
    """JWT 토큰 생성 테스트"""
    
    def test_create_access_token_valid_user(self):
        """유효한 사용자로 Access 토큰 생성"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        
        # 토큰이 문자열이고 비어있지 않은지 확인
        assert isinstance(token, str)
        assert len(token) > 0
        
        # JWT 형식 확인 (header.payload.signature)
        assert token.count('.') == 2
        
        # 토큰 디코딩하여 페이로드 확인
        payload = jwt.decode(
            token, 
            config.settings.JWT_SECRET_KEY, 
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        
        assert payload["user_id"] == user_data["user_id"]
        assert payload["email"] == user_data["email"]
        assert payload["role"] == user_data["role"]
        assert payload["company_type"] == user_data["company_type"]
        assert payload["type"] == "access"
        
        # 만료 시간 확인 (15분)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        
        # 14분 50초 ~ 15분 10초 범위 (약간의 오차 허용)
        assert timedelta(minutes=14, seconds=50) <= time_diff <= timedelta(minutes=15, seconds=10)
    
    def test_create_refresh_token_valid_user(self):
        """유효한 사용자로 Refresh 토큰 생성"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "wholesale"
        }
        
        token = create_refresh_token(user_data)
        
        # 토큰이 문자열이고 비어있지 않은지 확인
        assert isinstance(token, str)
        assert len(token) > 0
        
        # 토큰 디코딩하여 페이로드 확인
        payload = jwt.decode(
            token, 
            config.settings.JWT_SECRET_KEY, 
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        
        assert payload["user_id"] == user_data["user_id"]
        assert payload["email"] == user_data["email"]
        assert payload["type"] == "refresh"
        
        # 만료 시간 확인 (30일)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        
        # 29일 23시간 ~ 30일 1시간 범위
        assert timedelta(days=29, hours=23) <= time_diff <= timedelta(days=30, hours=1)
    
    def test_create_token_with_admin_role(self):
        """관리자 권한으로 토큰 생성"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "admin@example.com",
            "role": "admin",
            "company_type": "wholesale"
        }
        
        access_token = create_access_token(user_data)
        payload = jwt.decode(
            access_token, 
            config.settings.JWT_SECRET_KEY, 
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        
        assert payload["role"] == "admin"
    
    def test_create_token_missing_required_fields(self):
        """필수 필드 누락 시 예외 발생"""
        incomplete_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com"
            # role, company_type 누락
        }
        
        with pytest.raises(KeyError):
            create_access_token(incomplete_data)


class TestJWTTokenVerification:
    """JWT 토큰 검증 테스트"""
    
    def test_verify_valid_access_token(self):
        """유효한 Access 토큰 검증"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        token_data = verify_token(token, "access")
        
        assert isinstance(token_data, TokenData)
        assert token_data.user_id == user_data["user_id"]
        assert token_data.email == user_data["email"]
        assert token_data.role == user_data["role"]
        assert token_data.type == "access"
    
    def test_verify_valid_refresh_token(self):
        """유효한 Refresh 토큰 검증"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "wholesale"
        }
        
        token = create_refresh_token(user_data)
        token_data = verify_token(token, "refresh")
        
        assert isinstance(token_data, TokenData)
        assert token_data.user_id == user_data["user_id"]
        assert token_data.type == "refresh"
    
    def test_verify_expired_token(self):
        """만료된 토큰 검증 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        # 만료된 토큰 생성 (과거 시간)
        with patch('utils.jwt_utils.datetime') as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = past_time
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            token = create_access_token(user_data)
        
        with pytest.raises(TokenValidationError, match="토큰이 만료되었습니다"):
            verify_token(token, "access")
    
    def test_verify_invalid_token_format(self):
        """잘못된 형식의 토큰 검증 실패"""
        invalid_token = "invalid.token.format"
        
        with pytest.raises(TokenValidationError, match="잘못된 토큰 형식입니다"):
            verify_token(invalid_token, "access")
    
    def test_verify_token_wrong_type(self):
        """잘못된 토큰 타입 검증 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        
        with pytest.raises(TokenValidationError, match="토큰 타입이 일치하지 않습니다"):
            verify_token(access_token, "refresh")
    
    def test_verify_token_wrong_secret(self):
        """잘못된 시크릿으로 서명된 토큰 검증 실패"""
        # 다른 시크릿으로 토큰 생성
        fake_secret = "fake_secret_key_for_testing"
        payload = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "type": "access",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp())
        }
        
        fake_token = jwt.encode(payload, fake_secret, algorithm="HS256")
        
        with pytest.raises(TokenValidationError, match="토큰 서명이 유효하지 않습니다"):
            verify_token(fake_token, "access")


class TestJWTTokenDecoding:
    """JWT 토큰 디코딩 테스트"""
    
    def test_decode_valid_token(self):
        """유효한 토큰 디코딩"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "admin",
            "company_type": "wholesale"
        }
        
        token = create_access_token(user_data)
        payload = decode_token(token)
        
        assert payload["user_id"] == user_data["user_id"]
        assert payload["email"] == user_data["email"]
        assert payload["role"] == user_data["role"]
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_invalid_token(self):
        """잘못된 토큰 디코딩 실패"""
        invalid_token = "completely.invalid.token"
        
        with pytest.raises(TokenValidationError):
            decode_token(invalid_token)


class TestJWTTokenExpiration:
    """JWT 토큰 만료 확인 테스트"""
    
    def test_is_token_expired_valid_token(self):
        """유효한 토큰의 만료 확인"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        
        assert not is_token_expired(token)
    
    def test_is_token_expired_expired_token(self):
        """만료된 토큰의 만료 확인"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        # 만료된 토큰 생성
        with patch('utils.jwt_utils.datetime') as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = past_time
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            token = create_access_token(user_data)
        
        assert is_token_expired(token)
    
    def test_is_token_expired_invalid_token(self):
        """잘못된 토큰의 만료 확인"""
        invalid_token = "invalid.token.here"
        
        # 잘못된 토큰은 만료된 것으로 처리
        assert is_token_expired(invalid_token)


class TestJWTTokenPayload:
    """JWT 토큰 페이로드 테스트"""
    
    def test_get_token_payload_valid_token(self):
        """유효한 토큰에서 페이로드 추출"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user", 
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        payload = get_token_payload(token)
        
        assert payload is not None
        assert payload["user_id"] == user_data["user_id"]
        assert payload["email"] == user_data["email"]
        assert payload["role"] == user_data["role"]
    
    def test_get_token_payload_invalid_token(self):
        """잘못된 토큰에서 페이로드 추출 실패"""
        invalid_token = "invalid.token.format"
        
        payload = get_token_payload(invalid_token)
        assert payload is None


class TestJWTTokenRevocation:
    """JWT 토큰 폐기 테스트"""
    
    @patch('utils.jwt_utils.redis_client')
    def test_revoke_token_success(self, mock_redis):
        """토큰 폐기 성공"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        
        # Redis 클라이언트 모의 설정
        mock_redis.setex = MagicMock(return_value=True)
        
        result = revoke_token(token)
        
        assert result is True
        mock_redis.setex.assert_called_once()
    
    @patch('utils.jwt_utils.redis_client')
    def test_revoke_invalid_token(self, mock_redis):
        """잘못된 토큰 폐기 실패"""
        invalid_token = "invalid.token.format"
        
        result = revoke_token(invalid_token)
        
        assert result is False
        mock_redis.setex.assert_not_called()


class TestJWTErrorHandling:
    """JWT 오류 처리 테스트"""
    
    def test_token_validation_error_inheritance(self):
        """TokenValidationError 예외 클래스 확인"""
        error = TokenValidationError("테스트 오류")
        
        assert isinstance(error, Exception)
        assert str(error) == "테스트 오류"
    
    def test_verify_token_with_tampered_payload(self):
        """변조된 페이로드를 가진 토큰 검증 실패"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        token = create_access_token(user_data)
        
        # 토큰 변조 (payload 부분 수정)
        header, payload, signature = token.split('.')
        # payload를 base64 디코딩 후 수정하고 다시 인코딩
        import base64
        import json
        
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "==="))
        decoded_payload["role"] = "admin"  # 권한 변조 시도
        
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(decoded_payload).encode()
        ).decode().rstrip('=')
        
        tampered_token = f"{header}.{tampered_payload}.{signature}"
        
        with pytest.raises(TokenValidationError, match="토큰 서명이 유효하지 않습니다"):
            verify_token(tampered_token, "access")


class TestJWTConfigurationValidation:
    """JWT 설정 검증 테스트"""
    
    def test_jwt_secret_key_strength(self):
        """JWT 시크릿 키 강도 확인"""
        secret_key = config.settings.JWT_SECRET_KEY
        
        # 시크릿 키는 최소 32자 이상이어야 함
        assert len(secret_key) >= 32
        
        # 다양한 문자 조합 확인 (보안 강화)
        assert any(c.isupper() for c in secret_key)
        assert any(c.islower() for c in secret_key)
        assert any(c.isdigit() for c in secret_key)
    
    def test_jwt_algorithm_security(self):
        """JWT 알고리즘 보안성 확인"""
        algorithm = config.settings.JWT_ALGORITHM
        
        # HS256 이상의 안전한 알고리즘 사용 확인
        assert algorithm in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        
        # 기본적으로 HS256 사용
        assert algorithm == "HS256"
    
    def test_token_expiration_times(self):
        """토큰 만료 시간 설정 확인"""
        access_expire = config.settings.JWT_ACCESS_EXPIRE_MINUTES
        refresh_expire = config.settings.JWT_REFRESH_EXPIRE_DAYS
        
        # Access 토큰: 5분 ~ 60분 사이
        assert 5 <= access_expire <= 60
        
        # Refresh 토큰: 7일 ~ 90일 사이
        assert 7 <= refresh_expire <= 90


class TestJWTTokenTypes:
    """JWT 토큰 타입별 테스트"""
    
    def test_access_and_refresh_tokens_different(self):
        """Access와 Refresh 토큰이 다른지 확인"""
        user_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_type": "retail"
        }
        
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        # 토큰이 다른지 확인
        assert access_token != refresh_token
        
        # 타입이 다른지 확인
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        
        # 만료 시간이 다른지 확인
        assert access_payload["exp"] != refresh_payload["exp"]