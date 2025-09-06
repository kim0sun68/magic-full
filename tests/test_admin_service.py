"""
관리자 서비스 테스트
TDD 기반 AdminService 테스트
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.admin_service import AdminService
from models.auth import UserApproval
from models.notice import NoticeCreate, NoticeUpdate, NoticeFilter


class TestAdminService:
    """AdminService 테스트"""

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_pending_users_success(self, mock_supabase):
        """승인 대기 사용자 목록 조회 성공 테스트"""
        # Given: Mock DB 응답 데이터
        mock_pending_users = [
            {
                "id": str(uuid.uuid4()),
                "email": "pending1@example.com",
                "name": "대기사용자1",
                "phone": "010-1111-1111",
                "company_type": "retail",
                "created_at": "2025-09-01T10:00:00Z",
                "company_name": "테스트소매업체",
                "business_number": "123-45-67890",
                "address": "서울시 중구 남대문시장"
            },
            {
                "id": str(uuid.uuid4()),
                "email": "pending2@example.com",
                "name": "대기사용자2",
                "phone": "010-2222-2222",
                "company_type": "wholesale",
                "created_at": "2025-09-01T11:00:00Z",
                "company_name": "테스트도매업체",
                "business_number": "987-65-43210",
                "address": "서울시 중구 동대문시장"
            }
        ]
        
        mock_supabase.execute_sql = AsyncMock(return_value={"data": mock_pending_users})
        
        # When: 승인 대기 사용자 목록 조회
        result = await AdminService.get_pending_users()
        
        # Then: 올바른 결과 반환
        assert len(result) == 2
        assert result[0]["email"] == "pending1@example.com"
        assert result[1]["email"] == "pending2@example.com"
        
        # execute_sql이 올바른 파라미터로 호출되었는지 확인
        mock_supabase.execute_sql.assert_called_once()
        call_args = mock_supabase.execute_sql.call_args
        assert 'project_id' in call_args.kwargs
        assert call_args.kwargs['project_id'] == "vrsbmygqyfvvuaixibrh"
        assert 'query' in call_args.kwargs
        assert "WHERE u.approved = false" in call_args.kwargs['query']

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_pending_users_empty_result(self, mock_supabase):
        """승인 대기 사용자가 없는 경우 테스트"""
        # Given: 빈 결과
        mock_supabase.execute_sql = AsyncMock(return_value={"data": []})
        
        # When: 승인 대기 사용자 목록 조회
        result = await AdminService.get_pending_users()
        
        # Then: 빈 리스트 반환
        assert result == []
        mock_supabase.execute_sql.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_pending_users_database_error(self, mock_supabase):
        """데이터베이스 오류 시 예외 처리 테스트"""
        # Given: DB 오류 시뮬레이션
        mock_supabase.execute_sql = AsyncMock(side_effect=Exception("Database connection failed"))
        
        # When & Then: RuntimeError 발생 확인
        with pytest.raises(RuntimeError, match="사용자 목록 조회에 실패했습니다"):
            await AdminService.get_pending_users()

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_approve_user_success(self, mock_supabase):
        """사용자 승인 성공 테스트"""
        # Given: 승인 대기 사용자와 승인 데이터
        user_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())
        
        mock_user = {
            "id": user_id,
            "email": "test@example.com",
            "approved": False
        }
        
        approval_data = UserApproval(
            user_id=uuid.UUID(user_id),
            approved=True,
            reason="적격한 업체입니다"
        )
        
        mock_supabase.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_supabase.execute_sql = AsyncMock(return_value={"data": [{"id": user_id}]})
        
        # When: 사용자 승인 처리
        result = await AdminService.approve_user(admin_id, approval_data)
        
        # Then: 성공 결과 반환
        assert result is True
        mock_supabase.get_user_by_id.assert_called_once_with(user_id)
        mock_supabase.execute_sql.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_user_statistics_success(self, mock_supabase):
        """사용자 통계 조회 성공 테스트"""
        # Given: Mock 통계 데이터
        mock_stats = {
            "total_users": 10,
            "approved_users": 8,
            "pending_users": 2,
            "admin_users": 1,
            "wholesale_users": 4,
            "retail_users": 5
        }
        
        mock_supabase.execute_sql = AsyncMock(return_value={"data": [mock_stats]})
        
        # When: 사용자 통계 조회
        result = await AdminService.get_user_statistics()
        
        # Then: 올바른 통계 반환
        assert result == mock_stats
        mock_supabase.execute_sql.assert_called_once()
        call_args = mock_supabase.execute_sql.call_args
        assert 'project_id' in call_args.kwargs
        assert call_args.kwargs['project_id'] == "vrsbmygqyfvvuaixibrh"

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_delete_notice_success(self, mock_supabase):
        """공지사항 삭제 성공 테스트"""
        # Given: 존재하는 공지사항
        notice_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())
        
        mock_notice = {
            "id": notice_id,
            "title": "테스트 공지사항",
            "content": "테스트 내용"
        }
        
        mock_supabase.execute_sql = AsyncMock(return_value={"data": [mock_notice]})
        
        # When: 공지사항 삭제
        result = await AdminService.delete_notice(admin_id, notice_id)
        
        # Then: 성공 결과 반환
        assert result is True
        
        # execute_sql이 project_id와 함께 호출되었는지 확인
        calls = mock_supabase.execute_sql.call_args_list
        assert len(calls) >= 1
        # 마지막 호출(DELETE 쿼리)에서 project_id 확인
        delete_call = calls[-1]
        assert 'project_id' in delete_call.kwargs
        assert delete_call.kwargs['project_id'] == "vrsbmygqyfvvuaixibrh"