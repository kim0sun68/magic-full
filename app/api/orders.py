"""
주문 관리 API 엔드포인트
도소매 간 주문 처리 시스템
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging

from auth.middleware import get_current_user_required
from models.auth import UserResponse
from models.order import (
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse,
    OrderSearchFilter, OrderStatusUpdate, QuickOrderCreate,
    OrderItemUpdate, BulkOrderOperation, OrderStats
)
from services.order_service import OrderService
from services.company_service import CompanyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 생성 (소매업체만 가능)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문은 소매업체만 생성할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 주문 생성
        order, error_message = await OrderService.create_order(
            order_data, 
            str(current_user["id"]), 
            str(company.id)
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 생성에 실패했습니다"
            )
        
        return order
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"주문 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 생성에 실패했습니다"
        )


@router.post("/quick", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_quick_order(
    order_data: QuickOrderCreate,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """빠른 주문 생성 (상품 코드 기반, 소매업체만 가능)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문은 소매업체만 생성할 수 있습니다"
            )
        
        # 사용자의 회사 ID 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 빠른 주문 생성
        order, error_message = await OrderService.create_quick_order(
            order_data, 
            str(current_user["id"]), 
            str(company.id)
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "빠른 주문 생성에 실패했습니다"
            )
        
        return order
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"빠른 주문 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="빠른 주문 생성에 실패했습니다"
        )


