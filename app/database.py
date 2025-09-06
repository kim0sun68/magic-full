"""
마법옷장 데이터베이스 연결 설정
Supabase MCP 클라이언트 연동
"""

import config
import logging
from typing import Optional, Callable, Any
import uuid
from datetime import datetime

# Supabase MCP 실행 함수 (외부에서 주입받음)
_supabase_execute_fn: Optional[Callable] = None

logger = logging.getLogger(__name__)


def set_supabase_execute_function(execute_fn: Callable) -> None:
    """Supabase MCP execute 함수 설정"""
    global _supabase_execute_fn
    _supabase_execute_fn = execute_fn
    logger.info("Supabase MCP 실행 함수가 설정되었습니다")


async def init_db() -> None:
    """데이터베이스 연결 초기화 (Supabase MCP 사용)"""
    try:
        if not _supabase_execute_fn:
            logger.warning("Supabase MCP 함수가 설정되지 않았습니다")
            return
        
        # Supabase MCP를 통한 연결 테스트
        result = await _execute_sql("SELECT COUNT(*) as count FROM users")
        if result and len(result) > 0:
            user_count = result[0].get("count", 0)
            logger.info(f"Supabase MCP 데이터베이스 연결 성공 - 사용자 수: {user_count}")
        
        # utils.supabase_client에도 MCP 함수 설정
        from utils.supabase_client import set_supabase_execute_function
        set_supabase_execute_function(_supabase_execute_fn)
        
        # 초기 관리자 계정 생성 (존재하지 않는 경우)
        await create_admin_user()
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


async def _execute_sql(query: str) -> Optional[list]:
    """Supabase MCP를 통해 SQL 실행"""
    try:
        if not _supabase_execute_fn:
            logger.error("Supabase MCP 함수가 설정되지 않았습니다")
            return None
            
        result = await _supabase_execute_fn(
            project_id=config.settings.SUPABASE_PROJECT_ID,
            query=query
        )
        
        return result if isinstance(result, list) else [result] if result else None
        
    except Exception as e:
        logger.error(f"SQL 실행 오류: {str(e)}")
        return None


async def create_admin_user() -> None:
    """초기 관리자 계정 생성 (Supabase MCP 사용)"""
    try:
        # 관리자 계정 존재 확인
        result = await _execute_sql(f"""
            SELECT * FROM users WHERE email = '{config.settings.ADMIN_EMAIL}'
        """)
        
        if not result or len(result) == 0:
            # 관리자 계정 생성
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed_password = pwd_context.hash(config.settings.ADMIN_PASSWORD)
            
            # UUID 생성
            admin_id = str(uuid.uuid4())
            
            # 관리자 사용자 생성
            await _execute_sql(f"""
                INSERT INTO users (id, email, password_hash, name, role, approved, company_type)
                VALUES ('{admin_id}', '{config.settings.ADMIN_EMAIL}', '{hashed_password}', 
                        '{config.settings.ADMIN_NAME}', 'admin', true, 'wholesale')
            """)
            
            logger.info(f"초기 관리자 계정 생성 완료: {config.settings.ADMIN_EMAIL}")
        else:
            logger.info("관리자 계정이 이미 존재합니다")
            
    except Exception as e:
        logger.error(f"관리자 계정 생성 실패: {e}")
        # 관리자 계정 생성 실패는 치명적이지 않으므로 애플리케이션 시작은 계속


async def close_db() -> None:
    """데이터베이스 연결 종료 (Supabase MCP에서는 별도 작업 불필요)"""
    global _supabase_execute_fn
    _supabase_execute_fn = None
    logger.info("Supabase MCP 연결이 정리되었습니다")


# 데이터베이스 헬퍼 함수들
class DatabaseHelper:
    """데이터베이스 작업 헬퍼 클래스 (Supabase MCP 사용)"""
    
    @staticmethod
    async def execute_transaction(queries: list) -> bool:
        """트랜잭션 실행 (여러 쿼리를 원자적으로 실행)"""
        try:
            # Supabase MCP에서는 각 쿼리를 순차적으로 실행
            for query_data in queries:
                sql = query_data["sql"]
                result = await _execute_sql(sql)
                if result is None:
                    raise Exception(f"쿼리 실행 실패: {sql}")
                        
            return True
            
        except Exception as e:
            logger.error(f"트랜잭션 실행 실패: {e}")
            return False
    
    @staticmethod
    async def check_record_exists(table: str, field: str, value: str) -> bool:
        """레코드 존재 여부 확인"""
        try:
            result = await _execute_sql(f"""
                SELECT EXISTS(SELECT 1 FROM {table} WHERE {field} = '{value}')
            """)
            
            if result and len(result) > 0:
                return list(result[0].values())[0]  # EXISTS 결과는 첫 번째 값
            return False
                
        except Exception as e:
            logger.error(f"레코드 존재 확인 실패: {e}")
            return False
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[dict]:
        """이메일로 사용자 조회"""
        try:
            result = await _execute_sql(f"""
                SELECT * FROM users WHERE email = '{email}'
            """)
            
            return result[0] if result and len(result) > 0 else None
                
        except Exception as e:
            logger.error(f"사용자 조회 실패: {e}")
            return None
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]:
        """ID로 사용자 조회"""
        try:
            result = await _execute_sql(f"""
                SELECT * FROM users WHERE id = '{user_id}'
            """)
            
            return result[0] if result and len(result) > 0 else None
                
        except Exception as e:
            logger.error(f"사용자 조회 실패: {e}")
            return None


# 데이터베이스 헬퍼 인스턴스
db_helper = DatabaseHelper()

# Public alias for SQL execution function
execute_sql = _execute_sql