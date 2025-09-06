# 마법옷장 - 남대문시장 아동복 재고관리 플랫폼

> 남대문시장 아동복 도소매 업체를 위한 B2B 재고관리 및 주문 시스템

## 시스템 구성

```
Browser → CloudFront → ALB → Docker(Nginx → FastAPI) → Supabase
                                    ↓
                              Wasabi Cloud Storage
```

## 핵심 기능

- **사용자 관리**: JWT 인증, 관리자 승인 시스템
- **거래처 관리**: 도매-소매 업체 관계 관리
- **재고 관리**: 실시간 재고 추적, 안전재고 알림
- **주문 시스템**: 도소매간 주문 처리 워크플로우
- **실시간 채팅**: WebSocket 기반 업체간 소통
- **공지사항**: 관리자 전용 공지 시스템

## 빠른 시작

### 1. 환경 설정

```bash
# 환경변수 파일 생성
cp .env.example .env

# .env 파일에서 실제 값으로 수정
# - SUPABASE_* 키들
# - SESSION_SECRET, CSRF_SECRET
# - WASABI_* (선택적)
```

### 2. 로컬 개발 실행

```bash
# Docker Compose로 전체 시스템 실행
docker compose up --build -d

# 로그 확인
docker compose logs -f

# 서비스 확인
curl http://localhost/health
```

### 3. 서비스 접근

- **메인 페이지**: http://localhost
- **관리자 페이지**: http://localhost/admin
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost/health

### 4. 초기 관리자 계정

```
이메일: admin@example.com
비밀번호: admin123
```

## AWS 배포

### 1. 환경변수 수정

```bash
# AWS 프로덕션 환경 설정
ENVIRONMENT=production
DEBUG=false
COOKIE_SECURE=true
VOLUME_MODE=ro
WORKERS=4
LOG_LEVEL=warning
```

### 2. Docker 이미지 빌드 및 배포

```bash
# EC2/ECS에서 동일한 명령어 실행
docker compose up --build -d

# 또는 개별 이미지 빌드
docker build -t magic-app .
docker run -d --name magic-app magic-app
```

### 3. CloudFront 설정

- **Origin**: ALB 또는 EC2 인스턴스
- **Behavior**: 모든 요청 전달 (/*) 
- **Headers**: Host, X-Forwarded-Proto, X-Forwarded-For 전달
- **HTTPS Only**: Redirect HTTP to HTTPS

## 개발 가이드

### 테스트 실행

```bash
# 단위 테스트 (Docker 컨테이너 내부)
docker compose exec app python -m pytest tests/ -v

# 또는 로컬에서 (PYTHONPATH 설정 필요)
PYTHONPATH=./app python -m pytest tests/ -v
```

### 코드 품질 체크

```bash
# 린트 검사
docker compose exec app python -m flake8 app/

# 타입 체크  
docker compose exec app python -m mypy app/
```

### 로그 모니터링

```bash
# 실시간 로그
docker compose logs -f app

# 특정 서비스 로그
docker compose logs nginx
docker compose logs app
```

## 기술 스택

- **백엔드**: Python 3.13 + FastAPI
- **프론트엔드**: Jinja2 + HTMX + Alpine.js + Tailwind CSS
- **데이터베이스**: Supabase (PostgreSQL)
- **인증**: JWT (Access 15분 + Refresh 30일)
- **파일 저장**: Wasabi Cloud Storage
- **컨테이너**: Docker + Nginx
- **배포**: AWS (EC2/ECS + CloudFront + ALB)

## 디렉토리 구조

```
magic-full/
├── app/                    # FastAPI 애플리케이션
│   ├── main.py            # 애플리케이션 진입점
│   ├── api/               # API 라우터들
│   ├── models/            # Pydantic 모델들
│   ├── services/          # 비즈니스 로직
│   ├── auth/              # 인증 시스템
│   ├── utils/             # 유틸리티 함수들
│   ├── templates/         # Jinja2 템플릿들
│   └── static/            # CSS, JS, 이미지
├── tests/                 # 테스트 파일들
├── docker-compose.yml     # Docker 서비스 정의
├── Dockerfile            # FastAPI 컨테이너 빌드
├── nginx.conf            # Nginx 프록시 설정
├── requirements.txt      # Python 의존성
└── .env.example          # 환경변수 템플릿
```

## 포트 및 서비스

| 서비스 | 포트 | 용도 |
|--------|------|------|
| Nginx | 80 | HTTP 프록시 |
| Nginx | 443 | HTTPS (CloudFront 사용시 불필요) |
| FastAPI | 8000 | 백엔드 API |

## 문제 해결

### 일반적인 문제들

```bash
# 컨테이너 재시작
docker compose restart

# 이미지 재빌드
docker compose up --build --force-recreate

# 로그 확인
docker compose logs app

# 컨테이너 상태 확인
docker compose ps

# 환경변수 확인
docker compose exec app env | grep SUPABASE
```

### 헬스체크 실패

```bash
# FastAPI 상태 확인
curl http://localhost:8000/health

# Nginx 상태 확인  
curl http://localhost/health

# 데이터베이스 연결 확인
curl http://localhost/health/db
```

## 보안 고려사항

- **환경변수**: `.env` 파일을 git에 커밋하지 마세요
- **세션 시크릿**: 프로덕션에서는 강력한 32자 이상 키 사용
- **쿠키 보안**: AWS 배포시 `COOKIE_SECURE=true` 설정
- **Rate Limiting**: Nginx에서 API별 요청 제한 적용
- **HTTPS**: CloudFront에서 SSL/TLS 종료 처리

## 문서

- **ARCHITECTURE.md**: 시스템 아키텍처 및 DB 스키마
- **DESIGN.md**: UI/UX 디자인 가이드  
- **TESTPLAN.md**: 테스트 전략 및 케이스
- **PROGRESS.md**: 개발 진행 상황
- **NOTE.md**: 개발 중 발견한 이슈들 및 해결책