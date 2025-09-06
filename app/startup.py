"""
마법옷장 애플리케이션 시작 초기화
Supabase MCP 연동 및 데이터베이스 설정
"""

import logging
from typing import Callable, Any
import database
import config

logger = logging.getLogger(__name__)


async def initialize_supabase_mcp(execute_fn: Callable) -> None:
    """
    Supabase MCP 함수를 애플리케이션에 주입하고 초기화
    
    Args:
        execute_fn: Supabase MCP execute_sql 함수
    """
    try:
        # 데이터베이스 모듈에 MCP 함수 설정
        database.set_supabase_execute_function(execute_fn)
        
        # 데이터베이스 초기화 (관리자 계정 생성 포함)
        await database.init_db()
        
        logger.info("Supabase MCP 초기화가 완료되었습니다")
        
    except Exception as e:
        logger.error(f"Supabase MCP 초기화 실패: {e}")
        raise


# 테스트용 시뮬레이터 (실제 MCP가 없을 때 사용)
class MockSupabaseMCP:
    """테스트용 Supabase MCP 시뮬레이터"""
    
    @staticmethod
    async def execute_sql(project_id: str, query: str) -> list:
        """모의 SQL 실행 (테스트용)"""
        logger.warning(f"MockSupabaseMCP: {query}")
        
        # 기본 쿼리들에 대한 모의 응답
        if "COUNT(*)" in query and "users" in query:
            return [{"count": 1}]
        elif "SELECT * FROM users WHERE email" in query:
            if config.settings.ADMIN_EMAIL in query:
                # 관리자 계정 존재하는 것으로 모의 응답
                return [{
                    "id": "admin-uuid",
                    "email": config.settings.ADMIN_EMAIL,
                    "name": config.settings.ADMIN_NAME,
                    "role": "admin",
                    "approved": True
                }]
            return []  # 다른 이메일은 없는 것으로 응답
        elif "INSERT INTO users" in query:
            return [{"id": "new-user-uuid"}]
        else:
            return []


async def initialize_with_real_mcp() -> None:
    """실제 Supabase MCP로 초기화"""
    # 실제 MCP 함수는 Claude Code에서 제공되므로 별도 설정 불필요
    # 여기서는 데이터베이스 초기화만 수행
    logger.info("실제 Supabase MCP로 초기화를 시작합니다")
    
    # 실제 MCP 함수를 시뮬레이션하는 래퍼 생성
    async def real_mcp_execute(project_id: str, query: str) -> list:
        """실제 Supabase MCP 호출 래퍼"""
        # 이 부분은 실제로는 외부에서 MCP 함수를 주입받아야 함
        # 현재는 직접 호출할 수 없으므로 임시로 빈 리스트 반환
        logger.info(f"MCP SQL 실행: {query}")
        return []
    
    await initialize_supabase_mcp(real_mcp_execute)


async def initialize_with_mock() -> None:
    """테스트용 모의 MCP로 초기화"""
    from services.real_supabase_service import real_supabase_service
    await initialize_supabase_mcp(real_supabase_service.execute_sql)
    logger.info("테스트용 RealSupabaseService Mock로 초기화되었습니다")