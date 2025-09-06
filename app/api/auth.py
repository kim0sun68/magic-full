"""
인증 API 라우터
JWT 기반 인증 시스템 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import uuid
from datetime import datetime, timezone, timedelta

from models.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh,
    PasswordChange, PasswordReset, PasswordResetConfirm, UserApproval,
    CSRFToken, AuthResponse
)
from utils.jwt_utils import (
    create_access_token, create_refresh_token, verify_token, 
    revoke_token, TokenValidationError
)
from services.auth_service import AuthService
from auth.middleware import (
    get_current_user_required, get_admin_user_required
)
import config


router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)
# AuthService는 app.services.auth_service에서 가져옴


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """인증 쿠키 설정"""
    # Access 토큰 쿠키 (15분)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=config.settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        httponly=config.settings.COOKIE_HTTPONLY,
        secure=config.settings.COOKIE_SECURE,
        samesite=config.settings.COOKIE_SAMESITE,
        domain=config.settings.COOKIE_DOMAIN if config.settings.COOKIE_DOMAIN != "localhost" else None
    )
    
    # Refresh 토큰 쿠키 (30일)
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token,
        max_age=config.settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=config.settings.COOKIE_HTTPONLY,
        secure=config.settings.COOKIE_SECURE,
        samesite=config.settings.COOKIE_SAMESITE,
        domain=config.settings.COOKIE_DOMAIN if config.settings.COOKIE_DOMAIN != "localhost" else None
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, response: Response):
    """사용자 회원가입"""
    try:
        # 비밀번호 일치 확인
        user_data.validate_passwords_match()
        
        # 사용자 생성
        new_user = await AuthService.create_user(user_data)
        
        return AuthResponse(
            success=True,
            message="회원가입이 완료되었습니다. 관리자 승인 대기 중입니다.",
            user=UserResponse(**new_user)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, response: Response):
    """사용자 로그인"""
    try:
        # 사용자 인증
        user = await AuthService.authenticate_user(
            user_credentials.email, 
            user_credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 일치하지 않습니다"
            )
        
        # 승인 여부 확인
        if not user.get("approved", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 승인 대기 중입니다"
            )
        
        # 토큰 생성
        token_data = {
            "user_id": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
            "company_type": user["company_type"]
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # 쿠키 설정
        set_auth_cookies(response, access_token, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=config.settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh, response: Response):
    """토큰 갱신"""
    try:
        # Refresh 토큰 검증
        verified_token = verify_token(token_data.refresh_token, "refresh")
        
        # 사용자 정보 조회
        user = await AuthService.get_user_by_id(verified_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 새 토큰 생성
        new_token_data = {
            "user_id": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
            "company_type": user["company_type"]
        }
        
        new_access_token = create_access_token(new_token_data)
        new_refresh_token = create_refresh_token(new_token_data)
        
        # 기존 Refresh 토큰 폐기
        revoke_token(token_data.refresh_token)
        
        # 새 쿠키 설정
        set_auth_cookies(response, new_access_token, new_refresh_token)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=config.settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            user=UserResponse(**user)
        )
        
    except TokenValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", response_model=AuthResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user_required)
):
    """사용자 로그아웃"""
    try:
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")
        
        # 토큰 폐기
        if token:
            revoke_token(token)
        
        # 쿠키 삭제
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return AuthResponse(
            success=True,
            message="로그아웃되었습니다"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그아웃 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user_required)
):
    """비밀번호 변경"""
    try:
        # 새 비밀번호 일치 확인
        password_data.validate_passwords_match()
        
        # 비밀번호 변경
        success = await AuthService.change_user_password(
            str(current_user["id"]),
            password_data.current_password,
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 일치하지 않습니다"
            )
        
        return AuthResponse(
            success=True,
            message="비밀번호가 성공적으로 변경되었습니다"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/password-reset", response_model=AuthResponse)
async def request_password_reset(reset_data: PasswordReset):
    """비밀번호 재설정 요청"""
    try:
        # 이메일 전송
        success = await AuthService.send_password_reset_email(reset_data.email)
        
        if success:
            return AuthResponse(
                success=True,
                message="재설정 링크를 이메일로 전송했습니다"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 전송에 실패했습니다"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"비밀번호 재설정 요청 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/password-reset/confirm", response_model=AuthResponse)
async def confirm_password_reset(confirm_data: PasswordResetConfirm):
    """비밀번호 재설정 확인"""
    try:
        # 비밀번호 일치 확인
        confirm_data.validate_passwords_match()
        
        # 비밀번호 재설정
        success = await AuthService.reset_user_password(
            confirm_data.token,
            confirm_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 재설정 토큰입니다"
            )
        
        return AuthResponse(
            success=True,
            message="비밀번호가 성공적으로 재설정되었습니다"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/approve", response_model=AuthResponse)
async def approve_user(
    approval_data: UserApproval,
    admin_user: dict = Depends(get_admin_user_required)
):
    """사용자 승인/거부 (관리자 전용)"""
    try:
        # 사용자 승인 처리
        approved_user = await AuthService.approve_user(
            str(approval_data.user_id),
            approval_data.approved,
            approval_data.reason
        )
        
        action = "승인" if approval_data.approved else "거부"
        return AuthResponse(
            success=True,
            message=f"사용자가 {action}되었습니다",
            user=UserResponse(**approved_user)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 승인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/csrf-token", response_model=CSRFToken)
async def get_csrf_token(response: Response):
    """CSRF 토큰 발급"""
    import secrets
    
    csrf_token = secrets.token_urlsafe(32)
    
    # CSRF 토큰을 쿠키에 설정
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=3600,  # 1시간
        httponly=False,  # JavaScript에서 접근 가능해야 함
        secure=config.settings.COOKIE_SECURE,
        samesite=config.settings.COOKIE_SAMESITE,
        domain=config.settings.COOKIE_DOMAIN if config.settings.COOKIE_DOMAIN != "localhost" else None
    )
    
    return CSRFToken(csrf_token=csrf_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user_required)):
    """현재 사용자 정보 조회"""
    return UserResponse(**current_user)


# 서비스 함수들을 모듈 레벨로 노출 (테스트에서 사용)
create_user = AuthService.create_user
authenticate_user = AuthService.authenticate_user
get_user_by_id = AuthService.get_user_by_id
change_user_password = AuthService.change_user_password
send_password_reset_email = AuthService.send_password_reset_email
reset_user_password = AuthService.reset_user_password
approve_user = AuthService.approve_user