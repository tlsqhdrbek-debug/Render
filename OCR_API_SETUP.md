# 🖼️ OCR API 서버 설정 가이드

## 📋 개요

로컬 PC에서 EasyOCR 서버를 실행하고, Render 웹앱에서 원격으로 호출하여 빠른 OCR 처리를 수행합니다.

---

## 🚀 1단계: 로컬 PC에 OCR 서버 설치

### 1.1 가상환경 생성 (권장)

```bash
# 프로젝트 폴더로 이동
cd C:\Users\PC\Desktop\Render

# 가상환경 생성
python -m venv venv-ocr

# 활성화
venv-ocr\Scripts\activate  # Windows
```

### 1.2 패키지 설치

```bash
pip install -r requirements-ocr-server.txt
```

**설치되는 항목:**
- FastAPI (API 서버)
- EasyOCR (OCR 엔진)
- PyTorch (딥러닝 프레임워크)
- Uvicorn (서버 실행)

**설치 시간**: 약 5-10분 (GPU 버전)

---

## 🔑 2단계: API 키 설정

### 2.1 환경 변수 설정

`.env.local` 파일 생성:

```env
# OCR API 키 (직접 만드세요)
OCR_API_KEY=my-super-secret-key-abc123xyz
```

**보안 팁**: 강력한 키 생성
```bash
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

---

## 🖥️ 3단계: OCR 서버 실행

### 3.1 서버 시작

```bash
# 가상환경 활성화 상태에서
python ocr_server.py
```

**출력 예시:**
```
==================================================
🚀 OCR API 서버 시작
==================================================
📍 URL: http://localhost:8000
🔑 API Key: my-super-secret-key-abc123xyz
📚 Docs: http://localhost:8000/docs
==================================================
✅ EasyOCR 모델 로드 완료 (GPU 모드)
```

### 3.2 테스트

브라우저에서 접속:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 🌐 4단계: ngrok 설정 (인터넷 노출)

### 4.1 ngrok 설치

1. https://ngrok.com 회원가입
2. https://ngrok.com/download 다운로드
3. 압축 해제 후 PATH에 추가

### 4.2 ngrok 인증

```bash
# 대시보드에서 Authtoken 복사
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 4.3 터널 시작

**새 터미널 열기** (OCR 서버는 계속 실행 중)

```bash
ngrok http 8000
```

**출력 예시:**
```
Session Status: online
Forwarding: https://abc123.ngrok.io -> http://localhost:8000
```

**중요**: `https://abc123.ngrok.io` URL 복사!

---

## ☁️ 5단계: Render 환경 변수 설정

### 5.1 Render 대시보드 접속

1. Render.com 로그인
2. 웹앱 선택
3. **Environment** 탭 클릭

### 5.2 환경 변수 추가

| Key | Value | 설명 |
|-----|-------|------|
| `OCR_API_URL` | `https://abc123.ngrok.io` | ngrok URL |
| `OCR_API_KEY` | `my-super-secret-key-abc123xyz` | .env.local과 동일 |

### 5.3 재배포

환경 변수 저장 후 자동 재배포됩니다.

---

## ✅ 6단계: 작동 확인

### 6.1 Render 웹앱 접속

1. PDF 업로드
2. ✅ **"☁️ 원격 OCR API 연결됨"** 표시 확인
3. 🔍 **"OCR 강화 모드"** 체크
4. 데이터 추출 시작

### 6.2 속도 비교

| 모드 | 50페이지 처리 시간 |
|------|-------------------|
| PyMuPDF만 | ~5초 |
| 로컬 OCR | ~10-20분 |
| **원격 OCR (로컬 PC)** | **~1-2분** ⚡ |

---

## 🔧 트러블슈팅

### ❌ "원격 OCR API 미연결"

**원인 1**: ngrok 터널 종료
```bash
# ngrok 재시작
ngrok http 8000
# 새 URL을 Render 환경 변수에 업데이트
```

**원인 2**: API 키 불일치
```bash
# .env.local과 Render 환경 변수 확인
```

**원인 3**: 방화벽/네트워크
```bash
# 로컬에서 테스트
curl http://localhost:8000/health
```

### ❌ "OCR 처리 실패"

**원인 1**: 메모리 부족
```python
# ocr_server.py에서 배치 크기 줄이기
```

**원인 2**: GPU 오류
```python
# CPU 모드로 전환
reader = easyocr.Reader(['ko', 'en'], gpu=False)
```

---

## 💰 비용 최적화

### ngrok 플랜 비교

| 플랜 | 가격 | URL | 재시작 |
|------|------|-----|--------|
| **Free** | $0 | 변경됨 | 2시간마다 |
| **Pro** | $8/월 | 고정 | 없음 |

**추천**: 
- 테스트: Free
- 운영: Pro ($8/월)

---

## 🔒 보안 권장사항

### 1. 강력한 API 키 사용
```bash
# 32자 이상 랜덤 문자열
```

### 2. ngrok 인증 추가 (Pro 플랜)
```bash
ngrok http 8000 --basic-auth="user:password"
```

### 3. IP 화이트리스트 (Pro 플랜)
```bash
# Render IP만 허용
```

---

## 📊 모니터링

### OCR 서버 로그 확인
```bash
# 터미널에서 실시간 로그 확인
# 각 요청마다 표시됨:
# 📄 파일 수신
# 🔍 OCR 처리 시작
# ✅ OCR 완료
```

### ngrok 대시보드
- http://localhost:4040
- 요청/응답 모니터링

---

## 🎯 사용 팁

### 1. PC 항상 켜두기
- **절전 모드 비활성화**
- Windows 설정 → 전원 및 절전 → 절전 모드: 안 함

### 2. 자동 시작 설정
```bash
# Task Scheduler로 부팅 시 자동 실행
# 1. ocr_server.py 실행
# 2. ngrok http 8000 실행
```

### 3. ngrok URL 자동 업데이트
```python
# Python 스크립트로 Render API 호출하여 환경 변수 자동 업데이트
```

---

## 📞 문제 해결

### Discord/Slack 알림 설정
```python
# OCR 서버 다운 시 알림
# ngrok 터널 재시작 시 알림
```

### 백업 플랜
```python
# 원격 OCR 실패 시 로컬 OCR 자동 폴백
# (이미 구현됨)
```

---

## 🎉 완료!

이제 다음이 가능합니다:
- ✅ 로컬 PC의 고성능 OCR 활용
- ✅ Render 웹앱에서 빠른 처리
- ✅ 다른 사람도 사용 가능
- ✅ 24시간 서비스 (PC 켜두기만 하면)

**예상 전기세**: 월 3-5만원 (24시간 가동 시)
