## 빈번한 실수와 해결 방법

### Phase 1 Infrastructure Setup 교훈 (2025-08-31)

#### 1. Docker 에서 Module Import 경로 문제 (2025-08-31)
**문제**: `ModuleNotFoundError: No module named 'app'`
**원인**: Docker WORKDIR이 `/app`인데 코드에서 `import app.config` 사용
**해결책**: 모든 import를 상대 경로로 변경
```python
# ❌ 잘못된 방법 (Docker에서 실패)
from app.config import settings
from app.utils.jwt_utils import create_token

# ✅ 올바른 방법 (Docker 호환)
import config
from utils.jwt_utils import create_token  
```
**핵심**: Docker 컨테이너에서는 `app.` 접두사 없이 직접 모듈 import
**영향**: 16개 파일 수정 (소스 12개 + 테스트 4개), 모든 patch 경로 수정

#### 2. Nginx Rate Limiting 설정 위치 오류
**문제**: `"limit_req_zone" directive is not allowed here`
**원인**: server 블록 내부에 limit_req_zone 설정 시도
**해결책**: http 컨텍스트(최상위)에 rate limiting 설정
```nginx
# ✅ 올바른 위치 (http 컨텍스트)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;  # 사용만 여기서
    }
}
```

#### 3. Supabase 클라이언트 초기화 키 문제
**문제**: `Invalid API key` 인증 오류
**원인**: SERVICE_ROLE_KEY를 client 초기화에 사용
**해결책**: ANON_KEY 사용으로 변경
```python
# ❌ 잘못된 방법
supabase_client = create_client(url, service_role_key)

# ✅ 올바른 방법
supabase_client = create_client(url, anon_key)
```

#### 4. Python 의존성 버전 충돌
**문제**: `Could not find version cryptography==41.0.8`
**원인**: 정확한 버전(==) 지정으로 인한 호환성 문제
**해결책**: 최소 버전(>=) 사용
```
# ❌ 충돌 발생
cryptography==41.0.8

# ✅ 호환성 확보
cryptography>=41.0.0
```

#### 5. FastAPI lifespan 관리 베스트 프랙티스
**핵심**: @asynccontextmanager로 시작/종료 이벤트 관리
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("애플리케이션 시작")
    # 시작 시 초기화 작업
    yield  # 애플리케이션 실행
    logging.info("애플리케이션 종료")
    # 종료 시 정리 작업
```

### Phase 2 Authentication System 교훈 (2025-09-01)

#### 6. Pydantic 모델 필드 누락 오류 (2025-09-01)
**문제**: `1 validation error for UserResponse updated_at Field required`
**원인**: Pydantic 모델에 정의된 필수 필드가 API 응답 데이터에서 누락
**해결책**: SQL RETURNING 절과 Mock 응답 데이터 양쪽 모두 수정
```python
# ❌ 문제 상황
# models/auth.py의 UserResponse에는 updated_at 필드가 정의되어 있음
class UserResponse(UserBase):
    updated_at: datetime  # 필수 필드

# 하지만 services/real_supabase_service.py에서 누락
RETURNING id, email, name, phone, company_type, approved, role, created_at
#         ↑ updated_at 필드 누락

# ✅ 올바른 해결 방법
# 1. SQL RETURNING 절에 추가
RETURNING id, email, name, phone, company_type, approved, role, created_at, updated_at

