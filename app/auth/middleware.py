"""
JWT 인증 미들웨어
토큰 기반 라우트 보호 및 권한 확인
"""

from fastapi import Request, HTTPException, status
from typing import Optional, Dict, Any
import logging

from utils.jwt_utils import verify_token, TokenValidationError
from services.auth_service import AuthService


logger = logging.getLogger(__name__)


class AuthMiddleware:
    """인증 미들웨어 클래스"""
    
    def __init__(self):
        self.excluded_paths = {
            "/health", "/health/ready", "/health/db",
            "/api/auth/register", "/api/auth/login", 
            "/api/auth/csrf-token", "/api/auth/password-reset",
            "/api/auth/password-reset/confirm",
            "/static", "/docs", "/redoc", "/openapi.json"
        }
        self.excluded_exact_paths = set()  # 빈 집합 - 홈 경로도 인증 확인
    
    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        요청에서 인증 정보 추출 및 검증
        
        Args:
            request: FastAPI Request 객체
            
        Returns:
            Optional[Dict[str, Any]]: 인증된 사용자 정보 또는 None
        """
        # 제외 경로 확인
        if self._is_excluded_path(request.url.path):
            return None
        
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            # 쿠키에서 토큰 추출 (fallback)
            token = request.cookies.get("access_token")
        
        if not token:
            return None
        
        try:
            # 토큰 검증
            token_data = verify_token(token, "access")
            
            # 사용자 정보 조회
            user = await AuthService.get_user_by_id(token_data.user_id)
            if not user:
                logger.warning(f"Token valid but user not found: {token_data.user_id}")
                return None
            
            return user
            
        except TokenValidationError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
    
    def _is_excluded_path(self, path: str) -> bool:
        """경로가 인증 제외 대상인지 확인"""
        # 정확히 일치하는 경로 확인
        if path in self.excluded_exact_paths:
            return True
            
        # 접두어로 시작하는 경로 확인
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False


# 전역 인증 미들웨어 인스턴스
auth_middleware = AuthMiddleware()


async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """
    현재 사용자 정보 추출 (선택적 인증)
    인증이 실패해도 예외를 발생시키지 않음
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Optional[Dict[str, Any]]: 사용자 정보 또는 None
    """
    return await auth_middleware.authenticate_request(request)


async def get_current_user_required(request: Request) -> Dict[str, Any]:
    """
    현재 사용자 정보 추출 (필수 인증)
    인증이 실패하면 401 예외 발생
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Dict[str, Any]: 인증된 사용자 정보
        
    Raises:
        HTTPException: 인증 실패 시
    """
    user = await auth_middleware.authenticate_request(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def get_admin_user_required(request: Request) -> Dict[str, Any]:
    """
    관리자 사용자 확인 (필수 인증 + 관리자 권한)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Dict[str, Any]: 인증된 관리자 정보
        
    Raises:
        HTTPException: 인증 실패 또는 권한 부족 시
    """
    user = await get_current_user_required(request)
    
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    return user


async def get_approved_user_required(request: Request) -> Dict[str, Any]:
    """
    승인된 사용자 확인 (필수 인증 + 승인 상태)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Dict[str, Any]: 승인된 사용자 정보
        
    Raises:
        HTTPException: 인증 실패 또는 미승인 시
    """
    user = await get_current_user_required(request)
    
    if not user.get("approved", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 승인이 필요합니다"
        )
    
    return user


async def get_wholesale_user_required(request: Request) -> Dict[str, Any]:
    """
    도매업체 사용자 확인 (필수 인증 + 승인 상태 + 도매업체)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Dict[str, Any]: 도매업체 사용자 정보
        
    Raises:
        HTTPException: 인증 실패, 미승인, 또는 도매업체가 아닐 시
    """
    user = await get_approved_user_required(request)
    
    if user.get("company_type") != "wholesale":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="도매업체 권한이 필요합니다"
        )
    
    return user


async def get_retail_user_required(request: Request) -> Dict[str, Any]:
    """
    소매업체 사용자 확인 (필수 인증 + 승인 상태 + 소매업체)
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        Dict[str, Any]: 소매업체 사용자 정보
        
    Raises:
        HTTPException: 인증 실패, 미승인, 또는 소매업체가 아닐 시
    """
    user = await get_approved_user_required(request)
    
    if user.get("company_type") != "retail":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소매업체 권한이 필요합니다"
        )
    
    return user


async def require_company_permission(request: Request, company_id: str, action: str = "read") -> Dict[str, Any]:
    """
    회사별 권한 확인 (회사 소유자만 접근 가능)
    
    Args:
        request: FastAPI Request 객체
        company_id: 접근하려는 회사 ID
        action: 수행하려는 작업 (read, write, delete)
        
    Returns:
        Dict[str, Any]: 권한이 있는 사용자 정보
        
    Raises:
        HTTPException: 권한 부족 시
    """
    user = await get_approved_user_required(request)
    
    # 관리자는 모든 회사에 접근 가능
    if user.get("role") == "admin":
        return user
    
    # 일반 사용자는 자신의 회사만 접근 가능
    from services.company_service import CompanyService
    has_permission = await CompanyService.check_company_permission(
        str(user["id"]), company_id, action
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 회사에 대한 권한이 없습니다"
        )
    
    return user


async def require_trading_relationship(request: Request, wholesale_company_id: str, retail_company_id: str) -> Dict[str, Any]:
    """
    거래 관계 확인 (승인된 거래 관계에서만 접근 가능)
    
    Args:
        request: FastAPI Request 객체
        wholesale_company_id: 도매업체 ID
        retail_company_id: 소매업체 ID
        
    Returns:
        Dict[str, Any]: 거래 관계에 있는 사용자 정보
        
    Raises:
        HTTPException: 거래 관계가 없을 시
    """
    user = await get_approved_user_required(request)
    
    # 관리자는 모든 거래 관계에 접근 가능
    if user.get("role") == "admin":
        return user
    
    # 거래 관계 확인
    from services.company_service import CompanyService
    has_relationship = await CompanyService.check_trading_relationship(
        wholesale_company_id, retail_company_id
    )
    
    if not has_relationship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인된 거래 관계가 필요합니다"
        )
    
    # 사용자가 해당 거래 관계의 당사자인지 확인
    user_company = await CompanyService.get_company_by_user_id(str(user["id"]))
    if not user_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소속 회사를 찾을 수 없습니다"
        )
    
    user_company_id = str(user_company.id)
    if user_company_id != wholesale_company_id and user_company_id != retail_company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 거래 관계의 당사자가 아닙니다"
        )
    
    return user