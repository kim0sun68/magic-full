-- 마법옷장 Service Account 시스템 스키마
-- 제3자 서버에서 API 접근을 위한 서비스 계정 관리

-- Service Accounts 테이블
CREATE TABLE service_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,  -- 특정 회사와 연결 (선택사항)
    permissions TEXT[] DEFAULT '{}',  -- ["products:read", "orders:write", "inventory:read"]
    api_key VARCHAR(64) UNIQUE NOT NULL,  -- 공개 API 키 (32바이트 hex)
    secret_hash VARCHAR(255) NOT NULL,    -- 시크릿 해시 (bcrypt)
    token_expires_days INTEGER DEFAULT 30, -- JWT 토큰 만료 기간 (일)
    expires_at TIMESTAMP,                 -- 서비스 계정 만료일 (선택사항)
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,              -- 마지막 사용 시간
    request_count BIGINT DEFAULT 0,      -- 총 요청 횟수
    created_by UUID REFERENCES users(id), -- 생성한 관리자
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_service_accounts_api_key ON service_accounts(api_key);
CREATE INDEX idx_service_accounts_company_id ON service_accounts(company_id);
CREATE INDEX idx_service_accounts_is_active ON service_accounts(is_active);
CREATE INDEX idx_service_accounts_created_by ON service_accounts(created_by);

-- API 사용 로그 테이블 (선택적 상세 로깅)
CREATE TABLE api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_account_id UUID REFERENCES service_accounts(id) ON DELETE CASCADE,
    endpoint VARCHAR(200) NOT NULL,      -- /api/products, /api/orders 등
    method VARCHAR(10) NOT NULL,         -- GET, POST, PUT, DELETE
    status_code INTEGER NOT NULL,        -- 200, 401, 404 등
    response_time_ms INTEGER,            -- 응답 시간 (밀리초)
    ip_address INET,                     -- 요청 IP 주소
    user_agent TEXT,                     -- User-Agent 헤더
    request_size_bytes INTEGER,          -- 요청 크기
    response_size_bytes INTEGER,         -- 응답 크기
    error_message TEXT,                  -- 에러 발생 시 메시지
    created_at TIMESTAMP DEFAULT NOW()
);

-- 로그 테이블 인덱스
CREATE INDEX idx_api_usage_logs_service_account ON api_usage_logs(service_account_id);
CREATE INDEX idx_api_usage_logs_created_at ON api_usage_logs(created_at);
CREATE INDEX idx_api_usage_logs_endpoint ON api_usage_logs(endpoint);
CREATE INDEX idx_api_usage_logs_status_code ON api_usage_logs(status_code);

-- API 사용량 집계 테이블 (성능 최적화용)
CREATE TABLE api_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_account_id UUID REFERENCES service_accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,                  -- 집계 날짜
    endpoint VARCHAR(200) NOT NULL,      -- API 엔드포인트
    request_count INTEGER DEFAULT 0,     -- 요청 횟수
    success_count INTEGER DEFAULT 0,     -- 성공 요청 (2xx)
    error_count INTEGER DEFAULT 0,       -- 에러 요청 (4xx, 5xx)
    avg_response_time_ms FLOAT,         -- 평균 응답 시간
    total_request_size_bytes BIGINT DEFAULT 0,
    total_response_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(service_account_id, date, endpoint)
);

-- 집계 테이블 인덱스
CREATE INDEX idx_api_usage_stats_service_account ON api_usage_stats(service_account_id);
CREATE INDEX idx_api_usage_stats_date ON api_usage_stats(date);

-- Service Account 권한 체크를 위한 함수
CREATE OR REPLACE FUNCTION check_service_account_permission(
    account_id UUID,
    required_permission TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    account_permissions TEXT[];
BEGIN
    SELECT permissions INTO account_permissions 
    FROM service_accounts 
    WHERE id = account_id AND is_active = true;
    
    IF account_permissions IS NULL THEN
        RETURN FALSE;
    END IF;
    
    RETURN required_permission = ANY(account_permissions);
END;
$$ LANGUAGE plpgsql;

-- 서비스 계정 토큰 정보 조회 뷰
CREATE VIEW service_account_info AS
SELECT 
    sa.id,
    sa.name,
    sa.description,
    sa.company_id,
    c.name as company_name,
    sa.permissions,
    sa.api_key,
    sa.token_expires_days,
    sa.expires_at,
    sa.is_active,
    sa.last_used_at,
    sa.request_count,
    sa.created_at,
    u.name as created_by_name
FROM service_accounts sa
LEFT JOIN companies c ON sa.company_id = c.id
LEFT JOIN users u ON sa.created_by = u.id;

-- 기본 권한 상수들 (참조용 주석)
/*
사용 가능한 권한 목록:
- "products:read"      : 상품 조회
- "products:write"     : 상품 생성/수정/삭제
- "inventory:read"     : 재고 조회
- "inventory:write"    : 재고 조정/입출고
- "orders:read"        : 주문 조회
- "orders:write"       : 주문 생성/수정/상태변경
- "companies:read"     : 거래처 조회
- "users:read"         : 사용자 정보 조회 (제한적)
- "analytics:read"     : 통계 데이터 조회
- "admin:read"         : 관리자 데이터 조회
- "admin:write"        : 관리자 기능 수행
*/

-- 샘플 Service Account 데이터 (개발용)
INSERT INTO service_accounts (
    name,
    description,
    company_id,
    permissions,
    api_key,
    secret_hash,
    created_by
) VALUES (
    'ERP 시스템 연동',
    'ABC 도매업체 ERP 시스템에서 재고 동기화용',
    (SELECT id FROM companies WHERE name = 'ABC 도매업체' LIMIT 1),
    ARRAY['products:read', 'inventory:read', 'inventory:write'],
    'mk_' || encode(gen_random_bytes(16), 'hex'),  -- mk_로 시작하는 32글자 API 키
    '$2b$12$hash_for_secret_key',  -- 실제로는 bcrypt 해시
    (SELECT id FROM users WHERE role = 'admin' LIMIT 1)
) ON CONFLICT DO NOTHING;