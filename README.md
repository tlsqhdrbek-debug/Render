# 🚀 기업 분석 보고서 생성기 (RAG 기반)

Streamlit + OpenAI Embeddings + Supabase Vector를 활용한 AI 기반 기업 분석 보고서 자동 생성 시스템입니다.

## ✨ 주요 기능

### 📄 PDF 처리 및 텍스트 추출
- PyMuPDF를 통한 고속 PDF 텍스트 추출
- EasyOCR 폴백 지원 (이미지 기반 PDF)
- 여러 참고자료 PDF 동시 처리

### 🔮 임베딩 기반 RAG 시스템
- **텍스트 청킹**: 토큰 기반 스마트 분할 (overlap 지원)
- **벡터 임베딩**: OpenAI text-embedding-3-small (1536차원)
- **Supabase Vector DB**: pgvector 기반 고속 유사도 검색
- **의미론적 검색**: 키워드 매칭이 아닌 의미 기반 컨텍스트 검색

### 🤖 AI 기반 보고서 생성
- OpenAI GPT-4o-mini를 활용한 전문 보고서 작성
- RAG를 통한 정확한 컨텍스트 기반 분석
- 11가지 섹션별 맞춤 분석 (선택 가능)
- Word 문서 형식 다운로드

### 💾 Supabase 통합
- 기업 정보, PDF 메타데이터, 추출 데이터 저장
- 임베딩 벡터 자동 저장 및 관리
- 이전 분석 불러오기 기능

## 🏗️ 시스템 아키텍처

```
┌─────────────┐
│   사용자     │
│  (PDF 업로드)│
└──────┬──────┘
       │
       v
┌─────────────────────────────────┐
│     Streamlit 웹앱              │
│  - PDF 텍스트 추출              │
│  - 키워드 추출 (배치)           │
└──────┬──────────────────┬───────┘
       │                  │
       v                  v
┌──────────────┐   ┌──────────────────┐
│  OpenAI API  │   │  Supabase        │
│  - Embeddings│   │  - PostgreSQL    │
│  - GPT-4o    │   │  - pgvector      │
│  - RAG       │   │  - Storage       │
└──────────────┘   └──────────────────┘
       │                  │
       v                  v
┌─────────────────────────────────┐
│  벡터 검색 & 컨텍스트 검색      │
│  1. 쿼리 임베딩 생성            │
│  2. 코사인 유사도 계산          │
│  3. Top-K 문서 청크 반환        │
└─────────────────────────────────┘
       │
       v
┌─────────────────────────────────┐
│  AI 보고서 생성                 │
│  - 추출 데이터 + RAG 컨텍스트   │
│  - 참고자료 통합                │
│  - Word 문서 생성               │
└─────────────────────────────────┘
```

## 🚀 배포 방법

### 1. Supabase 설정

#### 1.1 Supabase 프로젝트 생성
1. [Supabase](https://supabase.com) 접속 및 회원가입
2. 새 프로젝트 생성

#### 1.2 데이터베이스 설정
1. Supabase 대시보드 → SQL Editor 열기
2. `supabase_setup.sql` 파일 내용 복사
3. SQL Editor에 붙여넣고 "Run" 실행
4. pgvector 확장 및 테이블 자동 생성

#### 1.3 API 키 확인
- **Project URL**: `https://xxxxx.supabase.co`
- **anon public key**: Project Settings → API → `anon public`

### 2. 환경 변수 설정

#### 로컬 개발: `.env` 파일 생성
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Render.com 배포
Environment Variables에 추가:
- `OPENAI_API_KEY`: OpenAI API 키
- `SUPABASE_URL`: Supabase 프로젝트 URL
- `SUPABASE_KEY`: Supabase anon key

### 3. Render.com 배포

#### 빌드 설정
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
- **Instance Type**: Free (또는 Starter)

## 💻 로컬 실행

### 1. 저장소 클론 및 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일 생성:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. 실행
```bash
streamlit run streamlit_app.py
```

브라우저에서 `http://localhost:8501` 접속

## 📊 데이터베이스 구조

### 테이블 구성

1. **companies** - 기업 정보
   - company_name, industry, created_at

2. **pdf_files** - PDF 메타데이터
   - company_id, file_name, file_type, storage_path, extracted_text

3. **extracted_data** - 추출된 키워드 데이터
   - company_id, field_name, field_value

4. **reports** - 생성된 보고서
   - company_id, report_content

5. **document_embeddings** - 임베딩 벡터 (RAG 핵심)
   - company_id, chunk_text, **embedding** (vector[1536]), token_count

### 벡터 검색 함수

`match_documents()` RPC 함수:
- 쿼리 임베딩과 코사인 유사도 계산
- Top-K 관련 문서 청크 반환
- company_id, file_type 필터링 지원

## 🔄 RAG 플로우

### 1️⃣ 임베딩 생성 (PDF 업로드 시)
```
PDF 텍스트 → 청킹 (500 토큰) → OpenAI Embeddings 
→ Supabase document_embeddings 저장
```

### 2️⃣ 유사도 검색 (보고서 생성 시)
```
사용자 쿼리 → OpenAI Embeddings → 벡터 검색 
→ Top-K 청크 검색 → 컨텍스트 조합
```

### 3️⃣ 보고서 생성
```
추출 데이터 + RAG 컨텍스트 + 참고자료 
→ GPT-4o 프롬프트 → 전문 보고서 생성
```

## 📦 필요한 환경
- Python 3.8+
- OpenAI API Key (임베딩 + GPT)
- Supabase 프로젝트 (pgvector 활성화)

## 🎯 사용 방법

### 1단계: 템플릿 설정
- 사이드바에서 추출할 키워드 선택
- 또는 직접 필드 추가

### 2단계: PDF 업로드
- **메인 PDF**: 분석 대상 기업 보고서
- **참고자료**: 경쟁사 분석, 산업 리포트 등 (선택)

### 3단계: 데이터 추출
- AI가 자동으로 키워드 추출
- **임베딩 생성 및 저장** (RAG 준비)

### 4단계: 보고서 생성
- 보고서 섹션 선택
- **RAG 기반 컨텍스트 검색**
- AI 보고서 자동 생성
- Word 문서 다운로드

## 🆕 주요 업그레이드 (v2.0)

### ✅ 이전 버전 (단순 텍스트 저장)
- 텍스트를 그대로 저장 (50,000자 제한)
- 키워드 기반 단순 매칭
- 대용량 문서 처리 제한

### 🚀 현재 버전 (임베딩 RAG)
- **벡터 임베딩 자동 생성**
- **의미론적 검색** (코사인 유사도)
- **무제한 문서 처리** (청킹)
- **정확한 컨텍스트 검색**
- **다중 참고자료 통합**

## 🤝 기여
이슈 및 PR 환영합니다!

## 📄 라이선스
MIT License
