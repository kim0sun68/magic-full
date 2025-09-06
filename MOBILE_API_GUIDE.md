# 마법옷장 모바일 앱 API 접근 가이드

## 개요
마법옷장 B2B 재고관리 플랫폼의 REST API를 모바일 애플리케이션에서 접근하기 위한 완전한 가이드입니다.

## 현재 API 상태 및 모바일 호환성

### ✅ 모바일 친화적 요소
- **Bearer 토큰 지원**: Authorization 헤더로 JWT 토큰 인증 가능
- **RESTful API**: 47개 표준 REST 엔드포인트 제공
- **JSON 응답**: 모든 API가 JSON 형식으로 데이터 반환
- **Pydantic 검증**: 엄격한 입력/출력 데이터 검증

### ⚠️ 현재 제약사항
- **CORS 제한**: localhost만 허용 (모바일 앱 접근 불가)
- **도메인 제한**: 로컬 개발 환경만 구성됨

## 서버 설정 변경사항

### 1. CORS 설정 수정 (`app/config.py`)
```python
# 현재 설정 (로컬만)
CORS_ORIGINS: List[str] = ["http://localhost", "http://127.0.0.1"]

# 모바일 지원을 위한 권장 설정
CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://127.0.0.1", 
    "https://your-domain.com",          # 프로덕션 도메인
    "https://your-api-domain.com",      # API 전용 도메인
    "*"  # 개발 환경에서만 사용, 프로덕션에서는 구체적 도메인 지정
]
```

### 2. 모바일 전용 API 도메인 설정
```python
# 모바일 전용 설정 추가
MOBILE_API_ORIGINS: List[str] = [
    "capacitor://localhost",     # Ionic Capacitor
    "ionic://localhost",         # Ionic 구버전
    "file://",                   # Cordova/PhoneGap
    "https://localhost"          # React Native
]

# CORS 미들웨어에 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + settings.MOBILE_API_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 모바일 앱 인증 플로우

### JWT Bearer 토큰 방식 (권장)
```javascript
// 1. 로그인 요청
const response = await fetch('https://api.magic-wardrobe.com/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});

const data = await response.json();
// 응답: { access_token: "eyJ...", refresh_token: "eyJ...", user: {...} }

// 2. 토큰 저장 (플랫폼별)
// React Native: AsyncStorage
await AsyncStorage.setItem('access_token', data.access_token);
await AsyncStorage.setItem('refresh_token', data.refresh_token);

// Flutter: SharedPreferences
SharedPreferences prefs = await SharedPreferences.getInstance();
await prefs.setString('access_token', data.accessToken);

// 3. API 요청 시 토큰 사용
const apiResponse = await fetch('https://api.magic-wardrobe.com/api/products', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  }
});
```

### 토큰 갱신 처리
```javascript
// 토큰 갱신 함수
async function refreshToken() {
  const refreshToken = await AsyncStorage.getItem('refresh_token');
  
  const response = await fetch('https://api.magic-wardrobe.com/api/auth/refresh', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${refreshToken}`,
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const data = await response.json();
    await AsyncStorage.setItem('access_token', data.access_token);
    return data.access_token;
  }
  
  // 갱신 실패 시 로그아웃 처리
  await logout();
}

// 401 에러 시 자동 갱신
async function apiRequest(url, options = {}) {
  let accessToken = await AsyncStorage.getItem('access_token');
  
  let response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      ...options.headers
    }
  });
  
  if (response.status === 401) {
    // 토큰 갱신 시도
    accessToken = await refreshToken();
    if (accessToken) {
      // 재시도
      response = await fetch(url, {
        ...options,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          ...options.headers
        }
      });
    }
  }
  
  return response;
}
```

## 플랫폼별 구현 예제

### React Native
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

class MagicWardrobeAPI {
  constructor() {
    this.baseURL = 'https://api.magic-wardrobe.com';
  }
  
  async login(email, password) {
    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      await AsyncStorage.multiSet([
        ['access_token', data.access_token],
        ['refresh_token', data.refresh_token],
        ['user', JSON.stringify(data.user)]
      ]);
      return data;
    }
    
    throw new Error('로그인 실패');
  }
  
  async getProducts(filters = {}) {
    return this.apiRequest('/api/products', {
      method: 'GET',
      params: filters
    });
  }
  
  async createOrder(orderData) {
    return this.apiRequest('/api/orders', {
      method: 'POST',
      body: JSON.stringify(orderData)
    });
  }
}
```

### Flutter (Dart)
```dart
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class MagicWardrobeAPI {
  static const String baseURL = 'https://api.magic-wardrobe.com';
  
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseURL/api/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email, 'password': password}),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final prefs = await SharedPreferences.getInstance();
      
      await prefs.setString('access_token', data['access_token']);
      await prefs.setString('refresh_token', data['refresh_token']);
      await prefs.setString('user', json.encode(data['user']));
      
      return data;
    }
    
    throw Exception('로그인 실패');
  }
  
  Future<Map<String, dynamic>> getProducts([Map<String, dynamic>? filters]) async {
    final prefs = await SharedPreferences.getInstance();
    final accessToken = prefs.getString('access_token');
    
    final response = await http.get(
      Uri.parse('$baseURL/api/products'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
    );
    
    return json.decode(response.body);
  }
}
```

### iOS Swift
```swift
import Foundation

