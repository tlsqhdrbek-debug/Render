"""
EasyOCR 로컬 테스트 스크립트
GPU/CPU 감지 및 간단한 OCR 테스트
"""

import sys

print("=" * 60)
print("🧪 EasyOCR 로컬 테스트 시작")
print("=" * 60)

# 1. 필요한 패키지 확인
print("\n📦 1단계: 패키지 확인")
required_packages = ['easyocr', 'torch', 'PIL', 'numpy']

for package in required_packages:
    try:
        if package == 'PIL':
            __import__('PIL')
            print(f"  ✅ {package} 설치됨")
        else:
            __import__(package)
            print(f"  ✅ {package} 설치됨")
    except ImportError:
        print(f"  ❌ {package} 미설치")
        print(f"\n설치 명령: pip install {package}")
        sys.exit(1)

# 2. GPU 확인
print("\n🖥️ 2단계: GPU 확인")
import torch
if torch.cuda.is_available():
    print(f"  ✅ CUDA 사용 가능")
    print(f"  📊 GPU: {torch.cuda.get_device_name(0)}")
    print(f"  💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print(f"  ⚠️ CUDA 사용 불가 - CPU 모드로 실행")

# 3. EasyOCR 로드 테스트
print("\n🔄 3단계: EasyOCR 모델 로딩")
print("  (처음 실행 시 모델 다운로드 - 수 분 소요)")

import easyocr
import time

start_time = time.time()

try:
    # GPU 시도
    print("  🔸 GPU 모드 시도...")
    reader = easyocr.Reader(['ko', 'en'], gpu=True, verbose=False)
    gpu_mode = True
    print(f"  ✅ GPU 모드 로드 완료 ({time.time() - start_time:.1f}초)")
except Exception as e:
    # CPU 폴백
    print(f"  ⚠️ GPU 실패: {e}")
    print("  🔸 CPU 모드로 재시도...")
    start_time = time.time()
    reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
    gpu_mode = False
    print(f"  ✅ CPU 모드 로드 완료 ({time.time() - start_time:.1f}초)")

# 4. 간단한 텍스트 이미지 생성 및 OCR 테스트
print("\n🖼️ 4단계: OCR 기능 테스트")

from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 테스트 이미지 생성
img = Image.new('RGB', (400, 100), color='white')
draw = ImageDraw.Draw(img)

# 기본 폰트 사용
try:
    font = ImageFont.truetype("malgun.ttf", 30)  # Windows 한글 폰트
except:
    font = ImageFont.load_default()

draw.text((10, 30), "안녕하세요 Hello 123", fill='black', font=font)

# 이미지 저장
img.save("test_ocr_image.png")
print("  📝 테스트 이미지 생성: test_ocr_image.png")

# OCR 수행
print("  🔍 OCR 처리 중...")
start_time = time.time()

img_array = np.array(img)
result = reader.readtext(img_array, detail=0)

ocr_time = time.time() - start_time
extracted_text = " ".join(result)

print(f"  ✅ OCR 완료 ({ocr_time:.2f}초)")
print(f"  📄 추출된 텍스트: '{extracted_text}'")

# 5. 결과 요약
print("\n" + "=" * 60)
print("📊 테스트 결과 요약")
print("=" * 60)
print(f"  GPU 모드: {'✅ 활성화' if gpu_mode else '❌ 비활성화 (CPU 사용)'}")
print(f"  OCR 처리 시간: {ocr_time:.2f}초")
print(f"  한글 인식: {'✅' if '안녕' in extracted_text or 'ㅇ' in extracted_text else '⚠️'}")
print(f"  영문 인식: {'✅' if 'Hello' in extracted_text or 'hello' in extracted_text.lower() else '⚠️'}")
print(f"  숫자 인식: {'✅' if '123' in extracted_text else '⚠️'}")

# 6. 권장 사항
print("\n💡 권장 사항:")
if not gpu_mode:
    print("  ⚠️ GPU 미사용 - 대용량 PDF는 매우 느릴 수 있음")
    print("  📌 Intel Arc GPU 드라이버 업데이트 권장")
else:
    print("  ✅ GPU 사용 중 - 최적 성능!")

if ocr_time > 2:
    print("  ⚠️ OCR 속도가 느림 - 50페이지는 오래 걸릴 수 있음")
else:
    print("  ✅ OCR 속도 양호!")

print("\n" + "=" * 60)
print("🎉 테스트 완료!")
print("=" * 60)
