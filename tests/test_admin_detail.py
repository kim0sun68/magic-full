"""
관리자 상세보기 기능 테스트
TDD 기반 사용자 승인 상세 정보 조회 테스트
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from datetime import datetime

from services.admin_service import AdminService
from models.auth import UserDetailResponse


class TestAdminDetailService:
    """AdminService의 get_user_detail 메서드 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_user_detail_success(self):
        """정상적인 사용자 상세 정보 조회"""
        # Given
        user_id = str(uuid.uuid4())
        mock_user_data = {
            'id': user_id,
            'email': 'test@example.com',
            'name': '테스트업체',
            'phone': '010-1234-5678',
            'role': 'user',
            'approved': False,
            'approved_at': None,
            'approved_by': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'company_id': str(uuid.uuid4()),
            'company_name': 'ABC상회',
            'business_number': '123-45-67890',
            'company_type': 'wholesale',
            'company_address': '서울시 중구 남대문로',
            'company_description': '아동복 도매업체',
            'company_status': 'active',
            'company_created_at': datetime.now()
        }
        
        with patch('services.admin_service.real_supabase_service.execute_sql') as mock_execute:
            mock_execute.return_value = {'data': [mock_user_data]}
            
            # When
            result = await AdminService.get_user_detail(user_id)
            
            # Then
            assert result is not None
            assert isinstance(result, UserDetailResponse)
            assert str(result.id) == user_id
            assert result.email == 'test@example.com'
            assert result.company_name == 'ABC상회'
            assert result.company_type == 'wholesale'
    
    @pytest.mark.asyncio
    async def test_get_user_detail_not_found(self):
        """존재하지 않는 사용자 조회"""
        # Given
        user_id = str(uuid.uuid4())
        
        with patch('services.admin_service.real_supabase_service.execute_sql') as mock_execute:
            mock_execute.return_value = {'data': []}
            
            # When
            result = await AdminService.get_user_detail(user_id)
            
            # Then
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_detail_without_company(self):
        """회사 정보 없는 사용자 조회"""
        # Given
        user_id = str(uuid.uuid4())
        mock_user_data = {
            'id': user_id,
            'email': 'admin@example.com',
            'name': '관리자',
            'phone': None,
            'role': 'admin',
            'approved': True,
            'approved_at': datetime.now(),
            'approved_by': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'company_id': None,
            'company_name': None,
            'business_number': None,
            'company_type': None,
            'company_address': None,
            'company_description': None,
            'company_status': None,
            'company_created_at': None
        }
        
        with patch('services.admin_service.real_supabase_service.execute_sql') as mock_execute:
            mock_execute.return_value = {'data': [mock_user_data]}
            
            # When
            result = await AdminService.get_user_detail(user_id)
            
            # Then
            assert result is not None
            assert result.role == 'admin'
            assert result.company_id is None
            assert result.company_name is None
    
    @pytest.mark.asyncio
    async def test_get_user_detail_database_error(self):
        """데이터베이스 오류 처리"""
        # Given
        user_id = str(uuid.uuid4())
        
        with patch('services.admin_service.real_supabase_service.execute_sql') as mock_execute:
            mock_execute.side_effect = Exception("Database connection failed")
            
            # When/Then
            with pytest.raises(RuntimeError, match="사용자 상세 정보 조회에 실패했습니다"):
                await AdminService.get_user_detail(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_detail_invalid_uuid(self):
        """잘못된 UUID 형식 처리"""
        # Given
        invalid_user_id = "invalid-uuid"
        
        with patch('services.admin_service.real_supabase_service.execute_sql') as mock_execute:
            mock_execute.side_effect = Exception("Invalid UUID format")
            
            # When/Then
            with pytest.raises(RuntimeError):
                await AdminService.get_user_detail(invalid_user_id)


class TestAdminDetailAPI:
    """관리자 상세보기 API 엔드포인트 테스트"""
    
    @pytest.mark.asyncio
    async def test_admin_detail_endpoint_success(self):
        """정상적인 관리자 상세보기 API 호출"""
        # Given
        user_id = uuid.uuid4()
        
        mock_detail = UserDetailResponse(
            id=user_id,
            email='test@example.com',
            name='테스트업체',
            company_name='ABC상회',
            company_type='wholesale',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('services.admin_service.AdminService.get_user_detail') as mock_service:
            mock_service.return_value = mock_detail
            
            # When
            from api.admin import get_user_detail
            admin_user = {'id': str(uuid.uuid4()), 'role': 'admin'}
            result = await get_user_detail(user_id, admin_user)
            
            # Then
            assert result == mock_detail
            mock_service.assert_called_once_with(str(user_id))
    
    @pytest.mark.asyncio
    async def test_admin_detail_endpoint_not_found(self):
        """존재하지 않는 사용자 API 호출"""
        # Given
        user_id = uuid.uuid4()
        
        with patch('services.admin_service.AdminService.get_user_detail') as mock_service:
            mock_service.return_value = None
            
            # When/Then
            from fastapi import HTTPException
            from api.admin import get_user_detail
            admin_user = {'id': str(uuid.uuid4()), 'role': 'admin'}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_user_detail(user_id, admin_user)
            
            assert exc_info.value.status_code == 404
            assert "사용자를 찾을 수 없습니다" in str(exc_info.value.detail)