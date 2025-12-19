# 🌱 Eco Veganism Chatbot (이오)

> **이 제품, 먹어도 될까?** - 식품 라벨 분석 및 비건 정보 제공 AI 챗봇

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45.1-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-Educational-green.svg)](LICENSE)

## 📋 프로젝트 소개

**이오(Eco Veganism Chatbot)**는 Streamlit 기반의 AI 챗봇으로, 사용자가 업로드한 식품 라벨 이미지를 분석하여 다음 정보를 제공합니다:

- ✅ **성분 분석**: 식품 표시 기준에 따른 성분 정보
- 🌿 **비건 식이 기준 확인**: 사용자의 비건 유형에 맞는 식품 여부 판단
- ⚠️ **알레르기 정보**: 알레르기 유발 성분 확인
- 📊 **칼로리 정보**: 제품의 칼로리 및 영양 정보
- 🌍 **환경 영향 분석**: LCA 기반 환경 영향 데이터 및 점수 계산

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🔍 **OCR 기반 분석** | Google Cloud Vision API를 사용한 식품 라벨 텍스트 추출 |
| 🤖 **RAG 기반 질의응답** | FAISS 벡터 데이터베이스를 활용한 지능형 문서 검색 및 답변 생성 |
| 👤 **개인화된 답변** | 사용자의 비건 유형(프루테리언, 비건, 락토, 오보, 락토오보) 및 알러지 정보를 고려한 맞춤형 분석 |
| 📈 **환경 영향 점수** | AGRIBALYSE 데이터 기반 환경 영향 분석 및 mPt 점수 계산 |
| 💾 **칼로리 추적** | 일일 칼로리 섭취량 추적 및 총합 계산 |

## 🚀 빠른 시작

### 필수 요구사항

- Python 3.8 이상
- OpenAI API 키
- Google Cloud Vision API 인증 정보
- FAISS 벡터 데이터베이스 파일 (`faiss_db_merged.zip`)

### 설치 방법

1. **저장소 클론**
```bash
git clone https://github.com/your-username/-veganismchatbot.git
cd -veganismchatbot
```

2. **의존성 설치**
```bash
pip install -r requirements.txt
```

3. **환경 변수 설정**

`.env` 파일을 생성하거나 Streamlit Secrets를 사용하세요:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_google_credentials.json
```

**Streamlit Secrets 사용 시** (`~/.streamlit/secrets.toml`):
```toml
[default]
OPENAI_API_KEY = "your_openai_api_key"

