-- 데이터 품질 검증 로그 테이블 생성
-- OCR 원본 → LLM 추출 → 보고서 생성 과정을 비교 분석하기 위한 테이블

CREATE TABLE IF NOT EXISTS public.data_quality_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_name TEXT,
    company_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 1. 선택된 추출 키워드 정보
    selected_keywords JSONB NOT NULL,  -- ["매출액", "영업이익", "회사명", ...]
    
    -- 2. OCR 원본 데이터 (Upstage Parse 결과)
    ocr_raw_text TEXT,  -- 전체 PDF 추출 텍스트
    ocr_structured_data JSONB,  -- 표, 제목 등 구조화된 데이터
    ocr_tables_count INTEGER,  -- 추출된 표 개수
    
    -- 3. LLM 추출 데이터 (각 키워드별)
    llm_extracted_data JSONB NOT NULL,  -- {"매출액": "2,345억 원", "영업이익": "551억 원", ...}
    llm_model TEXT DEFAULT 'gpt-4o-mini',
    llm_extraction_time_ms INTEGER,
    
    -- 4. 보고서 생성 데이터 (최종 output)
    report_generated BOOLEAN DEFAULT FALSE,
    report_content TEXT,  -- 생성된 보고서 전체 내용
    report_model TEXT,  -- 보고서 생성에 사용된 모델
    report_generation_time_ms INTEGER,
    
    -- 5. 품질 메트릭
    extraction_success_rate DECIMAL,  -- 추출 성공률 (정보 없음이 아닌 비율)
    keywords_with_data INTEGER,  -- 데이터가 있는 키워드 수
    keywords_missing_data INTEGER,  -- 정보 없음인 키워드 수
    
    -- 6. 기타 메타데이터
    pdf_filename TEXT,
    pdf_pages INTEGER,
    total_processing_time_ms INTEGER,
    
    -- 인덱스를 위한 필드
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES test_sessions(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_data_quality_logs_session ON public.data_quality_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_data_quality_logs_created_at ON public.data_quality_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_logs_user ON public.data_quality_logs(user_name);
CREATE INDEX IF NOT EXISTS idx_data_quality_logs_company ON public.data_quality_logs(company_name);

-- RLS (Row Level Security) 설정
ALTER TABLE public.data_quality_logs ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽을 수 있도록 (관리자 대시보드용)
CREATE POLICY "Enable read access for all users" ON public.data_quality_logs
    FOR SELECT USING (true);

-- 삽입은 인증된 사용자만
CREATE POLICY "Enable insert for authenticated users" ON public.data_quality_logs
    FOR INSERT WITH CHECK (true);

-- 주석 추가
COMMENT ON TABLE public.data_quality_logs IS 'OCR, LLM 추출, 보고서 생성 과정의 데이터 품질을 비교 분석하기 위한 로그';
COMMENT ON COLUMN public.data_quality_logs.selected_keywords IS '사용자가 선택한 추출 키워드 목록';
COMMENT ON COLUMN public.data_quality_logs.ocr_raw_text IS 'Upstage OCR로 추출한 원본 텍스트';
COMMENT ON COLUMN public.data_quality_logs.ocr_structured_data IS '표, 제목 등 구조화된 데이터 (Upstage Parse 결과)';
COMMENT ON COLUMN public.data_quality_logs.llm_extracted_data IS 'LLM이 추출한 각 키워드별 데이터';
COMMENT ON COLUMN public.data_quality_logs.report_content IS '최종 생성된 보고서 내용';
COMMENT ON COLUMN public.data_quality_logs.extraction_success_rate IS '전체 키워드 중 데이터가 성공적으로 추출된 비율';
