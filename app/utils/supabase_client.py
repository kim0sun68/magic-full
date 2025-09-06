"""
Supabase MCP 클라이언트 래퍼
AuthService에서 사용할 데이터베이스 연동 함수들
"""

import json
import logging
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

# Supabase MCP 함수들을 직접 import할 수 없으므로 외부에서 주입받음
_supabase_execute_fn = None


def set_supabase_execute_function(execute_fn):
    """Supabase MCP execute 함수 설정"""
    global _supabase_execute_fn
    _supabase_execute_fn = execute_fn


async def execute_sql_query(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Supabase MCP를 통해 SQL 쿼리 실행
    
    Args:
        query: 실행할 SQL 쿼리
        
    Returns:
        Optional[List[Dict[str, Any]]]: 쿼리 결과 리스트 또는 None
    """
    if not _supabase_execute_fn:
        # MCP 함수가 설정되지 않은 경우 직접 실행 (테스트 환경 등)
        logger.warning("Supabase MCP 함수가 설정되지 않아 직접 실행 시도")
        return await _execute_sql_direct(query)
    
    try:
        # Supabase MCP를 통해 쿼리 실행
        result = await _supabase_execute_fn(
            project_id=config.settings.SUPABASE_PROJECT_ID,
            query=query
        )
        
        # 결과 파싱
        if isinstance(result, str):
            # JSON 문자열인 경우 파싱
            try:
                parsed_result = json.loads(result)
                return parsed_result if isinstance(parsed_result, list) else [parsed_result]
            except json.JSONDecodeError:
                logger.error(f"JSON 파싱 실패: {result}")
                return None
        elif isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        else:
            logger.warning(f"예상치 못한 결과 타입: {type(result)}")
            return None
            
    except Exception as e:
        logger.error(f"Supabase SQL 실행 오류: {str(e)}")
        return None


async def _execute_sql_direct(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Supabase MCP 직접 호출 (fallback)
    """
    try:
        # 이 함수는 실제로는 Supabase MCP가 주입되어야 함
        # 현재는 임시로 빈 결과 반환
        logger.warning("Supabase MCP 직접 실행은 구현되지 않음")
        return None
        
    except Exception as e:
        logger.error(f"직접 SQL 실행 오류: {str(e)}")
        return None


# 헬퍼 함수들
async def check_user_exists(email: str) -> bool:
    """사용자 존재 여부 확인"""
    result = await execute_sql_query(f"""
        SELECT EXISTS(SELECT 1 FROM users WHERE email = '{email}')
    """)
    
    if result and len(result) > 0:
        return list(result[0].values())[0]  # EXISTS 결과는 첫 번째 값
    return False


async def get_user_count() -> int:
    """총 사용자 수 조회"""
    result = await execute_sql_query("SELECT COUNT(*) as count FROM users")
    
    if result and len(result) > 0:
        return result[0].get("count", 0)
    return 0


async def get_company_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 ID로 회사 정보 조회"""
    result = await execute_sql_query(f"""
        SELECT * FROM companies WHERE created_by = '{user_id}'
    """)
    
    return result[0] if result and len(result) > 0 else None