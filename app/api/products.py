"""
상품 관리 API 엔드포인트
상품, 카테고리, 재고 관리 시스템
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging

from auth.middleware import get_current_user_required
from models.auth import UserResponse
from models.product import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    ProductSearchFilter, InventoryResponse, InventoryUpdate,
    InventoryTransactionResponse, StockAdjustment, StockIn
)
from services.product_service import ProductService
from services.inventory_service import InventoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


# 카테고리 관리 엔드포인트
@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_user_required)
) -> CategoryResponse:
    """카테고리 생성 (관리자만 가능)"""
    try:
        # 관리자 권한 확인
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="카테고리는 관리자만 생성할 수 있습니다"
            )
        
        category = await ProductService.create_category(category_data)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="카테고리 생성에 실패했습니다"
            )
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"카테고리 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 생성에 실패했습니다"
        )


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    current_user: dict = Depends(get_current_user_required)
) -> List[CategoryResponse]:
    """카테고리 목록 조회"""
    try:
        categories = await ProductService.get_categories()
        return categories
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 목록 조회에 실패했습니다"
        )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> CategoryResponse:
    """카테고리 수정 (관리자만 가능)"""
    try:
        # 관리자 권한 확인
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="카테고리는 관리자만 수정할 수 있습니다"
            )
        
        category = await ProductService.update_category(category_id, category_data)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="카테고리를 찾을 수 없습니다"
            )
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"카테고리 수정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 수정에 실패했습니다"
        )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """카테고리 삭제 (관리자만 가능)"""
    try:
        # 관리자 권한 확인
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="카테고리는 관리자만 삭제할 수 있습니다"
            )
        
        success = await ProductService.delete_category(category_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="카테고리를 찾을 수 없습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"카테고리 삭제 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 삭제에 실패했습니다"
        )


# 상품 관리 엔드포인트
@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_user_required)
) -> ProductResponse:
    """상품 생성 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="상품은 도매업체만 생성할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        product = await ProductService.create_product(product_data, str(company.id))
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="상품 생성에 실패했습니다"
            )
        
        return product
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"상품 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 생성에 실패했습니다"
        )


