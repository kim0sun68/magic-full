# 마법옷장 아키텍처 문서

## 시스템 구조
```
Browser → CloudFront → ALB → Docker(Nginx → FastAPI) → Supabase PostgreSQL
                                    ↓
                              Wasabi Cloud (이미지 저장)
```

### 배포 아키텍처
- **로컬 개발**: `docker compose up --build -d`
- **AWS 프로덕션**: 동일한 docker-compose.yml로 EC2/ECS 배포
- **HTTPS 처리**: CloudFront에서 SSL/TLS 종료
- **로드 밸런싱**: ALB → Docker 컨테이너
- **통합 환경 설정**: 환경변수로 로컬/AWS 구분

## 사용자 권한 체계
```
관리자 (Admin)
├─ 전체 시스템 관리
├─ 사용자/거래처 승인
└─ 데이터 모니터링

도매업체 (Wholesale)
├─ 상품 등록/수정/삭제
├─ 재고 관리 (입고/출고/조정)
├─ 주문 접수/확인
└─ 소매업체와 채팅

소매업체 (Retail)
├─ 상품 조회
├─ 주문 생성/조회
├─ 거래 내역 확인
└─ 도매업체와 채팅
```

## DB 스키마

### users (사용자)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_approved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### companies (거래처)
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    business_number VARCHAR(20) UNIQUE,
    company_type VARCHAR(20) NOT NULL CHECK (company_type IN ('wholesale', 'retail')),
    address TEXT,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### company_relationships (거래처 관계)
```sql
CREATE TABLE company_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wholesale_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    retail_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(wholesale_company_id, retail_company_id)
);
```

### categories (상품 카테고리)
```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### products (상품)
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    category_id UUID REFERENCES categories(id),
    age_group VARCHAR(20) CHECK (age_group IN ('0-12m', '1-2y', '3-5y', '6-10y')),
    gender VARCHAR(10) CHECK (gender IN ('unisex', 'boys', 'girls')),
    wholesale_price INTEGER NOT NULL,
    retail_price INTEGER,
    description TEXT,
    images JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### inventory (재고)
```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    current_stock INTEGER DEFAULT 0,
    minimum_stock INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id)
);
```

### inventory_transactions (재고 거래내역)
```sql
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('in', 'out', 'adjustment')),
    quantity INTEGER NOT NULL,
    previous_stock INTEGER,
    current_stock INTEGER,
    reference_type VARCHAR(20) CHECK (reference_type IN ('order', 'adjustment', 'initial')),
    reference_id UUID,
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### orders (주문)
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    wholesale_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    retail_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_amount INTEGER DEFAULT 0,
    notes TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### order_items (주문 상품)
