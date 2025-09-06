"""
채팅 관리 API 엔드포인트
실시간 채팅 및 알림 시스템
"""

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, status
from typing import List, Optional
import logging
import json

from auth.middleware import get_current_user_required
from models.auth import UserResponse
from models.chat import (
    ChatRoomCreate, ChatRoomResponse, ChatRoomListResponse,
    ChatMessageBase, ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse,
    ChatMessageSearchFilter, ChatStats, WebSocketMessage,
    NotificationResponse, NotificationUpdate
)
from services.chat_service import ChatService, NotificationService, connection_manager
from services.company_service import CompanyService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


# 채팅방 관리 엔드포인트
@router.get("/rooms", response_model=ChatRoomListResponse)
async def get_chat_rooms(
    current_user: dict = Depends(get_current_user_required)
) -> ChatRoomListResponse:
    """사용자의 채팅방 목록 조회"""
    try:
        rooms = await ChatService.get_user_chat_rooms(
            str(current_user["id"]), 
            current_user.get("company_type")
        )
        
        return rooms
        
    except Exception as e:
        logger.error(f"채팅방 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 목록 조회에 실패했습니다"
        )


@router.post("/rooms", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: dict = Depends(get_current_user_required)
) -> ChatRoomResponse:
    """채팅방 생성 (도매업체-소매업체 간)"""
    try:
        # 사용자의 회사 ID 조회
        company = await CompanyService.get_company_by_user_id(str(current_user["id"]))
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="소속 회사를 찾을 수 없습니다"
            )
        
        # 거래 관계 확인
        has_relationship = await CompanyService.check_trading_relationship(
            str(room_data.wholesale_company_id), 
            str(room_data.retail_company_id)
        )
        
        if not has_relationship:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="거래 관계가 승인되지 않은 업체와는 채팅할 수 없습니다"
            )
        
        # 사용자가 해당 거래에 참여하는지 확인
        user_company_id = str(company.id)
        if user_company_id not in [str(room_data.wholesale_company_id), str(room_data.retail_company_id)]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="채팅방을 생성할 권한이 없습니다"
            )
        
        # 채팅방 생성 또는 기존 방 조회
        room = await ChatService.create_or_get_room(
            str(room_data.wholesale_company_id),
            str(room_data.retail_company_id)
        )
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="채팅방 생성에 실패했습니다"
            )
        
        return room
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채팅방 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 생성에 실패했습니다"
        )


@router.get("/rooms/{room_id}/messages", response_model=ChatMessageListResponse)
async def get_chat_messages(
    room_id: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(50, ge=1, le=100, description="페이지 크기"),
    current_user: dict = Depends(get_current_user_required)
) -> ChatMessageListResponse:
    """채팅방 메시지 목록 조회"""
    try:
        search_filter = ChatMessageSearchFilter(
            room_id=room_id,
            page=page,
            size=size
        )
        
        messages = await ChatService.get_room_messages(
            room_id, 
            str(current_user["id"]), 
            search_filter
        )
        
        # 메시지 읽음 처리
        await ChatService.mark_messages_as_read(room_id, str(current_user["id"]))
        
        return messages
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"채팅 메시지 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅 메시지 조회에 실패했습니다"
        )


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    room_id: str,
    message_data: ChatMessageBase,
    current_user: dict = Depends(get_current_user_required)
) -> ChatMessageResponse:
    """채팅 메시지 전송"""
    try:
        # room_id를 URL에서 가져와서 ChatMessageCreate 객체 생성
        chat_message_create = ChatMessageCreate(
            room_id=room_id,
            message=message_data.message,
            message_type=message_data.message_type,
            order_id=message_data.order_id
        )
        
        # 메시지 전송
        message = await ChatService.send_message(chat_message_create, str(current_user["id"]))
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="메시지 전송에 실패했습니다"
            )
        
        # WebSocket으로 실시간 브로드캐스트
        websocket_message = WebSocketMessage(
            type="message",
            data=message.model_dump(),
            room_id=room_id,
            sender_id=str(current_user["id"])
        )
        
        await connection_manager.send_to_room(room_id, websocket_message.model_dump())
        
        return message
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"메시지 전송 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 전송에 실패했습니다"
        )


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_message(
    message_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """채팅 메시지 삭제 (1시간 이내, 발신자만 가능)"""
    try:
        success = await ChatService.delete_message(message_id, str(current_user["id"]))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="메시지를 삭제할 권한이 없거나 시간이 초과되었습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메시지 삭제 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 삭제에 실패했습니다"
        )


@router.get("/rooms/{room_id}/search", response_model=ChatMessageListResponse)
async def search_chat_messages(
    room_id: str,
    keyword: str = Query(..., min_length=1, max_length=100, description="검색 키워드"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=50, description="페이지 크기"),
    current_user: dict = Depends(get_current_user_required)
) -> ChatMessageListResponse:
    """채팅방 메시지 검색"""
    try:
        messages = await ChatService.search_messages(
            room_id, 
            str(current_user["id"]), 
            keyword, 
            page, 
            size
        )
        
        return messages
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"메시지 검색 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메시지 검색에 실패했습니다"
        )


@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    current_user: dict = Depends(get_current_user_required)
) -> ChatStats:
    """채팅 통계 조회"""
    try:
        stats = await ChatService.get_chat_stats(str(current_user["id"]))
        return stats
        
    except Exception as e:
        logger.error(f"채팅 통계 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅 통계 조회에 실패했습니다"
        )


# 알림 관리 엔드포인트
@notifications_router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = Query(False, description="읽지 않은 알림만 조회"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user: dict = Depends(get_current_user_required)
) -> List[NotificationResponse]:
    """사용자 알림 목록 조회"""
    try:
        notifications = await NotificationService.get_user_notifications(
            str(current_user["id"]), 
            unread_only, 
            page, 
            size
        )
        
        return notifications
        
    except Exception as e:
        logger.error(f"알림 목록 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 목록 조회에 실패했습니다"
        )


