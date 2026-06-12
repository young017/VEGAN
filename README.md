# <span style="color:#1b5e20">이오 — EcoVeganism Chatbot</span>

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45.1-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT-412991?style=flat-square&logo=openai&logoColor=white)](https://openai.com/)
[![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-00897B?style=flat-square)](https://github.com/facebookresearch/faiss)
[![Deploy](https://img.shields.io/badge/Live-veganism.streamlit.app-success?style=flat-square)](https://veganism.streamlit.app/)

식품 라벨 이미지를 업로드하면 OCR → RAG → GPT 파이프라인을 통해 비건 적합성, 알레르기, 칼로리, 환경 영향(LCA)을 개인화된 방식으로 분석한다.

---

## 목차

1. [아키텍처](#1-아키텍처)
2. [기술 스택](#2-기술-스택)
3. [모듈 레퍼런스](#3-모듈-레퍼런스)
4. [데이터 소스](#4-데이터-소스)
5. [환경 설정](#5-환경-설정)
6. [배포](#6-배포)
7. [알려진 한계](#7-알려진-한계)

---

## 1. 아키텍처

### 페이지 라우팅

`st.session_state.page` 단일 값으로 뷰를 전환하는 **단일 진입점 라우팅** 구조다. Streamlit 멀티페이지 기능을 사용하지 않는다.

```mermaid
graph LR
    A[main.py] -->|page = start| B[start.py]
    A -->|page = infoslide| C[infoslide.py]
    A -->|page = chatbot| D[chatbot.py]
    A -->|page = info| E[info.py]
```

### 챗봇 응답 파이프라인

```mermaid
flowchart TD
    A[사용자 입력] --> B{인사말 감지}
    B -->|Yes| C[고정 응답 반환]
    B -->|No| D{칼로리 총합?}
    D -->|Yes| E[calorie_scores 합산]
    D -->|No| F{환경 점수 계산?}
    F -->|Yes| G[calculate_environmental_impact_with_score]
    F -->|No| H{키워드 필터}
    H -->|비관련| I[안내 메시지]
    H -->|관련| J{환경 영향 질문?}
    J -->|Yes| K[calculate_environmental_impact\nFAISS → difflib 유사도 → DataFrame]
    J -->|No| L[RAG 체인 실행]
    L --> M[GPT 질문 유형 분류\nv / a / n / e]
    M --> N[유형별 프롬프트 재구성]
    N --> O[최종 응답\nRAG 답변 + GPT 부연]
    O --> P{g 단위 포함?}
    P -->|Yes| Q[store_score_from_response]
```

### FAISS 초기화 흐름

```mermaid
flowchart LR
    A[faiss_db_merged.zip] -->|최초 1회 압축 해제| B[faiss_db_merged/]
    B -->|이중 구조 감지 시| C[내부 디렉토리]
    C --> D[FAISS.load_local\ntext-embedding-3-large]
    D --> E[session_state vectorstore]
```

> [!NOTE]
> FAISS는 `search_kwargs`의 `filter` 파라미터를 지원하지 않는다. 모든 문서 필터링은 검색 후 `doc.metadata["source"]`를 기준으로 수동 처리된다.

---

## 2. 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| UI | Streamlit | 1.45.1 |
| LLM | OpenAI ChatOpenAI | latest |
| Embeddings | text-embedding-3-large | latest |
| Vector Store | FAISS (faiss-cpu) | 1.7.4 |
| OCR | Google Cloud Vision API | ≥ 3.5.0 |
| RAG | LangChain / LangChain Community | latest |
| Data | Pandas / NumPy | NumPy 1.26.4 |

---

## 3. 모듈 레퍼런스

<details>
<summary><strong>main.py</strong> — 라우터</summary>

```python
st.session_state.page  # "start" | "infoslide" | "chatbot" | "info"
```

세션 상태의 `page` 값을 읽어 각 모듈의 `show()`를 호출한다.

</details>

<details>
<summary><strong>start.py</strong> — 시작 페이지</summary>

인라인 CSS 기반 레이아웃. "GET STARTED" 클릭 시 `page = "infoslide"` 전환.

| CSS 클래스 | 역할 |
|-----------|------|
| `.background` | 배경 (`#f0f9f4`) |
| `.title` | 타이틀 (`#1b5e20`) |
| `.footer` | 하단 고정 푸터 |

</details>

<details>
<summary><strong>infoslide.py</strong> — 사용자 정보 입력 (5단계)</summary>

| 단계 | 항목 | 위젯 |
|-----|------|------|
| 1 | 이름 | `st.text_input` |
| 2 | 성별 | 버튼 (남성 / 여성) |
| 3 | 나이 | `st.selectbox` (1–100) |
| 4 | 비건 유형 | 버튼 5종 |
| 5 | 알러지 | `st.text_input` |

완료 시 `st.session_state.user_info` 딕셔너리에 저장 후 `chatbot`으로 전환.

</details>

<details>
<summary><strong>chatbot.py</strong> — 핵심 챗봇 모듈 (주요 함수)</summary>

**`detect_text(image_path: str) → str`**

```
이미지 파일 → Vision ImageAnnotatorClient → text_annotations[0].description
```

Streamlit Secrets의 `google_credentials` 딕셔너리를 임시 JSON 파일로 변환해 인증한다.

---

**`analyze_question_type(prompt: str) → str | list | None`**

키워드 기반 문서 라우팅.

| 키워드 | 참조 문서 |
|-------|---------|
| 성분, 분석 | `식품표시기준.pdf` |
| 비건, 식이범위 | `식이범위.pdf` |
| 알러지, 알레르기 | `알러지.pdf` |
| 환경 영향 | `AGRIBALYSE.csv` |
| 수자원 | `수자원문서.pdf` |
| 칼로리 | `칼로리.pdf` |

---

**`calculate_environmental_impact(prompt, ocr_text) → pd.DataFrame | None`**

1. FAISS Retriever 검색
2. `metadata["source"]` 수동 필터링
3. `match_food_subgroup_from_prompt()` — 식품군 매칭
4. `difflib.SequenceMatcher` — OCR 텍스트 ↔ 제품명 유사도 계산
5. 가장 유사한 제품의 환경 영향 컬럼 추출 → DataFrame 반환

---

**`calculate_environmental_impact_with_score(prompt) → str | None`**

$$\text{score} = \sum_{i} \frac{v_i}{\text{NF}_i} \times w_i \times 1000 \quad [\text{mPt}]$$

`impact_factors` 딕셔너리에 16개 범주의 정규화 계수(NF)와 가중치(weight) 정의.

---

**`store_score_from_response(response, expected_gram)`**

정규식으로 GPT 응답에서 칼로리 수치 추출 후 `session_state["calorie_scores"]` 누적.

```
r'{gram}\s*g\s*당.*?(\d+(?:\.\d+)?)\s*(?:kcal|칼로리)'
```

---

**RAG 체인 구조**

```python
rag_chain = (
    RunnableMap({
        "question":     RunnablePassthrough(),
        "ocr_text":     RunnablePassthrough(),
        "context_docs": lambda _: "\n\n".join(doc.page_content for doc in filtered_docs),
    })
    | ChatPromptTemplate.from_template(...)
    | ChatOpenAI(temperature=1)
    | StrOutputParser()
)
```

</details>

---

## 4. 데이터 소스

### 벡터 DB 구성 (`faiss_db_merged.zip`)

| 파일 | 내용 | 활용 질의 유형 |
|------|------|--------------|
| `식품표시기준.pdf` | 식품 성분 표시 기준 | 성분 분석 |
| `식이범위.pdf` | 비건 식이 범위 | 비건 적합성 |
| `알러지.pdf` | 알레르기 유발 성분 | 알레르기 확인 |
| `AGRIBALYSE.csv` | LCA 기반 환경 영향 (프랑스 ADEME) | 환경 영향 |
| `수자원문서.pdf` | 수자원 영향 정보 | 수자원 |
| `칼로리.pdf` | 칼로리 정보 | 칼로리 |

### 환경 영향 지표 (AGRIBALYSE — 16개 범주)

| 대범주 | 지표 |
|-------|------|
| 생물학적 | 독성(비암성) · 독성(발암성) |
| 대기 | 기후변화(CO₂eq) · 오존층 파괴 · 이온화 방사선 · 광화학 오존 · 미세먼지 |
| 토지 | 산성화 · 육상 부영양화 · 토지 사용 · 화석 자원 고갈 · 광물 자원 고갈 |
| 수자원 | 담수 부영양화 · 해양 부영양화 · 생태 독성 |

---

## 5. 환경 설정

### 필수 시크릿

| 키 | 용도 |
|----|------|
| `OPENAI_API_KEY` | ChatOpenAI, OpenAIEmbeddings |
| `google_credentials` | Vision API 서비스 계정 JSON (딕셔너리) |

### 로컬 실행

```bash
pip install -r requirements.txt
streamlit run main.py
```

`~/.streamlit/secrets.toml`:

```toml
[default]
OPENAI_API_KEY = "sk-..."

[google_credentials]
type             = "service_account"
project_id       = "your-project-id"
private_key_id   = "..."
private_key      = "-----BEGIN RSA PRIVATE KEY-----\n..."
client_email     = "...@....iam.gserviceaccount.com"
```

> [!WARNING]
> `chatbot.py` 413–414행의 벡터 DB 경로가 배포 환경 기준으로 하드코딩되어 있다. 로컬 실행 시 `./faiss_db_merged.zip`으로 변경해야 한다.

---

## 6. 배포

**플랫폼:** Streamlit Community Cloud

```
1. GitHub 저장소 푸시
2. share.streamlit.io → 저장소 연결
3. Main file path: main.py
4. App settings → Secrets에 위 toml 내용 붙여넣기
```

> [!IMPORTANT]
> `faiss_db_merged.zip`이 저장소 루트에 포함되어야 한다. 배포 환경에서 `/mount/src/` 하위에 위치하므로 경로 설정에 주의한다.

---

## 7. 알려진 한계

| 항목 | 설명 |
|------|------|
| FAISS 필터 미지원 | 검색 후 `metadata["source"]` 수동 필터링 필요 |
| 경로 하드코딩 | 배포 경로(`/mount/src/`) 기준 절대 경로, 로컬 실행 시 수정 필요 |
| 토큰 버퍼 | `ConversationBufferMemory` 전체 대화 보존 → 장시간 사용 시 토큰 초과 가능 |
| 칼로리 파싱 | GPT 응답 포맷 의존 → 응답 변형 시 저장 실패 |
| 단일 비건 유형 | UI에서 복수 선택 불가 |
| 식품군 매칭 | 완전 일치 방식, 오타/표기 변형 처리 없음 |

---

**이오(EcoVeganism Chatbot)** — 사람과 지구 모두에게 이로운 선택
