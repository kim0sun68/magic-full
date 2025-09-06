"""
주문 관리 서비스
도매업체-소매업체 간 주문 처리 및 재고 연동
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from models.order import (
    OrderCreate, OrderUpdate, OrderStatusUpdate, OrderResponse,
    OrderListResponse, OrderSearchFilter, OrderStats, QuickOrderCreate,
    OrderItemResponse, BulkOrderOperation
)
from services.inventory_service import InventoryService
from services.company_service import CompanyService
from database import execute_sql

logger = logging.getLogger(__name__)


class OrderService:
    """주문 관리 서비스"""
    
    @staticmethod
    async def create_order(order_data: OrderCreate, user_id: str, retail_company_id: str) -> Tuple[Optional[OrderResponse], Optional[str]]:
        """
        주문 생성 (재고 예약 포함)
        
        Args:
            order_data: 주문 생성 데이터
            user_id: 주문 생성자 ID
            retail_company_id: 소매업체 ID
            
        Returns:
            Tuple[Optional[OrderResponse], Optional[str]]: (주문 정보, 오류 메시지)
        """
        try:
            # 거래 관계 확인
            relationship_exists = await CompanyService.check_trading_relationship(
                str(order_data.wholesale_company_id), retail_company_id
            )
            
            if not relationship_exists:
                return None, "승인되지 않은 도매업체입니다"
            
            # 주문 상품들의 재고 가용성 일괄 확인
            items_for_check = [
                {"product_id": str(item.product_id), "quantity": item.quantity}
                for item in order_data.items
            ]
            
            all_available, availability_results = await InventoryService.bulk_check_stock_availability(items_for_check)
            
            if not all_available:
                unavailable_items = [
                    f"{item['product_name']}(재고:{item['current_stock']}, 요청:{item['required_quantity']})"
                    for item in availability_results if not item['is_available']
                ]
                return None, f"재고 부족: {', '.join(unavailable_items)}"
            
            # 주문 번호 생성 (YYYYMMDD-XXXX 형식)
            today = datetime.now().strftime("%Y%m%d")
            order_count_result = await execute_sql(f"""
                SELECT COUNT(*) as count 
                FROM orders 
                WHERE order_number LIKE '{today}-%'
            """)
            
            order_count = order_count_result[0]['count'] if order_count_result else 0
            order_number = f"{today}-{order_count + 1:04d}"
            
            # 주문 생성
            order_id = str(uuid.uuid4())
            total_amount = sum(item.quantity * item.unit_price for item in order_data.items)
            
            order_result = await execute_sql(f"""
                INSERT INTO orders (
                    id, order_number, wholesale_company_id, retail_company_id,
                    status, total_amount, notes, created_by
                )
                VALUES (
                    '{order_id}', '{order_number}', '{order_data.wholesale_company_id}', 
                    '{retail_company_id}', 'pending', {total_amount}, 
                    {f"'{order_data.notes}'" if order_data.notes else "NULL"}, '{user_id}'
                )
                RETURNING id, order_number, wholesale_company_id, retail_company_id,
                         status, total_amount, notes, created_by, created_at, updated_at
            """)
            
            if not order_result:
                return None, "주문 생성에 실패했습니다"
            
            # 주문 상품들 생성 및 재고 예약
            order_items = []
            for item in order_data.items:
                # 재고 예약
                success, error = await InventoryService.reserve_stock(
                    str(item.product_id), item.quantity, order_id
                )
                
                if not success:
                    # 실패 시 이전 예약들 모두 취소
                    for prev_item in order_items:
                        await InventoryService.cancel_stock_reservation(
                            str(prev_item.product_id), prev_item.quantity, order_id
                        )
                    
                    # 주문도 삭제
                    await execute_sql(f"DELETE FROM orders WHERE id = '{order_id}'")
                    return None, f"재고 예약 실패: {error}"
                
                # 주문 상품 생성
                item_id = str(uuid.uuid4())
                total_price = item.quantity * item.unit_price
                
                item_result = await execute_sql(f"""
                    INSERT INTO order_items (
                        id, order_id, product_id, quantity, unit_price, total_price
                    )
                    VALUES (
                        '{item_id}', '{order_id}', '{item.product_id}', 
                        {item.quantity}, {item.unit_price}, {total_price}
                    )
                    RETURNING id, order_id, product_id, quantity, unit_price, total_price, created_at
                """)
                
                if item_result:
                    order_items.append(OrderItemResponse(**item_result[0]))
            
            # 완성된 주문 정보 반환
            order_dict = dict(order_result[0])
            order_dict['items'] = order_items
            
            return OrderResponse(**order_dict), None
            
        except Exception as e:
            logger.error(f"주문 생성 오류: {str(e)}")
            return None, f"주문 생성 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def get_orders(search_filter: OrderSearchFilter, company_id: str, company_type: str) -> OrderListResponse:
        """주문 목록 조회"""
        try:
            # WHERE 조건 구성
            conditions = []
            
            # 회사 유형별 접근 제어
            if company_type == "wholesale":
                conditions.append(f"o.wholesale_company_id = '{company_id}'")
            elif company_type == "retail":
                conditions.append(f"o.retail_company_id = '{company_id}'")
            
            if search_filter.status:
                conditions.append(f"o.status = '{search_filter.status}'")
            
            if search_filter.order_number:
                conditions.append(f"o.order_number ILIKE '%{search_filter.order_number}%'")
            
            if search_filter.start_date:
                conditions.append(f"o.created_at >= '{search_filter.start_date.isoformat()}'")
            
            if search_filter.end_date:
                conditions.append(f"o.created_at <= '{search_filter.end_date.isoformat()}'")
            
            if search_filter.min_amount is not None:
                conditions.append(f"o.total_amount >= {search_filter.min_amount}")
            
            if search_filter.max_amount is not None:
                conditions.append(f"o.total_amount <= {search_filter.max_amount}")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # 총 개수 조회
            count_result = await execute_sql(f"""
                SELECT COUNT(*) as total
                FROM orders o
                LEFT JOIN companies wc ON o.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON o.retail_company_id = rc.id
                {where_clause}
            """)
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (search_filter.page - 1) * search_filter.size
            
            # 주문 목록 조회
            result = await execute_sql(f"""
                SELECT 
                    o.id, o.order_number, o.wholesale_company_id, o.retail_company_id,
                    o.status, o.total_amount, o.notes, o.created_by, o.created_at, o.updated_at,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name,
                    u.name as created_by_name
                FROM orders o
                LEFT JOIN companies wc ON o.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON o.retail_company_id = rc.id
                LEFT JOIN users u ON o.created_by = u.id
                {where_clause}
                ORDER BY o.created_at DESC
                LIMIT {search_filter.size} OFFSET {offset}
            """)
            
            orders = []
            if result:
                for row in result:
                    order_dict = dict(row)
                    
                    # 주문 상품 목록 조회
                    items_result = await execute_sql(f"""
                        SELECT 
                            oi.id, oi.order_id, oi.product_id, oi.quantity, oi.unit_price, oi.total_price, oi.created_at,
                            p.name as product_name, p.code as product_code
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = '{row['id']}'
                        ORDER BY oi.created_at ASC
                    """)
                    
                    items = []
                    if items_result:
                        items = [OrderItemResponse(**dict(item_row)) for item_row in items_result]
                    
                    order_dict['items'] = items
                    orders.append(OrderResponse(**order_dict))
            
            has_next = (offset + search_filter.size) < total
            
            return OrderListResponse(
                orders=orders,
                total=total,
                page=search_filter.page,
                size=search_filter.size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"주문 목록 조회 오류: {str(e)}")
            return OrderListResponse(orders=[], total=0, page=1, size=20, has_next=False)
    
    @staticmethod
    async def get_order_by_id(order_id: str) -> Optional[OrderResponse]:
        """주문 상세 조회"""
        try:
            result = await execute_sql(f"""
                SELECT 
                    o.id, o.order_number, o.wholesale_company_id, o.retail_company_id,
                    o.status, o.total_amount, o.notes, o.created_by, o.created_at, o.updated_at,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name,
                    u.name as created_by_name
                FROM orders o
                LEFT JOIN companies wc ON o.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON o.retail_company_id = rc.id
                LEFT JOIN users u ON o.created_by = u.id
                WHERE o.id = '{order_id}'
            """)
            
            if not result:
                return None
            
            order_dict = dict(result[0])
            
            # 주문 상품 목록 조회
            items_result = await execute_sql(f"""
                SELECT 
                    oi.id, oi.order_id, oi.product_id, oi.quantity, oi.unit_price, oi.total_price, oi.created_at,
                    p.name as product_name, p.code as product_code
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = '{order_id}'
                ORDER BY oi.created_at ASC
            """)
            
            items = []
            if items_result:
                items = [OrderItemResponse(**dict(item_row)) for item_row in items_result]
            
            order_dict['items'] = items
            return OrderResponse(**order_dict)
            
        except Exception as e:
            logger.error(f"주문 조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def update_order_status(order_id: str, status_update: OrderStatusUpdate, 
                                user_id: str, company_id: str) -> Tuple[Optional[OrderResponse], Optional[str]]:
        """주문 상태 변경"""
        try:
            # 주문 정보 및 권한 확인
            order_info = await execute_sql(f"""
                SELECT 
                    o.id, o.status, o.wholesale_company_id, o.retail_company_id,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name
                FROM orders o
                LEFT JOIN companies wc ON o.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON o.retail_company_id = rc.id
                WHERE o.id = '{order_id}'
            """)
            
            if not order_info:
                return None, "주문을 찾을 수 없습니다"
            
            order = order_info[0]
            current_status = order['status']
            
            # 상태 변경 권한 확인
            if status_update.status in ['confirmed', 'preparing', 'shipped']:
                # 도매업체만 가능
                if str(order['wholesale_company_id']) != company_id:
                    return None, "주문 상태 변경 권한이 없습니다"
            elif status_update.status == 'cancelled':
                # 도매업체 또는 소매업체 모두 가능 (pending 상태에서만)
                if (str(order['wholesale_company_id']) != company_id and 
                    str(order['retail_company_id']) != company_id):
                    return None, "주문 취소 권한이 없습니다"
                if current_status not in ['pending', 'confirmed']:
                    return None, "이미 처리 중인 주문은 취소할 수 없습니다"
            
            # 상태 변경 검증
            valid_transitions = {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['preparing', 'cancelled'],
                'preparing': ['shipped'],
                'shipped': ['delivered'],
                'delivered': [],  # 최종 상태
                'cancelled': []   # 최종 상태
            }
            
            if status_update.status not in valid_transitions.get(current_status, []):
                return None, f"'{current_status}' 상태에서 '{status_update.status}' 상태로 변경할 수 없습니다"
            
            # 주문 취소 시 재고 복원
            if status_update.status == 'cancelled':
                # 주문 상품들의 재고 복원
                items_result = await execute_sql(f"""
                    SELECT product_id, quantity 
                    FROM order_items 
                    WHERE order_id = '{order_id}'
                """)
                
                if items_result:
                    for item in items_result:
                        success, error = await InventoryService.cancel_stock_reservation(
                            str(item['product_id']), item['quantity'], order_id
                        )
                        
                        if not success:
                            logger.warning(f"재고 복원 실패: {error}")
            
            # 주문 상태 업데이트
            update_result = await execute_sql(f"""
                UPDATE orders 
                SET status = '{status_update.status}', 
                    notes = COALESCE(notes, '') || 
                           CASE WHEN notes IS NOT NULL AND notes != '' THEN '\\n' ELSE '' END ||
                           '[{status_update.status.upper()}] {status_update.notes or ""}',
                    updated_at = NOW()
                WHERE id = '{order_id}'
                RETURNING id, order_number, wholesale_company_id, retail_company_id,
                         status, total_amount, notes, created_by, created_at, updated_at
            """)
            
            if not update_result:
                return None, "주문 상태 업데이트에 실패했습니다"
            
            # 업데이트된 주문 정보 반환
            updated_order = await OrderService.get_order_by_id(order_id)
            return updated_order, None
            
        except Exception as e:
            logger.error(f"주문 상태 변경 오류: {str(e)}")
            return None, f"주문 상태 변경 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def get_order_stats(company_id: str, company_type: str) -> OrderStats:
        """주문 통계 조회"""
        try:
            # 회사 유형별 조건
            company_condition = ""
            if company_type == "wholesale":
                company_condition = f"WHERE wholesale_company_id = '{company_id}'"
            elif company_type == "retail":
                company_condition = f"WHERE retail_company_id = '{company_id}'"
            
            result = await execute_sql(f"""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_orders,
                    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed_orders,
                    COUNT(*) FILTER (WHERE status = 'shipped') as shipped_orders,
                    COUNT(*) FILTER (WHERE status = 'delivered') as delivered_orders,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_orders,
                    COALESCE(SUM(total_amount), 0) as total_amount,
                    COALESCE(AVG(total_amount), 0) as average_order_value
                FROM orders 
                {company_condition}
            """)
            
            if result:
                return OrderStats(**dict(result[0]))
            else:
                return OrderStats(
                    total_orders=0, pending_orders=0, confirmed_orders=0,
                    shipped_orders=0, delivered_orders=0, cancelled_orders=0,
                    total_amount=0, average_order_value=0
                )
            
        except Exception as e:
            logger.error(f"주문 통계 조회 오류: {str(e)}")
            return OrderStats(
                total_orders=0, pending_orders=0, confirmed_orders=0,
                shipped_orders=0, delivered_orders=0, cancelled_orders=0,
                total_amount=0, average_order_value=0
            )
    
    @staticmethod
    async def create_quick_order(quick_order: QuickOrderCreate, user_id: str, retail_company_id: str) -> Tuple[Optional[OrderResponse], Optional[str]]:
        """빠른 주문 생성 (상품 코드 기반)"""
        try:
            # 거래 관계 확인
            relationship_exists = await CompanyService.check_trading_relationship(
                str(quick_order.wholesale_company_id), retail_company_id
            )
            
            if not relationship_exists:
                return None, "승인되지 않은 도매업체입니다"
            
            # 상품 코드로 상품 정보 조회
            product_codes = [item.product_code for item in quick_order.items]
            codes_str = "', '".join(product_codes)
            
            products_result = await execute_sql(f"""
                SELECT id, code, name, wholesale_price
                FROM products 
                WHERE code IN ('{codes_str}') 
                AND company_id = '{quick_order.wholesale_company_id}'
                AND is_active = true
            """)
            
            if not products_result or len(products_result) != len(quick_order.items):
                found_codes = [p['code'] for p in products_result] if products_result else []
                missing_codes = [code for code in product_codes if code not in found_codes]
                return None, f"존재하지 않는 상품 코드: {', '.join(missing_codes)}"
            
            # 상품 정보 매핑
            products_map = {p['code']: p for p in products_result}
            
            # 일반 주문 형식으로 변환
            from models.order import OrderItemCreate
            order_items = []
            
            for item in quick_order.items:
                product = products_map[item.product_code]
                order_items.append(OrderItemCreate(
                    product_id=product['id'],
                    quantity=item.quantity,
                    unit_price=product['wholesale_price']
                ))
            
            from models.order import OrderCreate
            order_create = OrderCreate(
                wholesale_company_id=quick_order.wholesale_company_id,
                notes=quick_order.notes,
                items=order_items
            )
            
            # 일반 주문 생성 프로세스 사용
            return await OrderService.create_order(order_create, user_id, retail_company_id)
            
        except Exception as e:
            logger.error(f"빠른 주문 생성 오류: {str(e)}")
            return None, f"빠른 주문 생성 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def bulk_update_order_status(bulk_operation: BulkOrderOperation, 
                                     user_id: str, company_id: str) -> Tuple[List[str], List[str]]:
        """주문 일괄 상태 변경"""
        try:
            success_orders = []
            failed_orders = []
            
            for order_id in bulk_operation.order_ids:
                from models.order import OrderStatusUpdate
                status_update = OrderStatusUpdate(
                    status=bulk_operation.status,
                    notes=bulk_operation.notes
                )
                
                updated_order, error = await OrderService.update_order_status(
                    str(order_id), status_update, user_id, company_id
                )
                
                if updated_order:
                    success_orders.append(str(order_id))
                else:
                    failed_orders.append(f"{order_id}: {error}")
            
            return success_orders, failed_orders
            
        except Exception as e:
            logger.error(f"주문 일괄 처리 오류: {str(e)}")
            return [], [f"일괄 처리 중 오류 발생: {str(e)}"]
    
    @staticmethod
    async def check_order_access(order_id: str, company_id: str, company_type: str) -> bool:
        """주문 접근 권한 확인"""
        try:
            condition = ""
            if company_type == "wholesale":
                condition = f"wholesale_company_id = '{company_id}'"
            elif company_type == "retail":
                condition = f"retail_company_id = '{company_id}'"
            else:
                return False
            
            result = await execute_sql(f"""
                SELECT id FROM orders 
                WHERE id = '{order_id}' AND {condition}
            """)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"주문 접근 권한 확인 오류: {str(e)}")
            return False