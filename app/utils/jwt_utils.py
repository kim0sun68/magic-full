"""
JWT 토큰 유틸리티 함수
JWT 기반 인증 시스템의 핵심 기능
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union
import uuid
from models.auth import TokenData
import config


class TokenValidationError(Exception):
    """JWT 토큰 검증 실패 예외"""
    pass


class MockRedisClient:
    """Redis 클라이언트 모의 구현 (테스트용)"""
    _revoked_tokens = set()
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """토큰을 폐기 목록에 추가"""
        self._revoked_tokens.add(key)
        return True
    
    def get(self, key: str) -> Optional[str]:
        """폐기된 토큰 확인"""
        return "revoked" if key in self._revoked_tokens else None


redis_client = MockRedisClient()


def create_access_token(user_data: Dict[str, Any]) -> str:
    """
    Access 토큰 생성
    
    Args:
        user_data: 사용자 정보 딕셔너리
            - user_id: 사용자 ID
            - email: 이메일
            - role: 역할 (user/admin)
            - company_type: 업체 타입 (wholesale/retail)
    
    Returns:
        str: JWT Access 토큰
        
    Raises:
        KeyError: 필수 필드 누락 시
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=config.settings.JWT_ACCESS_EXPIRE_MINUTES)
    
    payload = {
        "user_id": user_data["user_id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "company_type": user_data["company_type"],
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    
    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM
    )


def create_refresh_token(user_data: Dict[str, Any]) -> str:
    """
    Refresh 토큰 생성
    
    Args:
        user_data: 사용자 정보 딕셔너리
            - user_id: 사용자 ID
            - email: 이메일
            - role: 역할 (user/admin)
            - company_type: 업체 타입 (wholesale/retail)
    
    Returns:
        str: JWT Refresh 토큰
        
    Raises:
        KeyError: 필수 필드 누락 시
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=config.settings.JWT_REFRESH_EXPIRE_DAYS)
    
    payload = {
        "user_id": user_data["user_id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "company_type": user_data["company_type"],
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    
    return jwt.encode(
        payload,
        config.settings.JWT_SECRET_KEY,
        algorithm=config.settings.JWT_ALGORITHM
    )


def verify_token(token: str, expected_type: str) -> TokenData:
    """
    JWT 토큰 검증 및 TokenData 반환
    
    Args:
        token: JWT 토큰 문자열
        expected_type: 예상 토큰 타입 ("access" 또는 "refresh")
    
    Returns:
        TokenData: 검증된 토큰 데이터
        
    Raises:
        TokenValidationError: 토큰 검증 실패 시
    """
    try:
        payload = jwt.decode(
            token,
            config.settings.JWT_SECRET_KEY,
            algorithms=[config.settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise TokenValidationError("토큰이 만료되었습니다")
    except jwt.InvalidSignatureError:
        raise TokenValidationError("토큰 서명이 유효하지 않습니다")
    except jwt.DecodeError:
        raise TokenValidationError("잘못된 토큰 형식입니다")
    except jwt.InvalidTokenError:
        raise TokenValidationError("잘못된 토큰 형식입니다")
    except Exception as e:
        raise TokenValidationError(f"토큰 검증 실패: {str(e)}")
    
    # 토큰 타입 확인
    if payload.get("type") != expected_type:
        raise TokenValidationError("토큰 타입이 일치하지 않습니다")
    
    # 폐기된 토큰 확인
    token_id = f"token:{payload.get('user_id')}:{token}"
    if redis_client.get(token_id):
        raise TokenValidationError("폐기된 토큰입니다")
    
    return TokenData(
        user_id=payload["user_id"],
        email=payload["email"],
        role=payload["role"],
        company_type=payload["company_type"],
        exp=payload["exp"],
        iat=payload["iat"],
        type=payload["type"]
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    JWT 토큰 디코딩 (검증 없이)
    
    Args:
        token: JWT 토큰 문자열
    
    Returns:
        Dict[str, Any]: 토큰 페이로드
        
    Raises:
        TokenValidationError: 디코딩 실패 시
    """
    try:
        payload = jwt.decode(
            token,
            config.settings.JWT_SECRET_KEY,
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        raise TokenValidationError("잘못된 토큰 형식입니다")
    except Exception as e:
        raise TokenValidationError(f"토큰 디코딩 실패: {str(e)}")


def is_token_expired(token: str) -> bool:
    """
    토큰 만료 여부 확인
    
    Args:
        token: JWT 토큰 문자열
    
    Returns:
        bool: 만료되었으면 True, 아니면 False
    """
    try:
        payload = jwt.decode(
            token,
            config.settings.JWT_SECRET_KEY,
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True
            
        exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        return now >= exp_time
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return True
    except Exception:
        return True


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    토큰에서 페이로드 추출 (안전한 버전)
    
    Args:
        token: JWT 토큰 문자열
    
    Returns:
        Optional[Dict[str, Any]]: 페이로드 또는 None (실패 시)
    """
    try:
        payload = jwt.decode(
            token,
            config.settings.JWT_SECRET_KEY,
            algorithms=[config.settings.JWT_ALGORITHM]
        )
        return payload
    except Exception:
        return None


def revoke_token(token: str) -> bool:
    """
    토큰 폐기 처리
    
    Args:
        token: 폐기할 JWT 토큰 문자열
    
    Returns:
        bool: 폐기 성공 여부
    """
    try:
        payload = get_token_payload(token)
        if not payload:
            return False
            
        # 토큰 고유 키 생성
        token_id = f"token:{payload.get('user_id')}:{token}"
        
        # 토큰 만료 시간까지 Redis에 저장
        exp_timestamp = payload.get("exp", 0)
        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        ttl = max(exp_timestamp - now_timestamp, 1)
        
        redis_client.setex(token_id, ttl, "revoked")
        return True
        
    except Exception:
        return False