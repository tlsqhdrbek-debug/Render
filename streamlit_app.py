import streamlit as st
import fitz  # PyMuPDF
import os
import re
import numpy as np
from openai import OpenAI
from pathlib import Path
from docx import Document
from datetime import datetime
import tiktoken

# 페이지 설정
st.set_page_config(
    page_title="기업 분석 보고서 생성기",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
    }
    .stApp {
        background: white;
        border-radius: 24px;
        padding: 40px;
        margin: 20px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    }
    /* 사이드바 너비 증가 */
    [data-testid="stSidebar"] {
        min-width: 350px !important;
        max-width: 350px !important;
    }
    /* 사이드바 버튼 크기 조정 */
    .stSidebar button {
        font-size: 11px !important;
        padding: 5px 10px !important;
        white-space: nowrap !important;
    }
    /* Expander 내부 버튼도 작게 */
    [data-testid="stExpander"] button {
        font-size: 11px !important;
    }
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 30px;
        background-color: white;
        border-radius: 8px;
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #64748b;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-color: transparent !important;
    }
    .keyword-tag {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        margin: 3px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
    }
    .template-container {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        align-items: center;
        margin-bottom: 10px;
    }
    .delete-btn {
        background: rgba(255, 255, 255, 0.2);
        border: none;
        color: white;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        cursor: pointer;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# .env 파일 로드
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# OpenAI 클라이언트 초기화
openai_client = None
if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your-api-key-here":
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_client = OpenAI(api_key=openai_api_key)
    st.sidebar.success("✅ OpenAI API 키 로드됨")
else:
    st.sidebar.warning("⚠️ .env에 OPENAI_API_KEY를 설정하세요")

# Supabase 클라이언트 초기화
supabase_client = None
try:
    from supabase import create_client, Client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        st.sidebar.success("✅ Supabase 연결됨")
    else:
        st.sidebar.info("ℹ️ Supabase 미연결 (환경변수 미설정)")
except Exception as e:
    st.sidebar.error(f"⚠️ Supabase 연결 실패: {e}")

# 세션 스테이트 초기화
if 'template' not in st.session_state:
    st.session_state.template = []
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'report_sections' not in st.session_state:
    # 기본 보고서 섹션 선택 (모두 선택)
    st.session_state.report_sections = [
        "기업 개요",
        "사업 구조 및 Revenue Model 분석",
        "산업 및 시장 분석",
        "재무 요약",
        "재무 건전성 심화 분석",
        "고객사 및 매출 집중도 분석",
        "경쟁사 비교 분석",
        "경영진 역량 및 지배구조 분석",
        "신용도 및 법률 리스크",
        "리스크 요인",
        "종합 평가"
    ]
if 'show_template_editor' not in st.session_state:
    st.session_state.show_template_editor = False
if 'reference_pdfs' not in st.session_state:
    st.session_state.reference_pdfs = {}  # {filename: extracted_text}

# 보고서 섹션별 작성 지침 정의
REPORT_SECTION_TEMPLATES = {
    "기업 개요": """1. **기업 개요**
   - 회사명, 업종, 주요 사업 내용
   - 매출/영업이익 등 기본 정보
   - 설립 배경 및 주요 연혁
   - 조직 구조 요약(선택)
   - 추출된 데이터만 사용""",
    
    "사업 구조 및 Revenue Model 분석": """2. **사업 구조 및 Revenue Model 분석**
   - 주요 사업부 구조 및 매출 비중
   - 제품/서비스별 수익 모델
   - 고객 대상군(B2B/B2C), 지역별 매출 구조
   - 주요 원가/마진 구조
   - 여신 심사에 필요한 핵심 항목
   - 추출된 데이터 기반, 없으면 업종 특성 반영
   - *> 본 문서에 해당 내용이 없어, AI 모델이 학습한 일반 지식을 기반으로 작성했습니다. (2023년 10월 기준)*
   - *> 최신 정보나 경쟁사 비교가 필요하면 관련 PDF를 '참고자료'로 추가 업로드하시면 더 정확한 분석이 가능합니다.*""",
    
    "산업 및 시장 분석": """3. **산업 및 시장 분석**
   - 산업 규모, 성장성, 시장 동향
   - 경쟁 구도 및 트렌드
   - 해당 기업이 속한 시장의 위험 요인
   - PDF에 정보 없으면 업종 기준 일반 분석
   - *> 본 문서에 해당 내용이 없어, AI 모델이 학습한 일반 지식을 기반으로 작성했습니다. (2023년 10월 기준)*
   - *> 최신 산업 리포트나 시장 분석 자료를 '참고자료'로 추가 업로드하시면 더 정확한 분석이 가능합니다.*""",
    
    "재무 요약": """4. **재무 요약**
   - 매출, 영업이익, 성장률 분석
   - 추출된 핵심 재무 데이터 기반
   - 수익성·성장성 지표
   - 전년 대비 성장률, 수익성 지표 포함""",
    
    "재무 건전성 심화 분석": """5. **재무 건전성 심화 분석**
   - 부채 구조(단기/장기)
   - 이자보상배율, 차입 의존도
   - 영업현금흐름 안정성
   - 순운전자본(NWC) 분석
   - 대출 상환능력 평가 핵심 지표
   - 추출된 재무 데이터 기반""",
    
    "고객사 및 매출 집중도 분석": """6. **고객사 및 매출 집중도 분석**
   - 주요 고객사 TOP5
   - 단일 거래처 의존도
   - 매출 다변화 수준
   - 거래처 변경 가능성
   - 캐피탈 리스크 심사에서 매우 중요
   - PDF에 데이터가 있으면 사용, 없으면 언급""",
    
    "경쟁사 비교 분석": """7. **경쟁사 비교 분석**
   - 업종 내 주요 경쟁사 비교
   - 경쟁 우위·열위 분석
   - 시장 점유율 추정
   - 데이터 없으면 업종 기반 일반 비교
   - *> 본 문서에 해당 내용이 없어, AI 모델이 학습한 일반 지식을 기반으로 작성했습니다. (2023년 10월 기준)*
   - *> 경쟁사 사업보고서나 IR 자료를 '참고자료'로 추가 업로드하시면 더 정확한 비교 분석이 가능합니다.*""",
    
    "경영진 역량 및 지배구조 분석": """8. **경영진 역량 및 지배구조 분석**
   - CEO 및 핵심 임원 경력
   - 지분 구조, 오너 리스크
   - 지배구조 투명성
   - 경영진 교체 이력
   - 특히 중소기업 심사에 매우 중요
   - PDF에 데이터가 있으면 사용, 없으면 언급 안 함""",
    
    "신용도 및 법률 리스크": """9. **신용도 및 법률 리스크**
   - 신용등급(있으면)
   - 감사 의견(적정/한정 등)
   - 최근 소송·분쟁·제재 여부
   - 공정위/금융위 제재 여부
   - 기본 리스크 요인과 구분되는 정량적 리스크
   - PDF에 데이터가 있으면 사용
   - *> 본 문서에 해당 내용이 없어, AI 모델이 학습한 일반 지식을 기반으로 작성했습니다. (2023년 10월 기준)*""",
    
    "리스크 요인": """10. **리스크 요인**
   - 산업 리스크
   - 운영 리스크
   - 재무적 일반 리스크
   - PDF에 리스크 정보가 있으면 사용
   - 없으면 해당 산업의 일반적 리스크 설명
   - *> 본 문서에 해당 내용이 없어, AI 모델이 학습한 일반 지식을 기반으로 작성했습니다. (2023년 10월 기준)*""",
    
    "종합 평가": """11. **종합 평가 (투자/대출 관점)**
   - 재무 안정성 평가
   - 상환 능력 평가
   - 성장 가능성 요약
   - 종합 의견 및 권장 조치
   - 대출 승인/조건/유의사항 제시 가능
   - 추출된 데이터 기반으로 객관적 판단"""
}

# Supabase 헬퍼 함수
def save_to_supabase(company_name, pdf_file, extracted_text, extracted_data, report_content=None, create_embeddings_flag=True):
    """Supabase에 데이터 및 임베딩 저장"""
    if not supabase_client:
        st.warning("⚠️ Supabase 클라이언트가 연결되지 않았습니다.")
        return None
    
    try:
        # 1. 기업 정보 저장
        company_data = {
            "company_name": company_name,
            "industry": extracted_data.get("업종") or extracted_data.get("산업분류") or "미분류"
        }
        company_response = supabase_client.table("companies").insert(company_data).execute()
        company_id = company_response.data[0]["id"]
        st.info(f"✅ 기업 정보 저장 완료 (ID: {company_id})")
        
        # 2. PDF 파일을 Storage에 저장 (선택사항 - 에러 발생 시 무시)
        try:
            file_path = f"{company_id}/main.pdf"
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            supabase_client.storage.from_("company-pdfs").upload(
                file_path,
                pdf_bytes,
                {"content-type": "application/pdf"}
            )
            file_size = len(pdf_bytes)
            st.info("✅ PDF 파일 Storage 저장 완료")
        except Exception as storage_error:
            st.warning(f"⚠️ PDF Storage 저장 실패 (계속 진행): {storage_error}")
            file_path = "not_stored"
            file_size = 0
        
        # 3. PDF 파일 정보 저장
        pdf_data = {
            "company_id": company_id,
            "file_name": getattr(pdf_file, 'name', 'unknown.pdf'),
            "file_type": "main",
            "storage_path": file_path,
            "file_size": file_size,
            "extracted_text": extracted_text[:50000],  # 텍스트 크기 제한
            "pages_count": extracted_text.count("=== 페이지")
        }
        supabase_client.table("pdf_files").insert(pdf_data).execute()
        st.info("✅ PDF 메타데이터 저장 완료")
        
        # 4. 추출된 데이터 저장
        data_entries = []
        for field_name, field_value in extracted_data.items():
            data_entries.append({
                "company_id": company_id,
                "field_name": field_name,
                "field_value": str(field_value)[:5000]  # 길이 제한
            })
        
        if data_entries:
            supabase_client.table("extracted_data").insert(data_entries).execute()
            st.info(f"✅ 추출 데이터 {len(data_entries)}개 저장 완료")
        
        # 5. 보고서 저장 (선택사항)
        if report_content:
            report_data = {
                "company_id": company_id,
                "report_content": report_content[:100000]  # 크기 제한
            }
            supabase_client.table("reports").insert(report_data).execute()
            st.info("✅ 보고서 저장 완료")
        
        # 6. 임베딩 생성 및 저장 (RAG 시스템)
        if create_embeddings_flag and openai_client:
            with st.spinner("🔮 임베딩 벡터 생성 중..."):
                # 텍스트 청크 분할
                chunks = split_text_into_chunks(extracted_text, max_tokens=500, overlap_tokens=50)
                st.info(f"📦 {len(chunks)}개 청크 생성 완료")
                
                # 임베딩 생성
                embeddings = create_embeddings(chunks)
                
                if embeddings:
                    # Supabase에 저장
                    save_embeddings_to_supabase(company_id, embeddings, file_type="main")
                else:
                    st.warning("⚠️ 임베딩 생성 실패 - 텍스트 검색은 제한됩니다")
        
        return company_id
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        st.error(f"❌ Supabase 저장 실패")
        st.error(f"에러: {str(e)}")
        with st.expander("상세 에러 로그"):
            st.code(error_detail)
        return None

def load_companies_list():
    """저장된 기업 목록 불러오기"""
    if not supabase_client:
        return []
    
    try:
        response = supabase_client.table("companies").select("*").order("created_at", desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        st.error(f"기업 목록 로드 실패: {e}")
        return []

def load_company_data(company_id):
    """특정 기업의 추출된 데이터 불러오기"""
    if not supabase_client:
        return {}
    
    try:
        response = supabase_client.table("extracted_data").select("*").eq("company_id", company_id).execute()
        return {item["field_name"]: item["field_value"] for item in response.data}
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return {}

# ============================================
# 임베딩 및 RAG 시스템
# ============================================

def split_text_into_chunks(text, max_tokens=500, overlap_tokens=50):
    """텍스트를 토큰 기반으로 청크 분할"""
    try:
        encoding = tiktoken.encoding_for_model("text-embedding-3-small")
        tokens = encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)
            
            chunks.append({
                "text": chunk_text,
                "start_pos": start,
                "end_pos": end,
                "token_count": len(chunk_tokens)
            })
            
            start += (max_tokens - overlap_tokens)
        
        return chunks
    except Exception as e:
        st.error(f"청크 분할 실패: {e}")
        # 폴백: 단순 문자 기반 분할
        chunk_size = 2000
        overlap = 200
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append({
                "text": chunk_text,
                "start_pos": start,
                "end_pos": end,
                "token_count": len(chunk_text) // 4  # 대략적 추정
            })
            start += (chunk_size - overlap)
        return chunks

def create_embeddings(text_chunks):
    """OpenAI API로 임베딩 벡터 생성"""
    if not openai_client:
        st.error("OpenAI 클라이언트가 초기화되지 않았습니다.")
        return []
    
    embeddings = []
    try:
        for i, chunk in enumerate(text_chunks):
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk["text"]
            )
            embedding_vector = response.data[0].embedding
            
            embeddings.append({
                "chunk_index": i,
                "text": chunk["text"],
                "embedding": embedding_vector,
                "token_count": chunk["token_count"]
            })
            
            # 진행 상황 표시
            if (i + 1) % 10 == 0:
                st.info(f"임베딩 생성 중... {i + 1}/{len(text_chunks)}")
        
        return embeddings
    except Exception as e:
        st.error(f"임베딩 생성 실패: {e}")
        return []

