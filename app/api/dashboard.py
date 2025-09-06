"""
대시보드 API 라우터
통합 통계 및 대시보드 데이터 제공
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import logging

from models.dashboard import DashboardStats, DashboardResponse
from models.order import OrderSearchFilter
from services.order_service import OrderService
from services.inventory_service import InventoryService
from services.chat_service import ChatService
from auth.middleware import get_current_user_required


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user_required)):
    """대시보드 통계 조회"""
    try:
        user_id = str(current_user["id"])
        company_id = str(current_user.get("company_id", ""))
        company_type = current_user.get("company_type", "")
        
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자에게 연결된 회사 정보가 없습니다"
            )
        
        # 오늘 날짜 기준 주문 수 조회
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # 오늘 주문 검색 조건 설정
        today_order_filter = OrderSearchFilter(
            start_date=today_start,
            end_date=today_end,
            page=1,
            size=1000  # 하루 주문 수는 많지 않을 것으로 예상
        )
        
        # 병렬로 모든 통계 조회
        order_stats = await OrderService.get_order_stats(company_id, company_type)
        inventory_stats = await InventoryService.get_inventory_stats(company_id)
        chat_stats = await ChatService.get_chat_stats(user_id)
        
        # 오늘 주문 목록 조회
        today_orders_result = await OrderService.get_orders(today_order_filter, company_id, company_type)
        today_orders_count = len(today_orders_result.orders)
        
        # 최근 주문 5개 조회
        recent_order_filter = OrderSearchFilter(page=1, size=5)
        recent_orders_result = await OrderService.get_orders(recent_order_filter, company_id, company_type)
        
        # 재고 부족 알림 5개 조회
        low_stock_alerts = await InventoryService.get_low_stock_alerts(company_id)
        low_stock_alerts_limited = low_stock_alerts[:5]  # 최대 5개만
        
        # 대시보드 통계 구성
        dashboard_stats = DashboardStats(
            today_orders=today_orders_count,
            low_stock_count=inventory_stats.low_stock_products,
            unread_messages=chat_stats.unread_messages,
            order_stats=order_stats,
            inventory_stats=inventory_stats,
            chat_stats=chat_stats,
            recent_orders=recent_orders_result.orders,
            low_stock_alerts=low_stock_alerts_limited
        )
        
        # JavaScript가 기대하는 형식으로 직접 반환
        return {
            "todayOrders": dashboard_stats.today_orders,
            "lowStock": dashboard_stats.low_stock_count,
            "newMessages": dashboard_stats.unread_messages,
            "activePartners": 0,  # TODO: 거래처 통계 구현 필요
            "pendingPartners": 0  # TODO: 거래처 통계 구현 필요
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대시보드 통계 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대시보드 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/recent-orders", response_class=HTMLResponse)
async def get_recent_orders(
    request: Request,
    limit: int = 5,
    current_user: dict = Depends(get_current_user_required)
):
    """최근 주문 목록 조회 (HTMX용 HTML 반환)"""
    try:
        company_id = str(current_user.get("company_id", ""))
        company_type = current_user.get("company_type", "")
        
        if not company_id:
            return """<div class="text-red-500 text-sm">회사 정보가 없습니다</div>"""
        
        # 최근 주문 조회
        filter_params = OrderSearchFilter(page=1, size=limit)
        orders_result = await OrderService.get_orders(filter_params, company_id, company_type)
        
        if not orders_result.orders:
            return """<div class="text-gray-500 text-sm text-center py-4">최근 주문이 없습니다</div>"""
        
        # HTML 생성
        html = ""
        for order in orders_result.orders:
            status_colors = {
                "pending": "bg-yellow-100 text-yellow-800",
                "confirmed": "bg-blue-100 text-blue-800", 
                "shipped": "bg-purple-100 text-purple-800",
                "delivered": "bg-green-100 text-green-800",
                "cancelled": "bg-red-100 text-red-800"
            }
            status_color = status_colors.get(order.status, "bg-gray-100 text-gray-800")
            
            html += f'''
            <div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0">
                <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900">{order.order_number}</p>
                    <p class="text-xs text-gray-500">{order.created_at.strftime('%m/%d %H:%M')}</p>
                </div>
                <div class="flex items-center space-x-3">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {status_color}">
                        {order.status}
                    </span>
                    <span class="text-sm font-medium text-gray-900">{order.total_amount:,}원</span>
                </div>
            </div>
            '''
        
        return html
        
    except Exception as e:
        logger.error(f"최근 주문 조회 오류: {str(e)}")
        return f"""<div class="text-red-500 text-sm">오류: {str(e)}</div>"""


@router.get("/low-stock-alerts", response_class=HTMLResponse)
async def get_low_stock_alerts(
    request: Request,
    limit: int = 5,
    current_user: dict = Depends(get_current_user_required)
):
    """재고 부족 알림 목록 조회 (HTMX용 HTML 반환)"""
    try:
        company_id = str(current_user.get("company_id", ""))
        
        if not company_id:
            return """<div class="text-red-500 text-sm">회사 정보가 없습니다</div>"""
        
        # 재고 부족 알림 조회
        alerts = await InventoryService.get_low_stock_alerts(company_id)
        limited_alerts = alerts[:limit]
        
        if not limited_alerts:
            return """<div class="text-gray-500 text-sm text-center py-4">재고 부족 상품이 없습니다</div>"""
        
        # HTML 생성
        html = ""
        for alert in limited_alerts:
            shortage = alert.minimum_stock - alert.current_stock
            urgency_color = "text-red-600" if shortage > 10 else "text-yellow-600"
            
            html += f'''
            <div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0">
                <div class="flex-1">
                    <p class="text-sm font-medium text-gray-900">{alert.product_name}</p>
                    <p class="text-xs text-gray-500">상품코드: {alert.product_code}</p>
                </div>
                <div class="text-right">
                    <p class="text-sm {urgency_color}">재고: {alert.current_stock}개</p>
                    <p class="text-xs text-gray-500">최소: {alert.minimum_stock}개</p>
                </div>
            </div>
            '''
        
        return html
        
    except Exception as e:
        logger.error(f"재고 부족 알림 조회 오류: {str(e)}")
        return f"""<div class="text-red-500 text-sm">오류: {str(e)}</div>"""