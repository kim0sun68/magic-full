"""
재고 관리 서비스
PostgreSQL Row-level 락킹을 통한 동시성 제어 구현
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from models.product import (
    InventoryResponse, InventoryUpdate, InventoryTransactionCreate, 
    InventoryTransactionResponse, StockAdjustment, StockIn, 
    LowStockAlert, InventoryStats
)
from services.real_supabase_service import real_supabase_service

logger = logging.getLogger(__name__)


class InventoryService:
    """재고 관리 서비스 (동시성 제어 포함)"""
    
    @staticmethod
    async def get_inventory_by_product_id(product_id: str) -> Optional[InventoryResponse]:
        """상품별 재고 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT inv.id, inv.product_id, inv.current_stock, inv.minimum_stock, inv.last_updated, p.name as product_name, p.code as product_code FROM inventory inv JOIN products p ON inv.product_id = p.id WHERE inv.product_id = '{product_id}'"
            )
            
            if not result:
                return None
            
            inventory_dict = dict(result[0])
            inventory_dict['is_low_stock'] = inventory_dict['current_stock'] <= inventory_dict['minimum_stock']
            
            return InventoryResponse(**inventory_dict)
            
        except Exception as e:
            logger.error(f"재고 조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_company_inventory(company_id: str) -> List[InventoryResponse]:
        """회사별 재고 목록 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    inv.id, inv.product_id, inv.current_stock, inv.minimum_stock, inv.last_updated,
                    p.name as product_name, p.code as product_code
                FROM inventory inv
                JOIN products p ON inv.product_id = p.id
                WHERE p.company_id = '{company_id}' AND p.is_active = true
                ORDER BY p.name ASC
            """)
            
            inventories = []
            if result:
                for row in result:
                    inventory_dict = dict(row)
                    inventory_dict['is_low_stock'] = inventory_dict['current_stock'] <= inventory_dict['minimum_stock']
                    inventories.append(InventoryResponse(**inventory_dict))
            
            return inventories
            
        except Exception as e:
            logger.error(f"회사 재고 목록 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def update_stock_with_lock(product_id: str, quantity_change: int, 
                                   transaction_type: str, reference_type: Optional[str] = None,
                                   reference_id: Optional[str] = None, notes: Optional[str] = None,
                                   created_by: str = None) -> Tuple[bool, Optional[str]]:
        """
        재고 업데이트 (PostgreSQL Row-level 락킹 사용)
        
        Args:
            product_id: 상품 ID
            quantity_change: 수량 변화 (양수: 입고, 음수: 출고)
            transaction_type: 거래 유형 (in, out, adjustment)
            reference_type: 참조 유형 (order, adjustment, initial)
            reference_id: 참조 ID
            notes: 메모
            created_by: 생성자 ID
            
        Returns:
            Tuple[bool, Optional[str]]: (성공 여부, 오류 메시지)
        """
        try:
            # 트랜잭션 시작 및 Row-level 락킹
            lock_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT current_stock, minimum_stock 
                FROM inventory 
                WHERE product_id = '{product_id}' 
                FOR UPDATE
            """)
            
            if not lock_result:
                return False, "재고 정보를 찾을 수 없습니다"
            
            current_stock = lock_result[0]['current_stock']
            minimum_stock = lock_result[0]['minimum_stock']
            new_stock = current_stock + quantity_change
            
            # 재고 부족 확인 (출고 시)
            if new_stock < 0:
                return False, f"재고가 부족합니다 (현재: {current_stock}, 요청: {abs(quantity_change)})"
            
            # 재고 업데이트
            update_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE inventory 
                SET current_stock = {new_stock}, last_updated = NOW()
                WHERE product_id = '{product_id}'
            """)
            
            if not update_result:
                return False, "재고 업데이트에 실패했습니다"
            
            # 재고 거래내역 기록
            transaction_id = str(uuid.uuid4())
            await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                INSERT INTO inventory_transactions (
                    id, product_id, transaction_type, quantity, 
                    previous_stock, current_stock, reference_type, reference_id, 
                    notes, created_by
                )
                VALUES (
                    '{transaction_id}', '{product_id}', '{transaction_type}', {abs(quantity_change)},
                    {current_stock}, {new_stock}, 
                    {f"'{reference_type}'" if reference_type else "NULL"},
                    {f"'{reference_id}'" if reference_id else "NULL"},
                    {f"'{notes}'" if notes else "NULL"},
                    {f"'{created_by}'" if created_by else "NULL"}
                )
            """)
            
            # 안전재고 알림 확인
            if new_stock <= minimum_stock and minimum_stock > 0:
                logger.warning(f"안전재고 알림: 상품 {product_id}, 현재재고: {new_stock}, 최소재고: {minimum_stock}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"재고 업데이트 오류: {str(e)}")
            return False, f"재고 업데이트 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def stock_adjustment(adjustment: StockAdjustment, user_id: str, company_id: str) -> Tuple[bool, Optional[str]]:
        """재고 조정"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM products 
                WHERE id = '{adjustment.product_id}' AND company_id = '{company_id}'
            """)
            
            if not ownership_check:
                return False, "재고 조정 권한이 없는 상품입니다"
            
            # 재고 업데이트 (Row-level 락킹 적용)
            success, error = await InventoryService.update_stock_with_lock(
                product_id=str(adjustment.product_id),
                quantity_change=adjustment.adjustment_quantity,
                transaction_type="adjustment",
                reference_type="adjustment",
                notes=adjustment.reason,
                created_by=user_id
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"재고 조정 오류: {str(e)}")
            return False, f"재고 조정 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def stock_in(stock_in_data: StockIn, user_id: str, company_id: str) -> Tuple[bool, Optional[str]]:
        """입고 등록"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM products 
                WHERE id = '{stock_in_data.product_id}' AND company_id = '{company_id}'
            """)
            
            if not ownership_check:
                return False, "입고 등록 권한이 없는 상품입니다"
            
            # 재고 업데이트 (Row-level 락킹 적용)
            success, error = await InventoryService.update_stock_with_lock(
                product_id=str(stock_in_data.product_id),
                quantity_change=stock_in_data.quantity,
                transaction_type="in",
                reference_type="initial",
                notes=stock_in_data.notes,
                created_by=user_id
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"입고 등록 오류: {str(e)}")
            return False, f"입고 등록 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def reserve_stock(product_id: str, quantity: int, order_id: str) -> Tuple[bool, Optional[str]]:
        """재고 예약 (주문 생성 시)"""
        try:
            # 재고 차감 (Row-level 락킹 적용)
            success, error = await InventoryService.update_stock_with_lock(
                product_id=product_id,
                quantity_change=-quantity,
                transaction_type="out",
                reference_type="order",
                reference_id=order_id,
                notes="주문으로 인한 재고 예약"
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"재고 예약 오류: {str(e)}")
            return False, f"재고 예약 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def cancel_stock_reservation(product_id: str, quantity: int, order_id: str) -> Tuple[bool, Optional[str]]:
        """재고 예약 취소 (주문 취소 시)"""
        try:
            # 재고 복원 (Row-level 락킹 적용)
            success, error = await InventoryService.update_stock_with_lock(
                product_id=product_id,
                quantity_change=quantity,
                transaction_type="in",
                reference_type="order",
                reference_id=order_id,
                notes="주문 취소로 인한 재고 복원"
            )
            
            return success, error
            
        except Exception as e:
            logger.error(f"재고 예약 취소 오류: {str(e)}")
            return False, f"재고 예약 취소 중 오류가 발생했습니다: {str(e)}"
    
    @staticmethod
    async def get_inventory_transactions(product_id: Optional[str] = None, 
                                       company_id: Optional[str] = None,
                                       limit: int = 100) -> List[InventoryTransactionResponse]:
        """재고 거래내역 조회"""
        try:
            conditions = []
            
            if product_id:
                conditions.append(f"it.product_id = '{product_id}'")
            
            if company_id:
                conditions.append(f"p.company_id = '{company_id}'")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    it.id, it.product_id, it.transaction_type, it.quantity,
                    it.previous_stock, it.current_stock, it.reference_type, it.reference_id,
                    it.notes, it.created_by, it.created_at,
                    p.name as product_name, p.code as product_code,
                    u.name as created_by_name
                FROM inventory_transactions it
                JOIN products p ON it.product_id = p.id
                LEFT JOIN users u ON it.created_by = u.id
                {where_clause}
                ORDER BY it.created_at DESC
                LIMIT {limit}
            """)
            
            transactions = []
            if result:
                for row in result:
                    transactions.append(InventoryTransactionResponse(**dict(row)))
            
            return transactions
            
        except Exception as e:
            logger.error(f"재고 거래내역 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def get_low_stock_alerts(company_id: str) -> List[LowStockAlert]:
        """안전재고 미달 알림 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    p.id as product_id, p.name as product_name, p.code as product_code,
                    inv.current_stock, inv.minimum_stock,
                    (inv.minimum_stock - inv.current_stock) as shortage
                FROM inventory inv
                JOIN products p ON inv.product_id = p.id
                WHERE p.company_id = '{company_id}' 
                AND p.is_active = true
                AND inv.current_stock <= inv.minimum_stock
                AND inv.minimum_stock > 0
                ORDER BY shortage DESC
            """)
            
            alerts = []
            if result:
                for row in result:
                    alerts.append(LowStockAlert(**dict(row)))
            
            return alerts
            
        except Exception as e:
            logger.error(f"안전재고 알림 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def get_inventory_stats(company_id: str) -> InventoryStats:
        """재고 통계 조회"""
        try:
            # 기본 통계 조회
            stats_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    COUNT(*) as total_products,
                    COUNT(*) FILTER (WHERE p.is_active = true) as active_products,
                    COUNT(*) FILTER (WHERE inv.current_stock <= inv.minimum_stock AND inv.minimum_stock > 0) as low_stock_products,
                    COUNT(*) FILTER (WHERE inv.current_stock = 0) as out_of_stock_products,
                    COALESCE(SUM(inv.current_stock * p.wholesale_price), 0) as total_inventory_value
                FROM inventory inv
                JOIN products p ON inv.product_id = p.id
                WHERE p.company_id = '{company_id}'
            """)
            
            if stats_result:
                return InventoryStats(**dict(stats_result[0]))
            else:
                return InventoryStats(
                    total_products=0, active_products=0, low_stock_products=0,
                    out_of_stock_products=0, total_inventory_value=0
                )
            
        except Exception as e:
            logger.error(f"재고 통계 조회 오류: {str(e)}")
            return InventoryStats(
                total_products=0, active_products=0, low_stock_products=0,
                out_of_stock_products=0, total_inventory_value=0
            )
    
    @staticmethod
    async def update_minimum_stock(product_id: str, minimum_stock: int, company_id: str) -> bool:
        """최소 재고량 설정"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM products 
                WHERE id = '{product_id}' AND company_id = '{company_id}'
            """)
            
            if not ownership_check:
                return False
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE inventory 
                SET minimum_stock = {minimum_stock}, last_updated = NOW()
                WHERE product_id = '{product_id}'
            """)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"최소 재고량 설정 오류: {str(e)}")
            return False
    
    @staticmethod
    async def check_stock_availability(product_id: str, required_quantity: int) -> Tuple[bool, int]:
        """
        재고 가용성 확인
        
        Args:
            product_id: 상품 ID
            required_quantity: 필요 수량
            
        Returns:
            Tuple[bool, int]: (가용 여부, 현재 재고량)
        """
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT current_stock 
                FROM inventory 
                WHERE product_id = '{product_id}'
            """)
            
            if not result:
                return False, 0
            
            current_stock = result[0]['current_stock']
            is_available = current_stock >= required_quantity
            
            return is_available, current_stock
            
        except Exception as e:
            logger.error(f"재고 가용성 확인 오류: {str(e)}")
            return False, 0
    
    @staticmethod
    async def bulk_check_stock_availability(items: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        여러 상품 재고 가용성 일괄 확인
        
        Args:
            items: [{"product_id": str, "quantity": int}, ...]
            
        Returns:
            Tuple[bool, List[Dict]]: (전체 가용 여부, 각 상품별 재고 정보)
        """
        try:
            product_ids = [item['product_id'] for item in items]
            product_ids_str = "', '".join(product_ids)
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    p.id as product_id, p.name as product_name, p.code as product_code,
                    inv.current_stock
                FROM inventory inv
                JOIN products p ON inv.product_id = p.id
                WHERE p.id IN ('{product_ids_str}')
            """)
            
            if not result:
                return False, []
            
            # 재고 확인 결과 생성
            stock_info = {}
            for row in result:
                stock_info[row['product_id']] = {
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'product_code': row['product_code'],
                    'current_stock': row['current_stock'],
                    'required_quantity': 0,
                    'is_available': False
                }
            
            all_available = True
            availability_results = []
            
            for item in items:
                product_id = item['product_id']
                required_quantity = item['quantity']
                
                if product_id in stock_info:
                    stock_info[product_id]['required_quantity'] = required_quantity
                    stock_info[product_id]['is_available'] = stock_info[product_id]['current_stock'] >= required_quantity
                    
                    if not stock_info[product_id]['is_available']:
                        all_available = False
                    
                    availability_results.append(stock_info[product_id])
                else:
                    # 상품을 찾을 수 없음
                    all_available = False
                    availability_results.append({
                        'product_id': product_id,
                        'product_name': 'Unknown',
                        'product_code': 'Unknown',
                        'current_stock': 0,
                        'required_quantity': required_quantity,
                        'is_available': False
                    })
            
            return all_available, availability_results
            
        except Exception as e:
            logger.error(f"일괄 재고 확인 오류: {str(e)}")
            return False, []
    
    @staticmethod
    async def get_stock_movements(product_id: str, days: int = 30) -> List[InventoryTransactionResponse]:
        """재고 변동 내역 조회 (최근 N일)"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    it.id, it.product_id, it.transaction_type, it.quantity,
                    it.previous_stock, it.current_stock, it.reference_type, it.reference_id,
                    it.notes, it.created_by, it.created_at,
                    p.name as product_name, p.code as product_code,
                    u.name as created_by_name
                FROM inventory_transactions it
                JOIN products p ON it.product_id = p.id
                LEFT JOIN users u ON it.created_by = u.id
                WHERE it.product_id = '{product_id}'
                AND it.created_at >= NOW() - INTERVAL '{days} days'
                ORDER BY it.created_at DESC
            """)
            
            transactions = []
            if result:
                for row in result:
                    transactions.append(InventoryTransactionResponse(**dict(row)))
            
            return transactions
            
        except Exception as e:
            logger.error(f"재고 변동 내역 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def get_low_stock_products(company_id: str) -> List[InventoryResponse]:
        """안전재고 미달 상품 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    inv.id, inv.product_id, inv.current_stock, inv.minimum_stock, inv.last_updated,
                    p.name as product_name, p.code as product_code
                FROM inventory inv
                JOIN products p ON inv.product_id = p.id
                WHERE p.company_id = '{company_id}' 
                AND p.is_active = true
                AND inv.current_stock <= inv.minimum_stock
                AND inv.minimum_stock > 0
                ORDER BY (inv.minimum_stock - inv.current_stock) DESC
            """)
            
            inventories = []
            if result:
                for row in result:
                    row_dict = dict(row)
                    row_dict['is_low_stock'] = True
                    inventories.append(InventoryResponse(**row_dict))
            
            return inventories
            
        except Exception as e:
            logger.error(f"안전재고 미달 상품 조회 오류: {str(e)}")
            return []