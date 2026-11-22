# 이오 — EcoVeganism Chatbot

식품 라벨 이미지를 업로드하면 OCR → RAG → GPT 파이프라인을 통해 비건 적합성, 알레르기, 칼로리, 환경 영향(LCA)을 개인화된 방식으로 분석한다.

- [라이브 데모](https://veganism.streamlit.app/)

## 아키텍처

### 페이지 라우팅

`st.session_state.page` 단일 값으로 뷰를 전환하는 단일 진입점 라우팅 구조다. Streamlit 멀티페이지 기능을 사용하지 않는다. `main.py`가 `page` 값을 읽어 각 모듈의 `show()`를 호출한다.

```mermaid
graph LR
    classDef main fill:#1b5e20,stroke:#1b5e20,color:#fff,font-weight:bold
    classDef module fill:#4CAF50,stroke:#388E3C,color:#fff
    A[main.py]:::main -->|page = start| B[start.py]:::module
    A -->|page = infoslide| C[infoslide.py]:::module
    A -->|page = chatbot| D[chatbot.py]:::module
    A -->|page = info| E[info.py]:::module
```

### 챗봇 응답 파이프라인

```mermaid
flowchart TD
    classDef input  fill:#1b5e20,stroke:#1b5e20,color:#fff,font-weight:bold
    classDef decide fill:#2E7D32,stroke:#1b5e20,color:#fff
    classDef proc   fill:#4CAF50,stroke:#388E3C,color:#fff
    classDef out    fill:#A5D6A7,stroke:#4CAF50,color:#1b5e20

    A[사용자 입력]:::input --> B{인사말 감지}:::decide
    B -->|Yes| C[고정 응답 반환]:::out
    B -->|No| D{칼로리 총합?}:::decide
    D -->|Yes| E[calorie_scores 합산]:::out
    D -->|No| F{환경 점수 계산?}:::decide
    F -->|Yes| G[calculate_environmental_impact_with_score]:::proc
    F -->|No| H{키워드 필터}:::decide
    H -->|비관련| I[안내 메시지]:::out
    H -->|관련| J{환경 영향 질문?}:::decide
    J -->|Yes| K[calculate_environmental_impact\nFAISS → difflib 유사도 → DataFrame]:::proc
    J -->|No| L[RAG 체인 실행]:::proc
    L --> M[GPT 질문 유형 분류\nv / a / n / e]:::proc
    M --> N[유형별 프롬프트 재구성]:::proc
    N --> O[최종 응답\nRAG 답변 + GPT 부연]:::out
    O --> P{g 단위 포함?}:::decide
    P -->|Yes| Q[store_score_from_response]:::proc
```

### FAISS 초기화 흐름

```mermaid
flowchart LR
    classDef file   fill:#1b5e20,stroke:#1b5e20,color:#fff,font-weight:bold
    classDef proc   fill:#4CAF50,stroke:#388E3C,color:#fff
    classDef result fill:#A5D6A7,stroke:#4CAF50,color:#1b5e20,font-weight:bold

    A[faiss_db_merged.zip]:::file -->|최초 1회 압축 해제| B[faiss_db_merged/]:::proc
    B -->|이중 구조 감지 시| C[내부 디렉토리]:::proc
    C --> D[FAISS.load_local\ntext-embedding-3-large]:::proc
    D --> E[session_state vectorstore]:::result
```

## 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| UI | Streamlit | 1.45.1 |
| LLM | OpenAI ChatOpenAI | latest |
| Embeddings | text-embedding-3-large | latest |
| Vector Store | FAISS (faiss-cpu) | 1.7.4 |
| OCR | Google Cloud Vision API | ≥ 3.5.0 |
| RAG | LangChain / LangChain Community | latest |
| Data | Pandas / NumPy | NumPy 1.26.4 |

## 모듈 레퍼런스

### start.py — 시작 페이지

인라인 CSS 기반 레이아웃. "GET STARTED" 클릭 시 `page = "infoslide"`로 전환한다.

| CSS 클래스 | 역할 |
|-----------|------|
| `.background` | 배경 (`#f0f9f4`) |
| `.title` | 타이틀 (`#1b5e20`) |
| `.footer` | 하단 고정 푸터 |

### infoslide.py — 사용자 정보 입력 (5단계)

| 단계 | 항목 | 위젯 |
|-----|------|------|
| 1 | 이름 | `st.text_input` |
| 2 | 성별 | 버튼 (남성 / 여성) |
| 3 | 나이 | `st.selectbox` (1–100) |
| 4 | 비건 유형 | 버튼 5종 |
| 5 | 알러지 | `st.text_input` |

완료 시 `st.session_state.user_info` 딕셔너리에 저장 후 `chatbot`으로 전환한다.

### chatbot.py — 핵심 챗봇 모듈

**`detect_text(image_path: str) → str`**

```
이미지 파일 → Vision ImageAnnotatorClient → text_annotations[0].description
```

Streamlit Secrets의 `google_credentials` 딕셔너리를 임시 JSON 파일로 변환해 인증한다.

**`analyze_question_type(prompt: str) → str | list | None`**

질문의 키워드를 보고 참조할 문서를 정한다. 키워드와 문서의 대응은 [데이터 소스](#데이터-소스)를 참고한다.

**`calculate_environmental_impact(prompt, ocr_text) → pd.DataFrame | None`**

1. FAISS Retriever 검색
2. `metadata["source"]` 수동 필터링
3. `match_food_subgroup_from_prompt()` — 식품군 매칭
4. `difflib.SequenceMatcher` — OCR 텍스트 ↔ 제품명 유사도 계산
5. 가장 유사한 제품의 환경 영향 컬럼 추출 → DataFrame 반환

**`calculate_environmental_impact_with_score(prompt) → str | None`**

$$\text{score} = \sum_{i} \frac{v_i}{\text{NF}_i} \times w_i \times 1000 \quad [\text{mPt}]$$

`impact_factors` 딕셔너리에 범주별 정규화 계수(NF)와 가중치(weight)가 정의되어 있다.

**`store_score_from_response(response, expected_gram)`**

정규식으로 GPT 응답에서 칼로리 수치를 추출해 `session_state["calorie_scores"]`에 누적한다.

```
r'{gram}\s*g\s*당.*?(\d+(?:\.\d+)?)\s*(?:kcal|칼로리)'
```

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

## 데이터 소스

### 벡터 DB 구성 (`faiss_db_merged.zip`)

| 파일 | 내용 | 연결 키워드 |
|------|------|-----------|
| `식품표시기준.pdf` | 식품 성분 표시 기준 | 성분, 분석 |
| `식이범위.pdf` | 비건 식이 범위 | 비건, 식이범위 |
| `알러지.pdf` | 알레르기 유발 성분 | 알러지, 알레르기 |
| `AGRIBALYSE.csv` | LCA 기반 환경 영향 (프랑스 ADEME) | 환경 영향 |
| `수자원문서.pdf` | 수자원 영향 정보 | 수자원 |
| `칼로리.pdf` | 칼로리 정보 | 칼로리 |

### 환경 영향 지표 (AGRIBALYSE)

| 대범주 | 지표 |
|-------|------|
| 생물학적 | 독성(비암성) · 독성(발암성) |
| 대기 | 기후변화(CO₂eq) · 오존층 파괴 · 이온화 방사선 · 광화학 오존 · 미세먼지 |
| 토지 | 산성화 · 육상 부영양화 · 토지 사용 · 화석 자원 고갈 · 광물 자원 고갈 |
| 수자원 | 담수 부영양화 · 해양 부영양화 · 생태 독성 |

## 환경 설정

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

> **주의:** `chatbot.py` 413–414행의 벡터 DB 경로가 배포 환경(`/mount/src/`) 기준으로 하드코딩되어 있다. 로컬 실행 시 `./faiss_db_merged.zip`으로 변경해야 한다.

## 배포

플랫폼은 Streamlit Community Cloud다.

1. GitHub 저장소 푸시
2. share.streamlit.io에서 저장소 연결
3. Main file path를 `main.py`로 지정
4. App settings → Secrets에 위 toml 내용 붙여넣기

`faiss_db_merged.zip`은 저장소 루트에 포함되어야 한다.
