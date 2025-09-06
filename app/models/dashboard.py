"""
대시보드 관련 Pydantic 모델
통합 통계 및 알림 정보
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from models.order import OrderStats, OrderResponse
from models.product import InventoryStats, LowStockAlert
from models.chat import ChatStats


class DashboardStats(BaseModel):
    """대시보드 통합 통계"""
    
    # 오늘 주요 지표
    today_orders: int = Field(0, description="오늘 주문 건수")
    low_stock_count: int = Field(0, description="재고 부족 상품 수")
    unread_messages: int = Field(0, description="읽지 않은 메시지 수")
    
    # 주문 통계
    order_stats: OrderStats = Field(..., description="주문 통계")
    
    # 재고 통계  
    inventory_stats: InventoryStats = Field(..., description="재고 통계")
    
    # 채팅 통계
    chat_stats: ChatStats = Field(..., description="채팅 통계")
    
    # 최근 주문 목록 (5개)
    recent_orders: List[OrderResponse] = Field(default_factory=list, description="최근 주문 목록")
    
    # 재고 부족 알림 목록 (5개)
    low_stock_alerts: List[LowStockAlert] = Field(default_factory=list, description="재고 부족 알림")


class DashboardResponse(BaseModel):
    """대시보드 응답"""
    success: bool = True
    data: DashboardStats
    timestamp: datetime = Field(default_factory=datetime.now)