[google_credentials]
type = "service_account"
project_id = "your-project-id"
# ... 기타 인증 정보
```

4. **애플리케이션 실행**
```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501`로 접속하세요.

## 📖 사용 방법

### 1단계: 사용자 정보 입력
1. 시작 페이지에서 **"GET STARTED"** 버튼 클릭
2. 단계별로 다음 정보 입력:
   - 이름
   - 성별 (남성/여성)
   - 나이
   - 비건 종류 (프루테리언, 비건, 락토, 오보, 락토오보)
   - 알러지 정보

### 2단계: 식품 라벨 업로드
- 사이드바에서 식품 라벨 이미지 업로드 (PNG, JPG, JPEG)
- OCR 처리가 자동으로 진행됩니다

### 3단계: 질문하기
다음과 같은 질문을 할 수 있습니다:

| 질문 유형 | 예시 질문 |
|----------|----------|
| 성분 분석 | "이 제품의 성분을 분석해줘" |
| 비건 확인 | "이 제품이 비건인가요?" |
| 알레르기 | "알레르기 유발 성분이 있나요?" |
| 환경 영향 | "환경 영향은 어떤가요?" |
| 칼로리 | "150g당 칼로리는 얼마인가요?" |
| 총합 | "오늘 먹은 칼로리 총합은?" |

## 📁 프로젝트 구조

```
-veganismchatbot/
├── main.py                 # 메인 애플리케이션 진입점 (페이지 라우팅)
├── start.py                # 시작 페이지
├── infoslide.py            # 사용자 정보 입력 슬라이드
├── info.py                 # 사용자 정보 수정 페이지
├── chatbot.py              # 메인 챗봇 기능 (OCR, RAG, 환경 영향 계산)
├── test.py                 # 테스트 파일 (Chroma 벡터스토어 로드 테스트)
├── requirements.txt        # 프로젝트 의존성
├── faiss_db_merged.zip    # FAISS 벡터 데이터베이스
├── 제목.png               # 챗봇 아바타 이미지
├── 시작.jpeg              # 시작 페이지 이미지
└── README.md              # 프로젝트 문서
```

### 주요 파일 설명

#### `main.py`
- Streamlit 페이지 라우팅 담당
- 지원 페이지: `start`, `infoslide`, `chatbot`, `info`

#### `chatbot.py` (핵심 파일)
- **OCR 처리**: `detect_text()` - Google Vision API를 사용한 이미지 텍스트 추출
- **질문 분류**: `analyze_question_type()` - 질문 유형 자동 분석
- **환경 영향**: `calculate_environmental_impact()` - AGRIBALYSE 데이터 기반 분석
- **점수 계산**: `calculate_environmental_impact_with_score()` - 환경 영향 점수 계산
- **RAG 체인**: FAISS 벡터 DB 검색 → LLM 답변 생성

#### `infoslide.py`
- 단계별 사용자 정보 입력 (이름 → 성별 → 나이 → 비건 종류 → 알러지)
- 진행률 바 및 뒤로가기 기능

#### `info.py`
- 사용자 정보 수정 페이지
- 챗봇 페이지에서 접근 가능

### 데이터베이스 구성

`faiss_db_merged.zip`에 포함된 문서:
- `식품표시기준.pdf` - 식품 성분 표시 기준
- `식이범위.pdf` - 비건 식이 범위 정보
- `알러지.pdf` - 알레르기 유발 성분 정보
- `AGRIBALYSE.csv` - 환경 영향 데이터 (LCA)
- `수자원문서.pdf` - 수자원 영향 정보
- `칼로리.pdf` - 칼로리 정보

## 🛠 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **Frontend** | Streamlit 1.45.1 |
| **LLM** | OpenAI GPT (ChatOpenAI) |
| **Embeddings** | OpenAI text-embedding-3-large |
| **Vector DB** | FAISS (faiss-cpu 1.7.4) |
| **OCR** | Google Cloud Vision API |
| **RAG Framework** | LangChain, LangChain Community, LangChain OpenAI |
| **Data Processing** | Pandas, NumPy 1.26.4 |

## ⚠️ 주의사항

- **API 키 관리**: OpenAI API 키와 Google Cloud Vision API 인증 정보가 필요합니다.
- **데이터베이스**: `faiss_db_merged.zip` 파일이 프로젝트 루트에 있어야 합니다.
- **보안**: API 키는 환경 변수나 Streamlit Secrets를 통해 안전하게 관리하세요.
- **Python 버전**: Python 3.8 이상이 필요합니다.

## 🐛 문제 해결

### OCR 처리 실패
- Google Cloud Vision API 인증 정보를 확인하세요.
- 이미지 파일 형식이 올바른지 확인하세요 (PNG, JPG, JPEG).

### 벡터 데이터베이스 로드 실패
- `faiss_db_merged.zip` 파일이 존재하는지 확인하세요.
- 압축 해제 경로에 쓰기 권한이 있는지 확인하세요.

### API 키 오류
- `.env` 파일 또는 Streamlit Secrets 설정을 확인하세요.
- API 키가 유효한지 확인하세요.

## 📝 라이선스

이 프로젝트는 비거니즘 및 환경 보호를 위한 교육 목적으로 제작되었습니다.

## 👥 기여

프로젝트 개선을 위한 제안이나 버그 리포트는 이슈로 등록해주세요.

---

**이오(Eco Veganism Chatbot)** - 사람과 지구 모두에게 이로운 선택 🌱
