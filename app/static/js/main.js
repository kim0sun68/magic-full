// 마법옷장 메인 JavaScript

// 전역 유틸리티 함수
window.MagicWardrobe = {
    // 토스트 알림 표시 (직접 DOM 조작)
    showToast: function(type, message) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toastId = 'toast_' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden transform transition-all duration-300 translate-x-full`;
        
        const iconColors = {
            success: 'text-green-400',
            error: 'text-red-400', 
            warning: 'text-yellow-400'
        };
        
        const iconPaths = {
            success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
            error: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z'
        };
        
        toast.innerHTML = `
            <div class="p-4">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 ${iconColors[type]}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${iconPaths[type]}" />
                        </svg>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="text-sm font-medium text-gray-900 break-words">${message}</p>
                    </div>
                    <div class="ml-4 flex-shrink-0 flex">
                        <button onclick="MagicWardrobe.removeToast('${toastId}')" class="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500">
                            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(toast);
        
        // 애니메이션 시작
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 10);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            this.removeToast(toastId);
        }, 5000);
    },
    
    // 토스트 제거
    removeToast: function(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.classList.add('translate-x-full');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
    },
    
    // 성공 토스트
    showSuccess: function(message) {
        this.showToast('success', message);
    },
    
    // 에러 토스트
    showError: function(message) {
        this.showToast('error', message);
    },
    
    // 경고 토스트
    showWarning: function(message) {
        this.showToast('warning', message);
    },
    
    // 확인 다이얼로그
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // 숫자 포맷팅 (한국 원화)
    formatCurrency: function(amount) {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW'
        }).format(amount);
    },
    
    // 날짜 포맷팅 (한국 시간)
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    },
    
    // 이미지 파일 유효성 검사
    validateImageFile: function(file, maxSizeMB = 5) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        
        if (!allowedTypes.includes(file.type)) {
            this.showError('지원하지 않는 이미지 형식입니다. (JPG, PNG, GIF, WebP만 가능)');
            return false;
        }
        
        if (file.size > maxSizeBytes) {
            this.showError(`파일 크기가 ${maxSizeMB}MB를 초과합니다.`);
            return false;
        }
        
        return true;
    },
    
    // 이미지 리사이징
    resizeImage: function(file, maxWidth = 800, maxHeight = 600, quality = 0.8) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = function() {
                // 비율 계산
                let { width, height } = img;
                
                if (width > height) {
                    if (width > maxWidth) {
                        height = (height * maxWidth) / width;
                        width = maxWidth;
                    }
                } else {
                    if (height > maxHeight) {
                        width = (width * maxHeight) / height;
                        height = maxHeight;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                
                // 이미지 그리기
                ctx.drawImage(img, 0, 0, width, height);
                
                // Blob 생성
                canvas.toBlob(resolve, file.type, quality);
            };
            
            img.src = URL.createObjectURL(file);
        });
    },
    
    // CSRF 토큰 가져오기
    getCSRFToken: function() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    },
    
    // 페이지 로딩 표시
    showLoading: function(element) {
        const spinner = '<div class="spinner"></div>';
        element.innerHTML = spinner;
    },
    
    // 모달 제어
    openModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.classList.add('overflow-hidden');
        }
    },
    
    closeModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }
    }
};