@notifications_router.put("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """알림 읽음 처리"""
    try:
        success = await NotificationService.mark_notification_read(
            notification_id, 
            str(current_user["id"])
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알림을 찾을 수 없습니다"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"알림 읽음 처리 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 처리에 실패했습니다"
        )


@notifications_router.put("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user_required)
):
    """모든 알림 읽음 처리"""
    try:
        success = await NotificationService.mark_all_notifications_read(str(current_user["id"]))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 처리에 실패했습니다"
            )
        
    except Exception as e:
        logger.error(f"모든 알림 읽음 처리 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="알림 처리에 실패했습니다"
        )


# WebSocket 엔드포인트
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str
):
    """WebSocket 채팅 엔드포인트"""
    user_id = None
    
    try:
        # WebSocket에서 인증 정보 추출
        # 쿠키에서 토큰 확인하거나 쿼리 파라미터로 토큰 받기
        token = None
        
        # 쿠키에서 토큰 추출 시도
        if websocket.cookies.get("access_token"):
            token = websocket.cookies.get("access_token")
        
        # 쿼리 파라미터에서 토큰 추출 시도
        elif websocket.query_params.get("token"):
            token = websocket.query_params.get("token")
        
        if not token:
            await websocket.close(code=4001, reason="인증이 필요합니다")
            return
        
        # 토큰 검증 및 사용자 정보 추출
        from auth.middleware import verify_access_token
        try:
            payload = verify_access_token(token)
            user_id = payload["user_id"]
        except Exception:
            await websocket.close(code=4001, reason="유효하지 않은 토큰입니다")
            return
        
        # 채팅방 접근 권한 확인
        has_access = await ChatService.check_room_access(room_id, user_id)
        if not has_access:
            await websocket.close(code=4003, reason="채팅방에 접근할 권한이 없습니다")
            return
        
        # WebSocket 연결 등록
        await connection_manager.connect(websocket, room_id, user_id)
        
        # 사용자 입장 알림
        join_message = WebSocketMessage(
            type="user_joined",
            data={"user_id": user_id, "message": "사용자가 채팅방에 입장했습니다"},
            room_id=room_id,
            sender_id=user_id
        )
        await connection_manager.send_to_room(room_id, join_message.model_dump())
        
        # 메시지 읽음 처리
        await ChatService.mark_messages_as_read(room_id, user_id)
        
        # 메시지 수신 대기
        while True:
            try:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # 메시지 타입별 처리
                if message_data.get("type") == "message":
                    # 채팅 메시지 전송
                    chat_message = ChatMessageCreate(
                        room_id=room_id,
                        message=message_data.get("message", ""),
                        message_type=message_data.get("message_type", "text"),
                        order_id=message_data.get("order_id")
                    )
                    
                    # 메시지 저장
                    saved_message = await ChatService.send_message(chat_message, user_id)
                    
                    if saved_message:
                        # 모든 연결된 클라이언트에게 브로드캐스트
                        broadcast_message = WebSocketMessage(
                            type="message",
                            data=saved_message.model_dump(),
                            room_id=room_id,
                            sender_id=user_id
                        )
                        await connection_manager.send_to_room(room_id, broadcast_message.model_dump())
                
                elif message_data.get("type") == "typing":
                    # 타이핑 상태 브로드캐스트
                    typing_message = WebSocketMessage(
                        type="typing",
                        data={"user_id": user_id, "is_typing": message_data.get("is_typing", False)},
                        room_id=room_id,
                        sender_id=user_id
                    )
                    await connection_manager.send_to_room(room_id, typing_message.model_dump())
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # 잘못된 JSON 형식
                error_message = WebSocketMessage(
                    type="error",
                    data={"message": "잘못된 메시지 형식입니다"},
                    room_id=room_id
                )
                await websocket.send_json(error_message.model_dump())
            except Exception as e:
                logger.error(f"WebSocket 메시지 처리 오류: {str(e)}")
                error_message = WebSocketMessage(
                    type="error",
                    data={"message": "메시지 처리 중 오류가 발생했습니다"},
                    room_id=room_id
                )
                await websocket.send_json(error_message.model_dump())
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket 연결 오류: {str(e)}")
    finally:
        # 연결 해제 처리
        if user_id:
            connection_manager.disconnect(websocket, room_id, user_id)
            
            # 사용자 퇴장 알림
            leave_message = WebSocketMessage(
                type="user_left",
                data={"user_id": user_id, "message": "사용자가 채팅방을 나갔습니다"},
                room_id=room_id,
                sender_id=user_id
            )
            await connection_manager.send_to_room(room_id, leave_message.model_dump())


# 채팅방별 업체 정보 조회
@router.get("/rooms/{room_id}/info")
async def get_chat_room_info(
    room_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """채팅방 정보 조회 (참여 업체 정보)"""
    try:
        # 채팅방 접근 권한 확인
        has_access = await ChatService.check_room_access(room_id, str(current_user["id"]))
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="채팅방에 접근할 권한이 없습니다"
            )
        
        # 채팅방 및 업체 정보 조회
        result = await real_supabase_service.execute_sql(
            project_id=real_supabase_service.project_id,
            query=f"""
            SELECT 
                cr.id, cr.created_at,
                wc.id as wholesale_id, wc.name as wholesale_name, wc.address as wholesale_address,
                rc.id as retail_id, rc.name as retail_name, rc.address as retail_address
            FROM chat_rooms cr
            LEFT JOIN companies wc ON cr.wholesale_company_id = wc.id
            LEFT JOIN companies rc ON cr.retail_company_id = rc.id
            WHERE cr.id = '{room_id}'
        """)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다"
            )
        
        return dict(result[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채팅방 정보 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="채팅방 정보 조회에 실패했습니다"
        )


# 실시간 알림을 위한 SSE 엔드포인트
@router.get("/sse")
async def chat_notifications_sse(
    current_user: dict = Depends(get_current_user_required)
):
    """Server-Sent Events로 실시간 채팅 알림"""
    async def event_generator():
        try:
            while True:
                # 새로운 알림 체크 (30초마다)
                notifications = await NotificationService.get_user_notifications(
                    str(current_user["id"]), 
                    unread_only=True,
                    page=1,
                    size=10
                )
                
                if notifications:
                    for notification in notifications:
                        yield f"data: {notification.model_dump_json()}\n\n"
                
                # 30초 대기
                import asyncio
                await asyncio.sleep(30)
                
        except Exception as e:
            logger.error(f"SSE 스트림 오류: {str(e)}")
            yield f"data: {{'error': '알림 스트림 연결에 실패했습니다'}}\n\n"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )