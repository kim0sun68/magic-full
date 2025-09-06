"""
채팅 시스템 Pydantic 모델
실시간 채팅방 및 메시지 관리
"""

import uuid
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class ChatRoomBase(BaseModel):
    """채팅방 기본 정보"""
    wholesale_company_id: uuid.UUID = Field(..., description="도매업체 ID")
    retail_company_id: uuid.UUID = Field(..., description="소매업체 ID")


class ChatRoomCreate(ChatRoomBase):
    """채팅방 생성 요청"""
    pass


class ChatRoomResponse(ChatRoomBase):
    """채팅방 응답 데이터"""
    id: uuid.UUID
    last_message_at: datetime
    created_at: datetime
    
    # 관계 정보
    wholesale_company_name: Optional[str] = None
    retail_company_name: Optional[str] = None
    last_message: Optional[str] = None
    unread_count: int = Field(0, description="읽지 않은 메시지 수")
    
    model_config = ConfigDict(from_attributes=True)


class ChatMessageBase(BaseModel):
    """채팅 메시지 기본 정보"""
    message: str = Field(..., min_length=1, max_length=1000, description="메시지 내용")
    message_type: Literal["text", "image", "order"] = Field("text", description="메시지 유형")
    order_id: Optional[uuid.UUID] = Field(None, description="주문 ID (주문 메시지인 경우)")


class ChatMessageCreate(ChatMessageBase):
    """채팅 메시지 생성 요청"""
    room_id: uuid.UUID = Field(..., description="채팅방 ID")


class ChatMessageResponse(ChatMessageBase):
    """채팅 메시지 응답 데이터"""
    id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    created_at: datetime
    
    # 관계 정보
    sender_name: Optional[str] = None
    sender_company: Optional[str] = None
    order_info: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChatRoomListResponse(BaseModel):
    """채팅방 목록 응답"""
    rooms: List[ChatRoomResponse] = []
    total: int = 0


class ChatMessageListResponse(BaseModel):
    """채팅 메시지 목록 응답"""
    messages: List[ChatMessageResponse] = []
    total: int = 0
    page: int = 1
    size: int = 50
    has_next: bool = False


class ChatMessageSearchFilter(BaseModel):
    """채팅 메시지 검색 필터"""
    room_id: Optional[uuid.UUID] = None
    message_type: Optional[str] = None
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=100)


class WebSocketMessage(BaseModel):
    """WebSocket 메시지 포맷"""
    type: Literal["message", "typing", "user_joined", "user_left", "error"] = Field(..., description="메시지 타입")
    data: dict = Field(..., description="메시지 데이터")
    room_id: str = Field(..., description="채팅방 ID")
    sender_id: Optional[str] = Field(None, description="발신자 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotificationBase(BaseModel):
    """알림 기본 정보"""
    user_id: uuid.UUID = Field(..., description="수신자 ID")
    title: str = Field(..., min_length=1, max_length=200, description="알림 제목")
    message: str = Field(..., min_length=1, max_length=500, description="알림 내용")
    notification_type: Literal["order", "chat", "system", "low_stock"] = Field(..., description="알림 유형")
    reference_id: Optional[uuid.UUID] = Field(None, description="참조 ID")


class NotificationCreate(NotificationBase):
    """알림 생성 요청"""
    pass


class NotificationResponse(NotificationBase):
    """알림 응답 데이터"""
    id: uuid.UUID
    is_read: bool = Field(False, description="읽음 여부")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    """알림 업데이트 (읽음 처리)"""
    is_read: bool = Field(True, description="읽음 여부")


class ChatStats(BaseModel):
    """채팅 통계"""
    total_rooms: int = 0
    active_rooms: int = 0
    total_messages_today: int = 0
    unread_messages: int = 0