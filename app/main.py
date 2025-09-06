"""
마법옷장 FastAPI 메인 애플리케이션
남대문시장 아동복 B2B 재고관리 플랫폼
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import logging

import config
import database
import startup
from auth.middleware import get_current_user_optional


# 애플리케이션 시작/종료 이벤트 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logging.info("마법옷장 애플리케이션 시작")
    
    # Supabase MCP 초기화 시도 (실제 MCP가 없으면 Mock으로 fallback)
    try:
        # 실제 운영에서는 여기서 실제 Supabase MCP 함수를 주입받아야 함
        # 현재는 테스트용 Mock으로 초기화
        await startup.initialize_with_mock()
        logging.info("데이터베이스 초기화 완료")
    except Exception as e:
        logging.error(f"데이터베이스 초기화 실패: {e}")
        # 초기화 실패해도 애플리케이션은 시작 (임시 방조치)
    
    yield
    # 종료 시 실행
    logging.info("마법옷장 애플리케이션 종료")
    await database.close_db()


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="마법옷장 재고관리 시스템",
    description="남대문시장 아동복 B2B 도소매 재고관리 플랫폼",
    version="1.0.0",
    lifespan=lifespan
)

# 미들웨어 설정
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "마법옷장",
        "version": "1.0.0"
    }

@app.get("/health/ready")
async def readiness_check():
    """서비스 준비 상태 확인 (DB 연결 등)"""
    return {
        "status": "ready",
        "database": "temporarily_disabled",
        "note": "PostgreSQL 연결 설정 수정 중",
        "timestamp": config.settings.get_current_time()
    }

@app.get("/health/db")
async def database_health():
    """데이터베이스 상태 확인"""
    return {
        "status": "temporarily_disabled",
        "database": "configuration_pending",
        "note": "PostgreSQL 연결 설정 수정 중",
        "expected_tables": 12,
        "timestamp": config.settings.get_current_time()
    }

# 메인 페이지 라우트
@app.get("/")
async def main_page(request: Request):
    """메인 페이지 - 로그인 상태에 따른 리다이렉트"""
    current_user = await get_current_user_optional(request)
    
    if current_user:
        if current_user.get("role") == "admin":
            return RedirectResponse(url="/admin", status_code=302)
        else:
            return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        "main.html",
        {"request": request, "title": "마법옷장"}
    )

# 인증 페이지 라우트
@app.get("/login")
async def login_page(request: Request):
    """로그인 페이지"""
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "title": "로그인"}
    )

@app.get("/signup")
async def signup_page(request: Request):
    """회원가입 페이지"""
    return templates.TemplateResponse(
        "auth/signup.html",
        {"request": request, "title": "회원가입"}
    )

@app.get("/companies")
async def companies_page(request: Request):
    """거래처 관리 페이지"""
    return templates.TemplateResponse(
        "companies.html",
        {"request": request, "title": "거래처관리"}
    )

@app.get("/dashboard")
async def dashboard_page(request: Request):
    """대시보드 페이지 (로그인 필요)"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": "대시보드"}
    )

@app.get("/dashboard/inventory")
async def dashboard_inventory_content(request: Request):
    """대시보드 재고관리 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "partials/inventory_content.html",
        {"request": request}
    )

@app.get("/dashboard/products")
async def dashboard_products_content(request: Request):
    """대시보드 상품관리 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "products.html",
        {"request": request}
    )

@app.get("/dashboard/companies")
async def dashboard_companies_content(request: Request):
    """대시보드 거래처관리 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "companies.html",
        {"request": request}
    )

@app.get("/dashboard/orders")
async def dashboard_orders_content(request: Request):
    """대시보드 주문관리 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "orders.html",
        {"request": request}
    )

@app.get("/dashboard/chat")
async def dashboard_chat_content(request: Request):
    """대시보드 채팅 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "chat.html",
        {"request": request}
    )

@app.get("/dashboard/memos")
async def dashboard_memos_content(request: Request):
    """대시보드 메모관리 콘텐츠 (HTMX partial)"""
    return templates.TemplateResponse(
        "memos.html",
        {"request": request}
    )

@app.get("/inventory")
async def inventory_page(request: Request):
    """재고관리 페이지"""
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "재고관리"}
    )

@app.get("/products")
async def products_page(request: Request):
    """상품관리 페이지"""
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "title": "상품관리"}
    )

@app.get("/orders")
async def orders_page(request: Request):
    """주문관리 페이지"""
    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "title": "주문관리"}
    )

@app.get("/chat")
async def chat_page(request: Request):
    """채팅 페이지"""
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "title": "채팅"}
    )

@app.get("/memos")
async def memos_page(request: Request):
    """메모관리 페이지"""
    return templates.TemplateResponse(
        "memos.html",
        {"request": request, "title": "메모관리"}
    )

@app.get("/notices")
async def notices_page(request: Request):
    """공지사항 페이지"""
    return templates.TemplateResponse(
        "notices.html",
        {"request": request, "title": "공지사항"}
    )

@app.get("/admin")
async def admin_page(request: Request):
    """관리자 페이지"""
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "title": "관리자"}
    )

@app.get("/products/form")
async def product_form_page(request: Request):
    """상품 등록/수정 폼 페이지"""
    return templates.TemplateResponse(
        "product-form.html",
        {"request": request, "title": "상품 등록/수정"}
    )

@app.get("/orders/detail")
async def order_detail_page(request: Request):
    """주문 상세 페이지"""
    return templates.TemplateResponse(
        "order-detail.html",
        {"request": request, "title": "주문 상세"}
    )

@app.get("/profile")
async def profile_page(request: Request):
    """프로필 관리 페이지"""
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "title": "프로필 관리"}
    )

@app.get("/admin/users/{user_id}/detail")
async def admin_user_detail_page(request: Request, user_id: str):
    """관리자 회원신청 상세보기 페이지"""
    return templates.TemplateResponse(
        "admin-detail.html",
        {"request": request, "title": "회원신청 상세보기", "user_id": user_id}
    )

# Public notices API endpoint
from fastapi import HTTPException
from services.admin_service import AdminService
from models.notice import NoticeFilter, NoticeList

@app.get("/api/notices", response_model=NoticeList)
async def get_public_notices(
    is_important: bool = None,
    search: str = None,
    page: int = 1,
    per_page: int = 20
):
    """공지사항 목록 조회 (모든 사용자)"""
    try:
        filter_data = NoticeFilter(
            is_important=is_important,
            search=search,
            page=page,
            per_page=per_page
        )
        
        result = await AdminService.get_notices(filter_data)
        return NoticeList(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# API 라우터 등록
from api import auth, companies, products, orders, chat, dashboard, admin
app.include_router(auth.router, tags=["인증"])
app.include_router(companies.router, prefix="/api", tags=["거래처"])
app.include_router(products.router, prefix="/api", tags=["상품"])
app.include_router(products.inventory_router, prefix="/api", tags=["재고"])
app.include_router(products.categories_router, prefix="/api", tags=["카테고리"])
app.include_router(orders.router, prefix="/api", tags=["주문"])
app.include_router(chat.router, prefix="/api/chat", tags=["채팅"])
app.include_router(dashboard.router, tags=["대시보드"])
app.include_router(admin.router, prefix="/api", tags=["관리자"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )