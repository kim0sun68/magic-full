"""
관리자 상세보기 API 통합 테스트
실제 API 엔드포인트 및 인증 시스템 통합 테스트
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.auth import UserDetailResponse


class TestAdminDetailAPIIntegration:
    """관리자 상세보기 API 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.client = TestClient(app)
        self.admin_user_id = str(uuid.uuid4())
        self.test_user_id = str(uuid.uuid4())
        
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    def test_get_user_detail_success(self, mock_get_detail, mock_auth):
        """정상적인 사용자 상세보기 API 호출"""
        # Given
        mock_auth.return_value = {
            'id': self.admin_user_id,
            'email': 'admin@example.com',
            'role': 'admin'
        }
        
        mock_detail_response = UserDetailResponse(
            id=uuid.UUID(self.test_user_id),
            email='test@example.com',
            name='테스트업체',
            phone='010-1234-5678',
            role='user',
            approved=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            company_id=uuid.uuid4(),
            company_name='ABC상회',
            business_number='123-45-67890',
            company_type='wholesale',
            company_address='서울시 중구 남대문로',
            company_description='아동복 도매업체',
            company_status='active',
            company_created_at=datetime.now()
        )
        mock_get_detail.return_value = mock_detail_response
        
        # When
        response = self.client.get(f"/api/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == 'test@example.com'
        assert data['company_name'] == 'ABC상회'
        assert data['company_type'] == 'wholesale'
        mock_get_detail.assert_called_once_with(self.test_user_id)
    
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    def test_get_user_detail_not_found(self, mock_get_detail, mock_auth):
        """존재하지 않는 사용자 조회"""
        # Given
        mock_auth.return_value = {
            'id': self.admin_user_id,
            'role': 'admin'
        }
        mock_get_detail.return_value = None
        
        # When
        response = self.client.get(f"/api/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 404
        assert "사용자를 찾을 수 없습니다" in response.json()['detail']
    
    @patch('auth.middleware.get_admin_user_required')
    def test_get_user_detail_unauthorized(self, mock_auth):
        """관리자 권한 없는 사용자의 접근"""
        # Given
        mock_auth.side_effect = Exception("Unauthorized")
        
        # When
        response = self.client.get(f"/api/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 500  # FastAPI wraps auth exceptions
    
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    def test_get_user_detail_invalid_uuid(self, mock_get_detail, mock_auth):
        """잘못된 UUID 형식 처리"""
        # Given
        mock_auth.return_value = {'id': self.admin_user_id, 'role': 'admin'}
        invalid_user_id = "invalid-uuid-format"
        
        # When
        response = self.client.get(f"/api/admin/users/{invalid_user_id}/detail")
        
        # Then
        assert response.status_code == 422  # FastAPI validation error
    
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    def test_get_user_detail_service_error(self, mock_get_detail, mock_auth):
        """서비스 계층 오류 처리"""
        # Given
        mock_auth.return_value = {'id': self.admin_user_id, 'role': 'admin'}
        mock_get_detail.side_effect = RuntimeError("Database error")
        
        # When
        response = self.client.get(f"/api/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 500
        assert "Database error" in response.json()['detail']
    
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    def test_get_user_detail_without_company(self, mock_get_detail, mock_auth):
        """회사 정보 없는 사용자 (관리자 계정 등)"""
        # Given
        mock_auth.return_value = {'id': self.admin_user_id, 'role': 'admin'}
        
        mock_detail_response = UserDetailResponse(
            id=uuid.UUID(self.test_user_id),
            email='admin@example.com',
            name='시스템관리자',
            role='admin',
            approved=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            # 회사 정보 모두 None
            company_id=None,
            company_name=None,
            business_number=None,
            company_type=None,
            company_address=None,
            company_description=None,
            company_status=None,
            company_created_at=None
        )
        mock_get_detail.return_value = mock_detail_response
        
        # When
        response = self.client.get(f"/api/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data['role'] == 'admin'
        assert data['company_id'] is None
        assert data['company_name'] is None
    
    def test_admin_detail_page_route(self):
        """관리자 상세페이지 라우트 테스트"""
        # When
        response = self.client.get(f"/admin/users/{self.test_user_id}/detail")
        
        # Then
        assert response.status_code == 200
        assert "admin-detail.html" in str(response.content) or response.headers.get('content-type') == 'text/html; charset=utf-8'


class TestAdminDetailWorkflow:
    """관리자 상세보기 워크플로우 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)
        
    @patch('auth.middleware.get_admin_user_required')
    @patch('services.admin_service.AdminService.get_user_detail')
    @patch('services.admin_service.AdminService.approve_user')
    def test_detail_to_approval_workflow(self, mock_approve, mock_get_detail, mock_auth):
        """상세보기 → 승인 처리 워크플로우"""
        # Given
        admin_user_id = str(uuid.uuid4())
        test_user_id = str(uuid.uuid4())
        
        mock_auth.return_value = {'id': admin_user_id, 'role': 'admin'}
        
        # 상세 정보 조회 성공
        mock_detail = UserDetailResponse(
            id=uuid.UUID(test_user_id),
            email='test@example.com',
            name='테스트업체',
            approved=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            company_name='ABC상회'
        )
        mock_get_detail.return_value = mock_detail
        
        # 승인 처리 성공
        mock_approve.return_value = True
        
        # When - 상세 정보 조회
        detail_response = self.client.get(f"/api/admin/users/{test_user_id}/detail")
        
        # Then - 상세 정보 조회 성공
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data['approved'] == False
        
        # When - 승인 처리
        approval_response = self.client.put(
            f"/api/admin/users/{test_user_id}/approve",
            json={
                'user_id': test_user_id,
                'approved': True,
                'reason': '상세 검토 후 승인'
            }
        )
        
        # Then - 승인 처리 성공
        assert approval_response.status_code == 200
        approval_data = approval_response.json()
        assert approval_data['approved'] == True
        assert "승인" in approval_data['message']