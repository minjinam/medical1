# MediScan AI — Backend 실행 가이드

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 프론트엔드 파일 배치
cp mediscan_ai.html static/index.html

# 3. 서버 실행
python main.py
# 또는
uvicorn main:app --reload --port 8000

# 4. 브라우저에서 접속
# http://localhost:8000
```

## 프로젝트 구조

```
mediscan_backend/
├── main.py              # FastAPI 백엔드 (전체 API)
├── requirements.txt     # Python 의존성
├── README.md            # 이 파일
├── static/              # 프론트엔드 파일
│   └── index.html       # MediScan AI 앱 (mediscan_ai.html)
├── uploads/             # 처방전 이미지 업로드 (자동 생성)
└── db/                  # 사용자 데이터 JSON (자동 생성)
    └── default.json
```

## API 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 프론트엔드 서빙 |
| POST | `/api/scan` | 처방전 이미지 업로드 → OCR → HIRA DB 매칭 |
| POST | `/api/drug/search` | 약 이름 검색 (HIRA DB) |
| POST | `/api/food/analyze` | 식사 내용 분석 → 약물 상호작용 경고 |
| GET | `/api/medicines` | 등록된 약 목록 조회 |
| POST | `/api/medicines/add` | 약 추가 |
| DELETE | `/api/medicines/{id}` | 약 삭제 |
| GET | `/api/profile` | 프로필 조회 (BMI, 칼로리 포함) |
| POST | `/api/profile` | 프로필 저장 |
| POST | `/api/body-status` | 몸상태 기록 |
| GET | `/api/family-history` | 가족력 조회 |
| POST | `/api/family-history` | 가족력 추가 (AI 위험 분석 포함) |
| DELETE | `/api/family-history/{id}` | 가족력 삭제 |
| GET | `/api/risk-assessment` | AI 종합 위험 점검 |
| POST | `/api/nhis/connect` | 국민건강보험 연동 |
| POST | `/api/nhis/apply` | NHIS 데이터 → 약력/가족력 반영 |
| POST | `/api/reminder` | 복용 알림 설정 |
| POST | `/api/reminder/toggle/{id}` | 복용 완료/취소 토글 |
| GET | `/api/user-data` | 전체 사용자 데이터 (초기 로딩용) |

## API 문서 (자동 생성)

서버 실행 후:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 실제 서비스 배포 시 변경사항

### 1. OCR (처방전 인식)
현재: 시뮬레이션 텍스트 반환
변경: Google Cloud Vision API 또는 Tesseract OCR 연동

```python
# main.py의 scan_prescription() 내부
from google.cloud import vision
client = vision.ImageAnnotatorClient()
image = vision.Image(content=content)
response = client.text_detection(image=image)
ocr_text = response.text_annotations[0].description
```

### 2. LLM (AI 설명 생성)
현재: 하드코딩된 설명 텍스트
변경: Claude API 연동

```python
import anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": f"다음 약에 대해 일반인이 이해할 수 있게 설명해주세요: {drug_name}\n"
                   f"성분: {ingredient}, ATC: {atc}\n"
                   f"복용 시 주의할 음식도 알려주세요."
    }]
)
ai_description = message.content[0].text
```

### 3. HIRA 공공데이터
현재: Python dict 기반 내장 DB
변경: HIRA OpenAPI 실시간 조회 또는 PostgreSQL DB

```
보건의료빅데이터개방시스템: https://opendata.hira.or.kr
- ATC코드별 성분 통계 API
- DUR 점검 현황 API
- 질병별 의약품 통계 API
```

### 4. NHIS 연동
현재: 시뮬레이션 데이터
변경: 공공 마이데이터 포털 API 연동
- 본인인증 (PASS/공동인증서) 필요
- https://www.nhis.or.kr 건강검진 결과 조회 API

### 5. DB
현재: JSON 파일 (db/default.json)
변경: PostgreSQL + SQLAlchemy ORM

### 6. 인증
현재: user_id 파라미터 (인증 없음)
변경: JWT 토큰 기반 인증

### 7. 배포
```bash
# AWS EC2 배포 예시
# 1. EC2 인스턴스 (Ubuntu)
# 2. Nginx 리버스 프록시
# 3. SSL 인증서 (Let's Encrypt)
# 4. systemd 서비스 등록

# docker-compose.yml 구성도 가능
docker build -t mediscan .
docker run -p 8000:8000 mediscan
```
