"""
관리자 API 라우터
사용자 승인 및 공지사항 관리 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List, Dict, Any
import uuid

from models.auth import UserApproval, UserResponse, UserDetailResponse
from models.notice import (
    NoticeCreate, NoticeUpdate, NoticeResponse, NoticeList, NoticeFilter
)
from services.admin_service import AdminService
from auth.middleware import get_admin_user_required


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users/pending", response_model=List[Dict[str, Any]])
async def get_pending_users(
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """승인 대기 중인 사용자 목록 조회"""
    try:
        pending_users = await AdminService.get_pending_users()
        return pending_users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/users/{user_id}/approve")
async def approve_user(
    user_id: uuid.UUID,
    approval_data: UserApproval,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """사용자 승인/거부 처리"""
    try:
        # user_id 일치성 확인
        if str(approval_data.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL의 사용자 ID와 요청 데이터의 사용자 ID가 일치하지 않습니다"
            )
        
        success = await AdminService.approve_user(str(admin_user["id"]), approval_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 승인 처리에 실패했습니다"
            )
        
        action = "승인" if approval_data.approved else "거부"
        return {
            "success": True,
            "message": f"사용자가 {action}되었습니다",
            "user_id": str(user_id),
            "approved": approval_data.approved
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/notices", response_model=NoticeList)
async def get_notices(
    is_important: bool = None,
    created_by: uuid.UUID = None,
    search: str = None,
    page: int = 1,
    per_page: int = 20,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """공지사항 목록 조회 (관리자용)"""
    try:
        filter_data = NoticeFilter(
            is_important=is_important,
            created_by=created_by,
            search=search,
            page=page,
            per_page=per_page
        )
        
        result = await AdminService.get_notices(filter_data)
        return NoticeList(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/notices", response_model=NoticeResponse)
async def create_notice(
    notice_data: NoticeCreate,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """공지사항 생성"""
    try:
        notice = await AdminService.create_notice(str(admin_user["id"]), notice_data)
        return NoticeResponse(**notice)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: uuid.UUID,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """공지사항 상세 조회"""
    try:
        notice = await AdminService.get_notice_by_id(str(notice_id))
        if not notice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="공지사항을 찾을 수 없습니다"
            )
        
        return NoticeResponse(**notice)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: uuid.UUID,
    notice_data: NoticeUpdate,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """공지사항 수정"""
    try:
        notice = await AdminService.update_notice(
            str(admin_user["id"]), str(notice_id), notice_data
        )
        
        if not notice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="공지사항을 찾을 수 없습니다"
            )
        
        return NoticeResponse(**notice)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/notices/{notice_id}")
async def delete_notice(
    notice_id: uuid.UUID,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """공지사항 삭제"""
    try:
        success = await AdminService.delete_notice(str(admin_user["id"]), str(notice_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="공지사항을 찾을 수 없습니다"
            )
        
        return {
            "success": True,
            "message": "공지사항이 삭제되었습니다",
            "notice_id": str(notice_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/statistics")
async def get_admin_statistics(
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """관리자 통계 조회"""
    try:
        user_stats = await AdminService.get_user_statistics()
        
        return {
            "users": user_stats,
            "timestamp": admin_user.get("created_at"),
            "admin_info": {
                "id": admin_user["id"],
                "name": admin_user["name"],
                "email": admin_user["email"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/users/{user_id}/detail", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: uuid.UUID,
    admin_user: Dict[str, Any] = Depends(get_admin_user_required)
):
    """사용자 상세 정보 조회 (관리자용)"""
    try:
        user_detail = await AdminService.get_user_detail(str(user_id))
        
        if not user_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return user_detail
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )