"""
채팅 서비스
실시간 채팅방 및 메시지 관리 시스템
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from models.chat import (
    ChatRoomCreate, ChatRoomResponse, ChatRoomListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse,
    ChatMessageSearchFilter, ChatStats, NotificationCreate, NotificationResponse
)
from services.real_supabase_service import real_supabase_service
from services.company_service import CompanyService

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 관리 서비스"""
    
    @staticmethod
    async def create_or_get_room(wholesale_company_id: str, retail_company_id: str) -> Optional[ChatRoomResponse]:
        """채팅방 생성 또는 기존 방 조회"""
        try:
            # 기존 채팅방 확인
            existing_room = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cr.id, cr.wholesale_company_id, cr.retail_company_id, 
                    cr.last_message_at, cr.created_at,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name,
                    (SELECT message FROM chat_messages WHERE room_id = cr.id ORDER BY created_at DESC LIMIT 1) as last_message,
                    (SELECT COUNT(*) FROM chat_messages WHERE room_id = cr.id AND created_at > NOW() - INTERVAL '1 hour') as unread_count
                FROM chat_rooms cr
                LEFT JOIN companies wc ON cr.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON cr.retail_company_id = rc.id
                WHERE cr.wholesale_company_id = '{wholesale_company_id}' 
                AND cr.retail_company_id = '{retail_company_id}'
            """)
            
            if existing_room:
                return ChatRoomResponse(**dict(existing_room[0]))
            
            # 새 채팅방 생성
            room_id = str(uuid.uuid4())
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                INSERT INTO chat_rooms (id, wholesale_company_id, retail_company_id, last_message_at)
                VALUES ('{room_id}', '{wholesale_company_id}', '{retail_company_id}', NOW())
                RETURNING id, wholesale_company_id, retail_company_id, last_message_at, created_at
            """)
            
            if not result:
                return None
            
            # 회사 정보와 함께 반환
            room_with_company_info = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cr.id, cr.wholesale_company_id, cr.retail_company_id, 
                    cr.last_message_at, cr.created_at,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name
                FROM chat_rooms cr
                LEFT JOIN companies wc ON cr.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON cr.retail_company_id = rc.id
                WHERE cr.id = '{room_id}'
            """)
            
            if room_with_company_info:
                room_dict = dict(room_with_company_info[0])
                room_dict['unread_count'] = 0
                room_dict['last_message'] = None
                return ChatRoomResponse(**room_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"채팅방 생성/조회 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_chat_rooms(user_id: str, company_type: str) -> ChatRoomListResponse:
        """사용자의 채팅방 목록 조회"""
        try:
            # 사용자의 회사 ID 조회
            company = await CompanyService.get_company_by_user_id(user_id)
            if not company:
                return ChatRoomListResponse(rooms=[], total=0)
            
            # 회사 유형에 따른 조건 설정
            if company_type == "wholesale":
                company_condition = f"cr.wholesale_company_id = '{company.id}'"
                other_company_name = "rc.name as other_company_name"
            else:  # retail
                company_condition = f"cr.retail_company_id = '{company.id}'"
                other_company_name = "wc.name as other_company_name"
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cr.id, cr.wholesale_company_id, cr.retail_company_id, 
                    cr.last_message_at, cr.created_at,
                    wc.name as wholesale_company_name,
                    rc.name as retail_company_name,
                    {other_company_name},
                    (SELECT message FROM chat_messages WHERE room_id = cr.id ORDER BY created_at DESC LIMIT 1) as last_message,
                    (SELECT COUNT(*) FROM chat_messages WHERE room_id = cr.id 
                     AND sender_id != '{user_id}' 
                     AND created_at > COALESCE((SELECT last_read_at FROM chat_room_users WHERE room_id = cr.id AND user_id = '{user_id}'), cr.created_at)
                    ) as unread_count
                FROM chat_rooms cr
                LEFT JOIN companies wc ON cr.wholesale_company_id = wc.id
                LEFT JOIN companies rc ON cr.retail_company_id = rc.id
                WHERE {company_condition}
                ORDER BY cr.last_message_at DESC
            """)
            
            rooms = []
            if result:
                for row in result:
                    rooms.append(ChatRoomResponse(**dict(row)))
            
            return ChatRoomListResponse(rooms=rooms, total=len(rooms))
            
        except Exception as e:
            logger.error(f"채팅방 목록 조회 오류: {str(e)}")
            return ChatRoomListResponse(rooms=[], total=0)
    
    @staticmethod
    async def send_message(message_data: ChatMessageCreate, sender_id: str) -> Optional[ChatMessageResponse]:
        """메시지 전송"""
        try:
            # 채팅방 접근 권한 확인
            has_access = await ChatService.check_room_access(str(message_data.room_id), sender_id)
            if not has_access:
                raise ValueError("채팅방에 접근할 권한이 없습니다")
            
            message_id = str(uuid.uuid4())
            
            # 메시지 저장
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                INSERT INTO chat_messages (id, room_id, sender_id, message, message_type, order_id)
                VALUES ('{message_id}', '{message_data.room_id}', '{sender_id}', '{message_data.message}', '{message_data.message_type}', {f"'{message_data.order_id}'" if message_data.order_id else "NULL"})
                RETURNING id, room_id, sender_id, message, message_type, order_id, created_at
            """)
            
            if not result:
                return None
            
            # 채팅방 최종 메시지 시간 업데이트
            await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE chat_rooms 
                SET last_message_at = NOW() 
                WHERE id = '{message_data.room_id}'
            """)
            
            # 발신자 정보와 함께 메시지 반환
            message_with_sender = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cm.id, cm.room_id, cm.sender_id, cm.message, cm.message_type, cm.order_id, cm.created_at,
                    u.name as sender_name,
                    c.name as sender_company
                FROM chat_messages cm
                LEFT JOIN users u ON cm.sender_id = u.id
                LEFT JOIN companies c ON u.id = c.user_id
                WHERE cm.id = '{message_id}'
            """)
            
            if message_with_sender:
                message_dict = dict(message_with_sender[0])
                # 주문 정보가 있으면 추가
                if message_data.order_id:
                    message_dict['order_info'] = await ChatService._get_order_info(str(message_data.order_id))
                return ChatMessageResponse(**message_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"메시지 전송 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_room_messages(room_id: str, user_id: str, search_filter: ChatMessageSearchFilter) -> ChatMessageListResponse:
        """채팅방 메시지 목록 조회"""
        try:
            # 채팅방 접근 권한 확인
            has_access = await ChatService.check_room_access(room_id, user_id)
            if not has_access:
                raise ValueError("채팅방에 접근할 권한이 없습니다")
            
            # 총 메시지 수 조회
            count_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as total FROM chat_messages WHERE room_id = '{room_id}'"
            )
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (search_filter.page - 1) * search_filter.size
            
            # 메시지 조회 (최신순)
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cm.id, cm.room_id, cm.sender_id, cm.message, cm.message_type, cm.order_id, cm.created_at,
                    u.name as sender_name,
                    c.name as sender_company
                FROM chat_messages cm
                LEFT JOIN users u ON cm.sender_id = u.id
                LEFT JOIN companies c ON u.id = c.user_id
                WHERE cm.room_id = '{room_id}'
                ORDER BY cm.created_at DESC
                LIMIT {search_filter.size} OFFSET {offset}
            """)
            
            messages = []
            if result:
                for row in result:
                    message_dict = dict(row)
                    # 주문 정보가 있으면 추가
                    if message_dict.get('order_id'):
                        message_dict['order_info'] = await ChatService._get_order_info(str(message_dict['order_id']))
                    messages.append(ChatMessageResponse(**message_dict))
            
            has_next = (offset + search_filter.size) < total
            
            return ChatMessageListResponse(
                messages=messages,
                total=total,
                page=search_filter.page,
                size=search_filter.size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"채팅 메시지 조회 오류: {str(e)}")
            return ChatMessageListResponse(messages=[], total=0, page=1, size=50, has_next=False)
    
    @staticmethod
    async def check_room_access(room_id: str, user_id: str) -> bool:
        """채팅방 접근 권한 확인"""
        try:
            # 사용자의 회사 ID 조회
            company = await CompanyService.get_company_by_user_id(user_id)
            if not company:
                return False
            
            # 채팅방에 해당 회사가 포함되어 있는지 확인
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM chat_rooms 
                WHERE id = '{room_id}' 
                AND (wholesale_company_id = '{company.id}' OR retail_company_id = '{company.id}')
            """)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"채팅방 접근 권한 확인 오류: {str(e)}")
            return False
    
    @staticmethod
    async def get_chat_stats(user_id: str) -> ChatStats:
        """사용자의 채팅 통계 조회"""
        try:
            # 사용자의 회사 ID 조회
            company = await CompanyService.get_company_by_user_id(user_id)
            if not company:
                return ChatStats()
            
            # 회사 유형에 따른 조건 설정
            if company.company_type == "wholesale":
                company_condition = f"cr.wholesale_company_id = '{company.id}'"
            else:  # retail
                company_condition = f"cr.retail_company_id = '{company.id}'"
            
            # 채팅 통계 조회
            stats_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    COUNT(DISTINCT cr.id) as total_rooms,
                    COUNT(DISTINCT CASE WHEN cr.last_message_at > NOW() - INTERVAL '7 days' THEN cr.id END) as active_rooms,
                    COUNT(CASE WHEN cm.created_at >= CURRENT_DATE THEN cm.id END) as total_messages_today,
                    COUNT(CASE WHEN cm.sender_id != '{user_id}' AND cm.created_at > NOW() - INTERVAL '1 hour' THEN cm.id END) as unread_messages
                FROM chat_rooms cr
                LEFT JOIN chat_messages cm ON cr.id = cm.room_id
                WHERE {company_condition}
            """)
            
            if stats_result:
                return ChatStats(**dict(stats_result[0]))
            else:
                return ChatStats()
            
        except Exception as e:
            logger.error(f"채팅 통계 조회 오류: {str(e)}")
            return ChatStats()
    
    @staticmethod
    async def mark_messages_as_read(room_id: str, user_id: str) -> bool:
        """메시지 읽음 처리 (채팅방 입장 시)"""
        try:
            # 사용자의 마지막 읽은 시간 업데이트
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                INSERT INTO chat_room_users (room_id, user_id, last_read_at)
                VALUES ('{room_id}', '{user_id}', NOW())
                ON CONFLICT (room_id, user_id) 
                DO UPDATE SET last_read_at = NOW()
            """)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"메시지 읽음 처리 오류: {str(e)}")
            return False
    
    @staticmethod
    async def delete_message(message_id: str, user_id: str) -> bool:
        """메시지 삭제 (발신자만 가능, 1시간 이내)"""
        try:
            # 메시지 소유권 및 시간 확인
            message_check = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id FROM chat_messages 
                WHERE id = '{message_id}' 
                AND sender_id = '{user_id}'
                AND created_at > NOW() - INTERVAL '1 hour'
            """)
            
            if not message_check:
                return False
            
            # 메시지 삭제 (실제로는 내용만 삭제하고 "[삭제된 메시지]"로 표시)
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE chat_messages 
                SET message = '[삭제된 메시지]', message_type = 'text'
                WHERE id = '{message_id}'
            """)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"메시지 삭제 오류: {str(e)}")
            return False
    
    @staticmethod
    async def search_messages(room_id: str, user_id: str, keyword: str, 
                            page: int = 1, size: int = 20) -> ChatMessageListResponse:
        """채팅방 내 메시지 검색"""
        try:
            # 채팅방 접근 권한 확인
            has_access = await ChatService.check_room_access(room_id, user_id)
            if not has_access:
                raise ValueError("채팅방에 접근할 권한이 없습니다")
            
            # 검색 조건
            where_conditions = [
                f"cm.room_id = '{room_id}'",
                f"cm.message ILIKE '%{keyword}%'",
                "cm.message != '[삭제된 메시지]'"
            ]
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # 총 개수 조회
            count_result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"SELECT COUNT(*) as total FROM chat_messages cm {where_clause}"
            )
            
            total = count_result[0]['total'] if count_result else 0
            
            # OFFSET, LIMIT 계산
            offset = (page - 1) * size
            
            # 메시지 검색
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT 
                    cm.id, cm.room_id, cm.sender_id, cm.message, cm.message_type, cm.order_id, cm.created_at,
                    u.name as sender_name,
                    c.name as sender_company
                FROM chat_messages cm
                LEFT JOIN users u ON cm.sender_id = u.id
                LEFT JOIN companies c ON u.id = c.user_id
                {where_clause}
                ORDER BY cm.created_at DESC
                LIMIT {size} OFFSET {offset}
            """)
            
            messages = []
            if result:
                for row in result:
                    message_dict = dict(row)
                    if message_dict.get('order_id'):
                        message_dict['order_info'] = await ChatService._get_order_info(str(message_dict['order_id']))
                    messages.append(ChatMessageResponse(**message_dict))
            
            has_next = (offset + size) < total
            
            return ChatMessageListResponse(
                messages=messages,
                total=total,
                page=page,
                size=size,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"메시지 검색 오류: {str(e)}")
            return ChatMessageListResponse(messages=[], total=0, page=1, size=20, has_next=False)
    
    @staticmethod
    async def _get_order_info(order_id: str) -> Optional[Dict[str, Any]]:
        """주문 정보 조회 (메시지에 첨부된 주문용)"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id, order_number, status, total_amount, created_at
                FROM orders 
                WHERE id = '{order_id}'
            """)
            
            return dict(result[0]) if result else None
            
        except Exception as e:
            logger.error(f"주문 정보 조회 오류: {str(e)}")
            return None