```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    total_price INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### notices (공지사항)
```sql
CREATE TABLE notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_important BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### memos (메모)
```sql
CREATE TABLE memos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### chat_rooms (채팅방)
```sql
CREATE TABLE chat_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wholesale_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    retail_company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    last_message_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(wholesale_company_id, retail_company_id)
);
```

### chat_messages (채팅 메시지)
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES chat_rooms(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'order')),
    order_id UUID REFERENCES orders(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 주요 API 엔드포인트

### 인증 API
- `POST /api/auth/signup` - 회원가입 및 거래처 등록
- `POST /api/auth/login` - 로그인
- `POST /api/auth/logout` - 로그아웃
- `GET /api/auth/me` - 현재 사용자 정보

### 상품 관리 API
- `GET /api/products` - 상품 목록 조회
- `POST /api/products` - 상품 등록 (도매업체만)
- `PUT /api/products/{id}` - 상품 수정 (도매업체만)
- `DELETE /api/products/{id}` - 상품 삭제 (도매업체만)
- `POST /api/products/{id}/images` - 상품 이미지 업로드

### 재고 관리 API
- `GET /api/inventory` - 재고 현황 조회
- `POST /api/inventory/adjustment` - 재고 조정
- `GET /api/inventory/transactions` - 재고 거래내역
- `POST /api/inventory/stock-in` - 입고 등록

### 주문 관리 API
- `GET /api/orders` - 주문 목록 조회
- `POST /api/orders` - 주문 생성 (소매업체)
- `PUT /api/orders/{id}/status` - 주문 상태 변경 (도매업체)
- `GET /api/orders/{id}` - 주문 상세 조회

### 거래처 관리 API
- `GET /api/companies` - 거래처 목록
- `POST /api/companies/relationships` - 거래 관계 신청
- `PUT /api/companies/relationships/{id}` - 거래 관계 승인/거부

### 채팅 API
- `GET /api/chat/rooms` - 채팅방 목록
- `GET /api/chat/rooms/{id}/messages` - 채팅 메시지
- `POST /api/chat/rooms/{id}/messages` - 메시지 전송
- `GET /api/chat/sse` - Server-Sent Events 실시간 채팅

### 메모 관리 API
- `GET /api/memos` - 메모 목록 조회
- `POST /api/memos` - 메모 작성
- `PUT /api/memos/{id}` - 메모 수정
- `DELETE /api/memos/{id}` - 메모 삭제

### 관리자 API
- `GET /api/admin/users/pending` - 승인 대기 사용자
- `GET /api/admin/users/{id}/detail` - 사용자 상세 정보 조회
- `PUT /api/admin/users/{id}/approve` - 사용자 승인
- `GET /api/admin/notices` - 공지사항 관리
- `POST /api/admin/notices` - 공지사항 작성
- `PUT /api/admin/notices/{id}` - 공지사항 수정
- `DELETE /api/admin/notices/{id}` - 공지사항 삭제

## 파일 구조
```
/
├── app/
│   ├── main.py                 # FastAPI 애플리케이션 엔트리포인트
│   ├── config.py               # 설정 관리
│   ├── database.py             # Supabase 연결 설정
│   ├── auth/
│   │   ├── dependencies.py     # 인증 의존성
│   │   ├── models.py          # 인증 관련 모델
│   │   └── routes.py          # 인증 라우터
│   ├── models/
│   │   ├── user.py
│   │   ├── company.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── chat.py
│   ├── api/
│   │   ├── products.py
│   │   ├── inventory.py
│   │   ├── orders.py
│   │   ├── companies.py
│   │   ├── chat.py
│   │   └── admin.py
│   ├── templates/              # Jinja2 템플릿
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── dashboard/
│   │   └── components/
│   └── static/                 # CSS, JS, 이미지
│       ├── css/
│       ├── js/
│       └── images/
├── tests/                      # 테스트 파일
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

## UI 디자인 (wireframes/)
- **공통**: @header.xml, @footer.xml
- **인증**: @login.xml, @signup.xml  
- **메인**: @main.xml, @dashboard.xml
- **핵심기능**: @inventory.xml, @products.xml, @orders.xml, @companies.xml, @chat.xml
- **상세페이지**: @product-form.xml, @order-detail.xml, @profile.xml
- **커뮤니케이션**: @memos.xml, @notices.xml
- **관리자**: @admin.xml, @admin-detail.xml

**총 16개 페이지** (공통 2개 + 인증 2개 + 메인 2개 + 핵심기능 5개 + 상세 3개 + 커뮤니케이션 2개 + 관리자 2개)

## 페이지 플로우
```
[비로그인] → 로그인 → 대시보드 → 각 기능 페이지
                 ↓
               회원가입 → 관리자 승인 대기 → 승인 후 로그인

[로그인 후 사용자별 접근 페이지]
도매업체: 대시보드, 상품관리, 재고관리, 주문관리, 거래처관리, 채팅, 메모
소매업체: 대시보드, 상품조회, 주문관리, 거래처관리, 채팅, 메모  
관리자: 전체 페이지 + 관리자 전용 기능
```

## 인증 & 승인 시스템 설계

### JWT 토큰 전략 (Access + Refresh, 30일)
```python
# 토큰 구성
access_token: 15분 만료, API 인증용, httpOnly 쿠키
refresh_token: 30일 만료, 토큰 갱신용, httpOnly 쿠키
csrf_token: Double Submit Cookie 패턴

# 승인 프로세스
회원가입 → is_approved=false → 로그인 불가 → 메인페이지만 접근
관리자 승인 → is_approved=true → 로그인 가능 → 전체 기능 접근
```

### 업체간 거래관계 설계
```python
# 거래 신청 프로세스
소매업체 → 도매업체에 거래신청 (company_relationships.status='pending')
도매업체 → 승인/거부 (status='approved'/'rejected')
승인완료 → 상품조회/주문 가능

# 데이터 접근 권한
도매업체: 자사 상품 + 거래승인된 소매업체 주문
소매업체: 거래승인된 도매업체 상품만 조회
```

## 실시간 재고관리 & 동시성 제어

### 재고 차감 로직 (실시간 + 경합상태 해결)
```sql
-- PostgreSQL 트랜잭션 + Row Locking
BEGIN;
SELECT current_stock FROM inventory WHERE product_id = $1 FOR UPDATE;
-- 재고 충분성 검증
UPDATE inventory SET current_stock = current_stock - $2 
WHERE product_id = $1 AND current_stock >= $2;
-- 재고 거래내역 기록
INSERT INTO inventory_transactions (product_id, transaction_type, quantity, reference_type, reference_id);
COMMIT;
```

