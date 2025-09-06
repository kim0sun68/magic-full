"""
마법옷장 공지사항 관련 Pydantic 모델
관리자 전용 공지사항 관리 시스템
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class NoticeBase(BaseModel):
    """공지사항 기본 정보"""
    title: str = Field(..., min_length=2, max_length=200, description="공지사항 제목")
    content: str = Field(..., min_length=10, description="공지사항 내용")
    is_important: bool = Field(False, description="중요 공지 여부")


class NoticeCreate(NoticeBase):
    """공지사항 생성 요청 데이터"""
    pass


class NoticeUpdate(BaseModel):
    """공지사항 수정 요청 데이터"""
    title: Optional[str] = Field(None, min_length=2, max_length=200, description="공지사항 제목")
    content: Optional[str] = Field(None, min_length=10, description="공지사항 내용")
    is_important: Optional[bool] = Field(None, description="중요 공지 여부")


class NoticeResponse(NoticeBase):
    """공지사항 응답 데이터"""
    id: uuid.UUID
    created_by: uuid.UUID
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoticeInDB(NoticeResponse):
    """데이터베이스의 공지사항 정보 (내부용)"""
    pass


class NoticeList(BaseModel):
    """공지사항 목록 응답"""
    items: list[NoticeResponse]
    total: int
    page: int
    per_page: int
    has_next: bool


class NoticeFilter(BaseModel):
    """공지사항 필터링 조건"""
    is_important: Optional[bool] = None
    created_by: Optional[uuid.UUID] = None
    search: Optional[str] = Field(None, max_length=100, description="제목/내용 검색")
    page: int = Field(1, ge=1, description="페이지 번호")
    per_page: int = Field(20, ge=1, le=100, description="페이지당 항목 수")