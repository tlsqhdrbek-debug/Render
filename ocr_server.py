"""
🖼️ 로컬 PC OCR API 서버
EasyOCR을 FastAPI로 감싸서 원격 호출 가능하게 만듦
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import easyocr
import numpy as np
from PIL import Image
import io
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OCR API Server", version="1.0.0")

# CORS 설정 (모든 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 설정 (환경 변수에서 가져오기)
API_KEY = os.getenv("OCR_API_KEY", "your-secret-ocr-key-12345")

# EasyOCR 초기화 (앱 시작 시 한 번만 로드)
logger.info("🔄 EasyOCR 모델 로딩 중...")
try:
    reader = easyocr.Reader(['ko', 'en'], gpu=True, verbose=False)
    logger.info("✅ EasyOCR 모델 로드 완료 (GPU 모드)")
except Exception as e:
    logger.warning(f"⚠️ GPU 사용 실패, CPU 모드로 전환: {e}")
    reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
    logger.info("✅ EasyOCR 모델 로드 완료 (CPU 모드)")


@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "OCR API Server is running",
        "version": "1.0.0",
        "endpoints": ["/ocr", "/health"]
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        device = str(reader.detector.device) if hasattr(reader.detector, 'device') else "unknown"
        return {
            "status": "healthy",
            "gpu_enabled": "cuda" in device.lower(),
            "device": device,
            "languages": ["ko", "en"]
        }
    except Exception as e:
        return {
            "status": "healthy",
            "error": str(e)
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
        
        # OCR 처리
        logger.info("🔍 OCR 처리 시작...")
        result = reader.readtext(img_array, detail=0, paragraph=True)
        text = "\n".join(result)
        
        logger.info(f"✅ OCR 완료: {len(text)} 글자 추출")
        
        return {
            "text": text,
            "status": "success",
            "char_count": len(text),
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"❌ OCR 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


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
            
            img_array = np.array(image)
            result = reader.readtext(img_array, detail=0, paragraph=True)
            text = "\n".join(result)
            
            results.append({
                "filename": file.filename,
                "text": text,
                "status": "success",
                "char_count": len(text)
            })
            
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
