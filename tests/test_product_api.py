"""
상품 관리 API 테스트
TDD 기반 상품 및 카테고리 관리 시스템 테스트
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from main import app
from app.models.product import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse, ProductSearchFilter,
    ProductListResponse, InventoryResponse, InventoryUpdate,
    InventoryTransactionResponse, StockAdjustment, StockIn
)

client = TestClient(app)


class TestProductAPI:
    """상품 관리 API 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행"""
        self.test_user_id = str(uuid.uuid4())
        self.test_company_id = str(uuid.uuid4())
        self.test_product_id = str(uuid.uuid4())
        self.test_category_id = str(uuid.uuid4())
        
        # 테스트용 JWT 토큰
        self.wholesale_token = self._create_test_token("wholesale")
        self.retail_token = self._create_test_token("retail")
        self.admin_token = self._create_test_token("admin", "admin")
    
    def _create_test_token(self, company_type: str = "wholesale", role: str = "user") -> str:
        """테스트용 JWT 토큰 생성"""
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": role,
            "company_type": company_type
        }
        
        return create_access_token(user_data)


class TestCategoryAPI:
    """카테고리 API 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.test_category_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale")
        self.retail_token = self._create_test_token("retail")
        self.admin_token = self._create_test_token("admin", "admin")
    
    def _create_test_token(self, company_type: str = "wholesale", role: str = "user") -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": role,
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_create_category_success(self, mock_execute_sql):
        """카테고리 생성 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_category_id,
            "name": "상의",
            "description": "아동복 상의 카테고리",
            "created_at": datetime.now()
        }]
        
        # API 호출
        category_data = {
            "name": "상의",
            "description": "아동복 상의 카테고리"
        }
        
        response = client.post(
            "/api/products/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        # 검증
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "상의"
        assert data["description"] == "아동복 상의 카테고리"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_categories_success(self, mock_execute_sql):
        """카테고리 목록 조회 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [
            {
                "id": self.test_category_id,
                "name": "상의",
                "description": "아동복 상의",
                "created_at": datetime.now()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "하의",
                "description": "아동복 하의",
                "created_at": datetime.now()
            }
        ]
        
        # API 호출
        response = client.get(
            "/api/products/categories",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "상의"
        assert data[1]["name"] == "하의"
    
    def test_create_category_unauthorized(self):
        """관리자가 아닌 사용자 카테고리 생성 실패 테스트"""
        category_data = {
            "name": "신규 카테고리",
            "description": "테스트 카테고리"
        }
        
        response = client.post(
            "/api/products/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 403


class TestProductCRUDAPI:
    """상품 CRUD API 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.test_company_id = str(uuid.uuid4())
        self.test_product_id = str(uuid.uuid4())
        self.test_category_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale")
        self.retail_token = self._create_test_token("retail")
    
    def _create_test_token(self, company_type: str = "wholesale") -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": "user",
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_create_product_success(self, mock_execute_sql):
        """상품 생성 성공 테스트 (도매업체)"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_product_id,
            "company_id": self.test_company_id,
            "code": "TOP001",
            "name": "아동 티셔츠",
            "category_id": self.test_category_id,
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 15000,
            "retail_price": 25000,
            "description": "편안한 아동용 티셔츠",
            "is_active": True,
            "images": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "category_name": "상의",
            "company_name": "테스트 도매업체",
            "current_stock": None
        }]
        
        # API 호출
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "category_id": self.test_category_id,
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 15000,
            "retail_price": 25000,
            "description": "편안한 아동용 티셔츠"
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "TOP001"
        assert data["name"] == "아동 티셔츠"
        assert data["wholesale_price"] == 15000
        assert data["retail_price"] == 25000
    
    def test_create_product_retail_forbidden(self):
        """소매업체 상품 생성 금지 테스트"""
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 15000
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_products_wholesale_success(self, mock_execute_sql):
        """도매업체 상품 목록 조회 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_product_id,
            "company_id": self.test_company_id,
            "code": "TOP001",
            "name": "아동 티셔츠",
            "category_id": self.test_category_id,
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 15000,
            "retail_price": 25000,
            "description": "편안한 아동용 티셔츠",
            "is_active": True,
            "images": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "category_name": "상의",
            "company_name": "테스트 도매업체",
            "current_stock": 100
        }]
        
        # API 호출
        response = client.get(
            "/api/products",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 1
        assert data["products"][0]["name"] == "아동 티셔츠"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_products_retail_available_only(self, mock_execute_sql):
        """소매업체 이용 가능한 상품 목록 조회 테스트"""
        # Mock 설정 - 승인된 거래 관계의 도매업체 상품만 조회
        mock_execute_sql.return_value = [{
            "id": self.test_product_id,
            "company_id": self.test_company_id,
            "code": "TOP001",
            "name": "아동 티셔츠",
            "category_id": self.test_category_id,
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 15000,
            "retail_price": 25000,
            "description": "편안한 아동용 티셔츠",
            "is_active": True,
            "images": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "category_name": "상의",
            "company_name": "승인된 도매업체",
            "current_stock": 50
        }]
        
        # API 호출
        response = client.get(
            "/api/products",
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 1
        assert data["products"][0]["company_name"] == "승인된 도매업체"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_update_product_success(self, mock_execute_sql):
        """상품 수정 성공 테스트 (도매업체 소유자)"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_product_id,
            "company_id": self.test_company_id,
            "code": "TOP001",
            "name": "수정된 아동 티셔츠",
            "category_id": self.test_category_id,
            "age_group": "3-5y",
            "gender": "boys",
            "wholesale_price": 18000,
            "retail_price": 28000,
            "description": "수정된 설명",
            "is_active": True,
            "images": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }]
        
        # API 호출
        update_data = {
            "name": "수정된 아동 티셔츠",
            "gender": "boys",
            "wholesale_price": 18000,
            "retail_price": 28000,
            "description": "수정된 설명"
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 아동 티셔츠"
        assert data["wholesale_price"] == 18000
        assert data["retail_price"] == 28000
    
    def test_update_product_retail_forbidden(self):
        """소매업체 상품 수정 금지 테스트"""
        update_data = {
            "name": "수정된 이름"
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_delete_product_success(self, mock_execute_sql):
        """상품 삭제 성공 테스트 (비활성화)"""
        # Mock 설정
        mock_execute_sql.return_value = [{"success": True}]
        
        # API 호출
        response = client.delete(
            f"/api/products/{self.test_product_id}",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_search_products_with_filters(self, mock_execute_sql):
        """상품 검색 필터 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_product_id,
            "company_id": self.test_company_id,
            "code": "GIRL001",
            "name": "여아 원피스",
            "age_group": "3-5y",
            "gender": "girls",
            "wholesale_price": 20000,
            "retail_price": 35000,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }]
        
        # API 호출 - 필터 적용
        response = client.get(
            "/api/products?gender=girls&age_group=3-5y&min_price=15000&max_price=25000",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 1
        assert data["products"][0]["gender"] == "girls"
        assert data["products"][0]["age_group"] == "3-5y"


class TestInventoryAPI:
    """재고 관리 API 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.test_company_id = str(uuid.uuid4())
        self.test_product_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale")
        self.retail_token = self._create_test_token("retail")
    
    def _create_test_token(self, company_type: str = "wholesale") -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": "user",
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_inventory_success(self, mock_execute_sql):
        """재고 조회 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": str(uuid.uuid4()),
            "product_id": self.test_product_id,
            "current_stock": 100,
            "minimum_stock": 10,
            "last_updated": datetime.now(),
            "product_name": "아동 티셔츠",
            "product_code": "TOP001",
            "is_low_stock": False
        }]
        
        # API 호출
        response = client.get(
            f"/api/products/{self.test_product_id}/inventory",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["current_stock"] == 100
        assert data["minimum_stock"] == 10
        assert data["is_low_stock"] is False
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_update_inventory_success(self, mock_execute_sql):
        """재고 수정 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": str(uuid.uuid4()),
            "product_id": self.test_product_id,
            "current_stock": 150,
            "minimum_stock": 20,
            "last_updated": datetime.now(),
            "product_name": "아동 티셔츠",
            "product_code": "TOP001",
            "is_low_stock": False
        }]
        
        # API 호출
        update_data = {
            "current_stock": 150,
            "minimum_stock": 20
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}/inventory",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["current_stock"] == 150
        assert data["minimum_stock"] == 20
    
    def test_update_inventory_retail_forbidden(self):
        """소매업체 재고 수정 금지 테스트"""
        update_data = {
            "current_stock": 100
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}/inventory",
            json=update_data,
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_stock_adjustment_success(self, mock_execute_sql):
        """재고 조정 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{"success": True, "new_stock": 80}]
        
        # API 호출
        adjustment_data = {
            "product_id": self.test_product_id,
            "adjustment_quantity": -20,
            "reason": "손상품 제거"
        }
        
        response = client.post(
            "/api/inventory/adjust",
            json=adjustment_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["new_stock"] == 80
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_stock_in_success(self, mock_execute_sql):
        """입고 처리 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{"success": True, "new_stock": 150}]
        
        # API 호출
        stock_in_data = {
            "product_id": self.test_product_id,
            "quantity": 50,
            "notes": "새 상품 입고"
        }
        
        response = client.post(
            "/api/inventory/stock-in",
            json=stock_in_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_stock"] == 150
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_inventory_transactions_success(self, mock_execute_sql):
        """재고 거래내역 조회 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": str(uuid.uuid4()),
            "product_id": self.test_product_id,
            "transaction_type": "in",
            "quantity": 50,
            "previous_stock": 100,
            "current_stock": 150,
            "reference_type": "adjustment",
            "notes": "입고 처리",
            "created_by": self.test_user_id,
            "created_at": datetime.now(),
            "product_name": "아동 티셔츠",
            "product_code": "TOP001"
        }]
        
        # API 호출
        response = client.get(
            f"/api/products/{self.test_product_id}/inventory/transactions",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["transaction_type"] == "in"
        assert data[0]["quantity"] == 50


class TestProductValidation:
    """상품 데이터 검증 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale")
    
    def _create_test_token(self, company_type: str = "wholesale") -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": "user",
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    def test_invalid_age_group(self):
        """잘못된 연령대 검증 테스트"""
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "age_group": "invalid_age",  # 잘못된 연령대
            "gender": "unisex",
            "wholesale_price": 15000
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422
    
    def test_invalid_gender(self):
        """잘못된 성별 구분 검증 테스트"""
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "age_group": "3-5y",
            "gender": "invalid_gender",  # 잘못된 성별
            "wholesale_price": 15000
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422
    
    def test_negative_price(self):
        """음수 가격 검증 테스트"""
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": -1000  # 음수 가격
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422
    
    def test_retail_price_lower_than_wholesale(self):
        """소매가격이 도매가격보다 낮은 경우 검증 테스트"""
        product_data = {
            "code": "TOP001",
            "name": "아동 티셔츠",
            "age_group": "3-5y",
            "gender": "unisex",
            "wholesale_price": 20000,
            "retail_price": 15000  # 도매가격보다 낮음
        }
        
        response = client.post(
            "/api/products",
            json=product_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422


class TestInventoryConstraints:
    """재고 제약 조건 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.test_product_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale")
    
    def _create_test_token(self, company_type: str = "wholesale") -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": self.test_user_id,
            "email": "test@example.com",
            "role": "user",
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    def test_negative_stock_forbidden(self):
        """음수 재고 업데이트 금지 테스트"""
        update_data = {
            "current_stock": -10  # 음수 재고
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}/inventory",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422
    
    def test_zero_quantity_adjustment_forbidden(self):
        """0 수량 재고 조정 금지 테스트"""
        adjustment_data = {
            "product_id": self.test_product_id,
            "adjustment_quantity": 0,  # 0 수량
            "reason": "테스트"
        }
        
        response = client.post(
            "/api/inventory/adjust",
            json=adjustment_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 422


class TestProductAccessControl:
    """상품 접근 권한 테스트"""
    
    def setup_method(self):
        self.test_user_id = str(uuid.uuid4())
        self.other_user_id = str(uuid.uuid4())
        self.test_product_id = str(uuid.uuid4())
        self.wholesale_token = self._create_test_token("wholesale", self.test_user_id)
        self.other_wholesale_token = self._create_test_token("wholesale", self.other_user_id)
    
    def _create_test_token(self, company_type: str, user_id: str) -> str:
        from app.utils.jwt_utils import create_access_token
        
        user_data = {
            "user_id": user_id,
            "email": f"test-{user_id}@example.com",
            "role": "user",
            "company_type": company_type
        }
        
        return create_access_token(user_data)
    
    def test_update_other_company_product_forbidden(self):
        """다른 회사 상품 수정 권한 없음 테스트"""
        update_data = {
            "name": "수정된 이름"
        }
        
        response = client.put(
            f"/api/products/{self.test_product_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.other_wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 403
    
    def test_delete_other_company_product_forbidden(self):
        """다른 회사 상품 삭제 권한 없음 테스트"""
        response = client.delete(
            f"/api/products/{self.test_product_id}",
            headers={"Authorization": f"Bearer {self.other_wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 403