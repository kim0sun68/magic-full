"""
인증 서비스 클래스
Supabase MCP를 통한 데이터베이스 연동
"""

import uuid
import logging
from typing import Optional
from passlib.context import CryptContext

from models.auth import UserCreate
from services.real_supabase_service import real_supabase_service

logger = logging.getLogger(__name__)

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """인증 서비스 클래스 (Supabase MCP 연동)"""
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> dict:
        """새 사용자 생성"""
        try:
            # 이메일 중복 확인
            existing_user = await real_supabase_service.get_user_by_email(user_data.email)
            if existing_user:
                raise ValueError("이미 존재하는 이메일입니다")
            
            # 비밀번호 해싱
            hashed_password = pwd_context.hash(user_data.password)
            
            # 새 사용자 ID 생성
            user_id = str(uuid.uuid4())
            
            # 사용자 데이터 준비
            new_user_data = {
                'id': user_id,
                'email': user_data.email,
                'password_hash': hashed_password,
                'name': user_data.name,
                'phone': user_data.phone,
                'company_type': user_data.company_type
            }
            
            # 사용자 생성
            user = await real_supabase_service.create_user(new_user_data)
            
            if user:
                # 회사 정보도 생성
                await AuthService._create_company_for_user(user_id, user_data)
                return user
            else:
                raise ValueError("사용자 생성에 실패했습니다")
                
        except Exception as e:
            raise ValueError(f"사용자 생성 오류: {str(e)}")
    
    @staticmethod 
    async def authenticate_user(email: str, password: str) -> Optional[dict]:
        """사용자 인증"""
        try:
            # 이메일로 사용자 조회
            user = await real_supabase_service.get_user_by_email(email)
            if not user:
                return None
            
            # 비밀번호 검증
            if not pwd_context.verify(password, user["password_hash"]):
                return None
            
            # 비밀번호 해시 제거 후 반환
            user_info = {k: v for k, v in user.items() if k != "password_hash"}
            return user_info
            
        except Exception:
            return None
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]:
        """사용자 ID로 사용자 조회"""
        try:
            return await real_supabase_service.get_user_by_id(user_id)
        except Exception:
            return None
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[dict]:
        """이메일로 사용자 조회"""
        try:
            return await real_supabase_service.get_user_by_email(email)
        except Exception:
            return None
    
    @staticmethod
    async def change_user_password(user_id: str, current_password: str, new_password: str) -> bool:
        """사용자 비밀번호 변경"""
        try:
            # 현재 사용자 조회
            user = await real_supabase_service.get_user_by_id(user_id)
            if not user:
                return False
            
            # 전체 사용자 정보(비밀번호 포함) 조회
            user_with_password = await real_supabase_service.get_user_by_email(user["email"])
            if not user_with_password:
                return False
            
            # 현재 비밀번호 확인
            if not pwd_context.verify(current_password, user_with_password["password_hash"]):
                return False
            
            # 새 비밀번호 해싱
            new_hashed_password = pwd_context.hash(new_password)
            
            # 비밀번호 업데이트
            return await real_supabase_service.update_user_password(user_id, new_hashed_password)
            
        except Exception:
            return False
    
    @staticmethod
    async def send_password_reset_email(email: str) -> bool:
        """비밀번호 재설정 이메일 전송"""
        # 실제 이메일 서비스 연동 필요 (현재는 성공으로 가정)
        logger.info(f"비밀번호 재설정 이메일 전송: {email}")
        return True
    
    @staticmethod
    async def reset_user_password(token: str, new_password: str) -> bool:
        """재설정 토큰으로 비밀번호 재설정"""
        try:
            # TODO: 토큰 검증 로직 구현 필요
            logger.info(f"비밀번호 재설정 토큰: {token}")
            
            # 현재는 간단히 새 비밀번호만 설정
            new_hashed_password = pwd_context.hash(new_password)
            logger.info(f"새 비밀번호 해싱 완료: {len(new_hashed_password)} 문자")
            
            # TODO: 실제 구현에서는 토큰에서 사용자 정보 추출 필요
            return True
            
        except Exception:
            return False
    
    @staticmethod
    async def approve_user(user_id: str, approved: bool, reason: Optional[str] = None) -> dict:
        """사용자 승인/거부 처리"""
        try:
            # 승인 이유 로깅
            if reason:
                logger.info(f"사용자 승인 이유: {reason}")
            
            # 사용자 승인 상태 업데이트
            result = await real_supabase_service.approve_user(user_id, approved)
            
            if result:
                return result
            else:
                raise ValueError("사용자를 찾을 수 없습니다")
                
        except Exception as e:
            raise ValueError(f"사용자 승인 처리 오류: {str(e)}")
    
    @staticmethod
    async def _create_company_for_user(user_id: str, user_data: UserCreate) -> None:
        """사용자를 위한 회사 정보 생성"""
        try:
            await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"INSERT INTO companies (id, user_id, name, business_number, company_type, address, status) VALUES ('{str(uuid.uuid4())}', '{user_id}', '{user_data.company_name}', '{user_data.business_number}', '{user_data.company_type}', '{user_data.address}', 'active')"
            )
            
        except Exception as e:
            # 회사 생성 실패는 로그만 남기고 계속 진행
            import logging
            logging.error(f"회사 정보 생성 실패: {str(e)}")