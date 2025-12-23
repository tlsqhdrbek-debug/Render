# 📊 로깅 시스템 가이드

## 개요
사용자별 테스트 로그를 자동으로 수집하고 분석할 수 있는 시스템입니다.

## 기능
1. **사용자 세션 추적** - 사용자별로 모든 작업 기록
2. **단계별 로그** - PDF 업로드 → 키워드 추출 → 보고서 생성
3. **에러 추적** - 에러 발생 시 스택 트레이스 자동 저장
4. **실행 시간 측정** - 각 단계별 성능 모니터링

## 📋 Supabase 설정

### 1. SQL 실행
`supabase_setup.sql` 파일을 Supabase SQL Editor에서 실행하세요.

추가된 테이블:
- `test_users` - 테스트 사용자 정보
- `test_sessions` - 테스트 세션 (성공/실패 여부)
- `activity_logs` - 상세 활동 로그

### 2. 환경 변수 설정
`.env` 파일에 다음을 추가:
```
ADMIN_PASSWORD=your-secure-password-here
```

## 👤 사용자 관점

### 앱 사용 시작
1. 앱 접속 시 사이드바에서 **사용자 정보 입력**
   - 이름 (필수)
   - 이메일 (선택)
2. "시작하기" 버튼 클릭

### 자동 로깅되는 정보
- PDF 업로드 (파일명, 페이지 수, 처리 시간)
- 키워드 추출 (추출된 필드 개수, 실행 시간)
- 보고서 생성 (섹션 수, 실행 시간)
- 에러 발생 시 전체 스택 트레이스

## 🔧 관리자 기능

### 관리자 페이지 접근
1. "관리자" 탭 클릭
2. 비밀번호 입력 (기본값: `admin123`)

### 제공되는 기능

#### 📊 통계
- 총 사용자 수
- 총 세션 수
- 성공/실패 세션 수
- 성공률

#### 👥 사용자 목록
- 사용자별 세션 이력
- 사용자별 성공/실패 현황

#### 📋 로그 조회 및 다운로드
1. **필터링**
   - 전체 로그
   - 세션 로그만
   - 활동 로그만
   - 에러만

2. **CSV 다운로드**
   - 세션 로그 CSV
   - 활동 로그 CSV
   - 전체 다운로드

## 📥 로그 다운로드 및 분석

### CSV 파일 구조

#### session_logs.csv
```csv
id,user_id,session_id,company_name,pdf_filename,started_at,completed_at,status,error_message,total_execution_time_ms
```

#### activity_logs.csv
```csv
id,session_id,step,status,details,execution_time_ms,created_at
```

### 로그 단계별 의미

| Step | 설명 |
|------|------|
| `user_login` | 사용자 로그인 |
| `pdf_upload` | PDF 업로드 및 처리 |
| `keyword_extraction` | 키워드 추출 |
| `data_extraction` | 데이터 추출 |
| `data_save` | Supabase 저장 |
| `report_generation` | 보고서 생성 |
| `error` | 일반 에러 |

### Status 값
- `started` - 작업 시작
- `success` - 작업 성공
- `failed` - 작업 실패

## 🐛 디버깅 워크플로우

### 1. 에러 발생 시
1. 관리자 페이지에서 "에러만" 필터 선택
2. 해당 에러의 `details` 확인
3. `stack_trace` 확인하여 원인 파악

### 2. CSV 다운로드 → 전달
```bash
# 관리자 페이지에서 다운로드한 CSV 파일
activity_logs_20251222_153045.csv
session_logs_20251222_153045.csv
```

파일을 GitHub Copilot에 첨부하면:
- 에러 패턴 분석
- 성능 병목 지점 파악
- 개선 방안 제안

## 📊 로그 예시

### 정상 실행 로그
```json
{
  "session_id": "abc123",
  "step": "pdf_upload",
  "status": "success",
  "details": {
    "filename": "company_report.pdf",
    "pages": 45,
    "text_length": 125000
  },
  "execution_time_ms": 3500
}
```

### 에러 로그
```json
{
  "session_id": "abc123",
  "step": "keyword_extraction",
  "status": "failed",
  "details": {
    "error_type": "OpenAIError",
    "error_message": "API key invalid",
    "stack_trace": "Traceback (most recent call last):\n..."
  },
  "execution_time_ms": 150
}
```

## 🔍 모니터링 지표

### 성능 지표
- **평균 PDF 처리 시간**: 목표 < 5초
- **평균 키워드 추출 시간**: 목표 < 10초
- **평균 보고서 생성 시간**: 목표 < 30초

### 안정성 지표
- **성공률**: 목표 > 90%
- **에러율**: 목표 < 10%

## 💡 팁

### 성능 개선 힌트
```sql
-- Supabase SQL Editor에서 느린 쿼리 확인
SELECT step, AVG(execution_time_ms) as avg_time
FROM activity_logs
WHERE status = 'success'
GROUP BY step
ORDER BY avg_time DESC;
```

### 에러 빈도 확인
```sql
SELECT step, COUNT(*) as error_count
FROM activity_logs
WHERE status = 'failed'
GROUP BY step
ORDER BY error_count DESC;
```

## 🚨 주의사항
1. **개인정보 보호**: 사용자 이메일은 선택사항
2. **로그 크기**: 정기적으로 오래된 로그 삭제 권장 (3개월 이상)
3. **성능**: 로그가 많으면 조회 속도 저하 가능 (인덱스 설정됨)

## 📞 문제 해결

### Supabase 연결 안 됨
- `.env` 파일의 `SUPABASE_URL`, `SUPABASE_KEY` 확인
- Supabase 프로젝트가 활성화되어 있는지 확인

### 로그가 기록되지 않음
- `supabase_setup.sql` 실행 확인
- 테이블이 생성되었는지 Supabase 대시보드에서 확인

### 관리자 페이지 접근 안 됨
- `.env` 파일의 `ADMIN_PASSWORD` 확인
- 기본값: `admin123`
