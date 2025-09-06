# 마법옷장 남대문시장 아동복 재고관리 플랫폼

## 프로젝트 개요
- **서비스명**: 마법옷장 - 남대문시장 아동복 도소매 재고관리 서비스

## 기술 스택 
- **백엔드 & SSR 프론트**  
  - Python 3.13 + FastAPI
  - 템플릿: **Jinja2**  
  - UI: Tailwind CSS 3.4 + **HTMX**(부분 갱신)  
- **인증·DB**: **Supabase**  
  - Auth·SQL은 Supabase API를 *서버 측(FastAPI)* 에서만 호출
  - **브라우저에는 Supabase JS SDK·키를 포함하지 않음**  
- **파일 저장(이미지파일 등)**: Wasabi Cloud 서비스 사용
- **배포**: 통합 Docker Compose 환경
  - 로컬/AWS 환경 단일 docker-compose.yml로 통합
  - CloudFront + ALB + Docker(Nginx + FastAPI) 아키텍처
  - 환경변수 기반 로컬/프로덕션 설정 분리

## 핵심 문서
- **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
- **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 사항)
- **@DESIGN.md**: UI/UX 디자인 가이드
- **@TESTPLAN.md**: 테스트 전략
- **@TESTDATA.md**: 테스트 데이터

## 공통 작업 가이드
- 모든 작업은 ultra think 해서 작업해주세요.
- 모든 작업은 
  1. 먼저 현재 상태를 철저히 분석하고, 
  2. 철저하게 계획을 세우고, 
  3. sub agents 로 분리하지 말고, 순차적인 작업 계획을 작성한 후, 
  4. API 는 모두 TDD 기반으로 테스트 코드 및 실제 코드를 구현하고, 
  5. API 는 예외 케이스까지 완벽히 테스트하고, 
  6. 코드 완성 후에는 바로 종료하지 말고, 전체 코드를 코드 레벨로 확인하여, 확실한 버그가 발견되면, 수정해주세요
- 작업이 완료되면 꼭 기억해야할 내용에 대해서는 PROGRESS.md 파일에 기록해주고, 
- 필요시 CLAUDE.md 와 ARCHITECTURE.md 등의 다음 주요 파일들도 개선해주세요
- 모든 작업은 다음 주요 파일을 확인하여 작업해주세요
  - **@CLAUDE.md**: 전체 프로젝트 개요 및 기술스택과 작업 가이드
  - **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
  - **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 내용)
  - **@DESIGN.md**: UI/UX 디자인 가이드
    - wireframes 하위폴더에 UI 구현이 필요한 모든 화면은 xml 포멧으로 UI 화면 표현
  - **@TESTPLAN.md**: 테스트 항목
  - **@TESTDATA.md**: 테스트시 필요한 데이터
  - **@NOTE.md**: 빈번한 실수와 해결 방법 기억
- 작업 완료 후에는 테스트 항목을 @TESTPLAN.md 파일에 작성하고, 직접 docker 를 실행하고, puppeteer MCP 로 테스트하여, 모든 버그를 side effect 를 고려하여 신중하게 수정한 후, @TESTPLAN.md 에 기재된 모든 테스트 항목이 PASS 할 때까지 작업을 반복합니다
  - 주로 실수하는 항목은 @NOTE.md 파일에 이후 실수를 반복하지 않기 위해 기재합니다.
  - **중요**: 테스트 실행 시 `PYTHONPATH=./app python -m pytest` 로 실행 (임포트 경로 수정 후 필수)

## MCP 사용 설정
- 다음 MCP 가 연결되어 있으므로, 관련 작업은 해당 MCP 를 직접 사용해서 작업해주세요
  - supabase MCP (supabase 제어)
  - puppeteer MCP (브라우저 제어)

## Supabase 설정
- **프로젝트 ID**: vrsbmygqyfvvuaixibrh
- **초기 관리자**: admin@example.com / admin123
- **중요**: Email confirmation OFF, RLS OFF
  - FastAPI 내부에서만 supabase 에 엑세스하므로 RLS 불필요

## 핵심 기능

### 1. 사용자 관리 체계
- **인증/인가**: JWT 쿠키 방식, CSRF 보호, 세션 관리
- **회원가입 승인**: 관리자 승인 후 계정 활성화 (B2B 특성)
- **권한 관리**: 일반회원/관리자 역할 기반 접근 제어

### 2. 거래처 관리
- **업체 등록**: 도매/소매 구분, 사업자 정보 관리
- **업체 관계**: 도소매간 거래 관계 설정 및 관리
- **계정 상태**: 활성/휴면/정지 상태 관리

### 3. 아동복 상품 및 재고 관리
- **상품 관리**: 아동복 등록/수정/삭제, 카테고리 분류
- **재고 추적**: 실시간 재고 현황, 입/출고 관리
- **이미지 관리**: Wasabi Cloud 기반 상품 이미지 저장

### 4. 주문 및 거래 시스템
- **주문 처리**: 도소매간 주문 생성/수정/취소
- **거래 내역**: 주문 이력, 결제 상태, 배송 추적
- **재고 연동**: 주문 시 자동 재고 차감 및 업데이트

### 5. 커뮤니케이션 플랫폼
- **실시간 채팅**: 도소매간 정보교환, 주문 협의
- **업체별 메모**: Quill.js 에디터, Base64 이미지 (1MB 제한)
- **공지사항**: 관리자 전용 게시, 전체 공지 시스템

### 6. 관리자 시스템
- **사용자 관리**: 회원가입 승인, 계정 상태 관리
- **업체 관리**: 거래처 승인, 관계 설정, 모니터링
- **시스템 관리**: 공지사항 작성, 데이터 관리, 로그 모니터링

## 배포 환경 설정

### 로컬 개발 환경
```bash
# 환경변수 파일 생성
cp .env.example .env

# .env에서 실제 Supabase 키로 수정 후
docker compose up --build -d

# 서비스 접근
curl http://localhost/health
```

### AWS 프로덕션 환경
```bash
# .env 파일에서 프로덕션 설정으로 변경
ENVIRONMENT=production
DEBUG=false
COOKIE_SECURE=true
VOLUME_MODE=ro
WORKERS=4

# 동일한 명령어로 배포
docker compose up --build -d
```

### 필수 환경변수 (.env)
```
# Supabase 연동
SUPABASE_URL=https://vrsbmygqyfvvuaixibrh.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 보안 설정
SESSION_SECRET=your-session-secret
COOKIE_SECURE=false  # AWS 배포시 true
COOKIE_SAMESITE=lax

# 환경 구분
ENVIRONMENT=development  # production for AWS
DEBUG=true              # false for AWS
VOLUME_MODE=rw          # ro for AWS
```

## 보안 체크리스트
- XSS 방어 (bleach)
- CSRF 보호 (Double Submit Cookie)
- Rate Limiting (Nginx)
- HttpOnly·Secure 쿠키

## 초기 데이터 셋업
- 초기 게시판: 공지사항(관리자만 글쓰기 허용)
- 관리자 데이터 세팅