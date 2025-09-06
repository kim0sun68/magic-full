"""
회사 관리 API 테스트
TDD 기반 회사 관계 관리 시스템 테스트
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from main import app
from models.company import CompanyCreate, CompanyResponse, CompanyRelationshipCreate

client = TestClient(app)


class TestCompanyAPI:
    """회사 관리 API 테스트"""
    
    def setup_method(self):
        """각 테스트 전 실행"""
        self.test_user_id = str(uuid.uuid4())
        self.test_company_id = str(uuid.uuid4())
        self.test_wholesale_company_id = str(uuid.uuid4())
        self.test_retail_company_id = str(uuid.uuid4())
        
        # 테스트용 JWT 토큰 (도매업체)
        self.wholesale_token = self._create_test_token("wholesale")
        # 테스트용 JWT 토큰 (소매업체)
        self.retail_token = self._create_test_token("retail")
        # 테스트용 JWT 토큰 (관리자)
        self.admin_token = self._create_test_token("admin")
    
    def _create_test_token(self, company_type: str = "retail", role: str = "user") -> str:
        """테스트용 JWT 토큰 생성"""
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
    async def test_get_companies_list_success(self, mock_execute_sql):
        """회사 목록 조회 성공 테스트"""
        # Mock 데이터 설정
        mock_companies = [
            {
                "id": self.test_company_id,
                "user_id": self.test_user_id,
                "name": "테스트 도매업체",
                "business_number": "123-45-67890",
                "company_type": "wholesale",
                "address": "서울시 중구 남대문로",
                "description": "아동복 도매업체",
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        mock_execute_sql.return_value = mock_companies
        
        # API 호출
        response = client.get(
            "/api/companies",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert "companies" in data
        assert len(data["companies"]) == 1
        assert data["companies"][0]["name"] == "테스트 도매업체"
        assert data["companies"][0]["company_type"] == "wholesale"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_wholesale_companies_success(self, mock_execute_sql):
        """도매업체 목록 조회 성공 테스트 (소매업체가 거래 신청할 때)"""
        # Mock 데이터 설정
        mock_companies = [
            {
                "id": self.test_wholesale_company_id,
                "user_id": str(uuid.uuid4()),
                "name": "마법동화 도매업체",
                "business_number": "111-22-33333",
                "company_type": "wholesale",
                "address": "서울시 중구 남대문로 1가",
                "description": "프리미엄 아동복 도매",
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        mock_execute_sql.return_value = mock_companies
        
        # API 호출 (소매업체 토큰 사용)
        response = client.get(
            "/api/companies/wholesale",
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "마법동화 도매업체"
        assert data[0]["company_type"] == "wholesale"
    
    def test_get_companies_unauthorized(self):
        """인증되지 않은 사용자 회사 목록 조회 실패 테스트"""
        response = client.get("/api/companies")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_create_relationship_success(self, mock_execute_sql):
        """거래 관계 신청 성공 테스트"""
        # Mock 설정 - 중복 확인 + 관계 생성
        mock_execute_sql.side_effect = [
            [],  # 중복 관계 없음
            [{
                "id": str(uuid.uuid4()),
                "wholesale_company_id": self.test_wholesale_company_id,
                "retail_company_id": self.test_retail_company_id,
                "status": "pending",
                "created_at": datetime.now()
            }]
        ]
        
        # API 호출 (소매업체가 도매업체에 거래 신청)
        relationship_data = {
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id
        }
        
        response = client.post(
            "/api/companies/relationships",
            json=relationship_data,
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 201
        data = response.json()
        assert data["wholesale_company_id"] == self.test_wholesale_company_id
        assert data["retail_company_id"] == self.test_retail_company_id
        assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_create_relationship_duplicate_error(self, mock_execute_sql):
        """중복 거래 관계 신청 오류 테스트"""
        # Mock 설정 - 중복 관계 존재
        mock_execute_sql.return_value = [{"id": str(uuid.uuid4())}]
        
        relationship_data = {
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id
        }
        
        response = client.post(
            "/api/companies/relationships",
            json=relationship_data,
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 400
        data = response.json()
        assert "이미 존재하는 거래 관계" in data["detail"]
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_approve_relationship_success(self, mock_execute_sql):
        """거래 관계 승인 성공 테스트 (도매업체가 승인)"""
        relationship_id = str(uuid.uuid4())
        
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": relationship_id,
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id,
            "status": "approved",
            "created_at": datetime.now()
        }]
        
        # API 호출 (도매업체가 승인)
        update_data = {
            "status": "approved",
            "reason": "우수 소매업체로 판단됨"
        }
        
        response = client.put(
            f"/api/companies/relationships/{relationship_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["id"] == relationship_id
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_reject_relationship_success(self, mock_execute_sql):
        """거래 관계 거부 성공 테스트 (도매업체가 거부)"""
        relationship_id = str(uuid.uuid4())
        
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": relationship_id,
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id,
            "status": "rejected",
            "created_at": datetime.now()
        }]
        
        # API 호출 (도매업체가 거부)
        update_data = {
            "status": "rejected",
            "reason": "거래 조건 불일치"
        }
        
        response = client.put(
            f"/api/companies/relationships/{relationship_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_my_company_success(self, mock_execute_sql):
        """내 회사 정보 조회 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_company_id,
            "user_id": self.test_user_id,
            "name": "내 도매업체",
            "business_number": "123-45-67890",
            "company_type": "wholesale",
            "address": "서울시 중구",
            "description": "테스트 도매업체",
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }]
        
        # API 호출
        response = client.get(
            "/api/companies/me",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "내 도매업체"
        assert data["company_type"] == "wholesale"
        assert data["user_id"] == self.test_user_id
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_company_relationships_wholesale(self, mock_execute_sql):
        """도매업체 거래 관계 목록 조회 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": str(uuid.uuid4()),
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id,
            "status": "approved",
            "created_at": datetime.now(),
            "retail_company_name": "테스트 소매업체",
            "retail_business_number": "111-22-33333"
        }]
        
        # API 호출
        response = client.get(
            "/api/companies/relationships",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "approved"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_get_company_relationships_retail(self, mock_execute_sql):
        """소매업체 거래 관계 목록 조회 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": str(uuid.uuid4()),
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id,
            "status": "pending",
            "created_at": datetime.now(),
            "wholesale_company_name": "테스트 도매업체",
            "wholesale_business_number": "123-45-67890"
        }]
        
        # API 호출
        response = client.get(
            "/api/companies/relationships",
            headers={"Authorization": f"Bearer {self.retail_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_update_company_success(self, mock_execute_sql):
        """회사 정보 수정 성공 테스트"""
        # Mock 설정
        mock_execute_sql.return_value = [{
            "id": self.test_company_id,
            "user_id": self.test_user_id,
            "name": "수정된 업체명",
            "business_number": "123-45-67890",
            "company_type": "wholesale",
            "address": "수정된 주소",
            "description": "수정된 설명",
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }]
        
        # API 호출
        update_data = {
            "name": "수정된 업체명",
            "address": "수정된 주소",
            "description": "수정된 설명"
        }
        
        response = client.put(
            f"/api/companies/{self.test_company_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 업체명"
        assert data["address"] == "수정된 주소"
    
    def test_invalid_company_type_filter(self):
        """잘못된 업체 유형 필터 테스트"""
        response = client.get(
            "/api/companies?company_type=invalid",
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증 (422 Validation Error 예상)
        assert response.status_code == 422
    
    def test_unauthorized_relationship_creation(self):
        """인증되지 않은 거래 관계 신청 테스트"""
        relationship_data = {
            "wholesale_company_id": self.test_wholesale_company_id,
            "retail_company_id": self.test_retail_company_id
        }
        
        response = client.post(
            "/api/companies/relationships",
            json=relationship_data
        )
        
        # 검증
        assert response.status_code == 401
    
    def test_invalid_relationship_status_update(self):
        """잘못된 관계 상태 업데이트 테스트"""
        relationship_id = str(uuid.uuid4())
        
        # 잘못된 상태값
        update_data = {
            "status": "invalid_status"
        }
        
        response = client.put(
            f"/api/companies/relationships/{relationship_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {self.wholesale_token}"}
        )
        
        # 검증 (422 Validation Error 예상)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_company_permission_check_success(self, mock_execute_sql):
        """회사 권한 확인 성공 테스트"""
        # Mock 설정 - 사용자가 해당 회사 소유자
        mock_execute_sql.return_value = [{"id": self.test_company_id}]
        
        # 회사 서비스에서 권한 확인
        from services.company_service import CompanyService
        
        result = await CompanyService.check_company_permission(
            self.test_user_id, 
            self.test_company_id, 
            "write"
        )
        
        # 검증
        assert result is True
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_company_permission_check_failure(self, mock_execute_sql):
        """회사 권한 확인 실패 테스트"""
        # Mock 설정 - 사용자가 해당 회사 소유자가 아님
        mock_execute_sql.return_value = []
        
        # 회사 서비스에서 권한 확인
        from services.company_service import CompanyService
        
        result = await CompanyService.check_company_permission(
            self.test_user_id, 
            self.test_company_id, 
            "write"
        )
        
        # 검증
        assert result is False
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_trading_relationship_check_approved(self, mock_execute_sql):
        """승인된 거래 관계 확인 테스트"""
        # Mock 설정 - 승인된 관계 존재
        mock_execute_sql.return_value = [{"id": str(uuid.uuid4())}]
        
        from services.company_service import CompanyService
        
        result = await CompanyService.check_trading_relationship(
            self.test_wholesale_company_id,
            self.test_retail_company_id
        )
        
        # 검증
        assert result is True
    
    @pytest.mark.asyncio
    @patch('services.real_supabase_service.real_supabase_service.execute_sql')
    async def test_trading_relationship_check_not_approved(self, mock_execute_sql):
        """승인되지 않은 거래 관계 확인 테스트"""
        # Mock 설정 - 승인된 관계 없음
        mock_execute_sql.return_value = []
        
        from services.company_service import CompanyService
        
        result = await CompanyService.check_trading_relationship(
            self.test_wholesale_company_id,
            self.test_retail_company_id
        )
        
        # 검증
        assert result is False