"""
관리자 서비스 클래스
사용자 승인 및 공지사항 관리
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from models.auth import UserApproval, UserDetailResponse
from models.notice import NoticeCreate, NoticeUpdate, NoticeFilter
from services.real_supabase_service import real_supabase_service

logger = logging.getLogger(__name__)


class AdminService:
    """관리자 서비스 클래스 (Supabase MCP 연동)"""
    
    @staticmethod
    async def get_pending_users() -> List[Dict[str, Any]]:
        """승인 대기 중인 사용자 목록 조회"""
        try:
            # 승인되지 않은 사용자만 조회
            query = """
                SELECT u.id, u.email, u.name, u.phone, u.company_type, u.created_at,
                       c.name as company_name, c.business_number, c.address
                FROM users u
                LEFT JOIN companies c ON u.id = c.user_id
                WHERE u.approved = false
                ORDER BY u.created_at DESC
            """
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            return result.get('data', [])
            
        except Exception as e:
            logger.error(f"승인 대기 사용자 조회 실패: {str(e)}")
            raise RuntimeError(f"사용자 목록 조회에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def approve_user(admin_user_id: str, approval_data: UserApproval) -> bool:
        """사용자 승인/거부 처리"""
        try:
            user_id = str(approval_data.user_id)
            
            # 사용자 존재 확인
            user = await real_supabase_service.get_user_by_id(user_id)
            if not user:
                raise ValueError("존재하지 않는 사용자입니다")
            
            # 이미 승인된 사용자인지 확인
            if user.get("approved", False):
                raise ValueError("이미 승인된 사용자입니다")
            
            # 승인 상태 업데이트
            current_time = datetime.now()
            update_data = {
                'approved': approval_data.approved,
                'approved_at': current_time.isoformat() if approval_data.approved else None,
                'approved_by': admin_user_id if approval_data.approved else None,
                'updated_at': current_time.isoformat()
            }
            
            # 사용자 승인 상태 업데이트
            query = f"""
                UPDATE users 
                SET approved = {approval_data.approved}, 
                    approved_at = '{current_time.isoformat()}',
                    approved_by = '{admin_user_id}',
                    updated_at = '{current_time.isoformat()}'
                WHERE id = '{user_id}'
                RETURNING *
            """
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            
            if approval_data.approved:
                logger.info(f"사용자 승인 완료: {user_id} by {admin_user_id}")
            else:
                logger.info(f"사용자 승인 거부: {user_id} by {admin_user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"사용자 승인 처리 실패: {str(e)}")
            raise RuntimeError(f"승인 처리에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def get_notices(filter_data: NoticeFilter) -> Dict[str, Any]:
        """공지사항 목록 조회 (페이징)"""
        try:
            # 기본 쿼리
            base_query = """
                SELECT n.id, n.title, n.content, n.is_important, n.created_by, n.created_at, n.updated_at,
                       u.name as created_by_name
                FROM notices n
                LEFT JOIN users u ON n.created_by = u.id
            """
            
            # 필터 조건 추가
            conditions = []
            if filter_data.is_important is not None:
                conditions.append(f"n.is_important = {filter_data.is_important}")
            if filter_data.created_by:
                conditions.append(f"n.created_by = '{filter_data.created_by}'")
            if filter_data.search:
                search_term = filter_data.search.replace("'", "''")  # SQL injection 방지
                conditions.append(f"(n.title ILIKE '%{search_term}%' OR n.content ILIKE '%{search_term}%')")
            
            where_clause = ""
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
            
            # 총 개수 조회
            count_query = f"SELECT COUNT(*) as total FROM notices n{where_clause}"
            count_result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=count_query)
            total = count_result.get('data', [{}])[0].get('total', 0)
            
            # 페이징된 데이터 조회
            offset = (filter_data.page - 1) * filter_data.per_page
            data_query = f"""
                {base_query}{where_clause}
                ORDER BY n.is_important DESC, n.created_at DESC
                LIMIT {filter_data.per_page} OFFSET {offset}
            """
            
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=data_query)
            notices = result.get('data', [])
            
            return {
                "items": notices,
                "total": total,
                "page": filter_data.page,
                "per_page": filter_data.per_page,
                "has_next": total > filter_data.page * filter_data.per_page
            }
            
        except Exception as e:
            logger.error(f"공지사항 목록 조회 실패: {str(e)}")
            raise RuntimeError(f"공지사항 조회에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def create_notice(admin_user_id: str, notice_data: NoticeCreate) -> Dict[str, Any]:
        """공지사항 생성"""
        try:
            notice_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            escaped_title = notice_data.title.replace("'", "''")
            escaped_content = notice_data.content.replace("'", "''")
            
            insert_query = f"""
                INSERT INTO notices (id, title, content, is_important, created_by, created_at, updated_at)
                VALUES ('{notice_id}', '{escaped_title}', 
                        '{escaped_content}', {notice_data.is_important},
                        '{admin_user_id}', '{current_time.isoformat()}', '{current_time.isoformat()}')
            """
            
            await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=insert_query)
            
            # 생성된 공지사항을 사용자 정보와 함께 조회
            select_query = f"""
                SELECT n.id, n.title, n.content, n.is_important, n.created_by, n.created_at, n.updated_at,
                       u.name as created_by_name
                FROM notices n
                LEFT JOIN users u ON n.created_by = u.id
                WHERE n.id = '{notice_id}'
            """
            
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=select_query)
            notices = result.get('data', [])
            
            if not notices:
                # 직접 생성된 데이터 반환 (SELECT 실패 시)
                admin_query = f"SELECT name FROM users WHERE id = '{admin_user_id}'"
                admin_result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=admin_query)
                admin_data = admin_result.get('data', [])
                admin_name = admin_data[0].get('name', '관리자') if admin_data else '관리자'
                
                notice = {
                    'id': notice_id,
                    'title': notice_data.title,
                    'content': notice_data.content,
                    'is_important': notice_data.is_important,
                    'created_by': admin_user_id,
                    'created_at': current_time.isoformat(),
                    'updated_at': current_time.isoformat(),
                    'created_by_name': admin_name
                }
            else:
                notice = notices[0]
            
            logger.info(f"공지사항 생성 완료: {notice_id} by {admin_user_id}")
            return notice
            
        except Exception as e:
            logger.error(f"공지사항 생성 실패: {str(e)}")
            raise RuntimeError(f"공지사항 생성에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def get_notice_by_id(notice_id: str) -> Optional[Dict[str, Any]]:
        """공지사항 상세 조회"""
        try:
            query = f"""
                SELECT n.id, n.title, n.content, n.is_important, n.created_by, n.created_at, n.updated_at,
                       u.name as created_by_name
                FROM notices n
                LEFT JOIN users u ON n.created_by = u.id
                WHERE n.id = '{notice_id}'
            """
            
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            notices = result.get('data', [])
            
            return notices[0] if notices else None
            
        except Exception as e:
            logger.error(f"공지사항 조회 실패: {str(e)}")
            return None
    
    @staticmethod
    async def update_notice(admin_user_id: str, notice_id: str, notice_data: NoticeUpdate) -> Optional[Dict[str, Any]]:
        """공지사항 수정"""
        try:
            # 공지사항 존재 확인
            existing_notice = await AdminService.get_notice_by_id(notice_id)
            if not existing_notice:
                raise ValueError("존재하지 않는 공지사항입니다")
            
            # 수정할 필드만 추출
            update_fields = []
            if notice_data.title is not None:
                escaped_title = notice_data.title.replace("'", "''")
                update_fields.append(f"title = '{escaped_title}'")
            if notice_data.content is not None:
                escaped_content = notice_data.content.replace("'", "''")
                update_fields.append(f"content = '{escaped_content}'")
            if notice_data.is_important is not None:
                update_fields.append(f"is_important = {notice_data.is_important}")
            
            if not update_fields:
                return existing_notice  # 변경사항 없음
            
            current_time = datetime.now()
            update_fields.append(f"updated_at = '{current_time.isoformat()}'")
            
            query = f"""
                UPDATE notices 
                SET {', '.join(update_fields)}
                WHERE id = '{notice_id}'
                RETURNING *
            """
            
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            notice = result.get('data', [{}])[0]
            
            logger.info(f"공지사항 수정 완료: {notice_id} by {admin_user_id}")
            return notice
            
        except Exception as e:
            logger.error(f"공지사항 수정 실패: {str(e)}")
            raise RuntimeError(f"공지사항 수정에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def delete_notice(admin_user_id: str, notice_id: str) -> bool:
        """공지사항 삭제"""
        try:
            # 공지사항 존재 확인
            existing_notice = await AdminService.get_notice_by_id(notice_id)
            if not existing_notice:
                raise ValueError("존재하지 않는 공지사항입니다")
            
            query = f"DELETE FROM notices WHERE id = '{notice_id}'"
            await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            
            logger.info(f"공지사항 삭제 완료: {notice_id} by {admin_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"공지사항 삭제 실패: {str(e)}")
            raise RuntimeError(f"공지사항 삭제에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def get_user_statistics() -> Dict[str, Any]:
        """사용자 통계 조회"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN approved = true THEN 1 END) as approved_users,
                    COUNT(CASE WHEN approved = false THEN 1 END) as pending_users,
                    COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
                    COUNT(CASE WHEN company_type = 'wholesale' THEN 1 END) as wholesale_users,
                    COUNT(CASE WHEN company_type = 'retail' THEN 1 END) as retail_users
                FROM users
            """
            
            result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
            stats = result.get('data', [{}])[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"사용자 통계 조회 실패: {str(e)}")
            raise RuntimeError(f"통계 조회에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def get_user_detail(user_id: str) -> Optional[UserDetailResponse]:
        """사용자 상세 정보 조회 (users + companies 조인)"""
        try:
            query = """
                SELECT 
                    u.id, u.email, u.name, u.phone, u.role, u.approved, 
                    u.approved_at, u.approved_by, u.created_at, u.updated_at,
                    c.id as company_id, c.name as company_name, c.business_number,
                    c.company_type, c.address as company_address, 
                    c.description as company_description, c.status as company_status,
                    c.created_at as company_created_at
                FROM users u
                LEFT JOIN companies c ON u.id = c.user_id
                WHERE u.id = %s
            """
            
            result = await real_supabase_service.execute_sql(
                project_id="vrsbmygqyfvvuaixibrh", 
                query=query.replace('%s', f"'{user_id}'")
            )
            
            users = result.get('data', [])
            if not users:
                return None
            
            user_data = users[0]
            return UserDetailResponse(**user_data)
            
        except Exception as e:
            logger.error(f"사용자 상세 정보 조회 실패: {str(e)}")
            raise RuntimeError(f"사용자 상세 정보 조회에 실패했습니다: {str(e)}")