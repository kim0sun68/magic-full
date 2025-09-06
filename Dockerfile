# 마법옷장 FastAPI 애플리케이션 Dockerfile (Railway 배포용)
FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 환경 설정
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Railway 환경 변수 설정
ENV ENVIRONMENT=production
ENV DEBUG=false

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY ./app /app

# Railway에서 동적으로 할당하는 PORT 사용 (기본값: 8000)
EXPOSE ${PORT:-8000}

# 헬스체크 설정 (Railway PORT 환경변수 사용)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Railway 배포용 애플리케이션 실행 (동적 포트, 프로덕션 모드)
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}