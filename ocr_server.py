"""
🖼️ Upstage Document Parse API 서버
Upstage Document Parse API를 FastAPI로 감싸서 원격 호출
- 표 구조 완벽 인식
- 한국어 특화 (네이버 출신 팀)
- 이미지 + 텍스트 통합 분석
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import requests
import io
import os
import logging
import json
import base64

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Parse API Server (Upstage)", version="3.0.0")

# CORS 설정 (모든 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 설정
API_KEY = os.getenv("OCR_API_KEY", "your-secret-ocr-key-12345")  # 내부 인증용
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")  # Upstage API 키

if not UPSTAGE_API_KEY:
    logger.warning("⚠️ UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다!")
else:
    logger.info("✅ Upstage API 키 로드 완료")

# Upstage API 엔드포인트
UPSTAGE_API_URL = "https://api.upstage.ai/v1/document-ai/document-parse"


@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "Document Parse API Server (Upstage)",
        "version": "3.0.0",
        "engine": "Upstage Document Parse",
        "endpoints": ["/ocr", "/ocr-pdf", "/health"],
        "features": ["table_structure", "text_extraction", "layout_analysis", "korean_optimized"]
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "engine": "Upstage Document Parse",
        "api_configured": bool(UPSTAGE_API_KEY),
        "languages": ["korean", "english", "multilingual"],
        "features": ["table_recognition", "layout_analysis", "ocr", "document_understanding"]
    }


@app.post("/ocr")
async def process_ocr(
    file: UploadFile = File(..., description="이미지 파일 (PNG, JPG, etc.)"),
    api_key: str = Header(..., alias="X-API-Key", description="API 인증 키")
):
    """
    이미지에서 텍스트 추출 (OCR)
    
    - **file**: 업로드할 이미지 파일
    - **X-API-Key**: HTTP 헤더에 포함할 API 키
    """
    
    # API 키 검증
    if api_key != API_KEY:
        logger.warning(f"❌ 잘못된 API 키 시도: {api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        # 파일 읽기
        contents = await file.read()
        logger.info(f"📄 파일 수신: {file.filename} ({len(contents)} bytes)")
        
        # 이미지 변환
        image = Image.open(io.BytesIO(contents))
        
        # RGB로 변환 (RGBA 등 처리)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        logger.info(f"🖼️ 이미지 크기: {img_array.shape}")
        
        # Upstage API 호출
        logger.info("🔍 Upstage Document Parse API 호출 중...")
        
        # 이미지를 바이트로 변환
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        
        # Upstage API 요청
        headers = {
            "Authorization": f"Bearer {UPSTAGE_API_KEY}"
        }
        
        files = {
            "document": (file.filename, image_bytes, "image/png")
        }
        
        response = requests.post(
            UPSTAGE_API_URL,
            headers=headers,
            files=files,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Upstage API 오류: {response.status_code}")
            raise HTTPException(status_code=500, detail=f"Upstage API error: {response.text}")
        
        result = response.json()
        
        # 텍스트 추출
        text = result.get("text", "")
        elements = result.get("elements", [])
        
        logger.info(f"✅ 문서 파싱 완료: {len(text)} 글자, {len(elements)}개 요소 추출")
        
        return {
            "text": text,
            "elements": elements,  # 구조화된 요소 (표, 제목, 문단 등)
            "status": "success",
            "char_count": len(text),
            "element_count": len(elements),
            "filename": file.filename,
            "engine": "Upstage Document Parse"
        }
        
    except Exception as e:
        logger.error(f"❌ OCR 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.post("/ocr-pdf")
async def process_pdf_document(
    file: UploadFile = File(..., description="PDF 파일"),
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    PDF 파일 전체를 구조화하여 분석 (표, 이미지, 텍스트 모두 포함)
    """
    
    # API 키 검증
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        # 파일 읽기
        contents = await file.read()
        logger.info(f"📄 PDF 파일 수신: {file.filename} ({len(contents)} bytes)")
        
        # Upstage API 호출
        logger.info("🔍 Upstage Document Parse API로 PDF 분석 중...")
        
        headers = {
            "Authorization": f"Bearer {UPSTAGE_API_KEY}"
        }
        
        files = {
            "document": (file.filename, io.BytesIO(contents), "application/pdf")
        }
        
        # OCR 옵션 추가 (표 인식 강화)
        data = {
            "ocr": "force"  # 항상 OCR 사용 (이미지 기반 PDF도 처리)
        }
        
        response = requests.post(
            UPSTAGE_API_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=60  # PDF는 시간이 더 걸릴 수 있음
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Upstage API 오류: {response.status_code}")
            raise HTTPException(status_code=500, detail=f"Upstage API error: {response.text}")
        
        result = response.json()
        
        # 구조화된 데이터 추출
        content = result.get("content", {})
        text = content.get("text", "")
        html = content.get("html", "")
        
        # 페이지별 정보
        pages = []
        for page_data in result.get("pages", []):
            pages.append({
                "page": page_data.get("page"),
                "text": page_data.get("text", ""),
                "elements": page_data.get("elements", [])
            })
        
        logger.info(f"✅ PDF 분석 완료: {len(pages)}페이지, {len(text)} 글자")
        
        return {
            "text": text,
            "html": html,  # HTML 형태로도 제공
            "pages": pages,
            "page_count": len(pages),
            "char_count": len(text),
            "status": "success",
            "filename": file.filename,
            "engine": "Upstage Document Parse"
        }
        
    except Exception as e:
        logger.error(f"❌ PDF 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF parse failed: {str(e)}")


@app.post("/ocr-batch")
async def process_ocr_batch(
    files: list[UploadFile] = File(..., description="여러 이미지 파일"),
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    여러 이미지를 한 번에 OCR 처리
    """
    
    # API 키 검증
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    results = []
    
    for file in files:
        try:
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 이미지를 바이트로 변환
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            
            # Upstage API 호출
            headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
            files_data = {"document": (file.filename, image_bytes, "image/png")}
            
            response = requests.post(
                UPSTAGE_API_URL,
                headers=headers,
                files=files_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "")
                
                results.append({
                    "filename": file.filename,
                    "text": text,
                    "status": "success",
                    "char_count": len(text),
                    "engine": "Upstage"
                })
            else:
                raise Exception(f"API error: {response.status_code}")
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "total": len(files),
        "successful": len([r for r in results if r["status"] == "success"]),
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("🚀 OCR API 서버 시작")
    print("=" * 50)
    print(f"📍 URL: http://localhost:8000")
    print(f"🔑 API Key: {API_KEY}")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
