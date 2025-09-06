"""
회사 관리 서비스 클래스
도매업체-소매업체 관계 관리 시스템
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse, 
    CompanyRelationshipCreate, CompanyRelationshipUpdate, CompanyRelationshipResponse,
    CompanySearchFilter, CompanyPermission, CompanyStats
)
from services.real_supabase_service import real_supabase_service

logger = logging.getLogger(__name__)


class CompanyService:
    """회사 관리 서비스 (도매업체-소매업체 관계 관리)"""
    
    @staticmethod
    async def create_company(company_data: CompanyCreate) -> Optional[CompanyResponse]:
        """새 회사 생성"""
        try:
            company_id = str(uuid.uuid4())
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO companies (id, user_id, name, business_number, company_type, address, description, status) VALUES ('{company_id}', '{company_data.user_id}', '{company_data.name}', '{company_data.business_number}', '{company_data.company_type}', '{company_data.address}', '{company_data.description}', 'active') RETURNING id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at"
            )
            
            if result and len(result) > 0:
                return CompanyResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"회사 생성 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_company_by_id(company_id: str) -> Optional[CompanyResponse]:
        """회사 ID로 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at FROM companies WHERE id = '{company_id}'"
            )
            
            if result and len(result) > 0:
                return CompanyResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"회사 조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_company_by_user_id(user_id: str) -> Optional[CompanyResponse]:
        """사용자 ID로 소속 회사 조회"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at FROM companies WHERE user_id = '{user_id}' AND status = 'active'"
            )
            
            if result and len(result) > 0:
                return CompanyResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"사용자 회사 조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def update_company(company_id: str, company_data: CompanyUpdate) -> Optional[CompanyResponse]:
        """회사 정보 수정"""
        try:
            # 수정할 필드만 동적으로 구성
            update_fields = []
            if company_data.name is not None:
                update_fields.append(f"name = '{company_data.name}'")
            if company_data.business_number is not None:
                update_fields.append(f"business_number = '{company_data.business_number}'")
            if company_data.address is not None:
                update_fields.append(f"address = '{company_data.address}'")
            if company_data.description is not None:
                update_fields.append(f"description = '{company_data.description}'")
            
            if not update_fields:
                # 수정할 내용이 없으면 기존 데이터 반환
                return await CompanyService.get_company_by_id(company_id)
            
            update_fields.append("updated_at = NOW()")
            update_clause = ", ".join(update_fields)
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"UPDATE companies SET {update_clause} WHERE id = '{company_id}' RETURNING id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at"
            )
            
            if result and len(result) > 0:
                return CompanyResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"회사 정보 수정 오류: {str(e)}")
            return None
    
    @staticmethod
    async def search_companies(search_filter: CompanySearchFilter) -> List[CompanyResponse]:
        """회사 검색"""
        try:
            # WHERE 조건 구성
            where_conditions = []
            if search_filter.company_type:
                where_conditions.append(f"company_type = '{search_filter.company_type}'")
            if search_filter.status:
                where_conditions.append(f"status = '{search_filter.status}'")
            else:
                where_conditions.append("status = 'active'")  # 기본적으로 활성 상태만
            if search_filter.name:
                where_conditions.append(f"name ILIKE '%{search_filter.name}%'")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 페이지네이션
            offset = (search_filter.page - 1) * search_filter.size
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at FROM companies {where_clause} ORDER BY created_at DESC LIMIT {search_filter.size} OFFSET {offset}"
            )
            
            if result:
                return [CompanyResponse(**company) for company in result]
            return []
            
        except Exception as e:
            logger.error(f"회사 검색 오류: {str(e)}")
            return []
    
    @staticmethod
    async def get_wholesale_companies() -> List[CompanyResponse]:
        """도매업체 목록 조회 (소매업체가 거래 신청할 때 사용)"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query="SELECT id, user_id, name, business_number, company_type, address, description, status, created_at, updated_at FROM companies WHERE company_type = 'wholesale' AND status = 'active' ORDER BY name ASC"
            )
            
            if result:
                return [CompanyResponse(**company) for company in result]
            return []
            
        except Exception as e:
            logger.error(f"도매업체 목록 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def create_relationship(relationship_data: CompanyRelationshipCreate) -> Optional[CompanyRelationshipResponse]:
        """거래 관계 신청 (소매업체가 도매업체에 신청)"""
        try:
            # 중복 관계 확인
            existing = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id FROM company_relationships WHERE wholesale_company_id = '{relationship_data.wholesale_company_id}' AND retail_company_id = '{relationship_data.retail_company_id}'"
            )
            
            if existing and len(existing) > 0:
                raise ValueError("이미 존재하는 거래 관계입니다")
            
            relationship_id = str(uuid.uuid4())
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO company_relationships (id, wholesale_company_id, retail_company_id, status) VALUES ('{relationship_id}', '{relationship_data.wholesale_company_id}', '{relationship_data.retail_company_id}', 'pending') RETURNING id, wholesale_company_id, retail_company_id, status, created_at"
            )
            
            if result and len(result) > 0:
                return CompanyRelationshipResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"거래 관계 신청 오류: {str(e)}")
            raise ValueError(f"거래 관계 신청 실패: {str(e)}")
    
    @staticmethod
    async def update_relationship_status(relationship_id: str, update_data: CompanyRelationshipUpdate) -> Optional[CompanyRelationshipResponse]:
        """거래 관계 승인/거부 (도매업체가 처리)"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"UPDATE company_relationships SET status = '{update_data.status}', updated_at = NOW() WHERE id = '{relationship_id}' RETURNING id, wholesale_company_id, retail_company_id, status, created_at"
            )
            
            if result and len(result) > 0:
                return CompanyRelationshipResponse(**result[0])
            return None
            
        except Exception as e:
            logger.error(f"거래 관계 상태 업데이트 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_company_relationships(company_id: str, company_type: str) -> List[CompanyRelationshipResponse]:
        """회사의 거래 관계 목록 조회"""
        try:
            if company_type == "wholesale":
                # 도매업체: 자신을 도매업체로 하는 관계들
                query = f"""
                    SELECT cr.id, cr.wholesale_company_id, cr.retail_company_id, cr.status, cr.created_at,
                           c.name as retail_company_name, c.business_number as retail_business_number
                    FROM company_relationships cr
                    JOIN companies c ON c.id = cr.retail_company_id
                    WHERE cr.wholesale_company_id = '{company_id}'
                    ORDER BY cr.created_at DESC
                """
            else:
                # 소매업체: 자신을 소매업체로 하는 관계들
                query = f"""
                    SELECT cr.id, cr.wholesale_company_id, cr.retail_company_id, cr.status, cr.created_at,
                           c.name as wholesale_company_name, c.business_number as wholesale_business_number
                    FROM company_relationships cr
                    JOIN companies c ON c.id = cr.wholesale_company_id
                    WHERE cr.retail_company_id = '{company_id}'
                    ORDER BY cr.created_at DESC
                """
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=query
            )
            
            if result:
                return [CompanyRelationshipResponse(**rel) for rel in result]
            return []
            
        except Exception as e:
            logger.error(f"거래 관계 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def check_company_permission(user_id: str, company_id: str, action: str) -> bool:
        """회사 권한 확인"""
        try:
            # 사용자가 해당 회사의 소유자인지 확인
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id FROM companies WHERE id = '{company_id}' AND user_id = '{user_id}' AND status = 'active'"
            )
            
            return bool(result and len(result) > 0)
            
        except Exception as e:
            logger.error(f"회사 권한 확인 오류: {str(e)}")
            return False
    
    @staticmethod
    async def check_trading_relationship(wholesale_company_id: str, retail_company_id: str) -> bool:
        """거래 관계 승인 여부 확인"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT id FROM company_relationships WHERE wholesale_company_id = '{wholesale_company_id}' AND retail_company_id = '{retail_company_id}' AND status = 'approved'"
            )
            
            return bool(result and len(result) > 0)
            
        except Exception as e:
            logger.error(f"거래 관계 확인 오류: {str(e)}")
            return False
    
    @staticmethod
    async def get_company_stats(company_id: str) -> CompanyStats:
        """회사 통계 정보 조회"""
        try:
            # 기본 통계 (현재는 관계만 조회, 나중에 상품/주문 통계 추가)
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as total_relationships, COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_relationships FROM company_relationships WHERE wholesale_company_id = '{company_id}' OR retail_company_id = '{company_id}'"
            )
            
            if result and len(result) > 0:
                stats_data = result[0]
                return CompanyStats(
                    total_relationships=stats_data.get("total_relationships", 0),
                    pending_relationships=stats_data.get("pending_relationships", 0)
                )
            
            return CompanyStats()
            
        except Exception as e:
            logger.error(f"회사 통계 조회 오류: {str(e)}")
            return CompanyStats()