### 안전재고 알림 시스템
```python
# 실시간 SSE 알림
def check_low_stock_alert():
    if current_stock <= minimum_stock:
        send_sse_alert(company_id, "재고부족", product_info)
```

## UI 컴포넌트 구조 & 네비게이션

### 네비게이션 전환 (별도 컴포넌트)
```html
<!-- 비로그인: header.xml -->
<header>
    <left>마법옷장</left>
    <right>
        <button>로그인</button>
        <button>회원가입</button>
    </right>
</header>

<!-- 로그인 후: dashboard_header.html -->
<header>
    <left>마법옷장</left>
    <nav>대시보드|재고관리|상품관리|거래처관리|주문관리|채팅|메모</nav>
    <right>
        <dropdown>프로필|로그아웃</dropdown>
    </right>
</header>
```

## 실시간 통신 시스템

### WebSocket 채팅 (DB 저장)
```python
# FastAPI WebSocket
@app.websocket("/ws/chat/{room_id}")
async def chat_endpoint(websocket: WebSocket, room_id: str):
    # 1. 메시지 DB 저장
    # 2. WebSocket 브로드캐스트
    # 3. 오프라인 사용자용 알림 큐잉
```

### 파일업로드 (Wasabi 직접 + 리사이징)
```javascript
// 클라이언트 측 이미지 처리
1. 파일 선택 → Canvas 리사이징 (max: 1MB)
2. FastAPI presigned URL 요청
3. Wasabi 직접 업로드
4. 업로드 완료 → 서버에 URL 저장
```

## 주문 워크플로우 & 상태관리

### 주문 상태 전환도
```
대기(pending) → 확인(confirmed) → 준비(preparing) → 배송(shipped) → 완료(completed)
     ↓              ↓               ↓              ↓
  취소(cancelled) ← 취소(cancelled) ← 취소(cancelled) ← [배송 후 취소불가]
```

### 주문 프로세스
```python
# 주문 생성 시
1. 재고 확인 (FOR UPDATE 락)
2. 주문 생성 (status='pending')
3. 재고 예약 (가재고 차감)
4. 도매업체 알림

# 주문 확인 시  
1. 도매업체 확인 처리 (status='confirmed')
2. 예약 재고 → 실제 차감
3. 재고 거래내역 기록
```

## 데이터 검증 & 에러처리

### 이중 검증 전략
```javascript
// 클라이언트: HTMX + Alpine.js
<form hx-post="/api/products" hx-validate="true">
    <input x-model="product.name" @blur="validateName()">
</form>

// 서버: Pydantic + 비즈니스 룰
class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    wholesale_price: int = Field(gt=0)
```

### 토스트 알림 시스템
```html
<!-- HTMX + Alpine.js 토스트 -->
<div x-data="{ toasts: [] }" 
     @toast-success.window="addToast('success', $event.detail)"
     @toast-error.window="addToast('error', $event.detail)">
</div>
```

## 성능 & 모니터링 요구사항

### 응답시간 목표
```
재고 조회: <200ms
채팅 메시지: <100ms  
주문 처리: <500ms
이미지 업로드: <2초
```

### 헬스체크 & 모니터링
```python
# 헬스체크 엔드포인트
GET /health          # 서비스 상태
GET /health/ready    # 준비 상태 (DB 연결 등)
GET /health/db       # 데이터베이스 상태

# 로깅 전략
구조화된 JSON 로깅 (timestamp, level, service, message, context)
Nginx 액세스 로그 + FastAPI 애플리케이션 로그
```

## Docker 배포 구성

### 환경별 실행 설정
```bash
# 로컬 개발 환경
cp .env.example .env
docker compose up --build -d

# AWS 프로덕션 환경  
# .env 파일에서 아래 설정 변경:
ENVIRONMENT=production
DEBUG=false
COOKIE_SECURE=true
VOLUME_MODE=ro
WORKERS=4
LOG_LEVEL=warning

# 동일한 명령어로 실행
docker compose up --build -d
```

### CloudFront 연동 설정
- **Origin**: ALB 또는 EC2 Public IP
- **Behavior**: 모든 요청 전달 (/*) 
- **Headers**: Host, X-Forwarded-Proto, X-Forwarded-For 전달
- **HTTPS Only**: HTTP → HTTPS 자동 리디렉션
- **Real IP**: CloudFront IP 범위 설정으로 실제 클라이언트 IP 추적