// Alpine.js 전역 데이터
document.addEventListener('alpine:init', () => {
    Alpine.data('fileUpload', () => ({
        files: [],
        uploading: false,
        
        handleFileSelect(event) {
            const fileList = Array.from(event.target.files);
            const validFiles = [];
            
            fileList.forEach(file => {
                if (MagicWardrobe.validateImageFile(file)) {
                    validFiles.push(file);
                }
            });
            
            this.files = validFiles;
        },
        
        async uploadFiles() {
            if (this.files.length === 0) return;
            
            this.uploading = true;
            
            try {
                for (const file of this.files) {
                    // 이미지 리사이징
                    const resizedFile = await MagicWardrobe.resizeImage(file);
                    
                    // 업로드 처리 (Wasabi 연동 시 구현)
                    console.log('파일 업로드 준비:', file.name);
                }
                
                MagicWardrobe.showSuccess('파일 업로드가 완료되었습니다.');
                this.files = [];
                
            } catch (error) {
                console.error('파일 업로드 오류:', error);
                MagicWardrobe.showError('파일 업로드 중 오류가 발생했습니다.');
            } finally {
                this.uploading = false;
            }
        }
    }));
    
    Alpine.data('search', () => ({
        query: '',
        results: [],
        loading: false,
        
        async search() {
            if (this.query.length < 2) {
                this.results = [];
                return;
            }
            
            this.loading = true;
            
            try {
                // 검색 API 호출 (추후 구현)
                console.log('검색 쿼리:', this.query);
                
            } catch (error) {
                console.error('검색 오류:', error);
                MagicWardrobe.showError('검색 중 오류가 발생했습니다.');
            } finally {
                this.loading = false;
            }
        }
    }));
});

// 토스트 이벤트 리스너
document.addEventListener('toast-success', function(event) {
    MagicWardrobe.showSuccess(event.detail);
});

document.addEventListener('toast-error', function(event) {
    MagicWardrobe.showError(event.detail);
});

document.addEventListener('toast-warning', function(event) {
    MagicWardrobe.showWarning(event.detail);
});

// HTMX 전역 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    // HTMX 요청 시작
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        // CSRF 토큰 자동 추가
        const csrfToken = MagicWardrobe.getCSRFToken();
        if (csrfToken) {
            event.detail.requestConfig.headers['X-CSRF-Token'] = csrfToken;
        }
    });
    
    // HTMX 성공 응답
    document.body.addEventListener('htmx:afterRequest', function(event) {
        if (event.detail.xhr.status === 200) {
            const response = event.detail.xhr.getResponseHeader('HX-Trigger');
            if (response) {
                try {
                    const triggers = JSON.parse(response);
                    if (triggers.showMessage) {
                        MagicWardrobe.showSuccess(triggers.showMessage);
                    }
                } catch (e) {
                    // 단순 문자열 트리거인 경우
                    if (response === 'reload') {
                        window.location.reload();
                    }
                }
            }
        }
    });
    
    // 폼 검증
    document.body.addEventListener('htmx:beforeRequest', function(event) {
        const form = event.target.closest('form');
        if (form && form.hasAttribute('data-validate')) {
            const isValid = validateForm(form);
            if (!isValid) {
                event.preventDefault();
            }
        }
    });
});

// 폼 검증 함수
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        const errorElement = input.parentElement.querySelector('.form-error');
        
        if (!input.value.trim()) {
            showFieldError(input, '필수 입력 항목입니다.');
            isValid = false;
        } else if (input.type === 'email' && !isValidEmail(input.value)) {
            showFieldError(input, '올바른 이메일 주소를 입력해주세요.');
            isValid = false;
        } else if (input.type === 'tel' && !isValidPhone(input.value)) {
            showFieldError(input, '올바른 전화번호를 입력해주세요.');
            isValid = false;
        } else {
            hideFieldError(input);
        }
    });
    
    return isValid;
}

// 필드별 에러 표시
function showFieldError(input, message) {
    input.classList.add('border-red-500');
    
    let errorElement = input.parentElement.querySelector('.form-error');
    if (!errorElement) {
        errorElement = document.createElement('p');
        errorElement.className = 'form-error';
        input.parentElement.appendChild(errorElement);
    }
    errorElement.textContent = message;
}

function hideFieldError(input) {
    input.classList.remove('border-red-500');
    const errorElement = input.parentElement.querySelector('.form-error');
    if (errorElement) {
        errorElement.remove();
    }
}

// 유효성 검사 헬퍼
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidPhone(phone) {
    const phoneRegex = /^[0-9-+\s()]+$/;
    return phoneRegex.test(phone) && phone.length >= 10;
}

// 페이지 로드 완료 로그
console.log('마법옷장 JavaScript 로드 완료');