class MagicWardrobeAPI {
    static let baseURL = "https://api.magic-wardrobe.com"
    
    func login(email: String, password: String) async throws -> LoginResponse {
        let url = URL(string: "\(Self.baseURL)/api/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let loginData = ["email": email, "password": password]
        request.httpBody = try JSONSerialization.data(withJSONObject: loginData)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
            let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
            
            // 토큰 저장
            UserDefaults.standard.set(loginResponse.accessToken, forKey: "access_token")
            UserDefaults.standard.set(loginResponse.refreshToken, forKey: "refresh_token")
            
            return loginResponse
        }
        
        throw APIError.loginFailed
    }
    
    func getProducts(filters: [String: Any]? = nil) async throws -> ProductListResponse {
        guard let accessToken = UserDefaults.standard.string(forKey: "access_token") else {
            throw APIError.unauthorized
        }
        
        let url = URL(string: "\(Self.baseURL)/api/products")!
        var request = URLRequest(url: url)
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(ProductListResponse.self, from: data)
    }
}
```

### Android Kotlin
```kotlin
import okhttp3.*
import kotlinx.coroutines.*
import gson.Gson

class MagicWardrobeAPI {
    companion object {
        const val BASE_URL = "https://api.magic-wardrobe.com"
    }
    
    private val client = OkHttpClient()
    private val gson = Gson()
    
    suspend fun login(email: String, password: String): LoginResponse {
        val loginData = mapOf("email" to email, "password" to password)
        val json = gson.toJson(loginData)
        
        val requestBody = RequestBody.create(
            MediaType.parse("application/json"), 
            json
        )
        
        val request = Request.Builder()
            .url("$BASE_URL/api/auth/login")
            .post(requestBody)
            .build()
        
        val response = client.newCall(request).execute()
        
        if (response.isSuccessful) {
            val responseData = gson.fromJson(response.body()?.string(), LoginResponse::class.java)
            
            // SharedPreferences에 토큰 저장
            val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
            prefs.edit()
                .putString("access_token", responseData.accessToken)
                .putString("refresh_token", responseData.refreshToken)
                .apply()
            
            return responseData
        }
        
        throw Exception("로그인 실패")
    }
    
