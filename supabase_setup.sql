-- ============================================
-- Supabase RAG 시스템 데이터베이스 설정
-- ============================================

-- pgvector 확장 활성화 (벡터 검색을 위해 필수)
CREATE EXTENSION IF NOT EXISTS vector;

-- 기존 테이블이 있다면 삭제 (주의: 데이터 손실)
-- DROP TABLE IF EXISTS document_embeddings CASCADE;
-- DROP TABLE IF EXISTS extracted_data CASCADE;
-- DROP TABLE IF EXISTS pdf_files CASCADE;
-- DROP TABLE IF EXISTS reports CASCADE;
-- DROP TABLE IF EXISTS companies CASCADE;

-- ============================================
-- 1. 기업 정보 테이블 (기존 테이블이므로 생성 안 함)
-- ============================================
-- CREATE TABLE IF NOT EXISTS companies (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     company_name TEXT NOT NULL,
--     industry TEXT,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- 인덱스 생성 (기존에 없을 경우를 대비)
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name);
CREATE INDEX IF NOT EXISTS idx_companies_created ON companies(created_at DESC);

-- ============================================
-- 2. PDF 파일 메타데이터 테이블 (기존 테이블이므로 생성 안 함)
-- ============================================
-- CREATE TABLE IF NOT EXISTS pdf_files (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
--     file_name TEXT NOT NULL,
--     file_type TEXT DEFAULT 'main',
--     storage_path TEXT,
--     file_size INTEGER,
--     extracted_text TEXT,
--     pages_count INTEGER,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- 인덱스 생성 (기존에 없을 경우를 대비)
CREATE INDEX IF NOT EXISTS idx_pdf_files_company ON pdf_files(company_id);
CREATE INDEX IF NOT EXISTS idx_pdf_files_type ON pdf_files(file_type);

-- ============================================
-- 3. 추출된 데이터 테이블 (기존 테이블이므로 생성 안 함)
-- ============================================
-- CREATE TABLE IF NOT EXISTS extracted_data (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
--     field_name TEXT NOT NULL,
--     field_value TEXT,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- 인덱스 생성 (기존에 없을 경우를 대비)
CREATE INDEX IF NOT EXISTS idx_extracted_data_company ON extracted_data(company_id);
CREATE INDEX IF NOT EXISTS idx_extracted_data_field ON extracted_data(field_name);

-- ============================================
-- 4. 보고서 테이블 (기존 테이블이므로 생성 안 함)
-- ============================================
-- CREATE TABLE IF NOT EXISTS reports (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
--     report_content TEXT,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- 인덱스 생성 (기존에 없을 경우를 대비)
CREATE INDEX IF NOT EXISTS idx_reports_company ON reports(company_id);

-- ============================================
-- 5. 임베딩 벡터 테이블 (RAG 핵심) - 새로 생성!
-- ============================================
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    file_type TEXT DEFAULT 'main', -- 'main' 또는 'reference'
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small은 1536차원
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 벡터 유사도 검색을 위한 인덱스 (HNSW 알고리즘)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON document_embeddings 
USING hnsw (embedding vector_cosine_ops);

-- 일반 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_company ON document_embeddings(company_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_file_type ON document_embeddings(file_type);

-- ============================================
-- 6. 벡터 유사도 검색 함수 (RPC)
-- ============================================
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5,
    filter_company_id uuid DEFAULT NULL,
    filter_file_type text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    company_id uuid,
    chunk_text text,
    similarity float,
    token_count integer,
    file_type text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        document_embeddings.id,
        document_embeddings.company_id,
        document_embeddings.chunk_text,
        1 - (document_embeddings.embedding <=> query_embedding) AS similarity,
        document_embeddings.token_count,
        document_embeddings.file_type
    FROM document_embeddings
    WHERE 
        (filter_company_id IS NULL OR document_embeddings.company_id = filter_company_id)
        AND (filter_file_type IS NULL OR document_embeddings.file_type = filter_file_type)
        AND (1 - (document_embeddings.embedding <=> query_embedding)) > match_threshold
    ORDER BY document_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- 7. 자동 업데이트 트리거 (updated_at)
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 8. RLS (Row Level Security) 설정 (선택사항)
-- ============================================
-- 개발 환경에서는 비활성화, 프로덕션에서는 활성화 권장
-- ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pdf_files ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE extracted_data ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 9. 테스트 사용자 테이블 (로깅 시스템)
-- ============================================
CREATE TABLE IF NOT EXISTS test_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT,
    session_id TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_test_users_session ON test_users(session_id);
CREATE INDEX IF NOT EXISTS idx_test_users_created ON test_users(created_at DESC);

-- ============================================
-- 10. 테스트 세션 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS test_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES test_users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    company_name TEXT,
    pdf_filename TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'in_progress', -- 'in_progress', 'success', 'failed'
    error_message TEXT,
    total_execution_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_test_sessions_user ON test_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_test_sessions_session ON test_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_test_sessions_status ON test_sessions(status);
CREATE INDEX IF NOT EXISTS idx_test_sessions_started ON test_sessions(started_at DESC);

-- ============================================
-- 11. 활동 로그 테이블 (상세 로그)
-- ============================================
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    step TEXT NOT NULL, -- 'pdf_upload', 'keyword_extraction', 'data_extraction', 'report_generation', 'error'
    status TEXT NOT NULL, -- 'started', 'success', 'failed'
    details JSONB, -- 추출된 데이터, 에러 상세, 스택 트레이스 등
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_session ON activity_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_step ON activity_logs(step);
CREATE INDEX IF NOT EXISTS idx_activity_logs_status ON activity_logs(status);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at DESC);

-- ============================================
-- 완료!
-- ============================================
-- 이제 다음 작업을 수행하세요:
-- 1. Supabase 대시보드에서 SQL Editor를 열기
-- 2. 이 SQL 스크립트 전체를 복사하여 붙여넣기
-- 3. "Run" 버튼을 클릭하여 실행
-- 4. Storage에서 "company-pdfs" 버킷 생성 (선택사항)
