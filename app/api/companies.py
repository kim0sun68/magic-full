"""
회사 관리 API 엔드포인트
도매업체-소매업체 관계 관리 시스템
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from auth.middleware import get_current_user_required
from models.auth import UserResponse
from models.company import (
    CompanyResponse, CompanyUpdate, CompanySearchFilter,
    CompanyRelationshipCreate, CompanyRelationshipUpdate, CompanyRelationshipResponse,
    CompanyListResponse, CompanyStats
)
from services.company_service import CompanyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
async def get_companies(
    company_type: Optional[str] = Query(None, pattern="^(wholesale|retail)$"),
    status: Optional[str] = Query(None, pattern="^(active|inactive|suspended)$"),
    name: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_required)
) -> CompanyListResponse:
    """회사 목록 조회 (검색 및 필터링 지원)"""
    try:
        search_filter = CompanySearchFilter(
            company_type=company_type,
            status=status,
            name=name,
            page=page,
            size=size
        )
        
        companies = await CompanyService.search_companies(search_filter)
        
        return CompanyListResponse(
            companies=companies,
            total=len(companies),
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"회사 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 목록 조회에 실패했습니다")


@router.get("/wholesale", response_model=List[CompanyResponse])
async def get_wholesale_companies(
    current_user: dict = Depends(get_current_user_required)
) -> List[CompanyResponse]:
    """도매업체 목록 조회 (소매업체가 거래 신청할 때 사용)"""
    try:
        companies = await CompanyService.get_wholesale_companies()
        return companies
        
    except Exception as e:
        logger.error(f"도매업체 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="도매업체 목록 조회에 실패했습니다")


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    current_user: dict = Depends(get_current_user_required)
) -> CompanyResponse:
    """현재 사용자의 회사 정보 조회"""
    try:
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        
        if not company:
            raise HTTPException(status_code=404, detail="소속 회사를 찾을 수 없습니다")
        
        return company
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"내 회사 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 정보 조회에 실패했습니다")


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> CompanyResponse:
    """회사 정보 수정 (회사 소유자만 가능)"""
    try:
        # 권한 확인
        has_permission = await CompanyService.check_company_permission(
            str(current_user["id"]), company_id, "write"
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="회사 정보를 수정할 권한이 없습니다")
        
        # 회사 정보 수정
        updated_company = await CompanyService.update_company(company_id, company_data)
        
        if not updated_company:
            raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다")
        
        return updated_company
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회사 정보 수정 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 정보 수정에 실패했습니다")


@router.post("/relationships", response_model=CompanyRelationshipResponse, status_code=201)
async def create_company_relationship(
    relationship_data: CompanyRelationshipCreate,
    current_user: dict = Depends(get_current_user_required)
) -> CompanyRelationshipResponse:
    """거래 관계 신청 (소매업체가 도매업체에 신청)"""
    try:
        # 소매업체만 거래 신청 가능
        if current_user["company_type"] != "retail":
            raise HTTPException(status_code=403, detail="소매업체만 거래 신청이 가능합니다")
        
        # 자신의 회사 ID 확인
        my_company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not my_company:
            raise HTTPException(status_code=404, detail="소속 회사를 찾을 수 없습니다")
        
        # 신청 데이터의 소매업체 ID가 자신의 회사 ID와 일치하는지 확인
        if str(my_company.id) != str(relationship_data.retail_company_id):
            raise HTTPException(status_code=403, detail="본인 회사에 대해서만 거래 신청이 가능합니다")
        
        # 거래 관계 생성
        relationship = await CompanyService.create_relationship(relationship_data)
        
        if not relationship:
            raise HTTPException(status_code=500, detail="거래 관계 신청에 실패했습니다")
        
        return relationship
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"거래 관계 신청 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="거래 관계 신청에 실패했습니다")


@router.put("/relationships/{relationship_id}", response_model=CompanyRelationshipResponse)
async def update_company_relationship(
    relationship_id: str,
    update_data: CompanyRelationshipUpdate,
    current_user: dict = Depends(get_current_user_required)
) -> CompanyRelationshipResponse:
    """거래 관계 승인/거부 (도매업체가 처리)"""
    try:
        # 도매업체만 거래 관계 승인/거부 가능
        if current_user["company_type"] != "wholesale":
            raise HTTPException(status_code=403, detail="도매업체만 거래 관계를 승인/거부할 수 있습니다")
        
        # 거래 관계 상태 업데이트
        relationship = await CompanyService.update_relationship_status(relationship_id, update_data)
        
        if not relationship:
            raise HTTPException(status_code=404, detail="거래 관계를 찾을 수 없습니다")
        
        return relationship
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래 관계 상태 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="거래 관계 처리에 실패했습니다")


@router.get("/relationships", response_model=List[CompanyRelationshipResponse])
async def get_company_relationships(
    current_user: dict = Depends(get_current_user_required)
) -> List[CompanyRelationshipResponse]:
    """현재 사용자 회사의 거래 관계 목록 조회"""
    try:
        # 사용자의 회사 정보 조회
        my_company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not my_company:
            raise HTTPException(status_code=404, detail="소속 회사를 찾을 수 없습니다")
        
        # 거래 관계 목록 조회
        relationships = await CompanyService.get_company_relationships(
            str(my_company.id), 
            current_user["company_type"]
        )
        
        return relationships
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래 관계 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="거래 관계 목록 조회에 실패했습니다")


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company_detail(
    company_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> CompanyResponse:
    """회사 상세 정보 조회"""
    try:
        company = await CompanyService.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(status_code=404, detail="회사를 찾을 수 없습니다")
        
        # 권한 확인 (본인 회사이거나 거래 관계가 있는 경우만 상세 정보 조회 가능)
        if str(company.user_id) != str(current_user["id"]):
            # 거래 관계 확인
            my_company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
            if my_company:
                if current_user["company_type"] == "wholesale":
                    has_relationship = await CompanyService.check_trading_relationship(
                        str(my_company.id), company_id
                    )
                else:
                    has_relationship = await CompanyService.check_trading_relationship(
                        company_id, str(my_company.id)
                    )
                
                if not has_relationship:
                    raise HTTPException(status_code=403, detail="회사 정보를 조회할 권한이 없습니다")
            else:
                raise HTTPException(status_code=403, detail="회사 정보를 조회할 권한이 없습니다")
        
        return company
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회사 상세 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 정보 조회에 실패했습니다")


@router.get("/{company_id}/stats", response_model=CompanyStats)
async def get_company_stats(
    company_id: str,
    current_user: dict = Depends(get_current_user_required)
) -> CompanyStats:
    """회사 통계 정보 조회 (회사 소유자만 가능)"""
    try:
        # 권한 확인
        has_permission = await CompanyService.check_company_permission(
            str(current_user["id"]), company_id, "read"
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="회사 통계를 조회할 권한이 없습니다")
        
        stats = await CompanyService.get_company_stats(company_id)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"회사 통계 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="회사 통계 조회에 실패했습니다")