@router.get("", response_model=OrderListResponse)
async def get_orders(
    status_filter: Optional[str] = Query(None, regex="^(pending|confirmed|preparing|shipped|delivered|cancelled)$"),
    wholesale_company_id: Optional[str] = Query(None, description="도매업체 ID"),
    retail_company_id: Optional[str] = Query(None, description="소매업체 ID"),
    order_number: Optional[str] = Query(None, max_length=50, description="주문 번호"),
    min_amount: Optional[int] = Query(None, ge=0, description="최소 주문 금액"),
    max_amount: Optional[int] = Query(None, ge=0, description="최대 주문 금액"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user: dict = Depends(get_current_user_required)
) -> OrderListResponse:
    """주문 목록 조회 (검색 및 필터링 지원)"""
    try:
        # 사용자의 회사 정보 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 검색 필터 설정
        search_filter = OrderSearchFilter(
            status=status_filter,
            wholesale_company_id=wholesale_company_id,
            retail_company_id=retail_company_id,
            order_number=order_number,
            min_amount=min_amount,
            max_amount=max_amount,
            page=page,
            size=size
        )
        
        # 회사 유형에 따른 주문 조회
        if current_user.get("company_type") == "wholesale":
            # 도매업체: 자신에게 온 주문만 조회
            search_filter.wholesale_company_id = str(company.id)
        elif current_user.get("company_type") == "retail":
            # 소매업체: 자신이 한 주문만 조회
            search_filter.retail_company_id = str(company.id)
        
        orders = await OrderService.get_orders(search_filter, str(company.id), current_user.get("company_type"))
        return orders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 목록 조회에 실패했습니다"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 상세 정보 조회"""
    try:
        order = await OrderService.get_order_by_id(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        # 접근 권한 확인 (주문 당사자만 조회 가능)
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 도매업체 또는 소매업체 당사자인지 확인
        if (str(company.id) != str(order.wholesale_company_id) and 
            str(company.id) != str(order.retail_company_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문을 조회할 권한이 없습니다"
            )
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 상세 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 정보 조회에 실패했습니다"
        )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_data: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 상태 변경 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상태는 도매업체만 변경할 수 있습니다"
            )
        
        # 주문 확인 및 권한 체크
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company or str(company.id) != str(order.wholesale_company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상태를 변경할 권한이 없습니다"
            )
        
        # 주문 상태 업데이트
        updated_order, error_message = await OrderService.update_order_status(
            order_id, 
            status_data, 
            str(current_user["id"])
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 상태 변경에 실패했습니다"
            )
        
        return updated_order
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"주문 상태 변경 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 상태 변경에 실패했습니다"
        )


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 정보 수정 (소매업체만 가능, pending 상태만)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문은 소매업체만 수정할 수 있습니다"
            )
        
        # 주문 확인 및 권한 체크
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company or str(company.id) != str(order.retail_company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문을 수정할 권한이 없습니다"
            )
        
        # pending 상태만 수정 가능
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대기 중인 주문만 수정할 수 있습니다"
            )
        
        # 주문 정보 수정
        updated_order, error_message = await OrderService.update_order(order_id, order_data)
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message or "주문 수정에 실패했습니다"
            )
        
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 수정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 수정에 실패했습니다"
        )


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """주문 취소 (소매업체만 가능, pending 상태만)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문은 소매업체만 취소할 수 있습니다"
            )
        
        # 주문 확인 및 권한 체크
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company or str(company.id) != str(order.retail_company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문을 취소할 권한이 없습니다"
            )
        
        # pending 상태만 취소 가능
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대기 중인 주문만 취소할 수 있습니다"
            )
        
        # 주문 취소 처리
        success, error_message = await OrderService.cancel_order(order_id, str(current_user["id"]))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 취소에 실패했습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 취소 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 취소에 실패했습니다"
        )


@router.put("/{order_id}/items/{item_id}", response_model=OrderResponse)
async def update_order_item(
    order_id: str,
    item_id: str,
    item_data: OrderItemUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 상품 수정 (소매업체만 가능, pending 상태만)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상품은 소매업체만 수정할 수 있습니다"
            )
        
        # 주문 확인 및 권한 체크
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company or str(company.id) != str(order.retail_company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상품을 수정할 권한이 없습니다"
            )
        
        # pending 상태만 수정 가능
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대기 중인 주문만 수정할 수 있습니다"
            )
        
        # 주문 상품 수정
        updated_order, error_message = await OrderService.update_order_item(
            order_id, 
            item_id, 
            item_data, 
            str(current_user["id"])
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 상품 수정에 실패했습니다"
            )
        
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 상품 수정 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 상품 수정에 실패했습니다"
        )


@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
async def remove_order_item(
    order_id: str,
    item_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> OrderResponse:
    """주문 상품 제거 (소매업체만 가능, pending 상태만)"""
    try:
        # 소매업체 권한 확인
        if current_user.get("company_type") != "retail":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상품은 소매업체만 제거할 수 있습니다"
            )
        
        # 주문 확인 및 권한 체크
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="주문을 찾을 수 없습니다"
            )
        
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company or str(company.id) != str(order.retail_company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 상품을 제거할 권한이 없습니다"
            )
        
        # pending 상태만 수정 가능
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="대기 중인 주문만 수정할 수 있습니다"
            )
        
        # 주문 상품 제거
        updated_order, error_message = await OrderService.remove_order_item(
            order_id, 
            item_id, 
            str(current_user["id"])
        )
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 상품 제거에 실패했습니다"
            )
        
        return updated_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 상품 제거 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 상품 제거에 실패했습니다"
        )


@router.post("/bulk-operation")
async def bulk_order_operation(
    operation_data: BulkOrderOperation,
    current_user: dict = Depends(get_current_user_required)
):
    """주문 일괄 처리 (도매업체만 가능)"""
    try:
        # 도매업체 권한 확인
        if current_user.get("company_type") != "wholesale":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="주문 일괄 처리는 도매업체만 가능합니다"
            )
        
        # 사용자의 회사 ID 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 일괄 처리 실행
        results, error_message = await OrderService.bulk_order_operation(
            operation_data, 
            str(current_user["id"]), 
            str(company.id)
        )
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "주문 일괄 처리에 실패했습니다"
            )
        
        return {
            "success": True,
            "message": f"{len(operation_data.order_ids)}개 주문이 일괄 처리되었습니다",
            "processed_orders": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 일괄 처리 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 일괄 처리에 실패했습니다"
        )


@router.get("/stats", response_model=OrderStats)
async def get_order_stats(
    current_user: dict = Depends(get_current_user_required)
) -> OrderStats:
    """주문 통계 조회"""
    try:
        # 사용자의 회사 ID 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 회사 유형에 따른 통계 조회
        stats = await OrderService.get_order_stats(
            str(company.id), 
            current_user.get("company_type")
        )
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 통계 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="주문 통계 조회에 실패했습니다"
        )