"""
마법옷장 애플리케이션 설정 관리
환경변수 및 애플리케이션 설정
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional
from datetime import datetime
import os


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    # 애플리케이션 기본 설정
    APP_NAME: str = "마법옷장"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Supabase 설정 (Railway 환경에서 Optional 처리)
    SUPABASE_URL: str = "https://vrsbmygqyfvvuaixibrh.supabase.co"
    SUPABASE_ANON_KEY: str = "temp_key_for_railway"  # Railway에서 실제 키로 덮어쓰기
    SUPABASE_JWT_SECRET: str = "temp_secret_for_railway"
    SUPABASE_SERVICE_ROLE_KEY: str = "temp_service_key_for_railway"
    SUPABASE_PROJECT_ID: str = "vrsbmygqyfvvuaixibrh"
    
    # JWT 토큰 설정 (Railway 환경에서 Optional 처리)
    SESSION_SECRET: str = "temp_session_secret_for_railway_deployment"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        """JWT 토큰 서명용 시크릿 키"""
        return self.SESSION_SECRET
    
    # 쿠키 보안 설정
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = "localhost"
    COOKIE_HTTPONLY: bool = True
    
    # Wasabi Cloud 스토리지 설정 (Railway 환경에서 Optional 처리)
    WASABI_ACCESS_KEY: str = "temp_wasabi_key"
    WASABI_SECRET_KEY: str = "temp_wasabi_secret"  
    WASABI_BUCKET: str = "magic-wardrobe-files"
    WASABI_ENDPOINT: str = "https://s3.ap-northeast-1.wasabisys.com"
    WASABI_REGION: str = "ap-northeast-1"
    
    # 파일 업로드 제한
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "jpg,jpeg,png,gif,webp"
    
    # Rate Limiting 설정
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE: int = 10
    
    # 이메일 설정 (선택사항)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    
    # 관리자 초기 계정
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_NAME: str = "관리자"
    
    # CORS 설정
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    CORS_ORIGINS: List[str] = ["http://localhost", "http://127.0.0.1"]
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    def __post_init__(self):
        """Railway 프로덕션 환경에서 필수 환경변수 확인"""
        if self.ENVIRONMENT == "production":
            # Railway에서 실제 환경변수가 설정되지 않은 경우 경고
            temp_values = [
                "temp_key_for_railway",
                "temp_secret_for_railway", 
                "temp_service_key_for_railway",
                "temp_session_secret_for_railway_deployment",
                "temp_wasabi_key",
                "temp_wasabi_secret"
            ]
            
            current_values = [
                self.SUPABASE_ANON_KEY,
                self.SUPABASE_JWT_SECRET,
                self.SUPABASE_SERVICE_ROLE_KEY, 
                self.SESSION_SECRET,
                self.WASABI_ACCESS_KEY,
                self.WASABI_SECRET_KEY
            ]
            
            if any(val in temp_values for val in current_values):
                import logging
                logging.warning("🚨 Production mode with temporary values detected. Set proper environment variables in Railway dashboard.")
    
    def get_allowed_image_types(self) -> List[str]:
        """허용된 이미지 타입 리스트 반환"""
        return [t.strip().lower() for t in self.ALLOWED_IMAGE_TYPES.split(",")]
    
    def get_max_file_size_bytes(self) -> int:
        """최대 파일 크기를 바이트로 반환"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    def get_current_time(self) -> str:
        """현재 시간을 ISO 형식으로 반환"""
        return datetime.utcnow().isoformat()
    
    def is_production(self) -> bool:
        """프로덕션 환경 여부 확인"""
        return not self.DEBUG
    
    def get_supabase_config(self) -> dict:
        """Supabase 연결 설정 반환"""
        return {
            "url": self.SUPABASE_URL,
            "key": self.SUPABASE_SERVICE_ROLE_KEY,
            "anon_key": self.SUPABASE_ANON_KEY,
            "jwt_secret": self.SUPABASE_JWT_SECRET
        }
    
    def get_wasabi_config(self) -> dict:
        """Wasabi 설정 반환"""
        return {
            "access_key": self.WASABI_ACCESS_KEY,
            "secret_key": self.WASABI_SECRET_KEY,
            "bucket": self.WASABI_BUCKET,
            "endpoint": self.WASABI_ENDPOINT,
            "region": self.WASABI_REGION
        }


# 전역 설정 인스턴스
settings = Settings()

# 로깅 설정
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "magic-wardrobe", "message": "%(message)s", "module": "%(name)s"}',
        },
    },
    "handlers": {
        "default": {
            "formatter": "json" if settings.is_production() else "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": settings.LOG_LEVEL,
        "handlers": ["default"],
    },
}