class NotificationService:
    """알림 관리 서비스"""
    
    @staticmethod
    async def create_notification(notification_data: NotificationCreate) -> Optional[NotificationResponse]:
        """알림 생성"""
        try:
            notification_id = str(uuid.uuid4())
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                INSERT INTO notifications (id, user_id, title, message, notification_type, reference_id, is_read)
                VALUES ('{notification_id}', '{notification_data.user_id}', '{notification_data.title}', '{notification_data.message}', '{notification_data.notification_type}', {f"'{notification_data.reference_id}'" if notification_data.reference_id else "NULL"}, false)
                RETURNING id, user_id, title, message, notification_type, reference_id, is_read, created_at
            """)
            
            if result:
                return NotificationResponse(**dict(result[0]))
            return None
            
        except Exception as e:
            logger.error(f"알림 생성 오류: {str(e)}")
            return None
    
    @staticmethod
    async def get_user_notifications(user_id: str, unread_only: bool = False, 
                                   page: int = 1, size: int = 20) -> List[NotificationResponse]:
        """사용자 알림 목록 조회"""
        try:
            conditions = [f"user_id = '{user_id}'"]
            
            if unread_only:
                conditions.append("is_read = false")
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            # OFFSET, LIMIT 계산
            offset = (page - 1) * size
            
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT id, user_id, title, message, notification_type, reference_id, is_read, created_at
                FROM notifications
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {size} OFFSET {offset}
            """)
            
            notifications = []
            if result:
                for row in result:
                    notifications.append(NotificationResponse(**dict(row)))
            
            return notifications
            
        except Exception as e:
            logger.error(f"알림 목록 조회 오류: {str(e)}")
            return []
    
    @staticmethod
    async def mark_notification_read(notification_id: str, user_id: str) -> bool:
        """알림 읽음 처리"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE notifications 
                SET is_read = true 
                WHERE id = '{notification_id}' AND user_id = '{user_id}'
            """)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"알림 읽음 처리 오류: {str(e)}")
            return False
    
    @staticmethod
    async def mark_all_notifications_read(user_id: str) -> bool:
        """모든 알림 읽음 처리"""
        try:
            result = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                UPDATE notifications 
                SET is_read = true 
                WHERE user_id = '{user_id}' AND is_read = false
            """)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"모든 알림 읽음 처리 오류: {str(e)}")
            return False
    
    @staticmethod
    async def send_order_notification(order_id: str, recipient_user_id: str, notification_type: str):
        """주문 관련 알림 전송"""
        try:
            # 주문 정보 조회
            order_info = await real_supabase_service.execute_sql(
                project_id=real_supabase_service.project_id,
                query=f"""
                SELECT order_number, status, total_amount
                FROM orders 
                WHERE id = '{order_id}'
            """)
            
            if not order_info:
                return
            
            order = order_info[0]
            
            # 알림 타입별 메시지 구성
            notification_messages = {
                "order_created": f"새 주문이 접수되었습니다 (주문번호: {order['order_number']})",
                "order_confirmed": f"주문이 확인되었습니다 (주문번호: {order['order_number']})",
                "order_shipped": f"주문 상품이 배송되었습니다 (주문번호: {order['order_number']})",
                "order_delivered": f"주문이 배송 완료되었습니다 (주문번호: {order['order_number']})",
                "order_cancelled": f"주문이 취소되었습니다 (주문번호: {order['order_number']})"
            }
            
            title = "주문 상태 업데이트"
            message = notification_messages.get(notification_type, f"주문 상태가 {order['status']}로 변경되었습니다")
            
            # 알림 생성
            notification_data = NotificationCreate(
                user_id=uuid.UUID(recipient_user_id),
                title=title,
                message=message,
                notification_type="order",
                reference_id=uuid.UUID(order_id)
            )
            
            await NotificationService.create_notification(notification_data)
            
        except Exception as e:
            logger.error(f"주문 알림 전송 오류: {str(e)}")


# WebSocket 연결 관리자
class ConnectionManager:
    """WebSocket 연결 관리"""
    
    def __init__(self):
        # room_id -> List[WebSocket] 연결 관리
        self.room_connections: Dict[str, List[Any]] = {}
        # user_id -> WebSocket 연결 관리  
        self.user_connections: Dict[str, Any] = {}
    
    async def connect(self, websocket, room_id: str, user_id: str):
        """WebSocket 연결 추가"""
        await websocket.accept()
        
        # 룸별 연결 관리
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)
        
        # 사용자별 연결 관리
        self.user_connections[user_id] = websocket
        
        logger.info(f"WebSocket 연결: room={room_id}, user={user_id}")
    
    def disconnect(self, websocket, room_id: str, user_id: str):
        """WebSocket 연결 해제"""
        # 룸별 연결에서 제거
        if room_id in self.room_connections:
            try:
                self.room_connections[room_id].remove(websocket)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            except ValueError:
                pass
        
        # 사용자별 연결에서 제거
        if user_id in self.user_connections and self.user_connections[user_id] == websocket:
            del self.user_connections[user_id]
        
        logger.info(f"WebSocket 연결 해제: room={room_id}, user={user_id}")
    
    async def send_to_room(self, room_id: str, message: dict):
        """채팅방의 모든 연결에 메시지 전송"""
        if room_id in self.room_connections:
            disconnected = []
            for websocket in self.room_connections[room_id]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.append(websocket)
            
            # 연결이 끊어진 소켓 정리
            for websocket in disconnected:
                try:
                    self.room_connections[room_id].remove(websocket)
                except ValueError:
                    pass
    
    async def send_to_user(self, user_id: str, message: dict):
        """특정 사용자에게 메시지 전송"""
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except:
                del self.user_connections[user_id]


# 전역 연결 관리자 인스턴스
connection_manager = ConnectionManager()