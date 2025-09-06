# 마법옷장 REST API 문서

## 개요
남대문시장 아동복 B2B 재고관리 플랫폼의 REST API 문서입니다.

**베이스 URL**: `http://localhost` (로컬) / `https://your-domain.com` (프로덕션)
**인증 방식**: JWT 토큰 (HttpOnly 쿠키)
**응답 형식**: JSON

---

## 인증 API (`/api/auth`)

### 1. 회원가입
```http
POST /api/auth/register
```

**요청 바디**:
```json
{
  "email": "test@example.com",
  "password": "password123",
  "password_confirm": "password123",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "company_type": "wholesale",
  "company_name": "홍길동 도매",
  "business_number": "123-45-67890",
  "address": "서울특별시 중구 남대문시장"
}
```

**응답**: `201 Created`
```json
{
  "success": true,
  "message": "회원가입이 완료되었습니다. 관리자 승인 대기 중입니다.",
  "user": {
    "id": "uuid",
    "email": "test@example.com",
    "name": "홍길동",
    "role": "user",
    "approved": false,
    "created_at": "2025-09-03T10:00:00Z"
  }
}
```

### 2. 로그인
```http
POST /api/auth/login
```

**요청 바디**:
```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

**응답**: `200 OK` + JWT 쿠키 설정
```json
{
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "refresh_token": "eyJ0eXAiOiJKV1Q...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "name": "admin",
    "role": "admin",
    "approved": true
  }
}
```

### 3. 로그아웃
```http
POST /api/auth/logout
```
**인증**: 필요
**응답**: `200 OK` + 쿠키 삭제

### 4. 토큰 갱신
```http
POST /api/auth/refresh
```

### 5. 현재 사용자 정보
```http
GET /api/auth/me
```
**인증**: 필요

### 6. 비밀번호 변경
```http
POST /api/auth/change-password
```

### 7. CSRF 토큰 발급
```http
GET /api/auth/csrf-token
```

---

## 회사 관리 API (`/api/companies`)

### 1. 회사 목록 조회
```http
GET /api/companies?company_type=wholesale&status=active&page=1&size=20
```
**인증**: 필요
**쿼리 파라미터**:
- `company_type`: "wholesale" | "retail"
- `status`: "active" | "inactive" | "suspended"
- `name`: 업체명 검색
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지 크기 (기본값: 20, 최대: 100)

### 2. 도매업체 목록 조회
```http
GET /api/companies/wholesale
```

### 3. 내 회사 정보
```http
GET /api/companies/me
```

### 4. 회사 정보 수정
```http
PUT /api/companies/{company_id}
```

### 5. 거래 관계 신청
```http
POST /api/companies/relationships
```
**권한**: 소매업체만

### 6. 거래 관계 승인/거부
```http
PUT /api/companies/relationships/{relationship_id}
```
**권한**: 도매업체만

### 7. 거래 관계 목록
```http
GET /api/companies/relationships
```

### 8. 회사 상세 정보
```http
GET /api/companies/{company_id}
```

### 9. 회사 통계
```http
GET /api/companies/{company_id}/stats
```

---

## 상품 관리 API (`/api/products`)

### 1. 상품 생성
```http
POST /api/products
```
**권한**: 도매업체만

**요청 바디**:
```json
{
  "code": "P001",
  "name": "아동복 상의",
  "category_id": "uuid",
  "age_group": "3-5y",
  "gender": "unisex",
  "wholesale_price": 15000,
  "retail_price": 25000,
  "description": "고품질 아동복",
  "is_active": true
}
```

### 2. 상품 목록 조회
```http
GET /api/products?name=상의&age_group=3-5y&page=1&size=20
```
**쿼리 파라미터**:
- `name`: 상품명 검색
- `category_id`: 카테고리 필터
- `age_group`: "0-12m" | "1-2y" | "3-5y" | "6-10y"
- `gender`: "unisex" | "boys" | "girls"
- `min_price`, `max_price`: 가격 범위
- `is_active`: 활성 상품만

### 3. 상품 상세 조회
```http
GET /api/products/{product_id}
```

### 4. 상품 수정
```http
PUT /api/products/{product_id}
```
**권한**: 도매업체 소유자만

### 5. 상품 삭제 (비활성화)
```http
DELETE /api/products/{product_id}
```

### 6. 상품별 재고 조회
```http
GET /api/products/{product_id}/inventory
```

### 7. 상품별 재고 수정
```http
PUT /api/products/{product_id}/inventory
```

### 8. 상품별 재고 거래내역
```http
GET /api/products/{product_id}/inventory/transactions?page=1&size=20
```

---

## 카테고리 관리 API (`/api/categories`)

### 1. 카테고리 목록
```http
GET /api/categories
```

### 2. 카테고리 생성
```http
POST /api/products/categories
```
**권한**: 관리자만

### 3. 카테고리 수정
```http
PUT /api/products/categories/{category_id}
```

### 4. 카테고리 삭제
```http
DELETE /api/products/categories/{category_id}
```

---

## 재고 관리 API (`/api/inventory`)

### 1. 재고 조정
```http
POST /api/inventory/adjust
```
**권한**: 도매업체만

**요청 바디**:
```json
{
  "product_id": "uuid",
  "adjustment_quantity": 50,
  "reason": "입고 확인"
}
```

### 2. 입고 처리
```http
POST /api/inventory/stock-in
```

### 3. 안전재고 미달 상품
```http
GET /api/inventory/low-stock
```

### 4. 전체 재고 현황
```http
GET /api/inventory/overview
```

### 5. 재고 통계
```http
GET /api/inventory/stats
```

### 6. 재고 거래내역
```http
GET /api/inventory/transactions?days=30&page=1&size=20
```

---

## 주문 관리 API (`/api/orders`)

### 1. 주문 생성
```http
POST /api/orders
```
**권한**: 소매업체만

**요청 바디**:
```json
{
  "wholesale_company_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 10,
      "unit_price": 15000
    }
  ],
  "notes": "빠른 배송 부탁드립니다"
}
```

### 2. 빠른 주문 생성
```http
POST /api/orders/quick
```

### 3. 주문 목록 조회
```http
GET /api/orders?status=pending&page=1&size=20
```
**쿼리 파라미터**:
- `status`: "pending" | "confirmed" | "preparing" | "shipped" | "delivered" | "cancelled"
- `wholesale_company_id`: 도매업체 ID
- `retail_company_id`: 소매업체 ID
- `order_number`: 주문 번호
- `min_amount`, `max_amount`: 주문 금액 범위

### 4. 주문 상세 조회
```http
GET /api/orders/{order_id}
```

### 5. 주문 상태 변경
```http
PUT /api/orders/{order_id}/status
```
**권한**: 도매업체만

**요청 바디**:
```json
{
  "status": "confirmed",
  "notes": "주문 확인됨"
}
```

### 6. 주문 정보 수정
```http
PUT /api/orders/{order_id}
```
**권한**: 소매업체만 (pending 상태만)

### 7. 주문 취소
```http
DELETE /api/orders/{order_id}
```

### 8. 주문 상품 수정
```http
PUT /api/orders/{order_id}/items/{item_id}
```

### 9. 주문 상품 제거
```http
DELETE /api/orders/{order_id}/items/{item_id}
```

### 10. 주문 일괄 처리
```http
POST /api/orders/bulk-operation
```
**권한**: 도매업체만

### 11. 주문 통계
```http
GET /api/orders/stats
```

---

## 채팅 API (`/api/chat`)

### 1. 채팅방 목록
```http
GET /api/chat/rooms
```

### 2. 채팅방 생성
```http
POST /api/chat/rooms
```

**요청 바디**:
```json
{
  "wholesale_company_id": "uuid",
  "retail_company_id": "uuid"
}
```

### 3. 채팅 메시지 조회
```http
GET /api/chat/rooms/{room_id}/messages?page=1&size=50
```

### 4. 메시지 전송
```http
POST /api/chat/rooms/{room_id}/messages
```

**요청 바디**:
```json
{
  "message": "안녕하세요",
  "message_type": "text",
  "order_id": "uuid"
}
```

### 5. 메시지 삭제
```http
DELETE /api/chat/messages/{message_id}
```

### 6. 메시지 검색
```http
GET /api/chat/rooms/{room_id}/search?keyword=주문&page=1&size=20
```

### 7. 채팅 통계
```http
GET /api/chat/stats
```

### 8. 채팅방 정보
```http
GET /api/chat/rooms/{room_id}/info
```

### 9. WebSocket 연결
```
WS /api/chat/ws/{room_id}?token={jwt_token}
```

### 10. 실시간 알림 (SSE)
```http
GET /api/chat/sse
```

---

## 알림 API (`/api/chat/notifications`)

### 1. 알림 목록
```http
GET /api/chat/notifications?unread_only=true&page=1&size=20
```

### 2. 알림 읽음 처리
```http
PUT /api/chat/notifications/{notification_id}
```

### 3. 모든 알림 읽음
```http
PUT /api/chat/notifications/mark-all-read
```

---

## 대시보드 API (`/api/dashboard`)

### 1. 대시보드 통계
```http
GET /api/dashboard/stats
```

**응답**:
```json
{
  "todayOrders": 5,
  "lowStock": 3,
  "newMessages": 2,
  "activePartners": 10,
  "pendingPartners": 1
}
```

### 2. 최근 주문 (HTML)
```http
GET /api/dashboard/recent-orders?limit=5
```
**응답**: HTML (HTMX용)

### 3. 재고 부족 알림 (HTML)
```http
GET /api/dashboard/low-stock-alerts?limit=5
```
**응답**: HTML (HTMX용)

---

## 관리자 API (`/api/admin`)

### 1. 승인 대기 사용자
```http
GET /api/admin/users/pending
```
**권한**: 관리자만

### 2. 사용자 승인/거부
```http
PUT /api/admin/users/{user_id}/approve
```

**요청 바디**:
```json
{
  "user_id": "uuid",
  "approved": true,
  "reason": "승인 완료"
}
```

### 3. 관리자 통계
```http
GET /api/admin/statistics
```

### 4. 사용자 상세 정보
```http
GET /api/admin/users/{user_id}/detail
```

**응답**:
```json
{
  "id": "uuid",
  "email": "test@example.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "role": "user",
  "approved": false,
  "company_id": "uuid",
  "company_name": "홍길동 도매",
  "business_number": "123-45-67890",
  "company_type": "wholesale",
  "company_address": "서울특별시 중구",
  "company_status": "active"
}
```

### 5. 공지사항 관리
```http
GET /api/admin/notices?is_important=true&page=1&per_page=20
POST /api/admin/notices
GET /api/admin/notices/{notice_id}
PUT /api/admin/notices/{notice_id}
DELETE /api/admin/notices/{notice_id}
```

---

## 공지사항 API (Public)

### 1. 공지사항 목록 (모든 사용자)
```http
GET /api/notices?is_important=false&search=keyword&page=1&per_page=20
```

**응답**:
```json
{
  "notices": [
    {
      "id": "uuid",
      "title": "공지사항 제목",
      "content": "공지사항 내용",
      "is_important": false,
      "created_by": "uuid",
      "created_at": "2025-09-03T10:00:00Z",
      "updated_at": "2025-09-03T10:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

---

## 헬스체크 API

### 1. 서비스 상태
```http
GET /health
```

**응답**:
```json
{
  "status": "healthy",
  "service": "마법옷장",
  "version": "1.0.0"
}
```

### 2. 준비 상태
```http
GET /health/ready
```

### 3. 데이터베이스 상태
```http
GET /health/db
```

---

## 에러 응답 형식

모든 API는 일관된 에러 응답 형식을 사용합니다:

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드
- `200 OK`: 성공
- `201 Created`: 생성 성공
- `204 No Content`: 삭제 성공
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `422 Unprocessable Entity`: 유효성 검증 실패
- `500 Internal Server Error`: 서버 오류

---

## 인증 및 권한

### JWT 토큰
- **Access Token**: 15분 만료, API 인증용
- **Refresh Token**: 30일 만료, 토큰 갱신용
- **저장 방식**: HttpOnly 쿠키 (보안)

### 사용자 역할
- **admin**: 관리자 (모든 권한)
- **user**: 일반 사용자 (도매업체/소매업체)

### 업체 유형
- **wholesale**: 도매업체 (상품 등록, 재고 관리, 주문 승인)
- **retail**: 소매업체 (상품 조회, 주문 생성)

### 권한 매트릭스

| 기능 | 관리자 | 도매업체 | 소매업체 |
|------|--------|----------|----------|
| 회원 승인 | ✅ | ❌ | ❌ |
| 상품 등록/수정 | ✅ | ✅ (본인만) | ❌ |
| 상품 조회 | ✅ | ✅ (본인만) | ✅ (거래처만) |
| 재고 관리 | ✅ | ✅ (본인만) | ❌ |
| 주문 생성 | ✅ | ❌ | ✅ |
| 주문 승인 | ✅ | ✅ (받은 주문만) | ❌ |
| 거래 관계 신청 | ✅ | ❌ | ✅ |
| 거래 관계 승인 | ✅ | ✅ | ❌ |
| 채팅 | ✅ | ✅ (거래처와만) | ✅ (거래처와만) |
| 공지사항 작성 | ✅ | ❌ | ❌ |
| 공지사항 조회 | ✅ | ✅ | ✅ |

---

## Rate Limiting

Nginx 설정에 의한 요청 제한:
- **API 요청**: 10 req/sec (버스트: 20)
- **인증 요청**: 5 req/sec (버스트: 10)
- **채팅 요청**: 20 req/sec (버스트: 40)

---

## 페이지네이션

모든 목록 API는 페이지네이션을 지원합니다:

```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "has_next": true
}
```

---

## 실시간 통신

### WebSocket 채팅
```javascript
const ws = new WebSocket(`ws://localhost/api/chat/ws/${roomId}?token=${jwtToken}`);

// 메시지 전송
ws.send(JSON.stringify({
  type: "message",
  message: "안녕하세요",
  message_type: "text"
}));
```

### Server-Sent Events (알림)
```javascript
const eventSource = new EventSource('/api/chat/sse');
eventSource.onmessage = function(event) {
  const notification = JSON.parse(event.data);
  // 알림 처리
};
```

---

## 구현 현황

### ✅ 완료된 API (47개 엔드포인트)
- **인증**: 10개 엔드포인트
- **회사 관리**: 9개 엔드포인트
- **상품 관리**: 8개 엔드포인트
- **재고 관리**: 9개 엔드포인트
- **주문 관리**: 11개 엔드포인트
- **채팅**: 11개 엔드포인트
- **관리자**: 7개 엔드포인트
- **대시보드**: 3개 엔드포인트
- **헬스체크**: 3개 엔드포인트

### 🏗️ 구현 방식
- **아키텍처**: FastAPI + Pydantic + Jinja2
- **인증**: JWT 토큰 + HttpOnly 쿠키
- **데이터베이스**: Supabase PostgreSQL
- **실시간**: WebSocket + SSE
- **테스트**: TDD 기반 개발

---

**마지막 업데이트**: 2025-09-03
**API 버전**: v1.0.0