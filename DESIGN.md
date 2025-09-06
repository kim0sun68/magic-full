# 마법옷장 디자인 문서

### 디자인 가이드라인
- 반응형 완벽 지원 (puppeteer MCP 로 반응형 디자인도 문제가 없는지 확인)
- https://tx.shadcn.com/ 스타일로 전체 웹페이지에 일관된 디자인 적용

## XML 디자인 파일 개요

- 마법옷장 서비스의 모든 페이지 구조를 XML 형식으로 정의합니다. 
- 각 XML 파일은 페이지의 구조와 요소를 명확하게 표현하여 구현 시 참조할 수 있도록 합니다.

## XML 파일 목록

### 1. 공통 컴포넌트
- **@header.xml**: 마법옷장 브랜딩 헤더, 네비게이션 메뉴
- **@footer.xml**: 공통 푸터

### 2. 인증 및 메인 페이지
- **@login.xml**: 로그인 페이지 (/login)
- **@signup.xml**: 회원가입 및 거래처 등록 (/signup)
- **@main.xml**: 랜딩 페이지 (/)
- **@dashboard.xml**: 로그인 후 대시보드 (/dashboard)

### 3. 핵심 기능 페이지
- **@inventory.xml**: 재고관리 목록 페이지 (/inventory)
- **@products.xml**: 상품관리 목록 페이지 (/products)  
- **@orders.xml**: 주문관리 목록 페이지 (/orders)
- **@companies.xml**: 거래처관리 페이지 (/companies)
- **@chat.xml**: 실시간 채팅 페이지 (/chat)

### 4. 상세 및 폼 페이지
- **@product-form.xml**: 상품 등록/수정 폼 (/products/form)
- **@order-detail.xml**: 주문 상세 페이지 (/orders/detail)
- **@profile.xml**: 사용자 프로필 관리 (/profile)

### 5. 커뮤니케이션 페이지
- **@memos.xml**: 메모 관리 페이지 (/memos)
- **@notices.xml**: 공지사항 페이지 (/notices)

### 6. 관리자 페이지
- **@admin.xml**: 관리자 전용 페이지 (/admin)
- **@admin-detail.xml**: 회원신청 상세보기 페이지 (/admin/users/{id}/detail)

