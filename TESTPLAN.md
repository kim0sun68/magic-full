# AIZEVA 테스트 계획

## 테스트 전략
- 테스트 레벨별로 각각 테스트
  1. **단위 테스트**: 개별 함수 및 메서드
  2. **통합 테스트**: API 엔드포인트
  3. **E2E 테스트**: 전체 사용자 시나리오

## 테스트 환경
- **로컬**: Python pytest + Docker Compose
- **E2E**: Puppeteer MCP
- **데이터베이스**: 실제 Supabase 환경 (.env)

## 기능별 테스트 케이스

### ✅ Phase 1 - 인프라스트럭처 테스트 (2025-08-31 완료)

#### 1. Docker 환경 테스트
- [ ] `docker-compose up -d` 정상 실행
- [ ] nginx 컨테이너 80포트 리스닝 확인
- [ ] fastapi 컨테이너 8000포트 정상 응답
- [ ] 컨테이너 간 네트워크 통신 확인

#### 2. 헬스체크 엔드포인트 테스트
- [ ] GET `/health` → 200 OK, JSON 응답
- [ ] GET `/health/ready` → 200 OK, 서비스 준비 상태
- [ ] GET `/health/db` → 200 OK, DB 상태 (임시 mock 응답)

#### 3. Nginx 프록시 테스트
- [ ] Rate Limiting 정상 동작 (api: 10r/s, auth: 5r/s, chat: 20r/s)
- [ ] 보안 헤더 적용 확인 (X-Frame-Options, X-Content-Type-Options 등)
- [ ] 정적 파일 서빙 (/static/) 정상 동작
- [ ] API 프록시 (/api/) → FastAPI 정상 포워딩

#### 4. FastAPI 애플리케이션 테스트
- [ ] 메인 페이지 (/) 정상 렌더링
- [ ] Jinja2 템플릿 엔진 동작 확인
- [ ] 미들웨어 설정 (CORS, TrustedHost) 적용 확인

#### 5. Supabase 연결 테스트 (Phase 2에서 활성화)
- [ ] 데이터베이스 연결 정상 확인
- [ ] 12개 테이블 생성 및 관계 설정 검증
- [ ] 관리자 계정 생성 및 로그인 테스트

### 🔄 Phase 2 - JWT 인증 시스템 테스트 (TDD 기반)

#### 1. JWT 토큰 유틸리티 단위 테스트
- [ ] **create_access_token()**: 15분 만료 토큰 생성
- [ ] **create_refresh_token()**: 30일 만료 토큰 생성  
- [ ] **verify_token()**: 유효한 토큰 검증
- [ ] **verify_token()**: 만료된 토큰 거부
- [ ] **verify_token()**: 잘못된 토큰 거부
- [ ] **decode_token()**: 토큰에서 사용자 정보 추출
- [ ] **is_token_expired()**: 토큰 만료 확인

#### 2. 인증 API 엔드포인트 통합 테스트
**회원가입 (/api/auth/signup)**
- [x] 정상 회원가입: 201 Created + JWT 쿠키 설정 (2025-09-01 검증완료)
- [x] Pydantic 필드 누락 오류: UserResponse updated_at 필드 필수 (2025-09-01 수정완료)
- [x] E2E 회원가입 플로우: 폼 입력 → 제출 → 알림 → 리디렉션 (2025-09-01 검증완료)
- [ ] 중복 이메일: 409 Conflict 응답
- [ ] 잘못된 이메일 형식: 422 Validation Error
- [ ] 비밀번호 최소 길이 미달: 422 Validation Error
- [ ] 필수 필드 누락: 422 Validation Error

**로그인 (/api/auth/login)**
- [ ] 정상 로그인: 200 OK + JWT 쿠키 설정
- [ ] 잘못된 비밀번호: 401 Unauthorized
- [ ] 존재하지 않는 사용자: 401 Unauthorized
- [ ] 비활성화 사용자: 403 Forbidden
- [ ] Rate Limiting: 5초당 5회 초과 시 429

**토큰 갱신 (/api/auth/refresh)**  
- [ ] 유효한 Refresh 토큰: 200 OK + 새 Access 토큰
- [ ] 만료된 Refresh 토큰: 401 Unauthorized
- [ ] 잘못된 Refresh 토큰: 401 Unauthorized
- [ ] Refresh 토큰 없음: 401 Unauthorized

**로그아웃 (/api/auth/logout)**
- [ ] 정상 로그아웃: 200 OK + 쿠키 삭제
- [ ] 이미 로그아웃 상태: 200 OK (멱등성)

#### 3. 인증 미들웨어 테스트
- [ ] **유효한 Access 토큰**: 요청 통과 + user 정보 주입
- [ ] **만료된 Access 토큰**: 401 Unauthorized
- [ ] **잘못된 토큰**: 401 Unauthorized  
- [ ] **토큰 없음**: 401 Unauthorized (보호된 라우트)
- [ ] **공개 라우트**: 토큰 없이 접근 가능

#### 4. CSRF 보호 테스트
- [ ] **Double Submit Cookie**: CSRF 토큰 검증 성공
- [ ] **CSRF 토큰 누락**: 403 Forbidden
- [ ] **잘못된 CSRF 토큰**: 403 Forbidden
- [ ] **SameSite 쿠키**: 크로스 사이트 요청 차단

#### 5. 보안 테스트
- [ ] **HttpOnly 쿠키**: 브라우저 JS에서 접근 불가
- [ ] **Secure 쿠키**: HTTPS에서만 전송 (프로덕션)
- [ ] **SameSite=Lax**: CSRF 공격 방어
- [ ] **토큰 만료 처리**: 자동 갱신 또는 로그아웃
- [ ] **SQL Injection**: 인증 관련 쿼리 보안 검증

#### 6. E2E 인증 플로우 테스트 (Puppeteer MCP)
- [ ] **회원가입 → 로그인 → 보호된 페이지 접근**: 전체 플로우
- [ ] **자동 토큰 갱신**: Access 토큰 만료 시 자동 갱신
- [ ] **로그아웃 → 보호된 페이지 접근**: 리디렉션 확인
- [ ] **브라우저 재시작**: 쿠키 지속성 확인
- [ ] **동시 로그인**: 여러 브라우저/탭에서 동일 계정

#### 7. 성능 테스트
- [ ] **토큰 생성 속도**: 100ms 이내
- [ ] **토큰 검증 속도**: 50ms 이내  
- [ ] **동시 인증 요청**: 100개 동시 처리
- [ ] **DB 연결 풀**: 동시 쿼리 성능 확인

### ✅ Phase 7 - 관리자 상세보기 시스템 테스트 (2025-09-01 완료)

#### 1. AdminService.get_user_detail() 단위 테스트
- [x] **정상 조회**: users + companies LEFT JOIN 데이터 반환
- [x] **사용자 없음**: None 반환 처리
- [x] **회사 정보 없음**: 관리자 계정 등 회사 미연결 사용자 처리
- [x] **DB 오류**: RuntimeError 예외 발생 및 메시지 검증
- [x] **잘못된 UUID**: UUID 형식 오류 처리

#### 2. 관리자 상세보기 API 엔드포인트 통합 테스트
**사용자 상세 조회 (/api/admin/users/{user_id}/detail)**
- [x] 정상 조회: 200 OK + UserDetailResponse 반환
- [x] 존재하지 않는 사용자: 404 Not Found
- [x] 관리자 권한 확인: 일반 사용자 접근 거부 (403)
- [x] 잘못된 UUID 형식: 422 Validation Error
- [x] 인증되지 않은 접근: 401 Unauthorized

#### 3. 상세보기 UI 테스트 (E2E with Playwright MCP)
- [x] **상세보기 버튼**: 승인관리 탭에서 "세부정보" 버튼 표시
- [x] **페이지 이동**: 세부정보 버튼 클릭 → admin-detail 페이지 이동
- [x] **데이터 표시**: 계정정보, 거래처정보, 승인정보 3개 섹션 정상 표시
- [x] **승인/거부 버튼**: 승인 대기 사용자에 대해 액션 버튼 표시
- [x] **이미 승인된 사용자**: 승인 완료 메시지 표시
- [x] **돌아가기 기능**: history.back() 버튼으로 이전 페이지 복귀

#### 4. JavaScript 및 Alpine.js 연동 테스트
- [x] **URL 파싱**: `/admin/users/{user_id}/detail`에서 user_id 정상 추출
- [x] **API 호출**: fetchUserDetail() 함수로 상세 정보 조회
- [x] **데이터 바인딩**: Alpine.js x-text로 사용자 정보 표시
- [x] **상태 관리**: 로딩, 에러, 정상 상태 처리
- [x] **승인 처리**: approveUser() 함수로 승인/거부 처리

#### 5. 데이터베이스 연동 테스트
- [x] **JOIN 쿼리**: users와 companies 테이블 LEFT JOIN 정상 작동
- [x] **MockSupabaseService**: 관리자 상세 쿼리 패턴 매칭 지원
- [x] **RealSupabaseService**: 실제 Supabase DB 연동 쿼리 지원
- [x] **UUID 처리**: UUID 형식 검증 및 변환 정상 작동
- [x] **데이터 형식**: {"data": [...]} 형태 응답 표준화

