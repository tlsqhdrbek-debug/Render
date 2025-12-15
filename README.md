# 기업 분석 보고서 생성기

Streamlit 기반의 PDF 기업 분석 보고서 자동 생성 애플리케이션입니다.

## 기능
- PDF 파일 업로드 및 텍스트 추출
- OpenAI API를 활용한 기업 분석 보고서 생성
- Word 문서 형식으로 보고서 다운로드

## 배포 방법 (Render.com)

### 1. 환경 변수 설정
Render.com 대시보드에서 다음 환경 변수를 설정하세요:
- `OPENAI_API_KEY`: OpenAI API 키

### 2. 빌드 설정
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`

## 로컬 실행

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
# OPENAI_API_KEY=your_key_here

# 실행
streamlit run streamlit_app.py
```

## 필요한 환경
- Python 3.8+
- OpenAI API Key
