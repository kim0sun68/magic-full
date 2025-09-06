"""
공지사항 API 테스트
TDD 기반 공지사항 API 엔드포인트 테스트
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models.notice import NoticeCreate, NoticeUpdate

client = TestClient(app)

class TestNoticeAPI:
    """공지사항 API 테스트"""
    
    def setup_method(self):
        """테스트 초기화"""
        self.client = client
        self.admin_user_id = str(uuid.uuid4())
        self.regular_user_id = str(uuid.uuid4())

    @patch('api.admin.AdminService.create_notice')
    @patch('auth.middleware.get_admin_user_required')
    def test_create_notice_success(self, mock_auth, mock_create_notice):
        """공지사항 생성 성공 테스트 (관리자)"""
        # Given: 관리자 권한과 공지사항 데이터
        mock_admin_user = {
            "id": self.admin_user_id,
            "role": "admin", 
            "name": "관리자",
            "email": "admin@example.com"
        }
        mock_auth.return_value = mock_admin_user
        
        created_notice = {
            "id": str(uuid.uuid4()),
            "title": "테스트 공지사항",
            "content": "테스트 내용입니다.",
            "is_important": False,
            "created_by": self.admin_user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by_name": "관리자"
        }
        mock_create_notice.return_value = created_notice
        
        notice_data = {
            "title": "테스트 공지사항",
            "content": "테스트 내용입니다.", 
            "is_important": False
        }
        
        # When: POST /api/admin/notices
        response = self.client.post("/api/admin/notices", json=notice_data)
        
        # Then: 201 Created 응답
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["title"] == "테스트 공지사항"
        assert response_data["content"] == "테스트 내용입니다."
        assert response_data["is_important"] == False
        
        # AdminService.create_notice가 올바른 파라미터로 호출되었는지 확인
        mock_create_notice.assert_called_once()

    @patch('auth.middleware.get_admin_user_required')
    def test_create_notice_invalid_data(self, mock_auth):
        """공지사항 생성 데이터 검증 실패 테스트"""
        # Given: 관리자 권한
        mock_admin_user = {
            "id": self.admin_user_id,
            "role": "admin",
            "name": "관리자",
            "email": "admin@example.com"
        }
        mock_auth.return_value = mock_admin_user
        
        # When: 잘못된 데이터로 공지사항 생성 시도
        invalid_data = {
            "title": "짧은",  # 최소 길이 미달
            "content": "짧음",  # 최소 길이 미달 (10자 이상 필요)
            "is_important": False
        }
        
        # Then: 422 Validation Error
        response = self.client.post("/api/admin/notices", json=invalid_data)
        assert response.status_code == 422

    @patch('api.admin.AdminService.get_notices')
    @patch('auth.middleware.get_admin_user_required')
    def test_get_admin_notices_success(self, mock_auth, mock_get_notices):
        """관리자 공지사항 목록 조회 성공 테스트"""
        # Given: 관리자 권한
        mock_admin_user = {
            "id": self.admin_user_id,
            "role": "admin",
            "name": "관리자", 
            "email": "admin@example.com"
        }
        mock_auth.return_value = mock_admin_user
        
        mock_notices_result = {
            "items": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "테스트 공지사항",
                    "content": "테스트 내용입니다.",
                    "is_important": False,
                    "created_by": self.admin_user_id,
                    "created_at": "2025-09-01T10:00:00Z",
                    "updated_at": "2025-09-01T10:00:00Z",
                    "created_by_name": "관리자"
                }
            ],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "has_next": False
        }
        mock_get_notices.return_value = mock_notices_result
        
        # When: GET /api/admin/notices
        response = self.client.get("/api/admin/notices")
        
        # Then: 200 OK 응답
        assert response.status_code == 200
        response_data = response.json()
        assert "items" in response_data
        assert "total" in response_data
        assert len(response_data["items"]) == 1

    def test_get_public_notices_success(self):
        """공용 공지사항 목록 조회 성공 테스트 (인증 불필요)"""
        # Given: 공용 API이므로 인증 없음
        
        with patch('main.AdminService.get_notices') as mock_get_notices:
            mock_notices_result = {
                "items": [
                    {
                        "id": str(uuid.uuid4()),
                        "title": "공용 공지사항",
                        "content": "모든 사용자가 볼 수 있는 공지사항입니다.",
                        "is_important": True,
                        "created_by": self.admin_user_id,
                        "created_at": "2025-09-01T10:00:00Z",
                        "updated_at": "2025-09-01T10:00:00Z",
                        "created_by_name": "관리자"
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 20,
                "has_next": False
            }
            mock_get_notices.return_value = mock_notices_result
            
            # When: GET /api/notices (공용 API)
            response = self.client.get("/api/notices")
            
            # Then: 200 OK 응답
            assert response.status_code == 200
            response_data = response.json()
            assert "items" in response_data
            assert len(response_data["items"]) == 1
            assert response_data["items"][0]["title"] == "공용 공지사항"

    @patch('api.admin.AdminService.delete_notice')
    @patch('auth.middleware.get_admin_user_required')
    def test_delete_notice_success(self, mock_auth, mock_delete_notice):
        """공지사항 삭제 성공 테스트 (관리자)"""
        # Given: 관리자 권한
        mock_admin_user = {
            "id": self.admin_user_id,
            "role": "admin",
            "name": "관리자",
            "email": "admin@example.com"
        }
        mock_auth.return_value = mock_admin_user
        mock_delete_notice.return_value = True
        
        notice_id = str(uuid.uuid4())
        
        # When: DELETE /api/admin/notices/{notice_id}
        response = self.client.delete(f"/api/admin/notices/{notice_id}")
        
        # Then: 200 OK 응답
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == True
        assert response_data["message"] == "공지사항이 삭제되었습니다"
        
        # AdminService.delete_notice가 올바른 파라미터로 호출되었는지 확인
        mock_delete_notice.assert_called_once_with(self.admin_user_id, notice_id)

    @patch('api.admin.AdminService.delete_notice')
    @patch('auth.middleware.get_admin_user_required')
    def test_delete_notice_not_found(self, mock_auth, mock_delete_notice):
        """존재하지 않는 공지사항 삭제 테스트"""
        # Given: 관리자 권한
        mock_admin_user = {
            "id": self.admin_user_id,
            "role": "admin",
            "name": "관리자", 
            "email": "admin@example.com"
        }
        mock_auth.return_value = mock_admin_user
        mock_delete_notice.return_value = False  # 삭제 실패
        
        notice_id = str(uuid.uuid4())
        
        # When: DELETE /api/admin/notices/{notice_id}
        response = self.client.delete(f"/api/admin/notices/{notice_id}")
        
        # Then: 404 Not Found
        assert response.status_code == 404
        response_data = response.json()
        assert "공지사항을 찾을 수 없습니다" in response_data["detail"]

    def test_get_admin_notices_unauthorized(self):
        """관리자 공지사항 API 비인증 접근 테스트"""
        # Given: 인증 없음
        
        # When: GET /api/admin/notices (인증 헤더 없음)
        response = self.client.get("/api/admin/notices")
        
        # Then: 401 Unauthorized (또는 FastAPI 기본 인증 오류)
        # 실제 미들웨어 구현에 따라 상태 코드가 달라질 수 있음
        assert response.status_code in [401, 403, 422]

    @patch('api.admin.AdminService.create_notice')
    def test_create_notice_unauthorized(self, mock_create_notice):
        """관리자 공지사항 생성 비인증 접근 테스트"""
        # Given: 인증 없음
        notice_data = {
            "title": "무단 공지사항",
            "content": "권한 없는 사용자가 작성하려는 공지사항입니다.",
            "is_important": False
        }
        
        # When: POST /api/admin/notices (인증 헤더 없음)
        response = self.client.post("/api/admin/notices", json=notice_data)
        
        # Then: 401 Unauthorized (또는 FastAPI 기본 인증 오류)
        assert response.status_code in [401, 403, 422]
        
        # AdminService.create_notice가 호출되지 않았는지 확인
        mock_create_notice.assert_not_called()

    def test_get_public_notices_pagination_params(self):
        """공용 공지사항 페이징 파라미터 테스트"""
        # Given: 페이징 파라미터
        
        with patch('main.AdminService.get_notices') as mock_get_notices:
            mock_notices_result = {
                "items": [],
                "total": 0,
                "page": 2,
                "per_page": 10,
                "has_next": False
            }
            mock_get_notices.return_value = mock_notices_result
            
            # When: GET /api/notices?page=2&per_page=10&is_important=true
            response = self.client.get("/api/notices?page=2&per_page=10&is_important=true")
            
            # Then: 200 OK 응답 및 올바른 파라미터 전달
            assert response.status_code == 200
            
            # AdminService.get_notices가 올바른 필터로 호출되었는지 확인
            mock_get_notices.assert_called_once()
            call_args = mock_get_notices.call_args[0][0]  # NoticeFilter 객체
            assert call_args.page == 2
            assert call_args.per_page == 10
            assert call_args.is_important == True