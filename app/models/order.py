"""
마법옷장 주문 관련 Pydantic 모델
도매업체-소매업체 간 주문 관리 시스템
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Literal
from datetime import datetime
import uuid


class OrderItemBase(BaseModel):
    """주문 상품 기본 정보"""
    product_id: uuid.UUID = Field(..., description="상품 ID")
    quantity: int = Field(..., gt=0, description="주문 수량")
    unit_price: int = Field(..., gt=0, description="단가 (원)")


class OrderItemCreate(OrderItemBase):
    """주문 상품 생성 요청"""
    pass


class OrderItemResponse(OrderItemBase):
    """주문 상품 응답 데이터"""
    id: uuid.UUID
    order_id: uuid.UUID
    total_price: int = Field(..., description="총 가격 (수량 × 단가)")
    created_at: datetime
    
    # 관계 정보 (조인 시 포함)
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    """주문 기본 정보"""
    wholesale_company_id: uuid.UUID = Field(..., description="도매업체 ID")
    retail_company_id: uuid.UUID = Field(..., description="소매업체 ID")
    notes: Optional[str] = Field(None, max_length=1000, description="주문 메모")


class OrderCreate(BaseModel):
    """주문 생성 요청"""
    wholesale_company_id: uuid.UUID = Field(..., description="도매업체 ID")
    notes: Optional[str] = Field(None, max_length=1000, description="주문 메모")
    items: List[OrderItemCreate] = Field(..., min_items=1, description="주문 상품 목록")
    
    @validator('items')
    def validate_items(cls, v):
        """주문 상품 검증"""
        if not v:
            raise ValueError("최소 1개 이상의 상품이 필요합니다")
        
        # 중복 상품 체크
        product_ids = [item.product_id for item in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("중복된 상품은 주문할 수 없습니다")
        
        return v


class OrderUpdate(BaseModel):
    """주문 수정 요청"""
    status: Optional[Literal["pending", "confirmed", "preparing", "shipped", "delivered", "cancelled"]] = None
    notes: Optional[str] = Field(None, max_length=1000)


class OrderStatusUpdate(BaseModel):
    """주문 상태 변경 요청"""
    status: Literal["confirmed", "preparing", "shipped", "delivered", "cancelled"] = Field(..., description="변경할 상태")
    notes: Optional[str] = Field(None, max_length=500, description="상태 변경 사유")


class OrderResponse(OrderBase):
    """주문 응답 데이터"""
    id: uuid.UUID
    order_number: str = Field(..., description="주문 번호")
    status: Literal["pending", "confirmed", "preparing", "shipped", "delivered", "cancelled"] = Field(..., description="주문 상태")
    total_amount: int = Field(..., description="총 주문 금액 (원)")
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    # 관계 정보 (조인 시 포함)
    wholesale_company_name: Optional[str] = None
    retail_company_name: Optional[str] = None
    created_by_name: Optional[str] = None
    items: List[OrderItemResponse] = Field(default_factory=list, description="주문 상품 목록")
    
    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """주문 목록 응답"""
    orders: List[OrderResponse]
    total: int
    page: int
    size: int
    has_next: bool


class OrderSearchFilter(BaseModel):
    """주문 검색 필터"""
    status: Optional[Literal["pending", "confirmed", "preparing", "shipped", "delivered", "cancelled"]] = None
    wholesale_company_id: Optional[uuid.UUID] = None
    retail_company_id: Optional[uuid.UUID] = None
    order_number: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = Field(None, description="주문 시작 날짜")
    end_date: Optional[datetime] = Field(None, description="주문 종료 날짜")
    min_amount: Optional[int] = Field(None, ge=0, description="최소 주문 금액")
    max_amount: Optional[int] = Field(None, ge=0, description="최대 주문 금액")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지 크기")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """날짜 범위 검증"""
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v < values['start_date']:
                raise ValueError("종료 날짜는 시작 날짜보다 늦어야 합니다")
        return v
    
    @validator('max_amount')
    def validate_amount_range(cls, v, values):
        """금액 범위 검증"""
        if v is not None and 'min_amount' in values and values['min_amount'] is not None:
            if v < values['min_amount']:
                raise ValueError("최대 금액은 최소 금액보다 높아야 합니다")
        return v


class OrderStats(BaseModel):
    """주문 통계"""
    total_orders: int = Field(..., description="총 주문 수")
    pending_orders: int = Field(..., description="대기 주문 수")
    confirmed_orders: int = Field(..., description="확인 주문 수")
    shipped_orders: int = Field(..., description="배송 주문 수")
    delivered_orders: int = Field(..., description="완료 주문 수")
    cancelled_orders: int = Field(..., description="취소 주문 수")
    total_amount: int = Field(..., description="총 주문 금액 (원)")
    average_order_value: int = Field(..., description="평균 주문 금액 (원)")


class QuickOrderItem(BaseModel):
    """빠른 주문 상품"""
    product_code: str = Field(..., description="상품 코드")
    quantity: int = Field(..., gt=0, description="주문 수량")


class QuickOrderCreate(BaseModel):
    """빠른 주문 생성 (코드 기반)"""
    wholesale_company_id: uuid.UUID = Field(..., description="도매업체 ID")
    items: List[QuickOrderItem] = Field(..., min_items=1, description="주문 상품 목록")
    notes: Optional[str] = Field(None, max_length=1000, description="주문 메모")
    
    @validator('items')
    def validate_quick_items(cls, v):
        """빠른 주문 상품 검증"""
        if not v:
            raise ValueError("최소 1개 이상의 상품이 필요합니다")
        
        # 중복 상품 코드 체크
        product_codes = [item.product_code for item in v]
        if len(product_codes) != len(set(product_codes)):
            raise ValueError("중복된 상품 코드는 주문할 수 없습니다")
        
        return v


class OrderItemUpdate(BaseModel):
    """주문 상품 수정 요청"""
    quantity: Optional[int] = Field(None, gt=0, description="수량 수정")
    
    
class BulkOrderOperation(BaseModel):
    """주문 일괄 처리"""
    order_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50, description="처리할 주문 ID 목록")
    status: Literal["confirmed", "cancelled"] = Field(..., description="일괄 변경할 상태")
    notes: Optional[str] = Field(None, max_length=500, description="일괄 처리 사유")