@router.get("", response_model=ProductListResponse)
async def get_products(
    name: Optional[str] = Query(None, max_length=200, description="상품명 검색"),
    category_id: Optional[str] = Query(None, description="카테고리 필터"),
    age_group: Optional[str] = Query(None, regex="^(0-12m|1-2y|3-5y|6-10y)$", description="연령대 필터"),
    gender: Optional[str] = Query(None, regex="^(unisex|boys|girls)$", description="성별 필터"),
    min_price: Optional[int] = Query(None, ge=0, description="최소 가격"),
    max_price: Optional[int] = Query(None, ge=0, description="최대 가격"),
    is_active: Optional[bool] = Query(None, description="활성 상품만"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user: dict = Depends(get_current_user_required)
) -> ProductListResponse:
    """상품 목록 조회 (회사 유형별 접근 제어)"""
    try:
        search_filter = ProductSearchFilter(
            name=name,
            category_id=category_id,
            age_group=age_group,
            gender=gender,
            min_price=min_price,
            max_price=max_price,
            is_active=is_active,
            company_type=current_user.get("company_type"),
            page=page,
            size=size
        )
        
        # 회사 유형에 따른 상품 조회
        if current_user.get("company_type") == "wholesale":
            # 도매업체: 자신의 상품만 조회
            from services.company_service import CompanyService
            company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="소속 회사를 찾을 수 없습니다"
                )
            
            products = await ProductService.get_company_products(str(company.id), search_filter)
            
        elif current_user.get("company_type") == "retail":
            # 소매업체: 승인된 거래 관계의 도매업체 상품만 조회
            from services.company_service import CompanyService
            company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="소속 회사를 찾을 수 없습니다"
                )
            
            products = await ProductService.get_available_products_for_retail(str(company.id), search_filter)
            
        else:
            # 관리자: 모든 상품 조회
            products = await ProductService.search_products(search_filter)
        
        return products
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상품 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 목록 조회에 실패했습니다"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_detail(
    product_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> ProductResponse:
    """상품 상세 정보 조회"""
    try:
        product = await ProductService.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        # 접근 권한 확인
        if current_user.get("company_type") == "wholesale":
            # 도매업체: 자신의 상품만 조회 가능
            from services.company_service import CompanyService
            company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not company or str(product.company_id) != str(company.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="상품을 조회할 권한이 없습니다"
                )
        
        elif current_user.get("company_type") == "retail":
            # 소매업체: 승인된 거래 관계의 도매업체 상품만 조회 가능
            from services.company_service import CompanyService
            my_company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not my_company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="소속 회사를 찾을 수 없습니다"
                )
            
            # 거래 관계 확인
            has_relationship = await CompanyService.check_trading_relationship(
                str(product.company_id), str(my_company.id)
            )
            
            if not has_relationship:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="상품을 조회할 권한이 없습니다"
                )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상품 상세 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 정보 조회에 실패했습니다"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> ProductResponse:
    """상품 정보 수정 (도매업체 소유자만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="상품은 도매업체만 수정할 수 있습니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 상품 소유권 검증
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="상품을 수정할 권한이 없습니다"
            )
        
        # 상품 정보 수정
        updated_product = await ProductService.update_product(product_id, product_data, str(company.id))
        
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="상품 수정에 실패했습니다"
            )
        
        return updated_product
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"상품 수정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 수정에 실패했습니다"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """상품 삭제 (비활성화) (도매업체 소유자만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="상품은 도매업체만 삭제할 수 있습니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 상품 소유권 검증
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="상품을 삭제할 권한이 없습니다"
            )
        
        # 상품 삭제 (비활성화)
        success = await ProductService.delete_product(product_id, str(company.id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="상품 삭제에 실패했습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상품 삭제 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 삭제에 실패했습니다"
        )


# 재고 관리 엔드포인트
@router.get("/{product_id}/inventory", response_model=InventoryResponse)
async def get_product_inventory(
    product_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> InventoryResponse:
    """상품 재고 정보 조회"""
    try:
        # 상품 접근 권한 확인 (상품 상세 조회와 동일한 로직)
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        # 접근 권한 확인
        if current_user.get("company_type") == "wholesale":
            from services.company_service import CompanyService
            company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not company or str(product.company_id) != str(company.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="재고 정보를 조회할 권한이 없습니다"
                )
        
        elif current_user.get("company_type") == "retail":
            from services.company_service import CompanyService
            my_company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if not my_company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="소속 회사를 찾을 수 없습니다"
                )
            
            has_relationship = await CompanyService.check_trading_relationship(
                str(product.company_id), str(my_company.id)
            )
            
            if not has_relationship:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="재고 정보를 조회할 권한이 없습니다"
                )
        
        inventory = await InventoryService.get_inventory_by_product_id(product_id)
        
        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="재고 정보를 찾을 수 없습니다"
            )
        
        return inventory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 정보 조회에 실패했습니다"
        )


@router.put("/{product_id}/inventory", response_model=InventoryResponse)
async def update_product_inventory(
    product_id: str,
    inventory_data: InventoryUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> InventoryResponse:
    """상품 재고 정보 수정 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고는 도매업체만 수정할 수 있습니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고를 수정할 권한이 없습니다"
            )
        
        # 재고 정보 수정
        updated_inventory = await InventoryService.update_inventory(product_id, inventory_data)
        
        if not updated_inventory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="재고 수정에 실패했습니다"
            )
        
        return updated_inventory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 수정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 수정에 실패했습니다"
        )


@router.get("/{product_id}/inventory/transactions", response_model=List[InventoryTransactionResponse])
async def get_inventory_transactions(
    product_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_required)
) -> List[InventoryTransactionResponse]:
    """상품 재고 거래내역 조회 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 거래내역은 도매업체만 조회할 수 있습니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        product = await ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 거래내역을 조회할 권한이 없습니다"
            )
        
        transactions = await InventoryService.get_inventory_transactions(product_id, page, size)
        return transactions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 거래내역 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 거래내역 조회에 실패했습니다"
        )


# 카테고리 관리 독립 라우터 (categories 전용)
categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user_required)
) -> List[CategoryResponse]:
    """카테고리 목록 조회"""
    try:
        categories = await ProductService.get_categories()
        return categories
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 목록 조회에 실패했습니다"
        )


