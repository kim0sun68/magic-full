"""
마법옷장 인증 관련 Pydantic 모델
JWT 토큰 기반 인증 시스템
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """사용자 기본 정보"""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=50, description="사용자 이름")
    phone: Optional[str] = Field(None, pattern=r"^(01[016789]|02|0[3-6][1-9])-?\d{3,4}-?\d{4}$", description="연락처")
    company_type: Literal["wholesale", "retail"] = Field(..., description="업체 유형")


class UserCreate(UserBase):
    """회원가입 요청 데이터"""
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호")
    password_confirm: str = Field(..., description="비밀번호 확인")
    company_name: str = Field(..., min_length=2, max_length=200, description="업체명")
    business_number: str = Field(..., pattern=r"^\d{3}-\d{2}-\d{5}$", description="사업자등록번호")
    address: str = Field(..., min_length=5, max_length=500, description="업체 주소")
    
    def validate_passwords_match(self) -> "UserCreate":
        """비밀번호 일치 확인"""
        if self.password != self.password_confirm:
            raise ValueError("비밀번호가 일치하지 않습니다")
        return self


class UserLogin(BaseModel):
    """로그인 요청 데이터"""
    email: EmailStr
    password: str = Field(..., min_length=1, description="비밀번호")


class UserResponse(UserBase):
    """사용자 응답 데이터 (비밀번호 제외)"""
    id: uuid.UUID
    role: Literal["admin", "user"] = "user"
    approved: bool = False
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """데이터베이스의 사용자 정보 (내부용)"""
    password_hash: str
    approved_by: Optional[uuid.UUID] = None


class TokenData(BaseModel):
    """JWT 토큰 페이로드 데이터"""
    user_id: str
    email: str
    role: str
    company_type: str
    exp: int
    iat: int
    type: Literal["access", "refresh"]


class TokenResponse(BaseModel):
    """인증 성공 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access 토큰 만료 시간(초)")
    user: UserResponse


class TokenRefresh(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str


class AuthResponse(BaseModel):
    """인증 응답 (성공/실패)"""
    success: bool
    message: str
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None


class PasswordChange(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str = Field(..., min_length=1, description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호")
    new_password_confirm: str = Field(..., description="새 비밀번호 확인")
    
    def validate_passwords_match(self) -> "PasswordChange":
        """새 비밀번호 일치 확인"""
        if self.new_password != self.new_password_confirm:
            raise ValueError("새 비밀번호가 일치하지 않습니다")
        return self


class PasswordReset(BaseModel):
    """비밀번호 재설정 요청"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인"""
    token: str = Field(..., description="재설정 토큰")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호")
    new_password_confirm: str = Field(..., description="새 비밀번호 확인")
    
    def validate_passwords_match(self) -> "PasswordResetConfirm":
        """비밀번호 일치 확인"""
        if self.new_password != self.new_password_confirm:
            raise ValueError("비밀번호가 일치하지 않습니다")
        return self


class CSRFToken(BaseModel):
    """CSRF 토큰 응답"""
    csrf_token: str


class UserApproval(BaseModel):
    """사용자 승인 처리 (관리자용)"""
    user_id: uuid.UUID
    approved: bool
    reason: Optional[str] = Field(None, max_length=500, description="승인/거부 사유")


class UserUpdate(BaseModel):
    """사용자 정보 수정"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None, pattern=r"^(01[016789]|02|0[3-6][1-9])-?\d{3,4}-?\d{4}$")
    
    
class LoginHistory(BaseModel):
    """로그인 기록"""
    id: uuid.UUID
    user_id: uuid.UUID
    login_at: datetime
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """관리자용 사용자 상세 정보 (users + companies 조인)"""
    # 사용자 기본 정보
    id: uuid.UUID
    email: EmailStr
    name: str
    phone: Optional[str] = None
    role: Literal["admin", "user"] = "user"
    approved: bool = False
    approved_at: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    
    # 회사 정보
    company_id: Optional[uuid.UUID] = None
    company_name: Optional[str] = None
    business_number: Optional[str] = None
    company_type: Optional[Literal["wholesale", "retail"]] = None
    company_address: Optional[str] = None
    company_description: Optional[str] = None
    company_status: Optional[Literal["active", "inactive", "suspended"]] = None
    company_created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)