-- 데이터 품질 로그의 session_id를 nullable로 변경
-- 이유: 탭 전환이나 페이지 새로고침 시 세션이 초기화되어도 품질 로그를 저장할 수 있도록

-- 1. 외래키 제약 조건 삭제
ALTER TABLE public.data_quality_logs 
DROP CONSTRAINT IF EXISTS fk_session;

-- 2. session_id를 nullable로 변경
ALTER TABLE public.data_quality_logs 
ALTER COLUMN session_id DROP NOT NULL;

-- 3. 외래키 제약 조건을 다시 추가 (ON DELETE SET NULL로 변경)
ALTER TABLE public.data_quality_logs 
ADD CONSTRAINT fk_session 
FOREIGN KEY (session_id) 
REFERENCES test_sessions(id) 
ON DELETE SET NULL;

-- 주석 업데이트
COMMENT ON COLUMN public.data_quality_logs.session_id IS '테스트 세션 ID (nullable - 세션 없이도 독립적으로 로그 저장 가능)';