# 2. Mock 응답 데이터에도 추가  
return [{
    "updated_at": "2025-09-01T00:00:00Z"  # 추가
}]
```
**핵심**: Pydantic 모델 정의와 실제 API 응답 데이터 구조 일치 필수
**발견**: 회원가입 버튼이 응답하지 않는다고 생각했지만 실제로는 Pydantic 검증 오류
**예방**: API 개발 시 Pydantic 모델과 실제 반환 데이터 간 일치성 확인 필수

#### 7. 관리자 계정 비밀번호 해시 불일치 (2025-09-01)
**문제**: 관리자 로그인 실패 - "이메일 또는 비밀번호가 일치하지 않습니다"
**원인**: MockSupabaseService users_storage의 관리자 password_hash가 "admin123"에 대한 올바른 bcrypt 해시가 아님
**진단**: 
```python
# bcrypt 해시 검증 실패
pwd_context.verify("admin123", stored_hash)  # False 반환
```
**해결책**: Python으로 올바른 bcrypt 해시 생성 후 교체
```python
# 올바른 해시 생성
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
correct_hash = pwd_context.hash("admin123")
# Result: "$2b$12$Z7OxDpJQHNJHnllc/CqZ3evVu2TFChMePi1rMS6EFZeBPplMapxlW"
```
**핵심**: Mock 데이터의 비밀번호 해시는 실제 해싱 함수로 생성된 값 사용 필수
**예방**: 테스트 데이터 작성 시 하드코딩된 해시값 사용 금지, 실제 해시 함수 이용

### Phase 6 Admin Approval System 교훈 (2025-09-01)

#### 8. Mock Service 데이터 형식 일관성 문제 (2025-09-01)
**문제**: `'list' object has no attribute 'get'` 오류
**원인**: RealSupabaseService.execute_sql()이 때로는 직접 리스트 반환, 때로는 {"data": [...]} 반환
**해결책**: 모든 return 문을 {"data": [...]} 형식으로 통일
```python
# ❌ 잘못된 방법 (일관성 없음)
return [{"id": "123"}]          # 직접 리스트
return {"data": [{"id": "456"}]} # 래핑된 형식

# ✅ 올바른 방법 (일관성 확보)
return {"data": [{"id": "123"}]}  # 항상 래핑된 형식
return {"data": []}               # 빈 결과도 래핑
```
**핵심**: Mock 서비스는 실제 API와 동일한 데이터 형식을 유지해야 함
**영향**: 48개 return 문 수정, AdminService 정상 작동 확보

#### 9. Supabase MCP execute_sql 파라미터 누락 (2025-09-01)
**문제**: `TypeError: execute_sql() missing 1 required keyword-only argument: 'project_id'`
**원인**: AdminService에서 project_id 파라미터 누락
**해결책**: 모든 execute_sql 호출에 project_id 추가
```python
# ❌ 잘못된 방법
result = await real_supabase_service.execute_sql(query=query)

# ✅ 올바른 방법  
result = await real_supabase_service.execute_sql(project_id="vrsbmygqyfvvuaixibrh", query=query)
```
**핵심**: Supabase MCP는 project_id가 필수 키워드 인자
**영향**: AdminService 3개 메서드 수정 (get_notices, create_notice, delete_notice)

#### 10. TDD를 통한 관리자 API 신뢰성 확보 (2025-09-01)
**성공 요인**: 테스트 먼저 작성으로 요구사항 명확화 및 버그 조기 발견
```python
# ✅ TDD 접근법으로 성공
1. test_get_pending_users_success() 작성 (기대 동작 정의)
2. AdminService.get_pending_users() 구현 
3. 테스트 실행 → 실패 → 수정 → 반복
4. E2E 테스트로 실제 브라우저 검증
```
**핵심**: AsyncMock 사용으로 비동기 메서드 올바른 모킹
**결과**: 6개 테스트 케이스로 모든 엣지 케이스 커버 (성공, 빈 결과, DB 오류, 승인 처리, 통계)
**검증**: E2E 테스트로 실제 브라우저에서 승인 플로우 완전 검증

### Phase 7 회원신청 상세보기 구현 교훈 (2025-09-01)

#### 11. UUID 타입 비교 문제 (2025-09-01)
**문제**: 테스트에서 `assert result.id == user_id` 실패
**원인**: result.id는 UUID 객체, user_id는 문자열로 타입 불일치
**해결책**: `str(result.id) == user_id`로 문자열 변환 후 비교
```python
# ❌ 타입 불일치
assert result.id == user_id  # UUID vs str

