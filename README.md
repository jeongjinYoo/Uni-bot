# Uni-Bot

2026 ICT 한이음 드림업 프로젝트에서 개발한 대학 학사 규정 안내 챗봇 서버 코드입니다.
RAG(Retrieval-Augmented Generation)와 Self-RAG 기법을 활용하여, 학칙·규정집 기반 질의응답과 근거 조항의 원문 하이라이팅을 제공하는 듀얼 뷰 웹 애플리케이션을 구현하였습니다.

## 프로젝트 소개

대학 학칙·규정집을 학습해서 학생 질문에 답변하는 RAG 기반 챗봇입니다.
답변 근거(조항)를 원문 PDF 페이지와 함께 보여주는 듀얼 뷰 UI를 제공합니다.

## 개발 배경

학칙과 학사 안내 문서는 분량이 많고 조항이 흩어져 있어, 학생이 필요한 규정을 직접 찾기 어렵습니다.
일반 LLM 챗봇은 학교별 규정을 모르거나 그럴듯한 오답을 만들 수 있어 학사 안내에 그대로 쓰기 어렵습니다.
Uni-Bot은 학교 문서에서 근거를 찾아 답하고, 그 근거를 원문 위에 직접 보여줍니다.

## 시연
[![시연 영상](https://img.youtube.com/vi/영상ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=5LZM0tI3TYU)

## 시스템 구성 및 아키텍처

```
[오프라인: 문서 전처리·적재]

 학사 안내 PDF ──▶ Upstage Document Parse API ──▶ 제목 경로 기반 청킹 ──▶ 청크 JSON
 (data/raw)        (50쪽 단위 분할 호출, 응답 캐시)   (pdf_service.py)            │
                                                     · 표지/목차/반복 머리말 제거  │
                                                     · 제목 + 본문 병합            ▼
                                                     · 표 → "헤더: 값" 변환   ko-sroberta 임베딩
                                                                              ──▶ ChromaDB (코사인)

[온라인: 질의응답]

 React (학생 듀얼 뷰 / 관리자)
   │  ChatScreen ── 질문 ─────────▶ FastAPI  POST /api/chat
   │                                 ① 동의어 질의 확장 (synonyms.py)
   │                                 ② 하이브리드 검색: semantic 50% + keyword 50% (rag_service.py)
   │                                 ③ 최소 점수 필터, 청크 ID 중복 제거 → Top-3 근거
   │                                 ④ OpenAI 답변 생성 (answer_service.py)
   │                                 ⑤ Self-RAG 검증: 근거 점수 < 0.7 이면 답변 차단
   │                                 ⑥ 출처를 (문서, 페이지) 단위로 묶어 반환
   │                                 ⑦ 채팅 이력 저장 (SQLite / PostgreSQL)
   │  ◀── 답변 + 출처 칩 ─────────────┘
   ▼
 PdfViewer ── 출처 칩 클릭 시 원문 PDF 해당 페이지로 이동, 근거 구간 하이라이트
```

| 구성 요소 | 역할 | 주요 파일 |
| --- | --- | --- |
| 프론트엔드 | 학생용 듀얼 뷰(채팅 + 원문 PDF), 관리자 대시보드(문서 관리·검증 로그·신뢰도 분석 등) | `frontend/src/App.jsx`, `components/ChatScreen.jsx`, `components/PdfViewer.jsx`, `pages/` |
| API 서버 | 채팅·검색·채팅 이력·문서 업로드/목록 API, 서버 시작 시 임베딩 모델 warm-up | `backend/app/main.py` |
| 문서 전처리 | Upstage 파싱 결과에서 제목 경로를 만들어 청크 앞에 붙이고, 표를 텍스트로 변환 | `app/services/pdf_service.py`, `app/utils/table_parser.py` |
| 검색 (RAG) | 임베딩·ChromaDB 적재, 동의어 확장 + 하이브리드 검색 | `app/services/rag_service.py`, `app/services/synonyms.py` |
| 답변 생성 / Self-RAG | 근거 기반 답변 생성, 답변–근거 일치 검증 및 차단 | `app/services/answer_service.py` |
| 데이터 저장 | 벡터 DB(ChromaDB), 채팅 이력·문서 정보(SQLAlchemy ORM) | `chroma_db/`, `app/db.py`, `app/models.py` |
| 평가 스크립트 | 체크리스트 Top-N 검색 평가, 청킹 비교, Self-RAG 거부율 평가 | `backend/scripts/`, `backend/evaluation/`, `backend/experiments/` |

### 프로젝트 구조

```
unibot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 엔트리포인트 (라우트, 출처 묶기, 채팅 이력)
│   │   ├── db.py, models.py        # DB 연결, ChatLog / Document 모델
│   │   ├── services/
│   │   │   ├── pdf_service.py      # Upstage 파싱 + 제목 경로 청킹
│   │   │   ├── rag_service.py      # 임베딩, ChromaDB 적재, 하이브리드 검색
│   │   │   ├── synonyms.py         # 동의어 사전 (질의 확장)
│   │   │   └── answer_service.py   # OpenAI 답변 생성, Self-RAG 검증
│   │   ├── utils/table_parser.py   # HTML 표 → 텍스트 변환
│   │   └── Core/                   # 설정, 로거
│   ├── scripts/                    # 추출·평가·실험 스크립트
│   ├── evaluation/                 # 질문 체크리스트, 평가 결과
│   ├── experiments/                # 실험 보고서
│   ├── data/                       # 원본 PDF(raw), 전처리 청크(processed)
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx                 # 학생/관리자 화면 전환, 듀얼 뷰 레이아웃
        ├── components/             # ChatScreen, PdfViewer, 공통 Header
        ├── pages/                  # 홈, 관리자 대시보드 하위 페이지
        ├── api/                    # 백엔드 API 호출 (axios)
        └── styles/
```

## 성과 및 평가

### 검색 정확도

20개 표준 질의 × 표현 3종(완전문장/구어체/키워드형) = 60건
판정: 정답 키워드를 모두 포함한 청크가 Top-3 안에 있으면 PASS (`scripts/check_questions_auto.py`)

| 단계 | PASS |
| --- | --- |
| 개선 전 청킹 | 32/60 (53.3%) |
|   • 제목 경로 청킹 (`pdf_service.py`) | 38/60 (63.3%) |
|   • 중복 제거 기준을 청크 ID로 변경 | **43/60 (71.7%)** |
- 같은 60개 질의로 설계·평가하여 과적합 가능성이 있으며, 새 질의에 대한 일반화는 추가 검증 예정

### 표 검색

표 관련 질의 10개 + 비표 질의 5개

| 지표 | 결과 |
| --- | --- |
| Top-1 적중률 | 6/10 (60%) |
| Top-3 포함률 | 7/10 (70%) |
| 오탐 (비표 질의에 표가 1위) | 0/5 |

### 다중 학교 필터링

`school_id` 필터 적용 시 타 학교 데이터 섞임 0건 (더미 학교 3개로 검증)

### Self-RAG 답변 거부율

- 스크립트: `backend/scripts/evaluate_refusal_rate.py`
- 테스트셋: `backend/evaluation/refusal_testset.csv`
- 결과: 〔측정값〕
### 하이브리드 검색 비율

10개 학사 질의로 semantic : keyword 비율별 Top-1 정확도를 비교해 50:50을 채택했습니다.

| semantic : keyword | Top-1 정확도 |
|---|---|
| 100 : 0 | 5/10 (50%) |
| 85 : 15 | 6/10 (60%) |
| 70 : 30 | 6/10 (60%) |
| **50 : 50** | **7/10 (70%)** |

학칙은 학점·기한·자격요건처럼 수치와 용어가 정확히 일치해야 하는 문서라 keyword 비중을 높일수록 정확도가 올랐고, 표현이 다른 질문에 대응하기 위해 semantic도 50%를 유지했습니다.


## 개발 환경

| 항목 | 내용 |
| --- | --- |
| OS | Ubuntu 24.04 LTS, Windows |
| 런타임 | Python 3.13, Node.js 24 |
| 데이터베이스 | ChromaDB 1.5 (로컬 영속 저장), SQLite (기본) / PostgreSQL (`DATABASE_URL`로 전환) |
| 외부 API | OpenAI API (답변 생성·Self-RAG 검증, 기본 `gpt-4o-mini`), Upstage Document Parse API (PDF 파싱) |
| 실행 포트 | 백엔드 `localhost:8000`, 프론트엔드 `localhost:5173` |

## 개발 언어

| 영역 | 언어 |
| --- | --- |
| 백엔드 / AI | Python |
| 프론트엔드 | JavaScript (JSX), HTML, CSS |

## 개발 도구 / 라이브러리

### 개발 도구

| 도구 | 용도 |
| --- | --- |
| Visual Studio Code | 코드 편집 |
| GitLab | 버전 관리, 협업 |
| venv, pip | Python 가상환경·패키지 관리 |
| npm, Vite | 프론트엔드 패키지 관리, 개발 서버·빌드 |
| ESLint | 프론트엔드 코드 검사 |
| Swagger UI (`/docs`) | API 테스트 |

### 백엔드 라이브러리

| 라이브러리 | 용도 |
| --- | --- |
| FastAPI, Uvicorn | REST API 서버 |
| Pydantic | 요청/응답 스키마 검증 |
| python-multipart | PDF 파일 업로드 처리 |
| sentence-transformers (`jhgan/ko-sroberta-multitask`) | 한국어 문장 임베딩 |
| ChromaDB | 벡터 DB (코사인 거리 검색) |
| OpenAI Python SDK | 답변 생성, Self-RAG 검증 |
| requests | Upstage Document Parse API 호출 |
| pypdf | PDF 페이지 분할, API 없는 텍스트 추출 |
| BeautifulSoup4 | Upstage 결과의 HTML 표 파싱 |
| SQLAlchemy, psycopg2 | ORM, PostgreSQL 연결 |
| python-dotenv | 환경 변수 로드 |

### 프론트엔드 라이브러리

| 라이브러리 | 용도 |
| --- | --- |
| React 19 | UI |
| react-pdf (PDF.js) | 원문 PDF 렌더링, 근거 구간 하이라이트 |
| axios | 백엔드 API 호출 |
| Tailwind CSS, PostCSS, Autoprefixer | 스타일링 |
| lucide-react, react-icons | 아이콘 |

## 백엔드 실행 방법

```bash
cd backend
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 http://localhost:8000/docs 접속

### 환경 변수

`backend/.env` 파일을 만들고 아래 값을 채워주세요.

```
OPENAI_API_KEY=       # /api/chat 답변 생성에 사용 (answer_service.py)
UPSTAGE_API_KEY=      # PDF 파싱(pdf_service.py)에서 사용
```

```
답변 생성에 사용할 OpenAI 모델명
예: gpt-4o, gpt-4o-mini
OPENAI_MODEL=gpt-4o-mini

Self-RAG 검증에 사용할 OpenAI 모델명
예: gpt-4o-mini (저비용 검증용)
OPENAI_VERIFICATION_MODEL=gpt-4o-mini

Self-RAG 임계값 (0.0 ~ 1.0)
검증 score가 이 값보다 낮으면 근거 부족으로 차단
SELF_RAG_THRESHOLD=0.7
```

### 데이터 적재 (PDF → ChromaDB)

```bash
cd backend

# 1. PDF를 파싱해서 청크 JSON 만들기
python -m app.services.pdf_service data/raw/guide.pdf --school-id konkuk

# 2. 청크 JSON을 ChromaDB에 넣기
python -c "from app.services.rag_service import ingest_json; ingest_json('data/processed/konkuk/extracted_exp.json', reset=True)"
```

- 결과 파일은 `data/processed/<학교ID>/extracted_exp.json`에 저장됩니다.
- Upstage 파싱 결과는 캐시되어, 다시 실행해도 API를 재호출하지 않습니다. 새로 파싱하려면 `--force`를 붙이세요.
- `reset=True`는 기존 데이터를 지우고 새로 넣습니다. 다른 학교 데이터를 **추가**할 때는 `reset=False`로 실행하세요.

### 임베딩 모델 Warm-up 성능 비교

- Warm-up 적용 전: 첫 `/api/chat` 응답 시간 ≈ 15초 (모델 로드가 첫 요청 중에 발생)
- Warm-up 적용 후: 첫 `/api/chat` 응답 시간 ≈ 5초 (서버 시작 시 모델 로드, 첫 요청은 바로 검색/답변)

## 프론트엔드 실행 방법

```bash
cd frontend
npm install
npm run dev
```

## 주요 API

| Method | Path          | 설명                                       |
| ------ | ------------- | ------------------------------------------ |
| GET    | `/health`     | 서버 상태 및 적재된 청크 수 확인           |
| POST   | `/api/search` | ChromaDB 검색 결과만 확인 (답변 생성 없이) |
| POST   | `/api/chat`   | 검색 + 답변 생성을 포함한 채팅 API         |

## 팀 구성

| 담당   | 역할           |
| ------ | -------------- |
| 한다영 | Frontend       |
| 조한익 | Backend        |
| 이지은 | AI / Self-RAG  |
| 신예진 | OCR / Infra    |
| 유정진 | RAG 파이프라인 |