def save_embeddings_to_supabase(company_id, embeddings, file_type="main"):
    """Supabase에 임베딩 벡터 저장"""
    if not supabase_client:
        st.warning("Supabase 클라이언트가 연결되지 않았습니다.")
        return False
    
    try:
        # 벡터 데이터 준비
        vector_entries = []
        for emb in embeddings:
            vector_entries.append({
                "company_id": company_id,
                "file_type": file_type,
                "chunk_index": emb["chunk_index"],
                "chunk_text": emb["text"][:5000],  # 텍스트 길이 제한
                "embedding": emb["embedding"],
                "token_count": emb["token_count"]
            })
        
        # 배치로 저장 (한 번에 너무 많으면 분할)
        batch_size = 100
        for i in range(0, len(vector_entries), batch_size):
            batch = vector_entries[i:i + batch_size]
            supabase_client.table("document_embeddings").insert(batch).execute()
            st.info(f"벡터 저장 중... {min(i + batch_size, len(vector_entries))}/{len(vector_entries)}")
        
        st.success(f"✅ {len(vector_entries)}개 임베딩 벡터 저장 완료!")
        return True
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        st.error(f"벡터 저장 실패: {str(e)}")
        with st.expander("상세 에러 로그"):
            st.code(error_detail)
        return False

def semantic_search(query, company_id=None, top_k=5, file_type=None):
    """의미론적 유사도 검색"""
    if not supabase_client or not openai_client:
        st.warning("Supabase 또는 OpenAI 클라이언트가 연결되지 않았습니다.")
        return []
    
    try:
        # 쿼리 임베딩 생성
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Supabase에서 유사도 검색 (RPC 함수 사용)
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": top_k
        }
        
        # 회사 ID 필터
        if company_id:
            rpc_params["filter_company_id"] = company_id
        
        # 파일 타입 필터
        if file_type:
            rpc_params["filter_file_type"] = file_type
        
        # RPC 호출
        result = supabase_client.rpc(
            "match_documents",
            rpc_params
        ).execute()
        
        return result.data
    except Exception as e:
        st.error(f"유사도 검색 실패: {e}")
        return []

def retrieve_relevant_context(query, company_id=None, max_tokens=3000):
    """RAG: 쿼리와 관련된 컨텍스트 추출"""
    search_results = semantic_search(query, company_id=company_id, top_k=10)
    
    if not search_results:
        return "관련 컨텍스트를 찾을 수 없습니다."
    
    # 토큰 제한 내에서 관련 텍스트 조합
    context_parts = []
    total_tokens = 0
    
    for result in search_results:
        chunk_text = result.get("chunk_text", "")
        similarity = result.get("similarity", 0)
        token_count = result.get("token_count", 0)
        
        if total_tokens + token_count > max_tokens:
            break
        
        context_parts.append(f"[유사도: {similarity:.3f}]\n{chunk_text}")
        total_tokens += token_count
    
    return "\n\n---\n\n".join(context_parts)

# OCR Reader (lazy loading)
_ocr_reader = None

def get_ocr_reader():
    """OCR Reader를 lazy loading으로 가져오기"""
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)
    return _ocr_reader

def extract_text_from_pdf(pdf_file, max_pages=5):
    """PDF에서 텍스트 추출"""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        num_pages = min(len(doc), max_pages)
        
        text = ""
        for page_num in range(num_pages):
            page = doc[page_num]
            page_text = page.get_text()
            text += f"\n\n=== 페이지 {page_num+1} ===\n\n{page_text}"
        
        if len(text.strip()) > 100:
            doc.close()
            return text, num_pages
        
        # OCR 폴백 (텍스트가 부족한 경우)
        st.warning("텍스트 추출량이 적어 OCR을 사용합니다...")
        return extract_text_with_easyocr(pdf_file, max_pages)
        
    except Exception as e:
        st.error(f"PDF 읽기 오류: {e}")
        return "", 0

