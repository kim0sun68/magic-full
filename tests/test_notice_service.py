"""
공지사항 서비스 테스트
TDD 기반 Notice 관련 AdminService 테스트
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.admin_service import AdminService
from models.notice import NoticeCreate, NoticeUpdate, NoticeFilter


class TestNoticeService:
    """공지사항 서비스 테스트"""

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_create_notice_success(self, mock_supabase):
        """공지사항 생성 성공 테스트"""
        # Given: 공지사항 생성 데이터
        admin_user_id = str(uuid.uuid4())
        notice_data = NoticeCreate(
            title="테스트 공지사항",
            content="이것은 테스트용 공지사항 내용입니다.",
            is_important=False
        )
        
        # Mock 응답 데이터
        notice_id = str(uuid.uuid4())
        mock_created_notice = {
            "id": notice_id,
            "title": "테스트 공지사항",
            "content": "이것은 테스트용 공지사항 내용입니다.",
            "is_important": False,
            "created_by": admin_user_id,
            "created_at": "2025-09-01T10:00:00Z",
            "updated_at": "2025-09-01T10:00:00Z",
            "created_by_name": "관리자"
        }
        
        # execute_sql 호출 순서: INSERT → SELECT
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": []},  # INSERT 결과
            {"data": [mock_created_notice]}  # SELECT 결과
        ])
        
        # When: 공지사항 생성
        result = await AdminService.create_notice(admin_user_id, notice_data)
        
        # Then: 올바른 결과 반환
        assert result["id"] == notice_id
        assert result["title"] == "테스트 공지사항"
        assert result["content"] == "이것은 테스트용 공지사항 내용입니다."
        assert result["is_important"] == False
        assert result["created_by"] == admin_user_id
        
        # execute_sql이 2번 호출되었는지 확인 (INSERT + SELECT)
        assert mock_supabase.execute_sql.call_count == 2
        
        # 첫 번째 호출(INSERT) 검증
        first_call = mock_supabase.execute_sql.call_args_list[0]
        assert 'project_id' in first_call.kwargs
        assert first_call.kwargs['project_id'] == "vrsbmygqyfvvuaixibrh"
        assert "INSERT INTO notices" in first_call.kwargs['query']
        
        # 두 번째 호출(SELECT) 검증
        second_call = mock_supabase.execute_sql.call_args_list[1]
        assert "SELECT" in second_call.kwargs['query']
        assert "LEFT JOIN users" in second_call.kwargs['query']

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_create_notice_important_success(self, mock_supabase):
        """중요 공지사항 생성 성공 테스트"""
        # Given: 중요 공지사항 데이터
        admin_user_id = str(uuid.uuid4())
        notice_data = NoticeCreate(
            title="중요 공지사항",
            content="이것은 중요한 공지사항입니다. 모든 사용자가 반드시 확인해주세요.",
            is_important=True
        )
        
        mock_created_notice = {
            "id": str(uuid.uuid4()),
            "title": "중요 공지사항", 
            "content": "이것은 중요한 공지사항입니다. 모든 사용자가 반드시 확인해주세요.",
            "is_important": True,
            "created_by": admin_user_id,
            "created_at": "2025-09-01T10:00:00Z",
            "updated_at": "2025-09-01T10:00:00Z",
            "created_by_name": "관리자"
        }
        
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": []},  # INSERT
            {"data": [mock_created_notice]}  # SELECT
        ])
        
        # When: 중요 공지사항 생성
        result = await AdminService.create_notice(admin_user_id, notice_data)
        
        # Then: 중요 공지사항으로 생성됨
        assert result["is_important"] == True
        assert result["title"] == "중요 공지사항"

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_create_notice_database_error(self, mock_supabase):
        """공지사항 생성 데이터베이스 오류 테스트"""
        # Given: DB 오류 시뮬레이션
        admin_user_id = str(uuid.uuid4())
        notice_data = NoticeCreate(
            title="테스트 공지사항",
            content="테스트 내용입니다.",
            is_important=False
        )
        
        mock_supabase.execute_sql = AsyncMock(side_effect=Exception("Database connection failed"))
        
        # When & Then: RuntimeError 발생 확인
        with pytest.raises(RuntimeError, match="공지사항 생성에 실패했습니다"):
            await AdminService.create_notice(admin_user_id, notice_data)

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notices_success(self, mock_supabase):
        """공지사항 목록 조회 성공 테스트"""
        # Given: 공지사항 목록 Mock 데이터
        mock_notices = [
            {
                "id": str(uuid.uuid4()),
                "title": "중요 공지사항",
                "content": "중요한 내용입니다.",
                "is_important": True,
                "created_by": str(uuid.uuid4()),
                "created_at": "2025-09-01T10:00:00Z",
                "updated_at": "2025-09-01T10:00:00Z",
                "created_by_name": "관리자"
            },
            {
                "id": str(uuid.uuid4()),
                "title": "일반 공지사항",
                "content": "일반적인 공지 내용입니다.",
                "is_important": False,
                "created_by": str(uuid.uuid4()),
                "created_at": "2025-09-01T09:00:00Z",
                "updated_at": "2025-09-01T09:00:00Z",
                "created_by_name": "관리자"
            }
        ]
        
        # execute_sql 호출 순서: COUNT → SELECT
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [{"total": 2}]},  # COUNT 결과
            {"data": mock_notices}  # SELECT 결과
        ])
        
        filter_data = NoticeFilter(page=1, per_page=20)
        
        # When: 공지사항 목록 조회
        result = await AdminService.get_notices(filter_data)
        
        # Then: 올바른 구조로 반환
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "per_page" in result
        assert "has_next" in result
        
        assert len(result["items"]) == 2
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["has_next"] == False
        
        # 중요 공지사항이 먼저 나와야 함
        assert result["items"][0]["is_important"] == True
        assert result["items"][1]["is_important"] == False

    @pytest.mark.asyncio  
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notices_empty_result(self, mock_supabase):
        """공지사항이 없는 경우 테스트"""
        # Given: 빈 결과
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [{"total": 0}]},  # COUNT 결과
            {"data": []}  # SELECT 결과
        ])
        
        filter_data = NoticeFilter(page=1, per_page=20)
        
        # When: 공지사항 목록 조회
        result = await AdminService.get_notices(filter_data)
        
        # Then: 빈 목록 반환
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notices_with_search_filter(self, mock_supabase):
        """검색 필터 적용 공지사항 조회 테스트"""
        # Given: 검색 결과 Mock 데이터
        mock_notices = [
            {
                "id": str(uuid.uuid4()),
                "title": "중요 업데이트 공지",
                "content": "시스템 업데이트 관련 공지사항입니다.",
                "is_important": True,
                "created_by": str(uuid.uuid4()),
                "created_at": "2025-09-01T10:00:00Z",
                "updated_at": "2025-09-01T10:00:00Z",
                "created_by_name": "관리자"
            }
        ]
        
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [{"total": 1}]},  # COUNT 결과
            {"data": mock_notices}  # SELECT 결과
        ])
        
        filter_data = NoticeFilter(search="업데이트", page=1, per_page=20)
        
        # When: 검색어로 공지사항 조회
        result = await AdminService.get_notices(filter_data)
        
        # Then: 검색 조건이 쿼리에 포함되었는지 확인
        assert len(result["items"]) == 1
        assert "업데이트" in result["items"][0]["title"]
        
        # 두 번째 호출(SELECT) 쿼리에 검색 조건 포함 확인
        second_call = mock_supabase.execute_sql.call_args_list[1]
        assert "ILIKE '%업데이트%'" in second_call.kwargs['query']

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_delete_notice_success(self, mock_supabase):
        """공지사항 삭제 성공 테스트"""
        # Given: 존재하는 공지사항
        notice_id = str(uuid.uuid4())
        admin_user_id = str(uuid.uuid4())
        
        existing_notice = {
            "id": notice_id,
            "title": "삭제할 공지사항",
            "content": "삭제될 내용입니다.",
            "is_important": False,
            "created_by": admin_user_id,
            "created_at": "2025-09-01T10:00:00Z",
            "updated_at": "2025-09-01T10:00:00Z",
            "created_by_name": "관리자"
        }
        
        # execute_sql 호출 순서: SELECT (존재 확인) → DELETE
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [existing_notice]},  # get_notice_by_id 호출
            {"data": []}  # DELETE 결과
        ])
        
        # When: 공지사항 삭제
        result = await AdminService.delete_notice(admin_user_id, notice_id)
        
        # Then: 삭제 성공
        assert result == True
        
        # execute_sql이 2번 호출되었는지 확인
        assert mock_supabase.execute_sql.call_count == 2
        
        # 두 번째 호출(DELETE) 검증
        second_call = mock_supabase.execute_sql.call_args_list[1]
        assert f"DELETE FROM notices WHERE id = '{notice_id}'" in second_call.kwargs['query']

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_delete_notice_not_found(self, mock_supabase):
        """존재하지 않는 공지사항 삭제 테스트"""
        # Given: 존재하지 않는 공지사항
        notice_id = str(uuid.uuid4())
        admin_user_id = str(uuid.uuid4())
        
        # get_notice_by_id가 None 반환
        mock_supabase.execute_sql = AsyncMock(return_value={"data": []})
        
        # When & Then: ValueError 발생 확인
        with pytest.raises(RuntimeError, match="공지사항 삭제에 실패했습니다"):
            await AdminService.delete_notice(admin_user_id, notice_id)

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_update_notice_success(self, mock_supabase):
        """공지사항 수정 성공 테스트"""
        # Given: 수정할 공지사항과 업데이트 데이터
        notice_id = str(uuid.uuid4())
        admin_user_id = str(uuid.uuid4())
        
        existing_notice = {
            "id": notice_id,
            "title": "기존 제목",
            "content": "기존 내용입니다.",
            "is_important": False,
            "created_by": admin_user_id,
            "created_at": "2025-09-01T10:00:00Z",
            "updated_at": "2025-09-01T10:00:00Z",
            "created_by_name": "관리자"
        }
        
        updated_notice = {
            **existing_notice,
            "title": "수정된 제목",
            "content": "수정된 내용입니다.",
            "is_important": True,
            "updated_at": "2025-09-01T11:00:00Z"
        }
        
        notice_update = NoticeUpdate(
            title="수정된 제목",
            content="수정된 내용입니다.",
            is_important=True
        )
        
        # execute_sql 호출 순서: SELECT (존재 확인) → UPDATE
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [existing_notice]},  # get_notice_by_id 호출
            {"data": [updated_notice]}  # UPDATE 결과
        ])
        
        # When: 공지사항 수정
        result = await AdminService.update_notice(admin_user_id, notice_id, notice_update)
        
        # Then: 수정된 결과 반환
        assert result["title"] == "수정된 제목"
        assert result["content"] == "수정된 내용입니다."
        assert result["is_important"] == True
        
        # execute_sql이 2번 호출되었는지 확인
        assert mock_supabase.execute_sql.call_count == 2

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notice_by_id_success(self, mock_supabase):
        """공지사항 상세 조회 성공 테스트"""
        # Given: 존재하는 공지사항
        notice_id = str(uuid.uuid4())
        mock_notice = {
            "id": notice_id,
            "title": "테스트 공지사항",
            "content": "테스트 내용입니다.",
            "is_important": False,
            "created_by": str(uuid.uuid4()),
            "created_at": "2025-09-01T10:00:00Z",
            "updated_at": "2025-09-01T10:00:00Z",
            "created_by_name": "관리자"
        }
        
        mock_supabase.execute_sql = AsyncMock(return_value={"data": [mock_notice]})
        
        # When: 공지사항 상세 조회
        result = await AdminService.get_notice_by_id(notice_id)
        
        # Then: 올바른 공지사항 반환
        assert result is not None
        assert result["id"] == notice_id
        assert result["title"] == "테스트 공지사항"
        assert result["created_by_name"] == "관리자"

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notice_by_id_not_found(self, mock_supabase):
        """존재하지 않는 공지사항 조회 테스트"""
        # Given: 존재하지 않는 공지사항
        notice_id = str(uuid.uuid4())
        mock_supabase.execute_sql = AsyncMock(return_value={"data": []})
        
        # When: 공지사항 상세 조회
        result = await AdminService.get_notice_by_id(notice_id)
        
        # Then: None 반환
        assert result is None

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notices_pagination(self, mock_supabase):
        """공지사항 페이징 테스트"""
        # Given: 페이징된 공지사항 데이터
        mock_notices = [
            {
                "id": str(uuid.uuid4()),
                "title": f"공지사항 {i}",
                "content": f"내용 {i}",
                "is_important": i % 2 == 0,  # 짝수는 중요
                "created_by": str(uuid.uuid4()),
                "created_at": f"2025-09-01T1{i}:00:00Z",
                "updated_at": f"2025-09-01T1{i}:00:00Z",
                "created_by_name": "관리자"
            }
            for i in range(5)  # 5개 공지사항
        ]
        
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [{"total": 25}]},  # 전체 25개
            {"data": mock_notices}  # 현재 페이지 5개
        ])
        
        filter_data = NoticeFilter(page=2, per_page=5)
        
        # When: 2페이지 조회
        result = await AdminService.get_notices(filter_data)
        
        # Then: 페이징 정보 확인
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["per_page"] == 5
        assert result["has_next"] == True  # 25 > 2*5 = 10
        assert len(result["items"]) == 5
        
        # LIMIT OFFSET 쿼리 확인
        second_call = mock_supabase.execute_sql.call_args_list[1]
        assert "LIMIT 5 OFFSET 5" in second_call.kwargs['query']

    @pytest.mark.asyncio
    @patch('services.admin_service.real_supabase_service')
    async def test_get_notices_important_filter(self, mock_supabase):
        """중요 공지사항 필터 테스트"""
        # Given: 중요 공지사항만 Mock 데이터
        mock_important_notices = [
            {
                "id": str(uuid.uuid4()),
                "title": "중요 공지사항",
                "content": "중요한 내용입니다.",
                "is_important": True,
                "created_by": str(uuid.uuid4()),
                "created_at": "2025-09-01T10:00:00Z",
                "updated_at": "2025-09-01T10:00:00Z",
                "created_by_name": "관리자"
            }
        ]
        
        mock_supabase.execute_sql = AsyncMock(side_effect=[
            {"data": [{"total": 1}]},  # COUNT 결과
            {"data": mock_important_notices}  # SELECT 결과
        ])
        
        filter_data = NoticeFilter(is_important=True, page=1, per_page=20)
        
        # When: 중요 공지사항만 조회
        result = await AdminService.get_notices(filter_data)
        
        # Then: 중요 공지사항만 반환
        assert len(result["items"]) == 1
        assert result["items"][0]["is_important"] == True
        
        # WHERE 절에 is_important 조건 포함 확인
        first_call = mock_supabase.execute_sql.call_args_list[0]
        assert "n.is_important = True" in first_call.kwargs['query']