    suspend fun getProducts(filters: Map<String, Any>? = null): ProductListResponse {
        val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
        val accessToken = prefs.getString("access_token", null)
            ?: throw Exception("인증 토큰 없음")
        
        val request = Request.Builder()
            .url("$BASE_URL/api/products")
            .header("Authorization", "Bearer $accessToken")
            .build()
        
        val response = client.newCall(request).execute()
        return gson.fromJson(response.body()?.string(), ProductListResponse::class.java)
    }
}
```

## 주요 API 엔드포인트 (모바일용)

### 인증 API
```
POST /api/auth/login          # 로그인
POST /api/auth/refresh        # 토큰 갱신
POST /api/auth/logout         # 로그아웃
GET  /api/auth/me            # 현재 사용자 정보
```

### 상품 관리 API
```
GET    /api/products         # 상품 목록 (검색/필터링 지원)
POST   /api/products         # 상품 등록 (도매업체만)
PUT    /api/products/{id}    # 상품 수정 (도매업체만)
DELETE /api/products/{id}    # 상품 삭제 (도매업체만)
GET    /api/categories       # 카테고리 목록
```

### 주문 관리 API
```
GET    /api/orders           # 주문 목록 조회
POST   /api/orders           # 주문 생성 (소매업체)
PUT    /api/orders/{id}/status # 주문 상태 변경 (도매업체)
GET    /api/orders/{id}      # 주문 상세 조회
```

### 재고 관리 API
```
GET    /api/inventory        # 재고 현황 조회
POST   /api/inventory/adjustment # 재고 조정
GET    /api/inventory/transactions # 재고 거래내역
POST   /api/inventory/stock-in # 입고 등록
```

### 거래처 관리 API
```
GET    /api/companies        # 거래처 목록
POST   /api/companies/relationships # 거래 관계 신청
PUT    /api/companies/relationships/{id} # 관계 승인/거부
```

## 권한별 API 접근 매트릭스

### 관리자 (Admin)
- ✅ 모든 API 접근 가능
- ✅ 사용자 승인/관리: `/api/admin/*`
- ✅ 공지사항 관리: `/api/admin/notices/*`
- ✅ 시스템 통계: `/api/dashboard/stats`

### 도매업체 (Wholesale)
- ✅ 상품 등록/수정/삭제
- ✅ 재고 관리 (입고, 출고, 조정)
- ✅ 주문 접수 및 상태 변경
- ✅ 거래처 관계 승인/거부
- ❌ 관리자 기능 접근 불가

### 소매업체 (Retail)  
- ✅ 상품 조회 (거래 관계 업체만)
- ✅ 주문 생성 및 조회
- ✅ 거래처 관계 신청
- ❌ 상품 등록/수정 불가
- ❌ 재고 직접 조정 불가

## 에러 처리 및 상태 코드

### 인증 관련 에러
```json
// 401 Unauthorized - 토큰 없음/만료
{
  "detail": "인증이 필요합니다"
}

// 403 Forbidden - 권한 부족
{
  "detail": "관리자 권한이 필요합니다"
}

// 422 Validation Error - 잘못된 데이터
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 비즈니스 로직 에러
```json
// 404 Not Found - 리소스 없음
{
  "detail": "상품을 찾을 수 없습니다"
}

// 409 Conflict - 중복 데이터
{
  "detail": "이미 존재하는 상품 코드입니다"
}

// 400 Bad Request - 비즈니스 규칙 위반
{
  "detail": "소매가격은 도매가격보다 높아야 합니다"
}
```

## 실시간 기능 모바일 지원

### WebSocket 채팅
```javascript
// WebSocket 연결
const ws = new WebSocket(`wss://api.magic-wardrobe.com/ws/chat/${roomId}?token=${accessToken}`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  // 메시지 처리 로직
};

// 메시지 전송
ws.send(JSON.stringify({
  type: 'message',
  content: '메시지 내용',
  room_id: roomId
}));
```

### Server-Sent Events (SSE) 알림
```javascript
// SSE 연결 (모바일 브라우저/WebView)
const eventSource = new EventSource(
  `https://api.magic-wardrobe.com/api/chat/sse?token=${accessToken}`
);

eventSource.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  // 푸시 알림 처리
};
```

## 이미지 업로드 시스템 (Wasabi Cloud)

### Presigned URL 방식 이미지 업로드 (권장)

마법옷장에서는 Wasabi Cloud를 사용하여 이미지를 저장합니다. 모바일 앱에서는 다음 2단계 프로세스를 통해 이미지를 업로드할 수 있습니다:

#### 1단계: Presigned URL 요청
```javascript
// Presigned URL 생성 요청
const getPresignedUrl = async (fileName, fileType) => {
  const response = await fetch(`${baseURL}/api/products/upload/presigned`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: fileName,
      content_type: fileType,
      expires_in: 3600  // 1시간 유효
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    return {
      presignedUrl: data.presigned_url,
      imageUrl: data.image_url,  // 업로드 완료 후 사용할 URL
      uploadId: data.upload_id   // 추적용 ID
    };
  }
  
  throw new Error('Presigned URL 생성 실패');
};
```

#### 2단계: Wasabi Cloud 직접 업로드
```javascript
// Wasabi에 직접 업로드
const uploadToWasabi = async (presignedUrl, imageFile) => {
  const formData = new FormData();
  formData.append('file', imageFile);
  
  const response = await fetch(presignedUrl, {
    method: 'PUT',
    body: imageFile,  // 직접 파일 데이터
    headers: {
      'Content-Type': imageFile.type,
    }
  });
  
  if (!response.ok) {
    throw new Error('이미지 업로드 실패');
  }
  
  return response;
};
```

#### 3단계: 상품에 이미지 연결
```javascript
// 업로드된 이미지를 상품에 연결
const attachImageToProduct = async (productId, imageUrl, isPrimary = false) => {
  const response = await fetch(`${baseURL}/api/products/${productId}/images`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      product_id: productId,
      images: [{
        url: imageUrl,
        is_primary: isPrimary,
        alt_text: "상품 이미지"
      }]
    })
  });
  
  return response.json();
};
```

### 완전한 이미지 업로드 플로우

#### React Native 예제
```javascript
import { launchImageLibrary } from 'react-native-image-picker';

class ImageUploadService {
  async uploadProductImage(productId, isPrimary = false) {
    try {
      // 1. 이미지 선택
      const imageResult = await this.selectImage();
      if (!imageResult) return null;
      
      // 2. Presigned URL 요청
      const { presignedUrl, imageUrl } = await getPresignedUrl(
        imageResult.fileName,
        imageResult.type
      );
      
      // 3. 이미지 리사이징 (옵션)
      const resizedImage = await this.resizeImage(imageResult.uri, 800, 800);
      
      // 4. Wasabi 업로드
      await uploadToWasabi(presignedUrl, resizedImage);
      
      // 5. 상품에 이미지 연결
      const result = await attachImageToProduct(productId, imageUrl, isPrimary);
      
      return result;
      
    } catch (error) {
      console.error('이미지 업로드 실패:', error);
      throw error;
    }
  }
  
  selectImage() {
    return new Promise((resolve) => {
      launchImageLibrary({
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 1024,
        maxHeight: 1024,
      }, (response) => {
        if (response.assets && response.assets[0]) {
          resolve({
            uri: response.assets[0].uri,
            fileName: response.assets[0].fileName,
            type: response.assets[0].type,
            size: response.assets[0].fileSize
          });
        } else {
          resolve(null);
        }
      });
    });
  }
  
  async resizeImage(imageUri, maxWidth, maxHeight) {
    // react-native-image-resizer 사용
    const resized = await ImageResizer.createResizedImage(
      imageUri,
      maxWidth,
      maxHeight,
      'JPEG',
      80,  // 품질
      0,   // 회전
      null, // 출력 경로
      false, // keepMeta
      { mode: 'contain', onlyScaleDown: true }
    );
    
    return {
      uri: resized.uri,
      type: 'image/jpeg',
      name: 'resized_image.jpg'
    };
  }
}
```

#### Flutter 예제
```dart
import 'package:image_picker/image_picker.dart';
import 'package:image/image.dart' as img;
import 'package:http/http.dart' as http;

class ImageUploadService {
  Future<Map<String, dynamic>?> uploadProductImage(String productId, {bool isPrimary = false}) async {
    try {
      // 1. 이미지 선택
      final ImagePicker picker = ImagePicker();
      final XFile? imageFile = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      
      if (imageFile == null) return null;
      
      // 2. 이미지 리사이징
      final resizedImage = await resizeImage(imageFile.path);
      
      // 3. Presigned URL 요청
      final presignedData = await getPresignedUrl(
        imageFile.name,
        'image/jpeg'
      );
      
      // 4. Wasabi 업로드
      await uploadToWasabi(presignedData['presigned_url'], resizedImage);
      
      // 5. 상품에 이미지 연결
      final result = await attachImageToProduct(
        productId,
        presignedData['image_url'],
        isPrimary
      );
      
      return result;
      
    } catch (e) {
      print('이미지 업로드 실패: $e');
      rethrow;
    }
  }
  
  Future<List<int>> resizeImage(String imagePath, {int maxWidth = 800}) async {
    final bytes = await File(imagePath).readAsBytes();
    final image = img.decodeImage(bytes);
    
    if (image == null) throw Exception('이미지 디코딩 실패');
    
    final resized = img.copyResize(image, width: maxWidth);
    return img.encodeJpg(resized, quality: 80);
  }
  
  Future<void> uploadToWasabi(String presignedUrl, List<int> imageBytes) async {
    final response = await http.put(
      Uri.parse(presignedUrl),
      body: imageBytes,
      headers: {'Content-Type': 'image/jpeg'},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Wasabi 업로드 실패: ${response.statusCode}');
    }
  }
}
```

#### iOS Swift 예제
```swift
import UIKit

class ImageUploadService {
    func uploadProductImage(productId: String, isPrimary: Bool = false) async throws -> [String: Any] {
        // 1. 이미지 선택 (UIImagePickerController 사용)
        let image = try await selectImage()
        
        // 2. 이미지 리사이징
        let resizedImageData = resizeImage(image, maxWidth: 800)
        let fileName = "product_\(productId)_\(Date().timeIntervalSince1970).jpg"
        
        // 3. Presigned URL 요청
        let presignedData = try await getPresignedUrl(fileName: fileName, contentType: "image/jpeg")
        
        // 4. Wasabi 업로드
        try await uploadToWasabi(
            presignedUrl: presignedData["presigned_url"] as! String,
            imageData: resizedImageData
        )
        
        // 5. 상품에 이미지 연결
        return try await attachImageToProduct(
            productId: productId,
            imageUrl: presignedData["image_url"] as! String,
            isPrimary: isPrimary
        )
    }
    
    private func resizeImage(_ image: UIImage, maxWidth: CGFloat) -> Data {
        let ratio = min(maxWidth / image.size.width, maxWidth / image.size.height)
        let newSize = CGSize(width: image.size.width * ratio, height: image.size.height * ratio)
        
        UIGraphicsBeginImageContextWithOptions(newSize, false, 0.0)
        image.draw(in: CGRect(origin: .zero, size: newSize))
        let resizedImage = UIGraphicsGetImageFromCurrentImageContext()!
        UIGraphicsEndImageContext()
        
        return resizedImage.jpegData(compressionQuality: 0.8)!
    }
    
    private func uploadToWasabi(presignedUrl: String, imageData: Data) async throws {
        var request = URLRequest(url: URL(string: presignedUrl)!)
        request.httpMethod = "PUT"
        request.setValue("image/jpeg", forHTTPHeaderField: "Content-Type")
        request.httpBody = imageData
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 200 {
            throw URLError(.badServerResponse)
        }
    }
}
```

#### Android Kotlin 예제
```kotlin
import okhttp3.*
import java.io.File

class ImageUploadService {
    suspend fun uploadProductImage(productId: String, isPrimary: Boolean = false): Map<String, Any> {
        // 1. 이미지 선택 (Intent.ACTION_PICK 사용)
        val imageFile = selectImageFromGallery()
        
        // 2. 이미지 리사이징
        val resizedImageFile = resizeImage(imageFile, 800)
        val fileName = "product_${productId}_${System.currentTimeMillis()}.jpg"
        
        // 3. Presigned URL 요청
        val presignedData = getPresignedUrl(fileName, "image/jpeg")
        
        // 4. Wasabi 업로드
        uploadToWasabi(
            presignedUrl = presignedData["presigned_url"] as String,
            imageFile = resizedImageFile
        )
        
        // 5. 상품에 이미지 연결
        return attachImageToProduct(
            productId = productId,
            imageUrl = presignedData["image_url"] as String,
            isPrimary = isPrimary
        )
    }
    
    private fun resizeImage(imageFile: File, maxWidth: Int): File {
        val bitmap = BitmapFactory.decodeFile(imageFile.absolutePath)
        val ratio = minOf(maxWidth.toFloat() / bitmap.width, maxWidth.toFloat() / bitmap.height)
        val newWidth = (bitmap.width * ratio).toInt()
        val newHeight = (bitmap.height * ratio).toInt()
        
        val resizedBitmap = Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
        
        val outputFile = File(context.cacheDir, "resized_${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(outputFile)
        resizedBitmap.compress(Bitmap.CompressFormat.JPEG, 80, outputStream)
        outputStream.close()
        
        return outputFile
    }
    
    private suspend fun uploadToWasabi(presignedUrl: String, imageFile: File) {
        val requestBody = RequestBody.create(MediaType.parse("image/jpeg"), imageFile)
        val request = Request.Builder()
            .url(presignedUrl)
            .put(requestBody)
            .build()
        
        val response = client.newCall(request).execute()
        if (!response.isSuccessful) {
            throw Exception("Wasabi 업로드 실패: ${response.code()}")
        }
    }
}
```

### 이미지 업로드 API 엔드포인트

#### 1. Presigned URL 생성
```http
POST /api/products/upload/presigned
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "filename": "product_image.jpg",
  "content_type": "image/jpeg",
  "expires_in": 3600
}
```

**응답**:
```json
{
  "presigned_url": "https://s3.ap-northeast-1.wasabisys.com/magic-storage/products/uuid/image.jpg?X-Amz-Algorithm=...",
  "image_url": "https://s3.ap-northeast-1.wasabisys.com/magic-storage/products/uuid/image.jpg",
  "upload_id": "temp_upload_123",
  "expires_at": "2025-09-03T11:00:00Z"
}
```

#### 2. 상품에 이미지 연결
```http
POST /api/products/{product_id}/images
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "product_id": "product-uuid",
  "images": [
    {
      "url": "https://s3.ap-northeast-1.wasabisys.com/magic-storage/products/uuid/image.jpg",
      "is_primary": true,
      "alt_text": "상품 메인 이미지"
    }
  ]
}
```

### 배치 업로드 (여러 이미지)
```javascript
const uploadMultipleImages = async (productId, imageFiles) => {
  const uploadPromises = imageFiles.map(async (imageFile, index) => {
    // 1. Presigned URL 요청
    const { presignedUrl, imageUrl } = await getPresignedUrl(
      `${productId}_${index}_${imageFile.name}`,
      imageFile.type
    );
    
    // 2. Wasabi 업로드
    await uploadToWasabi(presignedUrl, imageFile);
    
    return {
      url: imageUrl,
      is_primary: index === 0,  // 첫 번째 이미지를 메인으로
      alt_text: `상품 이미지 ${index + 1}`
    };
  });
  
  // 모든 업로드 완료 대기
  const uploadedImages = await Promise.all(uploadPromises);
  
  // 상품에 이미지 배치 연결
  return await fetch(`${baseURL}/api/products/${productId}/images`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      product_id: productId,
      images: uploadedImages
    })
  });
};
```

### 이미지 최적화 및 검증

#### 클라이언트 측 이미지 처리
```javascript
// 이미지 유효성 검사
const validateImage = (file) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  const maxSizeBytes = 5 * 1024 * 1024; // 5MB
  
  if (!allowedTypes.includes(file.type)) {
    throw new Error('지원하지 않는 이미지 형식입니다.');
  }
  
  if (file.size > maxSizeBytes) {
    throw new Error('이미지 크기는 5MB 이하여야 합니다.');
  }
  
  return true;
};

// Canvas를 이용한 이미지 리사이징
const resizeImageOnClient = (file, maxWidth = 800, quality = 0.8) => {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      const ratio = Math.min(maxWidth / img.width, maxWidth / img.height);
      canvas.width = img.width * ratio;
      canvas.height = img.height * ratio;
      
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      
      canvas.toBlob(resolve, 'image/jpeg', quality);
    };
    
    img.src = URL.createObjectURL(file);
  });
};
```

### 에러 처리 및 재시도 로직
```javascript
const uploadWithRetry = async (presignedUrl, imageFile, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await uploadToWasabi(presignedUrl, imageFile);
      return; // 성공 시 종료
    } catch (error) {
      if (i === maxRetries - 1) {
        throw error; // 마지막 시도에서 실패 시 에러 발생
      }
      
      // 재시도 전 대기 (exponential backoff)
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
};

// 업로드 진행률 추적
const uploadWithProgress = async (presignedUrl, imageFile, onProgress) => {
  const xhr = new XMLHttpRequest();
  
  return new Promise((resolve, reject) => {
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        const progress = (event.loaded / event.total) * 100;
        onProgress(Math.round(progress));
      }
    });
    
    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve();
      } else {
        reject(new Error(`업로드 실패: ${xhr.status}`));
      }
    });
    
    xhr.addEventListener('error', () => reject(new Error('네트워크 오류')));
    
    xhr.open('PUT', presignedUrl);
    xhr.setRequestHeader('Content-Type', imageFile.type);
    xhr.send(imageFile);
  });
};
```

### Wasabi Cloud 설정

#### 환경 설정
```bash
# .env 파일 필수 설정
WASABI_ACCESS_KEY=5D6425175YDKHM09FV00
WASABI_SECRET_KEY=sLqqQXbUH7tpVeVttgphlT930lo7LkhIOgRJzqbu
WASABI_BUCKET=magic-storage
WASABI_ENDPOINT=https://s3.ap-northeast-1.wasabisys.com
WASABI_REGION=ap-northeast-1
```

#### 버킷 정책 설정 (Wasabi 콘솔)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::magic-storage/products/*"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::USER-ID:user/magic-wardrobe-user"
      },
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::magic-storage/products/*"
    }
  ]
}
```

### 이미지 URL 형식
```
업로드된 이미지 URL 패턴:
https://s3.ap-northeast-1.wasabisys.com/magic-storage/products/{product_id}/{timestamp}_{filename}

예시:
https://s3.ap-northeast-1.wasabisys.com/magic-storage/products/abc123-def456/1693737600_main_image.jpg
```

### 모바일 앱 보안 고려사항
- **Presigned URL**: 1시간 제한으로 보안 유지
- **파일 크기 제한**: 클라이언트에서 5MB 이하로 제한
- **이미지 형식 제한**: JPEG, PNG, GIF, WebP만 허용
- **업로드 권한**: 도매업체만 자사 상품 이미지 업로드 가능
- **이미지 최적화**: 모바일에서 업로드 전 리사이징 권장

### ⚠️ 현재 구현 상태 참고

현재 마법옷장 시스템에서 **Wasabi Cloud 이미지 업로드는 부분적으로만 구현**되어 있습니다:

#### ✅ 구현된 부분
- Wasabi 설정 및 환경변수 (config.py)
- 이미지 관련 Pydantic 모델 (ProductImage, ProductImageUpload)
- 클라이언트 측 이미지 검증 및 리사이징 (main.js)
- 상품에 이미지 URL 저장 로직 (ProductService.upload_product_images)

#### ❌ 추가 구현 필요
- Presigned URL 생성 API (`POST /api/products/upload/presigned`)
- Wasabi S3 클라이언트 연동 서비스
- boto3 라이브러리 의존성 추가
- 실제 Wasabi Cloud 업로드 로직

**모바일 앱 개발 전 서버 측 이미지 업로드 시스템을 완성해야 합니다.**

## 보안 고려사항

### 토큰 저장 보안
```javascript
// ✅ 안전한 저장소 사용
// React Native
import * as Keychain from 'react-native-keychain';
await Keychain.setInternetCredentials('magic-wardrobe', 'access_token', accessToken);

// Flutter  
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
const storage = FlutterSecureStorage();
await storage.write(key: 'access_token', value: accessToken);

// ❌ 안전하지 않은 저장 (일반 storage)
localStorage.setItem('access_token', token); // 브라우저만
```

### HTTPS 인증서 검증
```javascript
// 프로덕션 환경에서는 HTTPS 필수
const API_URL = __DEV__ 
  ? 'http://localhost:8000'          // 개발 환경
  : 'https://api.magic-wardrobe.com'; // 프로덕션
```

## 성능 최적화

### 페이지네이션 처리
```javascript
// 상품 목록 페이지네이션
const getProducts = async (page = 1, size = 20, filters = {}) => {
  const params = new URLSearchParams({
    page: page.toString(),
    size: size.toString(),
    ...filters
  });
  
  return apiRequest(`/api/products?${params}`);
};

// 무한 스크롤 구현
const [products, setProducts] = useState([]);
const [page, setPage] = useState(1);

const loadMoreProducts = async () => {
  const response = await getProducts(page + 1);
  setProducts([...products, ...response.products]);
  setPage(page + 1);
};
```

### 캐싱 전략
```javascript
// 상품 목록 캐싱 (5분)
const CACHE_DURATION = 5 * 60 * 1000;

const getCachedProducts = async () => {
  const cached = await AsyncStorage.getItem('products_cache');
  const timestamp = await AsyncStorage.getItem('products_cache_time');
  
  if (cached && timestamp) {
    const age = Date.now() - parseInt(timestamp);
    if (age < CACHE_DURATION) {
      return JSON.parse(cached);
    }
  }
  
  // 캐시 만료 시 새로 요청
  const products = await apiRequest('/api/products');
  await AsyncStorage.setItem('products_cache', JSON.stringify(products));
  await AsyncStorage.setItem('products_cache_time', Date.now().toString());
  
  return products;
};
```

## 필요한 서버 설정 변경 요약

### 1. CORS 설정 확장
- `config.py`에서 모바일 앱 도메인 추가
- 개발/프로덕션 환경별 CORS 정책 분리

### 2. 인증 토큰 응답 형식 확인
- 현재 쿠키 설정 외에 JSON 응답으로도 토큰 제공 확인
- Bearer 토큰 인증 우선순위 확인 (이미 구현됨)

### 3. Rate Limiting 조정
- 모바일 앱 전용 Rate Limit 설정
- API별 차등 제한 정책 적용

### 4. HTTPS 설정 (프로덕션)
- CloudFront SSL 설정 확인
- 모바일 앱 도메인 SSL 인증서 발급

## 테스트 방법

### Postman/Insomnia 테스트
```bash
# 1. 로그인
POST https://localhost/api/auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "admin123"
}

# 2. 토큰으로 API 테스트
GET https://localhost/api/products
Authorization: Bearer <access_token>
```

### cURL 테스트
```bash
# 로그인
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# Bearer 토큰 테스트
curl -X GET http://localhost/api/products \
  -H "Authorization: Bearer <access_token>"
```

이 가이드는 마법옷장 API를 모바일 앱에서 사용하기 위한 완전한 구현 가이드입니다. 서버 설정 변경 후 모든 플랫폼에서 안전하고 효율적인 API 접근이 가능합니다.