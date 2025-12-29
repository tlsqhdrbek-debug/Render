-- 데이터 품질 로그 테이블에 차트/그래프 개수 컬럼 추가
-- 기존 테이블이 있는 경우 이 마이그레이션 스크립트를 실행하세요

-- 컬럼 추가 (이미 있으면 무시)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'data_quality_logs' 
        AND column_name = 'ocr_charts_count'
    ) THEN
        ALTER TABLE public.data_quality_logs 
        ADD COLUMN ocr_charts_count INTEGER DEFAULT 0;
        
        RAISE NOTICE 'Column ocr_charts_count added successfully';
    ELSE
        RAISE NOTICE 'Column ocr_charts_count already exists';
    END IF;
END $$;

-- 주석 추가
COMMENT ON COLUMN public.data_quality_logs.ocr_charts_count IS '추출된 차트/그래프 개수 (Upstage Parse 결과)';

-- 기존 데이터에 대해 0으로 초기화 (NULL 방지)
UPDATE public.data_quality_logs 
SET ocr_charts_count = 0 
WHERE ocr_charts_count IS NULL;
