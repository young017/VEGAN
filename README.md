# <span style="color:#1b5e20">이오 (EcoVeganism Chatbot)</span> — 기술 문서

> 배포 주소: https://veganism.streamlit.app/

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [모듈 상세 설명](#4-모듈-상세-설명)
5. [데이터 파이프라인](#5-데이터-파이프라인)
6. [환경 설정](#6-환경-설정)
7. [배포 가이드](#7-배포-가이드)
8. [알려진 제한사항](#8-알려진-제한사항)

---

## 1. 시스템 개요

이오(EcoVeganism Chatbot)는 Streamlit 기반의 AI 챗봇으로, 사용자가 업로드한 식품 라벨 이미지를 분석하여 개인화된 비건 정보와 환경 영향을 제공한다.

**핵심 기능:**

| 기능 | 설명 |
|------|------|
| OCR 분석 | Google Cloud Vision API를 통한 식품 라벨 텍스트 추출 |
| RAG 질의응답 | FAISS 벡터 DB 기반 문서 검색 및 LLM 답변 생성 |
| 비건 적합성 판단 | 사용자 식이 유형(프루테리언 / 비건 / 락토 / 오보 / 락토오보)에 따른 성분 분석 |
| 환경 영향 계산 | AGRIBALYSE LCA 데이터 기반 환경 영향 지표 및 mPt 점수 산출 |
| 칼로리 추적 | 세션 내 칼로리 누적 합산 |

---

## 2. 시스템 아키텍처

### 2.1 페이지 라우팅 구조

```
main.py
├── start.py        ← 시작 페이지 (GET STARTED 버튼)
├── infoslide.py    ← 사용자 정보 입력 (5단계 슬라이드)
├── chatbot.py      ← 메인 챗봇 기능
└── info.py         ← 사용자 정보 수정
```

`st.session_state.page` 값에 따라 페이지가 전환된다. Streamlit의 멀티페이지 기능을 사용하지 않고 단일 진입점(`main.py`)에서 직접 라우팅을 제어하는 구조다.

### 2.2 챗봇 응답 처리 흐름

```
사용자 입력 (prompt)
        │
        ▼
종료 인사 감지 ──(인사말)──► 고정 응답 반환
        │
        ▼
칼로리 총합 요청 감지 ──────► session_state["calorie_scores"] 합산
        │
        ▼
환경 점수 계산 요청 감지 ────► calculate_environmental_impact_with_score()
        │
        ▼
키워드 필터링 ─(비관련 질문)─► 안내 메시지 반환
        │
        ▼
환경 영향 질문 감지 ─────────► calculate_environmental_impact()
        │                             │
        │                    FAISS 검색 → 문서 필터링
        │                    → 유사도 계산(difflib) → DataFrame 반환
        ▼
RAG 체인 실행
        │
        ├── analyze_question_type()  → 관련 문서 종류 결정
        ├── FAISS Retriever          → 벡터 유사도 검색
        ├── 수동 source 필터링        → 문서 타입별 분리
        └── ChatPromptTemplate       → LLM 입력 구성
        │
        ▼
GPT 질문 유형 분류 (v / a / n / e)
        │
        ▼
유형별 GPT 프롬프트 재구성 → 부연 설명 생성
        │
        ▼
최종 응답 = RAG 답변 + GPT 부연 설명
        │
        ▼
칼로리 저장 (g 단위 포함 시 store_score_from_response())
```

---

## 3. 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| UI Framework | Streamlit | 1.45.1 |
| LLM | OpenAI GPT (ChatOpenAI) | latest |
| Embeddings | text-embedding-3-large | latest |
| Vector Store | FAISS (faiss-cpu) | 1.7.4 |
| OCR | Google Cloud Vision API | ≥3.5.0 |
| RAG Framework | LangChain / LangChain Community | latest |
| Data Processing | Pandas, NumPy | NumPy 1.26.4 |
| 환경 관리 | python-dotenv | latest |

---

## 4. 모듈 상세 설명

### 4.1 `main.py` — 라우터

```python
st.session_state.page  # "start" | "infoslide" | "chatbot" | "info"
```

세션 상태에 저장된 `page` 값을 읽어 해당 모듈의 `show()` 함수를 호출한다. 별도의 URL 라우팅 없이 단일 앱 인스턴스 내에서 뷰를 교체하는 방식이다.

---

### 4.2 `start.py` — 시작 페이지

인라인 CSS로 반응형 레이아웃을 구성한다. "GET STARTED" 버튼 클릭 시 `st.session_state.page = "infoslide"`로 전환된다.

주요 스타일 변수:

| CSS 클래스 | 역할 |
|-----------|------|
| `.background` | 전체 배경 영역 (연두색 `#f0f9f4`) |
| `.title` | 메인 타이틀 (진한 초록 `#1b5e20`) |
| `.subtitle` | 부제목 |
| `.footer` | 하단 고정 저작권 표시 |

---

### 4.3 `infoslide.py` — 사용자 정보 입력

5단계 슬라이드 방식으로 사용자 프로필을 수집한다.

| 단계 | 수집 정보 | 입력 방식 |
|-----|----------|----------|
| 1 | 이름 | `st.text_input` |
| 2 | 성별 | 버튼 (남성 / 여성) |
| 3 | 나이 | `st.selectbox` (1–100) |
| 4 | 비건 유형 | 버튼 (5종 선택) |
| 5 | 알러지 | `st.text_input` |

완료 시 `st.session_state.user_info`에 딕셔너리 형태로 저장되고 `chatbot` 페이지로 전환된다.

진행률 바는 `step / total_steps * 100` 퍼센트로 HTML 커스텀 렌더링된다.

---

### 4.4 `chatbot.py` — 핵심 챗봇 모듈

#### 주요 함수

**`detect_text(image_path: str) -> str`**

Google Cloud Vision API를 사용해 이미지에서 텍스트를 추출한다. 서비스 계정 인증은 Streamlit Secrets에서 `google_credentials` 딕셔너리를 읽어 임시 JSON 파일로 저장하는 방식으로 처리된다.

```
이미지 파일 → Vision ImageAnnotatorClient → text_annotations[0].description
```

**`analyze_question_type(prompt: str) -> str | list | None`**

키워드 기반으로 질문 유형을 분류하고 참조할 문서 이름을 반환한다.

| 키워드 | 반환값 |
|-------|--------|
| 성분, 분석 | `"식품표시기준.pdf"` |
| 비건, 식이범위 | `"식이범위.pdf"` |
| 알러지, 알레르기 | `"알러지.pdf"` |
| 환경 영향 | `"AGRIBALYSE.csv"` |
| 수자원 | `["수자원문서.pdf"]` |
| 칼로리 | `"칼로리.pdf"` |

**`calculate_environmental_impact(prompt, ocr_text) -> pd.DataFrame | None`**

1. FAISS Retriever로 관련 문서 검색
2. `metadata.source` 기준으로 수동 필터링 (FAISS는 검색 시 필터 미지원)
3. `match_food_subgroup_from_prompt()`로 식품군 매칭
4. `difflib.SequenceMatcher`로 OCR 텍스트와 제품명 유사도 계산
5. 가장 유사한 제품의 환경 영향 데이터를 DataFrame으로 반환

**`calculate_environmental_impact_with_score(prompt) -> str | None`**

사용자가 제공한 환경 영향 수치를 파싱하여 mPt 단위의 종합 환경 점수를 계산한다.

```
점수 = Σ (value / NF) × weight × 1000
```

`impact_factors` 딕셔너리에 16개 영향 범주의 정규화 계수(NF)와 가중치(weight)가 정의되어 있다.

**`store_score_from_response(response, expected_gram)`**

GPT 응답에서 정규식으로 칼로리 수치를 추출하고 `st.session_state["calorie_scores"]` 리스트에 누적 저장한다.

```
패턴: r'{expected_gram}\s*g\s*당.*?(\d+(?:\.\d+)?)\s*(?:kcal|칼로리)'
```

---

### 4.5 FAISS 벡터스토어 초기화

```
faiss_db_merged.zip
        │
        ▼ (압축 해제, 최초 1회)
faiss_db_merged/
        │
        ▼ (이중 구조 감지 시 내부 경로로 이동)
FAISS.load_local(persist_dir, OpenAIEmbeddings("text-embedding-3-large"))
        │
        ▼
st.session_state["vectorstore"]
```

세션 내 최초 1회만 로드되며 이후에는 세션 상태에서 재사용된다.

---

### 4.6 RAG 체인 구성

```python
rag_chain = (
    RunnableMap({
        "question":     RunnablePassthrough(),
        "ocr_text":     RunnablePassthrough(),
        "context_docs": lambda input: "\n\n".join(doc.page_content for doc in filtered_docs),
    })
    | ChatPromptTemplate.from_template(...)
    | ChatOpenAI(temperature=1)
    | StrOutputParser()
)
```

FAISS의 필터링 미지원으로 인해, Retriever로 검색한 결과를 `doc.metadata["source"]`로 수동 필터링한 후 컨텍스트로 주입하는 방식을 채택하고 있다.

---

## 5. 데이터 파이프라인

### 5.1 벡터 DB 구성 문서

`faiss_db_merged.zip`에 포함된 문서 목록:

| 파일명 | 내용 | 활용 |
|-------|------|------|
| `식품표시기준.pdf` | 식품 성분 표시 기준 | 성분 분석 질의 |
| `식이범위.pdf` | 비건 식이 범위 | 비건 적합성 판단 |
| `알러지.pdf` | 알레르기 유발 성분 | 알레르기 정보 제공 |
| `AGRIBALYSE.csv` | LCA 기반 환경 영향 데이터 | 환경 영향 계산 |
| `수자원문서.pdf` | 수자원 영향 정보 | 수자원 관련 질의 |
| `칼로리.pdf` | 칼로리 정보 | 칼로리 질의 |

### 5.2 AGRIBALYSE 환경 영향 범주

총 4개 대범주, 16개 세부 지표:

| 대범주 | 세부 지표 |
|-------|----------|
| 생물학적 영향 | 독성(비암성), 독성(발암성) |
| 대기 영향 | 기후 변화(CO₂), 오존층 파괴, 이온화 방사선, 광화학적 오존 형성, 미세먼지 |
| 토지 영향 | 산성화, 육상 부영양화, 토지 사용, 화석 자원 고갈, 광물 자원 고갈 |
| 수자원 영향 | 담수 부영양화, 해양 부영양화, 생태 독성 |

---

## 6. 환경 설정

### 6.1 필수 API 키

| 키 | 용도 |
|----|------|
| `OPENAI_API_KEY` | ChatOpenAI, OpenAIEmbeddings |
| `google_credentials` | Google Cloud Vision API 서비스 계정 JSON |

### 6.2 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. .env 파일 생성
OPENAI_API_KEY=sk-...

# 3. Streamlit secrets 설정 (~/.streamlit/secrets.toml)
[default]
OPENAI_API_KEY = "sk-..."

[google_credentials]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n..."
client_email = "...@....iam.gserviceaccount.com"
# ... 기타 필드

# 4. 실행
streamlit run main.py
```

### 6.3 벡터 DB 경로 설정

`chatbot.py:413–414`에 배포 환경 기준 절대 경로가 하드코딩되어 있다.

```python
zip_path     = "/mount/src/-veganismchatbot/faiss_db_merged.zip"
persist_dir  = "/mount/src/-veganismchatbot/faiss_db_merged"
```

로컬 실행 시에는 상대 경로(`./faiss_db_merged.zip`)로 변경이 필요하다.

---

## 7. 배포 가이드

이 프로젝트는 **Streamlit Community Cloud**를 통해 배포된다.

### 배포 절차

1. GitHub 저장소에 코드 푸시
2. [https://share.streamlit.io](https://share.streamlit.io) 에서 저장소 연결
3. **Main file path**: `main.py`
4. **Secrets** 설정 (Streamlit Cloud 대시보드 → App settings → Secrets):

```toml
[default]
OPENAI_API_KEY = "sk-..."

[google_credentials]
type = "service_account"
project_id = "your-project-id"
...
```

5. `faiss_db_merged.zip`은 저장소에 포함되어야 한다 (배포 환경에서 `/mount/src/` 하위에 위치).

---

## 8. 알려진 제한사항

| 항목 | 내용 |
|------|------|
| FAISS 필터링 미지원 | `search_kwargs`에 `filter` 파라미터 사용 불가. 검색 후 `metadata["source"]`로 수동 필터링 필요 |
| 벡터 DB 경로 하드코딩 | 배포 환경(`/mount/src/`) 기준 절대 경로 사용. 로컬 실행 시 수동 변경 필요 |
| 대화 기억 범위 | `ConversationBufferMemory`는 전체 대화를 메모리에 유지하므로, 장시간 사용 시 토큰 초과 가능 |
| 칼로리 저장 조건 | GPT 응답 텍스트에서 정규식으로 파싱하는 방식이므로, 응답 포맷이 달라지면 저장 실패 |
| 단일 비건 유형 선택 | 현재 UI에서 비건 유형을 1가지만 선택 가능 (복수 선택 미지원) |
| 식품군 매칭 | 한국어 키워드 완전 일치 방식. 표기 변형이나 오타 처리 없음 |

---

<br>

**이오(EcoVeganism Chatbot)** — 사람과 지구 모두에게 이로운 선택
