# AWS EC2 배포 가이드

## 시스템 요구사항

### EC2 인스턴스 사양
- **최소 권장**: t3.medium (2 vCPU, 4GB RAM)
- **프로덕션 권장**: t3.large (2 vCPU, 8GB RAM) 이상
- **스토리지**: 20GB SSD (최소), 50GB+ (권장)
- **OS**: Ubuntu 22.04 LTS 또는 Amazon Linux 2023

### 네트워크 요구사항
- **보안 그룹**:
  - SSH: 22 (관리자 IP만)
  - HTTP: 80 (0.0.0.0/0 또는 ALB에서만)
  - HTTPS: 443 (CloudFront 사용시 불필요)

## 1단계: EC2 인스턴스 생성 및 초기 설정

### EC2 인스턴스 생성
```bash
# AWS CLI를 통한 인스턴스 생성 (선택사항)
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=magic-wardrobe}]'
```

### SSH 접속 및 시스템 업데이트
```bash
# EC2 인스턴스 접속
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y curl wget git unzip
```

## 2단계: Docker 설치

### Docker Engine 설치
```bash
# Docker 공식 GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Docker Compose 설치 (최신 버전)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

### Docker 설치 확인
```bash
# 새 세션 시작 또는 재로그인 후
docker --version
docker-compose --version
docker run hello-world
```

## 3단계: 프로젝트 코드 업로드

### 방법 1: Git Clone (권장)
```bash
# 프로젝트 클론
git clone https://github.com/your-username/magic-full.git
cd magic-full

# 또는 기존 프로젝트가 있다면
git pull origin main
```

### 방법 2: 파일 직접 업로드
```bash
# 로컬에서 EC2로 파일 전송
scp -i your-key.pem -r ./magic-full ubuntu@your-ec2-ip:~/

# EC2에서 디렉토리 이동
cd ~/magic-full
```

### 방법 3: 압축 파일 업로드
```bash
# 로컬에서 압축
tar -czf magic-full.tar.gz magic-full/

# EC2로 전송
scp -i your-key.pem magic-full.tar.gz ubuntu@your-ec2-ip:~/

# EC2에서 압축 해제
tar -xzf magic-full.tar.gz
cd magic-full
```

## 4단계: 환경 설정

### .env 파일 생성
```bash
# 환경 파일 복사
cp .env.example .env

# 환경 파일 편집
nano .env
```

### AWS 프로덕션 환경 설정
```bash
# .env 파일 내용 (필수 변경 사항)
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=warning

# 보안 설정 (HTTPS 사용시)
COOKIE_SECURE=true
COOKIE_SAMESITE=lax

# Docker 설정
VOLUME_MODE=ro
WORKERS=4
MAX_CONNECTIONS=1000

# Supabase 키 (실제 값으로 변경)
SUPABASE_URL=https://vrsbmygqyfvvuaixibrh.supabase.co
SUPABASE_ANON_KEY=your-actual-anon-key
SUPABASE_JWT_SECRET=your-actual-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-actual-service-role-key

# 세션 보안 (32자 이상 랜덤 키)
SESSION_SECRET=your-strong-session-secret-32-chars-min
CSRF_SECRET=your-csrf-secret

# Wasabi 설정 (선택사항)
WASABI_ACCESS_KEY=your-wasabi-access-key
WASABI_SECRET_KEY=your-wasabi-secret-key
WASABI_BUCKET=magic-storage
```

### 보안 강화 설정
```bash
# 강력한 세션 키 생성
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# .env 파일 권한 설정 (보안)
chmod 600 .env
```

## 5단계: 애플리케이션 배포

### Docker 빌드 및 실행
```bash
# 이미지 빌드 및 컨테이너 실행
docker compose up --build -d

# 실행 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f

# 특정 서비스 로그
docker compose logs app
docker compose logs nginx
```

### 헬스체크 확인
```bash
# 서비스 상태 확인
curl http://localhost/health
curl http://localhost/health/ready  
curl http://localhost/health/db

# FastAPI 직접 확인
curl http://localhost:8000/health
```

## 6단계: CloudFront 및 ALB 설정

### Application Load Balancer 생성
1. **타겟 그룹 생성**:
   - 타겟 타입: 인스턴스
   - 프로토콜: HTTP, 포트: 80
   - 헬스체크: `/health`

2. **ALB 생성**:
   - 스킴: Internet-facing
   - 리스너: HTTP:80 → 타겟 그룹

### CloudFront 배포 생성
1. **Origin 설정**:
   - Origin Domain: ALB DNS 이름
   - Protocol: HTTP Only
   - Origin Path: 비워둠

2. **Behavior 설정**:
   - Path Pattern: `*` (기본값)
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Allowed HTTP Methods: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - Cache Policy: Caching Disabled (동적 콘텐츠)

3. **Origins and Origin Groups**:
   - Custom Headers 추가:
     - `X-Forwarded-Proto`: `https`
     - `X-Forwarded-Port`: `443`

## 7단계: 도메인 및 SSL 설정

### Route 53 도메인 연결 (선택사항)
```bash
# CloudFront 배포 도메인 확인
aws cloudfront list-distributions --query "DistributionList.Items[0].DomainName"

# Route 53에서 CNAME 레코드 생성
# your-domain.com → d1234567890.cloudfront.net
```

### SSL 인증서 (CloudFront 자동 처리)
- CloudFront가 자동으로 SSL/TLS 처리
- 추가 SSL 설정 불필요

## 8단계: 모니터링 및 로그 설정

### CloudWatch 로그 설정 (선택사항)
```bash
# CloudWatch 에이전트 설치
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# 로그 그룹 생성
aws logs create-log-group --log-group-name /aws/ec2/magic-wardrobe
```

### 시스템 모니터링
```bash
# 시스템 리소스 모니터링
htop
df -h
free -h

# Docker 리소스 사용량
docker stats

# 애플리케이션 로그 실시간 모니터링
docker compose logs -f app
```

## 9단계: 자동 배포 스크립트

### 배포 스크립트 생성
```bash
# deploy.sh 파일 생성
cat > deploy.sh << 'EOF'
#!/bin/bash

echo "🚀 마법옷장 배포 시작..."

# Git 최신 코드 가져오기
git pull origin main

# 환경 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 설정하세요."
    exit 1
fi

# Docker 이미지 빌드 및 실행
echo "📦 Docker 이미지 빌드 중..."
docker compose down
docker compose up --build -d

# 헬스체크 대기
echo "⏳ 서비스 시작 대기 중..."
sleep 30

# 헬스체크 확인
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ 배포 성공! 서비스가 정상 작동 중입니다."
    echo "🌐 서비스 접속: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
else
    echo "❌ 배포 실패! 로그를 확인하세요:"
    docker compose logs app
    exit 1
fi
EOF

# 스크립트 실행 권한 부여
chmod +x deploy.sh
```

### 자동 재시작 설정
```bash
# 시스템 재부팅 시 자동 시작
cat > /etc/systemd/system/magic-wardrobe.service << 'EOF'
[Unit]
Description=Magic Wardrobe Docker Compose
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/magic-full
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl enable magic-wardrobe.service
```

## 10단계: 보안 및 최적화

### 보안 설정
```bash
# 방화벽 설정
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 자동 보안 업데이트 설정
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 성능 최적화
```bash
# 스왑 파일 생성 (메모리 부족 방지)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 배포 명령어 요약

### 초기 배포
```bash
# 1. EC2 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. 프로젝트 업로드
git clone https://github.com/your-repo/magic-full.git
cd magic-full

# 3. 환경 설정
cp .env.example .env
nano .env  # 프로덕션 값으로 수정

# 4. 배포 실행
./deploy.sh
```

### 업데이트 배포
```bash
# EC2에서 실행
cd magic-full
./deploy.sh
```

### 롤백 (문제 발생시)
```bash
# 이전 버전으로 롤백
git reset --hard HEAD~1
docker compose up --build -d
```

## 문제 해결

### 자주 발생하는 문제들

#### 1. 메모리 부족
```bash
# 메모리 사용량 확인
free -h
docker stats

# 스왑 추가 또는 인스턴스 크기 증가
sudo fallocate -l 2G /swapfile
```

#### 2. 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 프로세스 종료
sudo pkill -f nginx
sudo pkill -f uvicorn
```

#### 3. Docker 권한 문제
```bash
# Docker 그룹 추가 후 재로그인
sudo usermod -aG docker $USER
# 새 세션 시작 또는 재부팅
```

#### 4. 환경변수 문제
```bash
# 환경변수 확인
docker compose exec app env | grep SUPABASE

# .env 파일 권한 확인
ls -la .env
```

### 로그 확인 방법
```bash
# 전체 서비스 로그
docker compose logs

# 특정 서비스 로그
docker compose logs app
docker compose logs nginx

# 실시간 로그 모니터링
docker compose logs -f

# 시스템 로그
sudo journalctl -u docker.service
sudo journalctl -u magic-wardrobe.service
```

## CloudFront 최적화 설정

### Cache Behavior 세부 설정
- **Path Pattern**: `/static/*`
  - TTL: 1 year (정적 파일)
  - Cache Policy: Caching Optimized

- **Path Pattern**: `/api/*`  
  - TTL: 0 (동적 API)
  - Cache Policy: Caching Disabled

- **Path Pattern**: `*` (기본값)
  - TTL: 0 (HTML 페이지)
  - Cache Policy: Caching Disabled

### Origin Request Policy
- Headers: Host, X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Port
- Query Strings: All
- Cookies: All

## 보안 체크리스트

### EC2 보안
- [ ] SSH 키 기반 인증 (패스워드 인증 비활성화)
- [ ] 보안 그룹 최소 권한 설정
- [ ] 방화벽(UFW) 활성화
- [ ] 자동 보안 업데이트 설정

### 애플리케이션 보안  
- [ ] .env 파일 권한 600 설정
- [ ] 강력한 SESSION_SECRET 사용 (32자 이상)
- [ ] COOKIE_SECURE=true 설정
- [ ] Rate Limiting 동작 확인
- [ ] HTTPS Only 리디렉션 확인

### 운영 보안
- [ ] 정기 보안 업데이트 스케줄
- [ ] 로그 모니터링 및 알림 설정
- [ ] 백업 전략 수립
- [ ] 접근 로그 분석

## 성능 모니터링

### 주요 메트릭
```bash
# CPU 사용률
top

# 메모리 사용률  
free -h

# 디스크 사용률
df -h

# 네트워크 상태
netstat -i

# Docker 컨테이너 리소스
docker stats --no-stream
```

### 경고 임계값
- CPU 사용률: >80%
- 메모리 사용률: >85%  
- 디스크 사용률: >90%
- 응답 시간: >500ms