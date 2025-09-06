"""
마법옷장 회사 관련 Pydantic 모델
도매업체-소매업체 관계 관리 시스템
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid


class CompanyBase(BaseModel):
    """회사 기본 정보"""
    name: str = Field(..., min_length=2, max_length=200, description="업체명")
    business_number: Optional[str] = Field(None, pattern=r"^\d{3}-\d{2}-\d{5}$", description="사업자등록번호")
    company_type: Literal["wholesale", "retail"] = Field(..., description="업체 유형")
    address: Optional[str] = Field(None, max_length=500, description="업체 주소")
    description: Optional[str] = Field(None, max_length=1000, description="업체 소개")


class CompanyCreate(CompanyBase):
    """회사 생성 요청 데이터"""
    user_id: uuid.UUID = Field(..., description="소유자 사용자 ID")


class CompanyUpdate(BaseModel):
    """회사 정보 수정 요청 데이터"""
    name: Optional[str] = Field(None, min_length=2, max_length=200, description="업체명")
    business_number: Optional[str] = Field(None, pattern=r"^\d{3}-\d{2}-\d{5}$", description="사업자등록번호")
    address: Optional[str] = Field(None, max_length=500, description="업체 주소")
    description: Optional[str] = Field(None, max_length=1000, description="업체 소개")


class CompanyResponse(CompanyBase):
    """회사 응답 데이터"""
    id: uuid.UUID
    user_id: uuid.UUID
    status: Literal["active", "inactive", "suspended"] = "active"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyRelationshipBase(BaseModel):
    """회사 관계 기본 정보"""
    wholesale_company_id: uuid.UUID = Field(..., description="도매업체 ID")
    retail_company_id: uuid.UUID = Field(..., description="소매업체 ID")


class CompanyRelationshipCreate(CompanyRelationshipBase):
    """회사 관계 생성 요청 (소매업체가 도매업체에 거래 신청)"""
    pass


class CompanyRelationshipUpdate(BaseModel):
    """회사 관계 상태 업데이트 (도매업체가 승인/거부)"""
    status: Literal["approved", "rejected"] = Field(..., description="승인 상태")
    reason: Optional[str] = Field(None, max_length=500, description="승인/거부 사유")


class CompanyRelationshipResponse(CompanyRelationshipBase):
    """회사 관계 응답 데이터"""
    id: uuid.UUID
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: datetime
    
    # 관계 정보 확장
    wholesale_company: Optional[CompanyResponse] = None
    retail_company: Optional[CompanyResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    """회사 목록 응답"""
    companies: list[CompanyResponse]
    total: int
    page: int
    size: int


class CompanyRelationshipListResponse(BaseModel):
    """회사 관계 목록 응답"""
    relationships: list[CompanyRelationshipResponse]
    total: int
    page: int
    size: int


class CompanySearchFilter(BaseModel):
    """회사 검색 필터"""
    company_type: Optional[Literal["wholesale", "retail"]] = None
    status: Optional[Literal["active", "inactive", "suspended"]] = None
    name: Optional[str] = Field(None, max_length=200, description="업체명으로 검색")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지 크기")


class CompanyPermission(BaseModel):
    """회사 권한 확인"""
    user_id: uuid.UUID
    company_id: uuid.UUID
    action: Literal["read", "write", "delete", "manage"] = Field(..., description="수행하려는 작업")


class CompanyStats(BaseModel):
    """회사 통계 정보"""
    total_products: int = 0
    total_orders: int = 0
    total_relationships: int = 0
    pending_relationships: int = 0
    monthly_revenue: int = 0