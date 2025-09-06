"""
마법옷장 상품 관련 Pydantic 모델
아동복 상품 및 카테고리 관리 시스템
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Literal
from datetime import datetime
import uuid


class CategoryBase(BaseModel):
    """카테고리 기본 정보"""
    name: str = Field(..., min_length=1, max_length=100, description="카테고리명")
    description: Optional[str] = Field(None, max_length=500, description="카테고리 설명")


class CategoryCreate(CategoryBase):
    """카테고리 생성 요청"""
    pass


class CategoryUpdate(BaseModel):
    """카테고리 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CategoryResponse(CategoryBase):
    """카테고리 응답 데이터"""
    id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    """상품 기본 정보"""
    code: str = Field(..., min_length=3, max_length=50, description="상품 코드")
    name: str = Field(..., min_length=2, max_length=200, description="상품명")
    category_id: Optional[uuid.UUID] = Field(None, description="카테고리 ID")
    age_group: Literal["0-12m", "1-2y", "3-5y", "6-10y"] = Field(..., description="연령대")
    gender: Literal["unisex", "boys", "girls"] = Field(..., description="성별 구분")
    wholesale_price: int = Field(..., gt=0, description="도매가격 (원)")
    retail_price: Optional[int] = Field(None, gt=0, description="권장 소매가격 (원)")
    description: Optional[str] = Field(None, max_length=2000, description="상품 설명")
    is_active: bool = Field(True, description="판매 활성화 여부")


class ProductCreate(ProductBase):
    """상품 생성 요청"""
    
    @validator('retail_price')
    def validate_retail_price(cls, v, values):
        """소매가격이 도매가격보다 높은지 확인"""
        if v is not None and 'wholesale_price' in values:
            if v <= values['wholesale_price']:
                raise ValueError("소매가격은 도매가격보다 높아야 합니다")
        return v


class ProductUpdate(BaseModel):
    """상품 수정 요청"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    category_id: Optional[uuid.UUID] = None
    age_group: Optional[Literal["0-12m", "1-2y", "3-5y", "6-10y"]] = None
    gender: Optional[Literal["unisex", "boys", "girls"]] = None
    wholesale_price: Optional[int] = Field(None, gt=0)
    retail_price: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None
    
    @validator('retail_price')
    def validate_retail_price(cls, v, values):
        """소매가격이 도매가격보다 높은지 확인"""
        if v is not None and 'wholesale_price' in values and values['wholesale_price'] is not None:
            if v <= values['wholesale_price']:
                raise ValueError("소매가격은 도매가격보다 높아야 합니다")
        return v


class ProductResponse(ProductBase):
    """상품 응답 데이터"""
    id: uuid.UUID
    company_id: uuid.UUID
    images: List[str] = Field(default_factory=list, description="상품 이미지 URL 목록")
    created_at: datetime
    updated_at: datetime
    
    # 관계 정보 (조인 시 포함)
    category_name: Optional[str] = None
    company_name: Optional[str] = None
    current_stock: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """상품 목록 응답"""
    products: List[ProductResponse]
    total: int
    page: int
    size: int
    has_next: bool


class ProductSearchFilter(BaseModel):
    """상품 검색 필터"""
    name: Optional[str] = Field(None, max_length=200, description="상품명 검색")
    category_id: Optional[uuid.UUID] = Field(None, description="카테고리 필터")
    age_group: Optional[Literal["0-12m", "1-2y", "3-5y", "6-10y"]] = Field(None, description="연령대 필터")
    gender: Optional[Literal["unisex", "boys", "girls"]] = Field(None, description="성별 필터")
    min_price: Optional[int] = Field(None, ge=0, description="최소 가격")
    max_price: Optional[int] = Field(None, ge=0, description="최대 가격")
    is_active: Optional[bool] = Field(None, description="활성 상품만")
    company_type: Optional[Literal["wholesale", "retail"]] = Field(None, description="업체 유형")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지 크기")
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        """가격 범위 검증"""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError("최대 가격은 최소 가격보다 높아야 합니다")
        return v


class InventoryBase(BaseModel):
    """재고 기본 정보"""
    current_stock: int = Field(..., ge=0, description="현재 재고량")
    minimum_stock: int = Field(0, ge=0, description="최소 재고량")


class InventoryUpdate(BaseModel):
    """재고 수정 요청"""
    current_stock: Optional[int] = Field(None, ge=0)
    minimum_stock: Optional[int] = Field(None, ge=0)


class InventoryResponse(InventoryBase):
    """재고 응답 데이터"""
    id: uuid.UUID
    product_id: uuid.UUID
    last_updated: datetime
    
    # 관계 정보
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    is_low_stock: bool = Field(False, description="안전재고 미달 여부")
    
    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionBase(BaseModel):
    """재고 거래내역 기본 정보"""
    product_id: uuid.UUID = Field(..., description="상품 ID")
    transaction_type: Literal["in", "out", "adjustment"] = Field(..., description="거래 유형")
    quantity: int = Field(..., description="수량")
    previous_stock: int = Field(..., ge=0, description="이전 재고량")
    current_stock: int = Field(..., ge=0, description="현재 재고량")
    reference_type: Optional[Literal["order", "adjustment", "initial"]] = Field(None, description="참조 유형")
    reference_id: Optional[uuid.UUID] = Field(None, description="참조 ID")
    notes: Optional[str] = Field(None, max_length=500, description="메모")


class InventoryTransactionCreate(BaseModel):
    """재고 거래내역 생성 요청"""
    product_id: uuid.UUID
    transaction_type: Literal["in", "out", "adjustment"]
    quantity: int = Field(..., ne=0, description="수량 (양수: 입고, 음수: 출고)")
    reference_type: Optional[Literal["order", "adjustment", "initial"]] = None
    reference_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=500)


class InventoryTransactionResponse(InventoryTransactionBase):
    """재고 거래내역 응답 데이터"""
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    
    # 관계 정보
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    created_by_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    """재고 조정 요청"""
    product_id: uuid.UUID = Field(..., description="상품 ID")
    adjustment_quantity: int = Field(..., ne=0, description="조정 수량 (양수: 증가, 음수: 감소)")
    reason: str = Field(..., min_length=2, max_length=500, description="조정 사유")


class StockIn(BaseModel):
    """입고 등록 요청"""
    product_id: uuid.UUID = Field(..., description="상품 ID")
    quantity: int = Field(..., gt=0, description="입고 수량")
    notes: Optional[str] = Field(None, max_length=500, description="입고 메모")


class LowStockAlert(BaseModel):
    """안전재고 알림"""
    product_id: uuid.UUID
    product_name: str
    product_code: str
    current_stock: int
    minimum_stock: int
    shortage: int = Field(..., description="부족 수량")


class InventoryStats(BaseModel):
    """재고 통계"""
    total_products: int = Field(..., description="전체 상품 수")
    active_products: int = Field(..., description="활성 상품 수")
    low_stock_products: int = Field(..., description="안전재고 미달 상품 수")
    out_of_stock_products: int = Field(..., description="품절 상품 수")
    total_inventory_value: int = Field(..., description="총 재고 가치 (원)")


class ProductImage(BaseModel):
    """상품 이미지"""
    url: str = Field(..., description="이미지 URL")
    is_primary: bool = Field(False, description="메인 이미지 여부")
    alt_text: Optional[str] = Field(None, max_length=200, description="이미지 설명")


class ProductImageUpload(BaseModel):
    """상품 이미지 업로드 요청"""
    product_id: uuid.UUID = Field(..., description="상품 ID")
    images: List[ProductImage] = Field(..., max_items=10, description="업로드할 이미지 목록")