def extract_text_with_easyocr(pdf_file, max_pages=5):
    """EasyOCR로 텍스트 추출"""
    text = ""
    try:
        pdf_file.seek(0)
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        num_pages = min(len(doc), max_pages)
        
        for page_num in range(num_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                img_array = img_array[:, :, :3]
            
            ocr_reader = get_ocr_reader()
            ocr_result = ocr_reader.readtext(img_array, detail=0, paragraph=True)
            page_text = "\n".join(ocr_result)
            text += f"\n\n=== 페이지 {page_num+1} ===\n\n{page_text}"
        
        doc.close()
        return text, num_pages
    except Exception as e:
        st.error(f"OCR 오류: {e}")
        return "", 0

def extract_all_keywords_batch(text, field_names):
    """배치 방식으로 모든 키워드를 한 번에 추출 (토큰 절감)"""
    if not openai_client:
        # API 없으면 개별 방식으로 폴백
        result = {}
        for field_name in field_names:
            result[field_name] = extract_keyword_simple(text, field_name)
        return result
    
    try:
        # 텍스트가 너무 길면 앞부분만 사용
        text_preview = text[:4000]
        
        # 모든 필드를 한 번에 요청
        fields_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(field_names)])
        
        prompt = f"""다음 텍스트에서 아래 항목들에 해당하는 정보를 찾아서 정확하게 추출하세요.

텍스트:
{text_preview}

추출할 항목:
{fields_list}

요구사항:
1. 각 항목별로 관련된 모든 정보를 추출
2. 정보가 없으면 "정보 없음"이라고만 응답
3. 원문의 표현을 최대한 유지
4. 반드시 다음 형식으로 답변 (각 항목은 새 줄에):

[항목명]: 추출된 내용

답변:"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 문서에서 정확한 정보를 추출하는 전문가입니다. 반드시 '[항목명]: 내용' 형식으로 답변합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        print(f"[DEBUG] 배치 추출 결과:\n{result_text}\n")
        
        # 결과 파싱 - 더 간단한 방식
        extracted_data = {}
        
        for line in result_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # [항목명]: 또는 항목명: 형식 찾기
            if ':' in line:
                # [ ] 제거
                line = line.replace('[', '').replace(']', '')
                parts = line.split(':', 1)
                
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    value = parts[1].strip()
                    
                    # 필드명이 요청한 항목 중 하나인지 확인
                    for fn in field_names:
                        if fn == field_name or fn in field_name or field_name in fn:
                            extracted_data[fn] = value
                            break
        
        # 누락된 필드는 "정보 없음"으로 채우기
        for field_name in field_names:
            if field_name not in extracted_data:
                extracted_data[field_name] = "정보 없음"
        
        print(f"[DEBUG] 파싱된 데이터: {extracted_data}\n")
        return extracted_data
        
    except Exception as e:
        print(f"[DEBUG] 배치 추출 실패: {e}")
        # 실패 시 개별 방식으로 폴백
        result = {}
        for field_name in field_names:
            result[field_name] = extract_keyword_simple(text, field_name)
        return result

def extract_keyword(text, field_name):
    """OpenAI API로 지능적으로 키워드 관련 정보 추출"""
    if not openai_client:
        return extract_keyword_simple(text, field_name)
    
    try:
        # 텍스트가 너무 길면 앞부분만 사용 (토큰 제한)
        text_preview = text[:4000]
        
        prompt = f"""다음 텍스트에서 "{field_name}"에 해당하는 정보를 찾아서 정확하게 추출하세요.

텍스트:
{text_preview}

요구사항:
1. "{field_name}"와 관련된 모든 정보를 추출
2. 정보가 없으면 "정보 없음"이라고만 응답
3. 추출한 정보를 그대로 답변 (설명 없이)
4. 여러 항목이 있으면 모두 포함
5. 원문의 표현을 최대한 유지

답변:"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 문서에서 정확한 정보를 추출하는 전문가입니다. 요청받은 정보를 원문 그대로 완전하게 추출합니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # 빈 응답이거나 너무 짧으면 폴백
        if not result or len(result) < 2:
            return extract_keyword_simple(text, field_name)
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] OpenAI 추출 실패 ({field_name}): {e}")
        return extract_keyword_simple(text, field_name)

