"""
상품 관리 서비스
아동복 상품 CRUD 및 비즈니스 로직 구현
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.product import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse, ProductSearchFilter,
    ProductListResponse, ProductImageUpload
)
from services.real_supabase_service import real_supabase_service

logger = logging.getLogger(__name__)


class ProductService:
    """상품 관리 서비스"""
    
    @staticmethod
    async def create_category(category_data: CategoryCreate) -> CategoryResponse:
        """카테고리 생성"""
        try:
            category_id = str(uuid.uuid4())
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO categories (id, name, description) VALUES ('{category_id}', '{category_data.name}', '{category_data.description or ""}') RETURNING id, name, description, created_at"
            )
            
            if not result or len(result) == 0:
                raise ValueError("카테고리 생성에 실패했습니다")
            
            return CategoryResponse(**result[0])
            
        except Exception as e:
            logger.error(f"카테고리 생성 오류: {str(e)}")
            raise
    
    @staticmethod
    async def get_categories() -> List[CategoryResponse]:
        """카테고리 목록 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query="SELECT id, name, description, created_at FROM categories ORDER BY name ASC"
            )
            
            return [CategoryResponse(**row) for row in result] if result else []
            
        except Exception as e:
            logger.error(f"카테고리 목록 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def update_category(category_id: str, update_data: CategoryUpdate) -> Optional[CategoryResponse]:
        """카테고리 수정"""
        try:
            # 업데이트할 필드만 추출
            update_fields = []
            if update_data.name is not None:
                update_fields.append(f"name = '{update_data.name}'")
            if update_data.description is not None:
                update_fields.append(f"description = '{update_data.description}'")
            
            if not update_fields:
                # 수정할 필드가 없으면 현재 데이터 반환
                result = await real_supabase_service.execute_sql(
                    project_id=real_supabase_service.project_id,
                    query=f"SELECT id, name, description, created_at FROM categories WHERE id = '{category_id}'"
                )
                return CategoryResponse(**result[0]) if result else None
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"UPDATE categories SET {', '.join(update_fields)} WHERE id = '{category_id}' RETURNING id, name, description, created_at"
            )
            
            return CategoryResponse(**result[0]) if result else None
            
        except Exception as e:
            logger.error(f"카테고리 수정 오류: {str(e)}")
            return None
    
    @staticmethod
    async def delete_category(category_id: str) -> bool:
        """카테고리 삭제"""
        try:
            # 해당 카테고리를 사용하는 상품이 있는지 확인
            check_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as count FROM products WHERE category_id = '{category_id}'"
            )
            
            if check_result and check_result[0]['count'] > 0:
                raise ValueError("해당 카테고리를 사용하는 상품이 있어 삭제할 수 없습니다")
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"DELETE FROM categories WHERE id = '{category_id}'"
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"카테고리 삭제 오류: {str(e)}")
            return False
    
    @staticmethod
    async def create_product(product_data: ProductCreate, company_id: str) -> ProductResponse:
        """상품 생성"""
        try:
            product_id = str(uuid.uuid4())
            
            # 상품 코드 중복 확인
            existing = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id FROM products WHERE code = '{product_data.code}'"
            )
            
            if existing:
                raise ValueError("이미 존재하는 상품 코드입니다")
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO products (id, company_id, code, name, category_id, age_group, gender, wholesale_price, retail_price, description, is_active) VALUES ('{product_id}', '{company_id}', '{product_data.code}', '{product_data.name}', {f"'{product_data.category_id}'" if product_data.category_id else "NULL"}, '{product_data.age_group}', '{product_data.gender}', {product_data.wholesale_price}, {product_data.retail_price or "NULL"}, '{product_data.description or ""}', {product_data.is_active}) RETURNING id, company_id, code, name, category_id, age_group, gender, wholesale_price, retail_price, description, is_active, created_at, updated_at"
            )
            
            if not result or len(result) == 0:
                raise ValueError("상품 생성에 실패했습니다")
            
            # 초기 재고 생성
            await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO inventory (id, product_id, current_stock, minimum_stock) VALUES ('{str(uuid.uuid4())}', '{product_id}', 0, 0)"
            )
            
            product_data_dict = result[0]
            product_data_dict['images'] = []
            
            return ProductResponse(**product_data_dict)
            
        except Exception as e:
            logger.error(f"상품 생성 오류: {str(e)}")
            raise
    
    @staticmethod
    async def get_products(search_filter: ProductSearchFilter, company_id: Optional[str] = None) -> ProductListResponse:
        """상품 목록 조회 (검색 및 필터링)"""
        try:
            # WHERE 조건 구성
            conditions = []
            
            if company_id:
                conditions.append(f"p.company_id = '{company_id}'")
            
            if search_filter.name:
                conditions.append(f"p.name ILIKE '%{search_filter.name}%'")
            
            if search_filter.category_id:
                conditions.append(f"p.category_id = '{search_filter.category_id}'")
            
            if search_filter.age_group:
                conditions.append(f"p.age_group = '{search_filter.age_group}'")
            
            if search_filter.gender:
                conditions.append(f"p.gender = '{search_filter.gender}'")
            
            if search_filter.min_price is not None:
                conditions.append(f"p.wholesale_price >= {search_filter.min_price}")
            
            if search_filter.max_price is not None:
                conditions.append(f"p.wholesale_price <= {search_filter.max_price}")
            
            if search_filter.is_active is not None:
                conditions.append(f"p.is_active = {search_filter.is_active}")
            
            if search_filter.company_type:
                conditions.append(f"c.company_type = '{search_filter.company_type}'")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # 총 개수 조회
            count_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as total FROM products p LEFT JOIN companies c ON p.company_id = c.id {where_clause}"
            )
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (search_filter.page - 1) * search_filter.size
            
            # 상품 목록 조회
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT p.id, p.company_id, p.code, p.name, p.category_id, p.age_group, p.gender, p.wholesale_price, p.retail_price, p.description, p.images, p.is_active, p.created_at, p.updated_at, cat.name as category_name, c.name as company_name, inv.current_stock FROM products p LEFT JOIN categories cat ON p.category_id = cat.id LEFT JOIN companies c ON p.company_id = c.id LEFT JOIN inventory inv ON p.id = inv.product_id {where_clause} ORDER BY p.created_at DESC LIMIT {search_filter.size} OFFSET {offset}"
            )
            
            products = []
            if result:
                for row in result:
                    product_dict = dict(row)
                    if product_dict.get('images') is None:
                        product_dict['images'] = []
                    products.append(ProductResponse(**product_dict))
            
            has_next = (offset + search_filter.size) < total
            
            return ProductListResponse(
                products=products,
                total=total,
                page=search_filter.page,
                size=search_filter.size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"상품 목록 조회 오류: {str(e)}")
            return ProductListResponse(products=[], total=0, page=1, size=20, has_next=False)
    
    @staticmethod
    async def get_product_by_id(product_id: str) -> Optional[ProductResponse]:
        """상품 상세 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    p.id, p.company_id, p.code, p.name, p.category_id, p.age_group, p.gender,
                    p.wholesale_price, p.retail_price, p.description, p.images, p.is_active,
                    p.created_at, p.updated_at,
                    cat.name as category_name,
                    c.name as company_name,
                    inv.current_stock
                FROM products p
                LEFT JOIN categories cat ON p.category_id = cat.id
                LEFT JOIN companies c ON p.company_id = c.id
                LEFT JOIN inventory inv ON p.id = inv.product_id
                WHERE p.id = '{product_id}'
            """)
            
            if not result:
                return None
            
            product_dict = dict(result[0])
            if product_dict.get('images') is None:
                product_dict['images'] = []
            
            return ProductResponse(**product_dict)
            
        except Exception as e:
            logger.error(f"상품 조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def update_product(product_id: str, update_data: ProductUpdate, company_id: str) -> Optional[ProductResponse]:
        """상품 수정"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM products 
                WHERE id = '{product_id}' AND company_id = '{company_id}'
            """)
            
            if not ownership_check:
                raise ValueError("수정 권한이 없는 상품입니다")
            
            # 업데이트할 필드만 추출
            update_fields = []
            if update_data.name is not None:
                update_fields.append(f"name = '{update_data.name}'")
            if update_data.category_id is not None:
                update_fields.append(f"category_id = '{update_data.category_id}'")
            if update_data.age_group is not None:
                update_fields.append(f"age_group = '{update_data.age_group}'")
            if update_data.gender is not None:
                update_fields.append(f"gender = '{update_data.gender}'")
            if update_data.wholesale_price is not None:
                update_fields.append(f"wholesale_price = {update_data.wholesale_price}")
            if update_data.retail_price is not None:
                update_fields.append(f"retail_price = {update_data.retail_price}")
            if update_data.description is not None:
                update_fields.append(f"description = '{update_data.description}'")
            if update_data.is_active is not None:
                update_fields.append(f"is_active = {update_data.is_active}")
            
            if not update_fields:
                # 수정할 필드가 없으면 현재 데이터 반환
                return await ProductService.get_product_by_id(product_id)
            
            update_fields.append("updated_at = NOW()")
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"UPDATE products SET {', '.join(update_fields)} WHERE id = '{product_id}' RETURNING id, company_id, code, name, category_id, age_group, gender, wholesale_price, retail_price, description, images, is_active, created_at, updated_at"
            )
            
            if not result:
                return None
            
            product_dict = dict(result[0])
            if product_dict.get('images') is None:
                product_dict['images'] = []
            
            return ProductResponse(**product_dict)
            
        except Exception as e:
            logger.error(f"상품 수정 오류: {str(e)}")
            return None
    
    @staticmethod
    async def delete_product(product_id: str, company_id: str) -> bool:
        """상품 삭제"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM products 
                WHERE id = '{product_id}' AND company_id = '{company_id}'
            """)
            
            if not ownership_check:
                raise ValueError("삭제 권한이 없는 상품입니다")
            
            # 주문에 포함된 상품인지 확인
            order_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as count FROM order_items WHERE product_id = '{product_id}'"
            )
            
            if order_check and order_check[0]['count'] > 0:
                # 주문에 포함된 상품은 비활성화만 가능
                await real_supabase_service.execute_sql(
                    project_id=real_supabase_service.project_id,
                    query=f"UPDATE products SET is_active = false, updated_at = NOW() WHERE id = '{product_id}'"
                )
            return True
            
            # 완전 삭제 (재고도 함께 삭제됨 - CASCADE)
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"DELETE FROM products WHERE id = '{product_id}'"
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"상품 삭제 오류: {str(e)}")
            return False
    
    @staticmethod
    async def upload_product_images(upload_data: ProductImageUpload, company_id: str) -> bool:
        """상품 이미지 업로드"""
        try:
            # 상품 소유권 확인
            ownership_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id FROM products WHERE id = '{upload_data.product_id}' AND company_id = '{company_id}'"
            )
            
            if not ownership_check:
                raise ValueError("이미지 업로드 권한이 없는 상품입니다")
            
            # 이미지 URL 목록 생성
            image_urls = [img.url for img in upload_data.images]
            images_json = str(image_urls).replace("'", '"')  # JSON 형식으로 변환
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"UPDATE products SET images = '{images_json}', updated_at = NOW() WHERE id = '{upload_data.product_id}'"
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"상품 이미지 업로드 오류: {str(e)}")
            return False
    
    @staticmethod
    async def get_products_by_company(company_id: str, is_active: bool = True) -> List[ProductResponse]:
        """회사별 상품 목록 조회"""
        try:
            active_condition = f"AND p.is_active = {is_active}" if is_active is not None else ""
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    p.id, p.company_id, p.code, p.name, p.category_id, p.age_group, p.gender,
                    p.wholesale_price, p.retail_price, p.description, p.images, p.is_active,
                    p.created_at, p.updated_at,
                    cat.name as category_name,
                    c.name as company_name,
                    inv.current_stock
                FROM products p
                LEFT JOIN categories cat ON p.category_id = cat.id
                LEFT JOIN companies c ON p.company_id = c.id
                LEFT JOIN inventory inv ON p.id = inv.product_id
                WHERE p.company_id = '{company_id}' {active_condition}
                ORDER BY p.created_at DESC
            """)
            
            products = []
            if result:
                for row in result:
                    product_dict = dict(row)
                    if product_dict.get('images') is None:
                        product_dict['images'] = []
                    products.append(ProductResponse(**product_dict))
            
            return products
            
        except Exception as e:
            logger.error(f"회사 상품 목록 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def check_product_access(product_id: str, user_company_id: str, company_type: str) -> bool:
        """상품 접근 권한 확인"""
        try:
            if company_type == "wholesale":
                # 도매업체는 자사 상품만 접근 가능
                result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                    SELECT id FROM products 
                    WHERE id = '{product_id}' AND company_id = '{user_company_id}'
                """)
                return bool(result)
            
            elif company_type == "retail":
                # 소매업체는 거래 승인된 도매업체 상품만 접근 가능
                result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                    SELECT p.id 
                    FROM products p
                    JOIN company_relationships cr ON p.company_id = cr.wholesale_company_id
                    WHERE p.id = '{product_id}' 
                    AND cr.retail_company_id = '{user_company_id}'
                    AND cr.status = 'approved'
                """)
                return bool(result)
            
            return False
            
        except Exception as e:
            logger.error(f"상품 접근 권한 확인 오류: {str(e)}")
            return False
    
    @staticmethod
    async def get_company_products(company_id: str, search_filter: ProductSearchFilter) -> ProductListResponse:
        """회사별 상품 목록 조회 (도매업체용)"""
        try:
            # WHERE 조건 구성
            conditions = [f"p.company_id = '{company_id}'"]
            
            if search_filter.name:
                conditions.append(f"p.name ILIKE '%{search_filter.name}%'")
            
            if search_filter.category_id:
                conditions.append(f"p.category_id = '{search_filter.category_id}'")
            
            if search_filter.age_group:
                conditions.append(f"p.age_group = '{search_filter.age_group}'")
            
            if search_filter.gender:
                conditions.append(f"p.gender = '{search_filter.gender}'")
            
            if search_filter.min_price is not None:
                conditions.append(f"p.wholesale_price >= {search_filter.min_price}")
            
            if search_filter.max_price is not None:
                conditions.append(f"p.wholesale_price <= {search_filter.max_price}")
            
            if search_filter.is_active is not None:
                conditions.append(f"p.is_active = {search_filter.is_active}")
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            # 총 개수 조회
            count_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as total FROM products p LEFT JOIN companies c ON p.company_id = c.id {where_clause}"
            )
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (search_filter.page - 1) * search_filter.size
            
            # 상품 목록 조회
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT p.id, p.company_id, p.code, p.name, p.category_id, p.age_group, p.gender, p.wholesale_price, p.retail_price, p.description, p.images, p.is_active, p.created_at, p.updated_at, cat.name as category_name, c.name as company_name, inv.current_stock FROM products p LEFT JOIN categories cat ON p.category_id = cat.id LEFT JOIN companies c ON p.company_id = c.id LEFT JOIN inventory inv ON p.id = inv.product_id {where_clause} ORDER BY p.created_at DESC LIMIT {search_filter.size} OFFSET {offset}"
            )
            
            products = []
            if result:
                for row in result:
                    product_dict = dict(row)
                    if product_dict.get('images') is None:
                        product_dict['images'] = []
                    products.append(ProductResponse(**product_dict))
            
            has_next = (offset + search_filter.size) < total
            
            return ProductListResponse(
                products=products,
                total=total,
                page=search_filter.page,
                size=search_filter.size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"회사 상품 목록 조회 오류: {str(e)}")
            return ProductListResponse(products=[], total=0, page=1, size=20, has_next=False)
    
    @staticmethod
    async def search_products(search_filter: ProductSearchFilter) -> ProductListResponse:
        """상품 검색 (관리자용 - 모든 상품 검색)"""
        return await ProductService.get_products(search_filter)
    
    @staticmethod
    async def get_available_products_for_retail(retail_company_id: str, search_filter: ProductSearchFilter) -> ProductListResponse:
        """소매업체가 주문 가능한 상품 목록 조회"""
        try:
            # WHERE 조건 구성 (거래 승인된 도매업체 상품만)
            conditions = [
                f"cr.retail_company_id = '{retail_company_id}'",
                "cr.status = 'approved'",
                "p.is_active = true"
            ]
            
            if search_filter.name:
                conditions.append(f"p.name ILIKE '%{search_filter.name}%'")
            
            if search_filter.category_id:
                conditions.append(f"p.category_id = '{search_filter.category_id}'")
            
            if search_filter.age_group:
                conditions.append(f"p.age_group = '{search_filter.age_group}'")
            
            if search_filter.gender:
                conditions.append(f"p.gender = '{search_filter.gender}'")
            
            if search_filter.min_price is not None:
                conditions.append(f"p.wholesale_price >= {search_filter.min_price}")
            
            if search_filter.max_price is not None:
                conditions.append(f"p.wholesale_price <= {search_filter.max_price}")
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            # 총 개수 조회
            count_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT COUNT(*) as total
                FROM products p
                JOIN company_relationships cr ON p.company_id = cr.wholesale_company_id
                LEFT JOIN categories cat ON p.category_id = cat.id
                LEFT JOIN companies c ON p.company_id = c.id
                {where_clause}
            """)
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (search_filter.page - 1) * search_filter.size
            
            # 상품 목록 조회
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    p.id, p.company_id, p.code, p.name, p.category_id, p.age_group, p.gender,
                    p.wholesale_price, p.retail_price, p.description, p.images, p.is_active,
                    p.created_at, p.updated_at,
                    cat.name as category_name,
                    c.name as company_name,
                    inv.current_stock
                FROM products p
                JOIN company_relationships cr ON p.company_id = cr.wholesale_company_id
                LEFT JOIN categories cat ON p.category_id = cat.id
                LEFT JOIN companies c ON p.company_id = c.id
                LEFT JOIN inventory inv ON p.id = inv.product_id
                {where_clause}
                ORDER BY p.created_at DESC
                LIMIT {search_filter.size} OFFSET {offset}
            """)
            
            products = []
            if result:
                for row in result:
                    product_dict = dict(row)
                    if product_dict.get('images') is None:
                        product_dict['images'] = []
                    products.append(ProductResponse(**product_dict))
            
            has_next = (offset + search_filter.size) < total
            
            return ProductListResponse(
                products=products,
                total=total,
                page=search_filter.page,
                size=search_filter.size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"소매업체 상품 목록 조회 오류: {str(e)}")
            return ProductListResponse(products=[], total=0, page=1, size=20, has_next=False)