# 재고 관리 독립 라우터 (inventory 전용)
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])


@inventory_router.post("/adjust")
async def adjust_stock(
    adjustment_data: StockAdjustment,
    current_user: dict = Depends(get_current_user_required)
):
    """재고 조정 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 조정은 도매업체만 가능합니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        product = await ProductService.get_product_by_id(str(adjustment_data.product_id))
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고를 조정할 권한이 없습니다"
            )
        
        # 재고 조정 실행
        success, error_message = await InventoryService.adjust_stock(
            str(adjustment_data.product_id),
            adjustment_data.adjustment_quantity,
            adjustment_data.reason,
            str(current_user["id"])
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "재고 조정에 실패했습니다"
            )
        
        # 업데이트된 재고 정보 반환
        updated_inventory = await InventoryService.get_inventory_by_product_id(str(adjustment_data.product_id))
        
        return {
            "success": True,
            "message": "재고 조정이 완료되었습니다",
            "new_stock": updated_inventory.current_stock if updated_inventory else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 조정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 조정에 실패했습니다"
        )


@inventory_router.post("/stock-in")
async def stock_in(
    stock_data: StockIn,
    current_user: dict = Depends(get_current_user_required)
):
    """입고 처리 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="입고 처리는 도매업체만 가능합니다"
            )
        
        # 상품 소유권 확인
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        product = await ProductService.get_product_by_id(str(stock_data.product_id))
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상품을 찾을 수 없습니다"
            )
        
        if str(product.company_id) != str(company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="입고 처리할 권한이 없습니다"
            )
        
        # 입고 처리 실행
        success, error_message = await InventoryService.stock_in(
            str(stock_data.product_id),
            stock_data.quantity,
            stock_data.notes,
            str(current_user["id"])
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "입고 처리에 실패했습니다"
            )
        
        # 업데이트된 재고 정보 반환
        updated_inventory = await InventoryService.get_inventory_by_product_id(str(stock_data.product_id))
        
        return {
            "success": True,
            "message": "입고 처리가 완료되었습니다",
            "new_stock": updated_inventory.current_stock if updated_inventory else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"입고 처리 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="입고 처리에 실패했습니다"
        )


@inventory_router.get("/low-stock", response_model=List[InventoryResponse])
async def get_low_stock_products(
    current_user: dict = Depends(get_current_user_required)
) -> List[InventoryResponse]:
    """안전재고 미달 상품 조회 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 현황은 도매업체만 조회할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        low_stock_products = await InventoryService.get_low_stock_products(str(company.id))
        return low_stock_products
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"안전재고 미달 상품 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="안전재고 미달 상품 조회에 실패했습니다"
        )


@inventory_router.get("/overview", response_model=List[InventoryResponse])
async def get_company_inventory_overview(
    current_user: dict = Depends(get_current_user_required)
) -> List[InventoryResponse]:
    """회사 전체 재고 현황 조회 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 현황은 도매업체만 조회할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        inventory_list = await InventoryService.get_company_inventory(str(company.id))
        return inventory_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회사 재고 현황 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회사 재고 현황 조회에 실패했습니다"
        )


@inventory_router.get("/stats")
async def get_inventory_stats(
    current_user: dict = Depends(get_current_user_required)
):
    """재고 통계 조회 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 통계는 도매업체만 조회할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        stats = await InventoryService.get_inventory_stats(str(company.id))
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 통계 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 통계 조회에 실패했습니다"
        )


@inventory_router.get("/transactions", response_model=List[InventoryTransactionResponse])
async def get_all_inventory_transactions(
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_required)
) -> List[InventoryTransactionResponse]:
    """회사 전체 재고 거래내역 조회 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="재고 거래내역은 도매업체만 조회할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        from services.company_service import CompanyService
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        transactions = await InventoryService.get_inventory_transactions(
            company_id=str(company.id), 
            days=days, 
            page=page, 
            size=size
        )
        
        return transactions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 거래내역 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 거래내역 조회에 실패했습니다"
        )


# 카테고리 관리 독립 라우터 (categories 전용)
categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user_required)
) -> List[CategoryResponse]:
    """카테고리 목록 조회"""
    try:
        categories = await ProductService.get_categories()
        return categories
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 목록 조회에 실패했습니다"
        )