def extract_keyword_simple(text, field_name):
    """단순 텍스트 매칭 방식 (폴백)"""
    keywords_map = {
        "회사": ["회사", "기업", "법인", "㈜", "(주)", "주식회사"],
        "회사명": ["회사", "기업", "법인", "㈜", "(주)", "주식회사"],
        "회사이름": ["회사", "기업", "법인", "㈜", "(주)", "주식회사"],
        "기업명": ["회사", "기업", "법인", "㈜", "(주)", "주식회사"],
        "대표": ["대표", "CEO", "대표이사", "대표자"],
        "대표이름": ["대표", "CEO", "대표이사", "대표자"],
        "대표이사": ["대표", "CEO", "대표이사", "대표자"],
        "CEO": ["CEO", "대표", "대표이사"],
        "사업": ["사업", "업종", "사업분야", "사업내용"],
        "사업분야": ["사업분야", "사업", "업종", "주요 사업"],
        "사업내용": ["사업내용", "사업", "업종"],
        "매출": ["매출", "매출액", "Revenue"],
        "매출액": ["매출액", "매출", "Revenue"],
        "연매출": ["연매출", "매출액", "매출", "연간매출"],
        "영업이익": ["영업이익", "영업익", "Operating Profit"],
        "순이익": ["순이익", "당기순이익", "Net Profit"],
        "성과": ["성과", "실적", "주요 성과", "성과 지표"],
    }
    
    search_keywords = keywords_map.get(field_name, [field_name])
    
    lines = text.split('\n')
    result = []
    
    for keyword in search_keywords:
        pattern = re.compile(rf'{re.escape(keyword)}[:\s]*([^\n]+)', re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if match:
                value = match.group(1).strip()
                if value and len(value) > 1:
                    result.append(value)
    
    return result[0] if result else "정보 없음"

def generate_report_with_openai(data_dict, report_sections=None, model="gpt-4o-mini", company_id=None, use_rag=True):
    """RAG 기반 OpenAI API로 체계적인 기업 분석 보고서 생성"""
    if not openai_client:
        return "❌ OpenAI API 키를 .env 파일에 설정하세요."
    
    # 보고서 섹션이 없으면 세션에서 가져오기
    if report_sections is None:
        report_sections = st.session_state.get('report_sections', [])
    
    # 선택된 섹션에 해당하는 작성 지침만 조합
    selected_guidelines = []
    for section in report_sections:
        if section in REPORT_SECTION_TEMPLATES:
            selected_guidelines.append(REPORT_SECTION_TEMPLATES[section])
    
    report_template = "\n\n".join(selected_guidelines)
    
    # 작성 규칙 추가
    report_template += """

**작성 규칙:**
- 각 섹션을 명확히 구분하여 작성
- PDF에서 추출한 정보는 그대로 사용
- PDF에 없는 정보로 외부 지식을 활용할 때는 반드시 "*> 본 문서에 해당 내용이 없어 외부 정보를 참고하여 답변 생성 (출처: [정보 출처])*" 형식으로 표시
- 마크다운 형식 사용 (## 제목, **강조**)
- 전문적이고 객관적인 톤 유지
- 구체적인 숫자와 데이터 중심으로 작성"""
    
    # 추출된 데이터 정리
    available_data = []
    missing_fields = []
    
    for key, value in data_dict.items():
        if value and value != "정보 없음":
            available_data.append(f"- {key}: {value}")
        else:
            missing_fields.append(key)
    
    if not available_data:
        return "❌ 추출된 데이터가 없습니다."
    
    available_data_text = "\n".join(available_data)
    missing_fields_text = ", ".join(missing_fields) if missing_fields else "없음"
    
    # RAG: 의미론적 검색으로 관련 컨텍스트 가져오기
    rag_context = ""
    if use_rag and company_id and supabase_client:
        with st.spinner("🔍 관련 문서 검색 중..."):
            # 보고서 섹션별 쿼리 생성
            queries = [
                f"{company_name} 재무 정보 매출 영업이익",
                f"{company_name} 사업 구조 제품 서비스",
                f"{company_name} 경쟁사 시장 분석",
                "리스크 요인 위험 요소"
            ]
            
            retrieved_contexts = []
            for query in queries:
                context = retrieve_relevant_context(query, company_id=company_id, max_tokens=1000)
                if context and context != "관련 컨텍스트를 찾을 수 없습니다.":
                    retrieved_contexts.append(context)
            
            if retrieved_contexts:
                rag_context = "\n\n**🔍 관련 문서 컨텍스트 (벡터 검색 결과):**\n" + "\n\n".join(retrieved_contexts[:2])  # 상위 2개만
                st.success(f"✅ {len(retrieved_contexts)}개 관련 컨텍스트 검색 완료")
    
    # 참고자료 텍스트 추가 (기존 방식)
    reference_context = ""
    if st.session_state.get('reference_pdfs'):
        reference_texts = []
        for filename, text in st.session_state.reference_pdfs.items():
            # 각 참고자료에서 앞부분 2000자만 사용 (토큰 절약)
            reference_texts.append(f"[{filename}]\n{text[:2000]}")
        
        reference_context = "\n\n**참고자료 (경쟁사/산업 분석 자료):**\n" + "\n\n---\n\n".join(reference_texts)
    
    try:
        prompt = f"""다음 기업 데이터를 바탕으로 전문적인 기업 분석 보고서를 작성하세요.

**PDF에서 추출된 데이터:**
{available_data_text}

**PDF에 없는 정보:** {missing_fields_text}

{rag_context}

{reference_context}

**보고서 작성 지침:**
{report_template}

**보고서:**"""
        
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": """당신은 기업 분석 전문가입니다. 
제공된 데이터를 바탕으로 체계적이고 전문적인 분석 보고서를 작성합니다.

**출처 표시 규칙 (필수):**
1. PDF에서 추출한 원본 데이터: `[출처: 메인 PDF]`
   예: "2023년 매출은 100억원입니다. [출처: 메인 PDF]"

2. 참고자료에서 가져온 정보: `[출처: 참고자료 - 파일명]`
   예: "경쟁사 A의 시장점유율은 30%입니다. [출처: 참고자료 - 산업분석.pdf]"

3. PDF 데이터를 분석/추론한 내용: `[분석: 메인 PDF 기반]`
   예: "영업이익률이 16%로 이자보상능력이 양호할 것으로 판단됩니다. [분석: 메인 PDF 기반]"

4. AI 학습 데이터 기반 일반 지식: `[출처: AI 학습 데이터 (2023년 10월 기준)]`
   예: "AI 산업은 기술 변화가 빠른 특성이 있습니다. [출처: AI 학습 데이터 (2023년 10월 기준)]"

5. PDF + AI 지식을 종합 분석: `[분석: 종합 판단]`
   예: "안정적 수익성을 보유하나 경쟁 심화로 모니터링이 필요합니다. [분석: 종합 판단]"

**중요:**
- 모든 문장에 반드시 출처를 명시하세요
- [추정], [예상] 같은 애매한 표현 사용 금지
- 출처가 명확하지 않으면 해당 내용을 작성하지 마세요

투자자와 대출 심사역이 읽기에 적합한 형식으로 작성합니다."""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"❌ OpenAI API 오류: {str(e)}"

# 타이틀
st.markdown("""
<div style='
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px 40px;
    border-radius: 20px;
    margin-bottom: 30px;
    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    text-align: center;
'>
    <div style='
        font-size: 32px;
        font-weight: 800;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        margin-bottom: 8px;
        letter-spacing: -1px;
    '>
        기업 분석 보고서 생성기
    </div>
    <div style='
        font-size: 15px;
        color: rgba(255, 255, 255, 0.95);
        font-weight: 500;
        letter-spacing: 0.5px;
    '>
        ✨ AI 기반 자동 정보 추출 및 전문 보고서 작성 시스템
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("")

# 사이드바 - 템플릿 설정
with st.sidebar:
    st.header("📝 템플릿 설정")
    
    # 이전 분석 불러오기
    if supabase_client:
        st.markdown("---")
        with st.expander("📂 이전 분석 불러오기"):
            companies = load_companies_list()
            if companies:
                company_names = [f"{c['company_name']} ({c['created_at'][:10]})" for c in companies]
                selected = st.selectbox("기업 선택", ["선택하세요..."] + company_names)
                
                if selected != "선택하세요...":
                    idx = company_names.index(selected)
                    company_id = companies[idx]["id"]
                    
                    if st.button("불러오기", type="primary"):
                        loaded_data = load_company_data(company_id)
                        if loaded_data:
                            st.session_state.extracted_data = loaded_data
                            st.success("✅ 데이터 로드 완료!")
                            st.rerun()
            else:
                st.info("저장된 분석이 없습니다.")
        st.markdown("---")
    
    # 추천 키워드
    st.subheader("🎯 추천 키워드")
    
    categories = {
        "🏢 기업 기본 정보": [
            ("회사명", "텍스트"), ("기업명", "텍스트"), ("법인명", "텍스트"), ("설립일", "텍스트"),
            ("본사 위치", "텍스트"), ("대표이사", "텍스트"), ("CEO", "텍스트"), ("직원 수", "텍스트"),
            ("계열사", "텍스트"), ("업종", "텍스트"), ("산업분류", "텍스트"), ("기업 규모", "텍스트")
        ],
        "💰 재무정보": [
            ("매출액", "숫자"), ("영업이익", "숫자"), ("영업이익률", "숫자"), ("순이익", "숫자"),
            ("EBITDA", "숫자"), ("부채비율", "숫자"), ("현금흐름", "숫자"), ("ROE", "숫자"),
            ("CAPEX", "숫자"), ("전년 대비 증감", "숫자"), ("YoY", "숫자"), ("분기 실적", "숫자")
        ],
        "🏭 사업구조 & 제품": [
            ("사업분야", "텍스트"), ("주요 제품", "텍스트"), ("핵심 기술", "텍스트"), ("경쟁우위", "텍스트"),
            ("시장 점유율", "텍스트"), ("고객사", "텍스트"), ("유통 구조", "텍스트"), ("플랫폼", "텍스트")
        ],
        "⚔️ 경쟁환경": [
            ("경쟁사", "텍스트"), ("시장 규모", "텍스트"), ("시장 성장률", "텍스트"), ("진입장벽", "텍스트"),
            ("SWOT 분석", "텍스트"), ("규제 이슈", "텍스트"), ("산업 트렌드", "텍스트"), ("CAGR", "텍스트")
        ],
        "⚠️ 주요 리스크": [
            ("재무 리스크", "텍스트"), ("운영 리스크", "텍스트"), ("공급망 리스크", "텍스트"), ("기술 리스크", "텍스트"),
            ("규제 리스크", "텍스트"), ("환율 영향", "텍스트"), ("법적 이슈", "텍스트"), ("ESG 리스크", "텍스트")
        ],
        "🚀 기회 요인 & 전략": [
            ("신규 사업", "텍스트"), ("M&A", "텍스트"), ("투자 계획", "텍스트"), ("글로벌 진출", "텍스트"),
            ("R&D", "텍스트"), ("신제품 출시", "텍스트"), ("ESG 전략", "텍스트"), ("수익성 개선", "텍스트")
        ]
    }
    
    for category, keywords in categories.items():
        with st.expander(category):
            cols = st.columns(2)
            for idx, (kw, ftype) in enumerate(keywords):
                col = cols[idx % 2]
                if col.button(f"➕ {kw}", key=f"add_{category}_{kw}", use_container_width=True):
                    if not any(f['name'] == kw for f in st.session_state.template):
                        st.session_state.template.append({"name": kw, "type": ftype})
                        st.rerun()
    
    st.markdown("---")
    st.subheader("✏️ 직접 추가")
    
    with st.form("add_field_form"):
        field_name = st.text_input("필드 이름", placeholder="예: 회사이름")
        field_type = st.selectbox("데이터 타입", ["텍스트", "숫자"])
        submitted = st.form_submit_button("➕ 필드 추가", use_container_width=True)
        
        if submitted and field_name:
            if not any(f['name'] == field_name for f in st.session_state.template):
                st.session_state.template.append({"name": field_name, "type": field_type})
                st.rerun()
            else:
                st.warning(f"'{field_name}'은(는) 이미 추가되어 있습니다")
    
    col1, col2 = st.columns(2)
    if col1.button("📋 예시 로드", use_container_width=True):
        st.session_state.template = [
            {"name": "회사이름", "type": "텍스트"},
            {"name": "대표이름", "type": "텍스트"},
            {"name": "사업분야", "type": "텍스트"},
            {"name": "연매출", "type": "숫자"},
        ]
        st.rerun()
    
    if col2.button("🗑️ 초기화", use_container_width=True):
        st.session_state.template = []
        st.rerun()

# 메인 영역
tab1, tab2, tab3 = st.tabs(["📋 템플릿 목록", "🔍 데이터 추출", "📄 보고서 생성"])

with tab1:
    st.subheader("📋 현재 템플릿 목록")
    
    if st.session_state.template:
        st.markdown(f"**총 {len(st.session_state.template)}개 필드**")
        
        # 버튼 스타일로 표시 (추천 키워드처럼)
        cols = st.columns(4)  # 한 줄에 4개
        for idx, field in enumerate(st.session_state.template):
            col = cols[idx % 4]
            type_icon = "🔢" if field['type'] == "숫자" else "📝"
            
            with col:
                # 키워드명과 X 버튼을 한 줄로 표시
                button_col1, button_col2 = st.columns([4, 1])
                with button_col1:
                    st.markdown(f"""
                    <div style='
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 10px 15px;
                        border-radius: 12px;
                        font-size: 13px;
                        font-weight: 500;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        margin-bottom: 10px;
                        text-align: left;
                    '>
                        {type_icon} {field['name']}
                    </div>
                    """, unsafe_allow_html=True)
                with button_col2:
                    if st.button("✕", key=f"delete_{idx}", help="삭제", use_container_width=True):
                        st.session_state.template.pop(idx)
                        st.rerun()
    else:
        st.info("템플릿이 비어있습니다. 왼쪽 사이드바에서 키워드를 추가하세요.")

with tab2:
    st.subheader("🔍 데이터 추출")
    st.info("PDF 파일을 업로드하고 AI가 자동으로 정보를 추출합니다")
    
    # 메인 PDF 업로드
    st.markdown("### 📄 기업 보고서 (필수)")
    uploaded_file = st.file_uploader("기업 사업보고서 PDF 업로드", type=['pdf'], key="main_pdf")
    
    # 참고자료 PDF 업로드 (RAG)
    st.markdown("---")
    st.markdown("### 📚 참고자료 추가 (선택)")
    st.info("💡 경쟁사 자료, 산업 리포트, 시장 분석 자료 등을 추가하면 더 정확한 보고서가 생성됩니다.")
    
    reference_files = st.file_uploader(
        "참고자료 PDF 업로드 (여러 개 가능)", 
        type=['pdf'], 
        accept_multiple_files=True,
        key="reference_pdfs_upload"
    )
    
    # 참고자료 처리
    if reference_files:
        st.markdown("**📋 업로드된 참고자료:**")
        for ref_file in reference_files:
            st.markdown(f"- {ref_file.name}")
    
    st.markdown("---")
    
    if uploaded_file and st.button("🚀 데이터 추출 시작", type="primary"):
        if not st.session_state.template:
            st.error("❌ 템플릿을 먼저 설정하세요! 사이드바에서 키워드를 추가하세요.")
        else:
            with st.spinner("📄 PDF 처리 중..."):
                # 메인 PDF 텍스트 추출
                pdf_text, num_pages = extract_text_from_pdf(uploaded_file, max_pages=5)
                st.session_state.pdf_text = pdf_text
                
                # 참고자료 PDF 처리
                st.session_state.reference_pdfs = {}
                if reference_files:
                    with st.spinner(f"📚 참고자료 {len(reference_files)}개 처리 중..."):
                        for ref_file in reference_files:
                            ref_text, ref_pages = extract_text_from_pdf(ref_file, max_pages=10)
                            if ref_text:
                                st.session_state.reference_pdfs[ref_file.name] = ref_text
                                st.success(f"✅ {ref_file.name} 처리 완료 ({ref_pages}페이지, {len(ref_text)}자)")
                
                if pdf_text:
                    st.success(f"✅ 메인 PDF {num_pages}페이지 처리 완료 (총 {len(pdf_text)}자 추출)")
                    
                    # 배치 방식으로 키워드 추출 (토큰 절감)
                    with st.spinner("🔍 데이터 추출 중..."):
                        field_names = [field['name'] for field in st.session_state.template]
                        extracted_data = extract_all_keywords_batch(pdf_text, field_names)
                        st.session_state.extracted_data = extracted_data
                    
                    # Supabase에 저장
                    if supabase_client:
                        with st.spinner("💾 Supabase에 저장 중..."):
                            company_name = extracted_data.get("회사명") or extracted_data.get("기업명") or "Unknown"
                            company_id = save_to_supabase(
                                company_name=company_name,
                                pdf_file=uploaded_file,
                                extracted_text=pdf_text,
                                extracted_data=extracted_data
                            )
                            if company_id:
                                st.success("✅ Supabase 저장 완료!")
                    
                    # 결과 표시 - Gradio 스타일로
                    st.markdown("---")
                    st.markdown("## ✅ 처리 완료!")
                    st.markdown("### 🤖 AI가 자동으로 추출한 정보")
                    
                    # 추출된 데이터를 카드 형식으로 표시
                    for field in st.session_state.template:
                        value = extracted_data.get(field['name'], "정보 없음")
                        st.markdown(f"**📌 {field['name']}**")
                        st.markdown(f"""
                        <div style='padding: 10px; background: white; border-radius: 8px; 
                        margin-bottom: 15px; border: 1px solid #e2e8f0;'>
                        {value}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 원본 텍스트 표시
                    st.markdown("---")
                    st.markdown("### 📄 추출된 원본 텍스트 (처음 1000자)")
                    st.markdown(f"""
                    <div style='background: #f8fafc; padding: 15px; border-radius: 8px; 
                    font-family: monospace; font-size: 13px; line-height: 1.6; 
                    max-height: 400px; overflow-y: auto;'>
                    {pdf_text[:1000]}...
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ PDF에서 텍스트를 추출할 수 없습니다.")
    
    # 이미 추출된 데이터가 있으면 표시
    elif st.session_state.extracted_data and st.session_state.pdf_text:
        st.markdown("---")
        st.markdown("## ✅ 처리 완료!")
        st.markdown("### 🤖 AI가 자동으로 추출한 정보")
        
        for field in st.session_state.template:
            value = st.session_state.extracted_data.get(field['name'], "정보 없음")
            st.markdown(f"**📌 {field['name']}**")
            st.markdown(f"""
            <div style='padding: 10px; background: white; border-radius: 8px; 
            margin-bottom: 15px; border: 1px solid #e2e8f0;'>
            {value}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📄 추출된 원본 텍스트 (처음 1000자)")
        st.markdown(f"""
        <div style='background: #f8fafc; padding: 15px; border-radius: 8px; 
        font-family: monospace; font-size: 13px; line-height: 1.6; 
        max-height: 400px; overflow-y: auto;'>
        {st.session_state.pdf_text[:1000]}...
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.subheader("📄 보고서 생성")
    st.info("AI가 추출한 데이터를 바탕으로 전문 보고서를 자동 생성합니다")
    
    if not st.session_state.extracted_data:
        st.warning("⚠️ 먼저 '데이터 추출' 탭에서 PDF 데이터를 추출하세요.")
    else:
        st.markdown("### 📊 추출된 데이터 확인")
        for key, value in st.session_state.extracted_data.items():
            st.markdown(f"**{key}**: {value}")
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("📋 보고서 미리보기", type="secondary"):
                with st.spinner("✨ OpenAI로 보고서 생성 중..."):
                    try:
                        report = generate_report_with_openai(
                            st.session_state.extracted_data
                        )
                        
                        # 참고자료 정보 추가
                        if st.session_state.get('reference_pdfs'):
                            ref_list = list(st.session_state.reference_pdfs.keys())
                            report += f"\n\n---\n\n**📚 참고자료 목록:**\n"
                            for ref_file in ref_list:
                                report += f"- {ref_file}\n"
                        
                        # 보고서를 세션에 저장
                        st.session_state.report = report
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 보고서 생성 실패: {str(e)}")
        
        with col2:
            if st.button("📄 보고서 생성 (DOCX)", type="primary"):
                if 'report' not in st.session_state or not st.session_state.report:
                    st.error("❌ 먼저 '보고서 미리보기' 버튼으로 보고서를 생성하세요.")
                else:
                    try:
                        # DOCX 생성
                        doc = Document()
                        
                        # 제목
                        title = doc.add_heading('기업 분석 보고서', 0)
                        title.alignment = 1  # 중앙 정렬
                        
                        # 작성일
                        date_para = doc.add_paragraph(f'작성일: {datetime.now().strftime("%Y년 %m월 %d일")}')
                        date_para.alignment = 1
                        doc.add_paragraph('')
                        
                        # 보고서 내용 파싱 및 추가
                        lines = st.session_state.report.split('\n')
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # 제목 처리 (## 시작)
                            if line.startswith('## '):
                                doc.add_heading(line.replace('## ', ''), 1)
                            elif line.startswith('### '):
                                doc.add_heading(line.replace('### ', ''), 2)
                            # 볼드 처리 (**텍스트**)
                            elif line.startswith('**') and line.endswith('**'):
                                p = doc.add_paragraph()
                                p.add_run(line.strip('*')).bold = True
                            # 리스트 처리
                            elif line.startswith('- ') or line.startswith('* '):
                                doc.add_paragraph(line[2:], style='List Bullet')
                            # 일반 문단
                            else:
                                doc.add_paragraph(line)
                        
                        doc.add_paragraph('')
                        doc.add_paragraph('─' * 50)
                        doc.add_paragraph('')
                        
                        # 추출된 데이터 테이블
                        doc.add_heading('📋 추출된 상세 데이터', 1)
                        
                        table = doc.add_table(rows=1, cols=2)
                        table.style = 'Light Grid Accent 1'
                        
                        hdr = table.rows[0].cells
                        hdr[0].text = '항목'
                        hdr[1].text = '내용'
                        
                        for key, val in st.session_state.extracted_data.items():
                            row = table.add_row().cells
                            row[0].text = key
                            row[1].text = str(val)
                        
                        # 파일 저장
                        output_path = "기업_분석_보고서.docx"
                        doc.save(output_path)
                        
                        # 다운로드 버튼 제공
                        with open(output_path, "rb") as file:
                            st.download_button(
                                label="📥 보고서 다운로드",
                                data=file,
                                file_name=f"기업_분석_보고서_{datetime.now().strftime('%Y%m%d')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        
                        st.success("✅ DOCX 보고서가 생성되었습니다!")
                        
                    except Exception as e:
                        st.error(f"❌ DOCX 생성 실패: {str(e)}")
        
        with col3:
            if st.button("⚙️ 템플릿", help="보고서 작성 지침 수정"):
                st.session_state.show_template_editor = not st.session_state.show_template_editor
                st.rerun()
        
        # 보고서 템플릿 편집기
        if st.session_state.show_template_editor:
            st.markdown("---")
            st.markdown("### ⚙️ 보고서 섹션 선택")
            st.info("💡 원하는 보고서 섹션을 선택하세요. 선택한 섹션만 보고서에 포함됩니다.")
            
            # 모든 섹션 체크박스
            available_sections = [
                "기업 개요",
                "사업 구조 및 Revenue Model 분석",
                "산업 및 시장 분석",
                "재무 요약",
                "재무 건전성 심화 분석",
                "고객사 및 매출 집중도 분석",
                "경쟁사 비교 분석",
                "경영진 역량 및 지배구조 분석",
                "신용도 및 법률 리스크",
                "리스크 요인",
                "종합 평가"
            ]
            
            # 2열로 배치
            cols = st.columns(2)
            selected_sections = []
            
            for idx, section in enumerate(available_sections):
                col = cols[idx % 2]
                with col:
                    is_selected = st.checkbox(
                        section,
                        value=section in st.session_state.report_sections,
                        key=f"section_{section}"
                    )
                    if is_selected:
                        selected_sections.append(section)
            
            col_save, col_reset = st.columns(2)
            with col_save:
                if st.button("💾 선택 저장", type="primary", use_container_width=True):
                    st.session_state.report_sections = selected_sections
                    st.success(f"✅ {len(selected_sections)}개 섹션이 선택되었습니다!")
            
            with col_reset:
                if st.button("🔄 전체 선택", use_container_width=True):
                    st.session_state.report_sections = available_sections.copy()
                    st.success("✅ 모든 섹션이 선택되었습니다!")
                    st.rerun()
            
            # 선택된 섹션 미리보기
            if selected_sections:
                with st.expander("📋 선택된 섹션 미리보기", expanded=False):
                    for section in selected_sections:
                        st.markdown(f"**✓ {section}**")
                        if section in REPORT_SECTION_TEMPLATES:
                            st.text(REPORT_SECTION_TEMPLATES[section])
                        st.markdown("---")
        
        # 생성된 보고서가 있으면 항상 표시
        if 'report' in st.session_state and st.session_state.report:
            st.markdown("---")
            st.markdown("### 📄 생성된 보고서")
            st.markdown(st.session_state.report)