# ✅ 문자열 변환 후 비교  
assert str(result.id) == user_id
```

#### 12. MockSupabaseService UUID 형식 오류 (2025-09-01)
**문제**: `{user_id}-company` 형태 문자열을 company_id로 사용하여 UUID 파싱 실패
**원인**: UUID 형식이 아닌 문자열을 UUID 필드에 할당
**해결책**: `str(uuid.uuid4())`로 실제 UUID 생성
```python
# ❌ 잘못된 UUID 형식
'company_id': f"{user_id}-company"

# ✅ 올바른 UUID 형식
'company_id': str(uuid.uuid4())
```

#### 13. JavaScript URL 파싱 버그 (2025-09-01)
**문제**: `window.location.pathname.split('/').pop()`이 "detail"을 반환하여 user_id 추출 실패
**원인**: `/admin/users/{user_id}/detail` 경로에서 마지막 요소는 "detail"임
**해결책**: `pathParts[pathParts.length - 2]` 사용하여 user_id 추출
```javascript
// ❌ 잘못된 URL 파싱
const userId = window.location.pathname.split('/').pop(); // "detail" 반환

// ✅ 올바른 URL 파싱
const pathParts = window.location.pathname.split('/');
const userId = pathParts[pathParts.length - 2]; // user_id 반환
```

#### 14. RealSupabaseService JOIN 쿼리 미지원 (2025-09-01)
**문제**: 관리자 상세 조회 시 LEFT JOIN 쿼리를 처리하지 못함
**원인**: real_supabase_service.py에 복잡한 JOIN 쿼리 패턴 매칭 로직 부재
**해결책**: 쿼리 패턴 매칭 추가로 JOIN 쿼리 지원
```python
# 추가된 패턴 매칭
elif "LEFT JOIN companies c ON u.id = c.user_id" in query and "WHERE u.id =" in query:
    # JOIN 쿼리 처리 로직
```
**핵심**: 복잡한 JOIN 쿼리는 별도 패턴 매칭으로 처리 필요
**영향**: AdminService.get_user_detail() 정상 작동 확보

### Phase 8 공지사항 시스템 버그 수정 교훈 (2025-09-01)

#### 15. 공지사항 생성 후 공용 페이지 빈 상태 문제 (2025-09-01)
**문제**: 관리자에서 공지사항 생성 성공(200 OK)하지만 공용 공지사항 페이지(`/notices`)에서 빈 상태로 표시
**원인**: MockSupabaseService의 INSERT INTO notices 쿼리 패턴 매칭 실패
**진단**: 
```bash
# 로그 분석 결과
WARNING:services.real_supabase_service:📊 현재 notices_storage 길이: 0  # 저장소 비어있음
# INSERT 쿼리 실행되지만 패턴 매칭 실패
```
**해결책**: 멀티라인 쿼리 정규화 및 정규식 패턴 개선
```python
# ❌ 문제 상황: 멀티라인 INSERT 쿼리 패턴 매칭 실패
values_match = re.search(r"VALUES \('([^']+)', '([^']+)', ...", query)  # 실패

# ✅ 해결 방법: 쿼리 정규화 후 패턴 매칭
normalized_query = re.sub(r'\s+', ' ', query.strip())  # 멀티라인 → 한줄
values_match = re.search(r"VALUES \('([^']+)', '([^']+)', ...", normalized_query)  # 성공
```
**핵심**: 멀티라인 SQL 쿼리는 정규화 후 패턴 매칭 필요
**결과**: `notices_storage 길이: 1`, 공용 페이지에 공지사항 정상 표시
**영향**: 공지사항 시스템 완전 정상화

#### 16. 공지사항 페이지 네비게이션 누락 문제 (2025-09-01)
**문제**: `/notices` 공용 페이지에 네비게이션 메뉴 및 돌아가기 버튼 없음
**원인**: notices.html 템플릿에 header 블록 미정의로 base.html의 기본 헤더만 표시
**해결책**: notices.html에 header 블록 추가하여 전용 네비게이션 구현
```html
{% block header %}
<header class="bg-white shadow-sm border-b border-gray-200">
    <!-- 로고 + 네비게이션 링크 + 돌아가기 버튼 -->
    <a href="/">홈</a>
    <a href="/dashboard">대시보드</a>
    <button onclick="history.back()">돌아가기</button>
