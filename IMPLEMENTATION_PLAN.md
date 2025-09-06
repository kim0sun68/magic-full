# 마법옷장 구현 계획서

## 📋 전체 구현 로드맵 (8주)

### **Phase 1: 핵심 인프라 (2주)**
```
Week 1: 인증 시스템 + 기본 CRUD
- JWT 토큰 시스템 (Access + Refresh)
- 회원가입/로그인/승인 프로세스
- 기본 데이터베이스 모델
- Docker 환경 구성

Week 2: 거래관계 + 권한 시스템
- 업체간 거래신청/승인 로직
- 데이터 접근 권한 구현
- 기본 UI 컴포넌트 (header/footer/nav)
```

### **Phase 2: 핵심 비즈니스 로직 (2주)**
```
Week 3: 상품 & 재고 관리
- 상품 CRUD + 이미지 업로드
- 실시간 재고 관리 + 동시성 제어
- 안전재고 알림 시스템

Week 4: 주문 관리 시스템
- 주문 생성/확인/상태 변경
- 재고 연동 + 트랜잭션 처리
- 주문 상세 페이지
```

### **Phase 3: 실시간 통신 (2주)**
```
Week 5: WebSocket 채팅
- 실시간 채팅 시스템
- 메시지 DB 저장/조회
- 파일 첨부 기능

Week 6: 알림 & SSE
- Server-Sent Events 구현
- 재고 부족 실시간 알림
- 주문 상태 변경 알림
```

### **Phase 4: 관리자 & 최적화 (2주)**
```
Week 7: 관리자 기능
- 승인 관리 시스템
- 공지사항 관리 (Quill.js)
- 메모 관리 시스템
- 사용자/거래처 관리

Week 8: 테스트 & 배포
- E2E 테스트 (Playwright)
- 성능 최적화
- 보안 검증
- 프로덕션 배포
```

## 🛠 기술 구현 상세

### 1. 인증 시스템 구현
```python
# app/auth/jwt_handler.py
class JWTHandler:
    def create_access_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    def create_refresh_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(days=30)
        
    def verify_token(self, token: str) -> dict:
        # JWT 검증 + 만료 확인

# app/auth/middleware.py  
async def auth_middleware(request: Request, call_next):
    # Access token 확인 → 만료시 refresh token으로 갱신
    # CSRF 토큰 검증 (POST/PUT/DELETE 요청)
```

### 2. 거래관계 시스템
```python
# app/models/company.py
class CompanyRelationship(BaseModel):
    wholesale_company_id: UUID
    retail_company_id: UUID
    status: Literal['pending', 'approved', 'rejected']
    
# app/api/companies.py
@router.post("/relationships")
async def create_relationship(request: RelationshipRequest):
    # 1. 중복 신청 방지 확인
    # 2. 거래관계 생성 (status='pending')
    # 3. 도매업체에 알림 전송
    
@router.put("/relationships/{id}/approve")  
async def approve_relationship(id: UUID):
    # 도매업체만 승인 가능 (권한 확인)
    # status='approved' 업데이트
```

### 3. 재고 동시성 제어
```python
# app/services/inventory.py
async def decrease_inventory(product_id: UUID, quantity: int, order_id: UUID):
    async with database.transaction():
        # Row-level locking
        current = await database.fetch_one(
            "SELECT current_stock FROM inventory WHERE product_id = $1 FOR UPDATE",
            product_id
        )
        
        if current['current_stock'] < quantity:
            raise HTTPException(400, "재고 부족")
            
        # 재고 차감
        await database.execute(
            "UPDATE inventory SET current_stock = current_stock - $1 WHERE product_id = $2",
            quantity, product_id
        )
        
        # 거래내역 기록
        await database.execute(
            "INSERT INTO inventory_transactions (product_id, transaction_type, quantity, reference_id) VALUES ($1, 'out', $2, $3)",
            product_id, quantity, order_id
        )
```

### 4. WebSocket 채팅 구현
```python
# app/api/chat.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        
    async def broadcast_message(self, room_id: str, message: dict):
        # DB 저장
        await save_message_to_db(message)
        
        # WebSocket 브로드캐스트
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

@app.websocket("/ws/chat/{room_id}")
async def chat_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
```