</header>
{% endblock %}
```
**핵심**: 공용 페이지도 적절한 네비게이션 제공으로 사용자 경험 향상 필요
**검증**: E2E 테스트로 admin → notices → home → notices 플로우 정상 작동 확인

### Phase 9 전체 코드 버그 분석 교훈 (2025-09-01)

#### 17. API 라우터 prefix 중복 문제 (2025-09-01)
**문제**: `/api/api/dashboard` 경로 중복 생성
**원인**: dashboard.py에서 `APIRouter(prefix="/api/dashboard")`인데 main.py에서 `prefix="/api"` 추가
**해결책**: main.py에서 dashboard.router prefix 제거
```python
# ❌ 잘못된 방법 (중복 발생)
app.include_router(dashboard.router, prefix="/api", tags=["대시보드"])

# ✅ 올바른 방법 (중복 제거)
app.include_router(dashboard.router, tags=["대시보드"])
```
**핵심**: 라우터 내부 prefix와 main.py 등록 시 prefix 중복 확인 필수
**검증**: `/api/dashboard/stats` 경로 정상 작동 확인

#### 18. SQL 인젝션 취약점 패턴 발견 (2025-09-01)
**문제**: 모든 서비스에서 f-string SQL 쿼리 사용으로 SQL 인젝션 위험
**위치**: real_supabase_service.py, product_service.py, company_service.py, auth_service.py
**패턴**: `f"SELECT * FROM users WHERE email = '{email}'"` 형태
**권장사항**: 파라미터화된 쿼리 사용
```python
# ❌ 위험한 방법 (SQL 인젝션 취약)
f"SELECT * FROM users WHERE email = '{email}'"

# ✅ 안전한 방법 (파라미터화)
"SELECT * FROM users WHERE email = %s", (email,)
```
**현재 상태**: Mock 서비스이므로 즉시 위험도는 낮음
**예방**: 실제 DB 연동 시 Supabase MCP 파라미터화 쿼리 사용 필수

### 로그인 세션 지속성 버그 수정 교훈 (2025-09-02)

#### 19. testuser 계정 로그인 리다이렉트 실패 (2025-09-02)
**문제**: testuser@example.com 계정 로그인 후 대시보드로 리다이렉트되지 않음
**원인**: RealSupabaseService에서 testuser UUID가 쿼리 패턴 매칭에 포함되지 않음
**진단**: 
```bash
# 로그 분석 결과
WARNING:auth.middleware:Token valid but user not found: 33333333-4444-5555-6666-777777777777
WARNING:services.real_supabase_service:처리되지 않은 쿼리: SELECT id, email, name, phone, company_type, approved, role, created_at, updated_at FROM users WHERE id = '33333333-4444-5555-6666-777777777777'
```
**해결책**: RealSupabaseService 쿼리 패턴에 testuser UUID 추가
```python
# ❌ 문제 상황: testuser UUID 누락
elif "SELECT id, email, name" in query and ("admin@example.com" in query or "7b4590df-10cc-4074-9186-4957ef96bfbb" in query or "11111111-2222-3333-4444-555555555555" in query or "22222222-3333-4444-5555-666666666666" in query):

# ✅ 해결 방법: testuser UUID 추가
elif "SELECT id, email, name" in query and ("admin@example.com" in query or "7b4590df-10cc-4074-9186-4957ef96bfbb" in query or "11111111-2222-3333-4444-555555555555" in query or "22222222-3333-4444-5555-666666666666" in query or "33333333-4444-5555-6666-777777777777" in query):
```
**핵심**: 새로운 테스트 사용자 추가 시 Mock 서비스의 쿼리 패턴에도 UUID 추가 필수
**검증**: E2E 테스트로 testuser 로그인 → 대시보드 리다이렉트 정상 작동 확인
**영향**: 모든 테스트 사용자 계정의 완전한 인증 플로우 보장