### 5. Wasabi 파일업로드
```python
# app/services/file_upload.py
async def generate_presigned_url(file_name: str, content_type: str):
    # Wasabi S3 호환 presigned URL 생성
    return {
        "upload_url": presigned_url,
        "file_key": file_key,
        "expire_time": expire_time
    }

# 클라이언트 측 (JavaScript)
async function uploadImage(file) {
    // 1. 이미지 리사이징 (Canvas API)
    const resized = await resizeImage(file, { maxWidth: 800, maxHeight: 600, quality: 0.8 });
    
    // 2. Presigned URL 요청
    const { upload_url, file_key } = await fetch('/api/files/presigned-url');
    
    // 3. Wasabi 직접 업로드
    await fetch(upload_url, { method: 'PUT', body: resized });
    
    // 4. 서버에 파일 URL 저장
    await fetch('/api/files/confirm', { 
        method: 'POST', 
        body: JSON.stringify({ file_key }) 
    });
}
```

## 🔄 개발 우선순위 매트릭스

### Critical Path (병렬 개발 불가)
```
1. DB 스키마 → 2. 인증 시스템 → 3. 권한 시스템 → 4. 거래관계 → 5. 주문시스템
```

### 병렬 개발 가능
```
A) UI 컴포넌트 개발 (템플릿 + CSS)
B) 파일업로드 시스템
C) 채팅 시스템  
D) 관리자 기능
E) 테스트 코드 작성
```

### 통합 순서
```
Week 1-2: Critical Path (1-3)
Week 3-4: Critical Path (4-5) + 병렬 (A, B)
Week 5-6: 병렬 (C, D) + 통합 테스트
Week 7-8: 병렬 (E) + 성능 최적화 + 배포
```

## 🧪 테스트 전략

### 단위 테스트 (pytest)
```python
# tests/test_auth.py
def test_jwt_token_generation()
def test_refresh_token_rotation()
def test_csrf_validation()

# tests/test_inventory.py  
def test_concurrent_inventory_decrement()
def test_low_stock_alert_trigger()
```

### 통합 테스트 (FastAPI TestClient)
```python
# tests/test_api.py
def test_order_creation_workflow()
def test_company_relationship_approval()
def test_unauthorized_access_prevention()
```

### E2E 테스트 (Playwright MCP)
```python
# 핵심 사용자 시나리오
1. 회원가입 → 관리자 승인 → 로그인 플로우
2. 거래관계 신청 → 승인 → 상품 주문 플로우  
3. 실시간 채팅 → 주문 생성 → 상태 변경 플로우
4. 재고 관리 → 알림 → 조정 플로우
```

## 📊 성능 최적화 계획

### 데이터베이스 최적화
```sql
-- 인덱스 생성
CREATE INDEX idx_products_company_category ON products(company_id, category_id);
CREATE INDEX idx_orders_status_date ON orders(status, created_at);
CREATE INDEX idx_inventory_low_stock ON inventory(product_id) WHERE current_stock <= minimum_stock;
CREATE INDEX idx_chat_messages_room_time ON chat_messages(room_id, created_at);
```

### 캐싱 전략
```python
# Redis 캐싱 (선택사항)
- 상품 목록: 5분 캐시
- 재고 현황: 실시간 (캐시 없음)
- 거래처 목록: 30분 캐시
- 공지사항: 1시간 캐시
```

### 프론트엔드 최적화
```javascript
// HTMX + Alpine.js 최적화
- 이미지 지연 로딩
- 무한 스크롤 (상품/주문 목록)
- 디바운스 검색
- 로컬 스토리지 캐싱
```

## 🚀 배포 & 운영

### Docker 구성
```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    
  app:
    build: .
    environment:
      - SUPABASE_URL
      - WASABI_ENDPOINT
    depends_on: [nginx]
```

### 모니터링 & 로깅
```python
# 구조화된 로깅
{
  "timestamp": "2025-08-31T10:00:00Z",
  "level": "INFO",
  "service": "inventory",
  "action": "stock_update",
  "product_id": "uuid",
  "previous_stock": 100,
  "new_stock": 95,
  "user_id": "uuid"
}
```

### 보안 체크리스트
```
✅ JWT httpOnly 쿠키 + CSRF 보호
✅ SQL Injection 방어 (Parameterized queries)
✅ XSS 방어 (bleach HTML 정화)
✅ Rate Limiting (Nginx)
✅ 파일업로드 검증 (타입/크기 제한)
✅ HTTPS 강제 (프로덕션)
✅ 환경변수 보안 관리
```