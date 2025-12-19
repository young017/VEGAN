from langchain_community.vectorstores import FAISS  # ✅ FAISS용 모듈
import zipfile
import os
import streamlit as st
import tempfile
import io
import atexit
import pandas as pd
import re
from google.cloud import vision
from dotenv import load_dotenv
import base64
import difflib
from langchain_openai import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableMap, RunnableLambda, RunnablePassthrough
import streamlit as st
from dotenv import load_dotenv
import os
import json
import tempfile
from google.oauth2 import service_account
from google.cloud import vision
import io


def show():
    
    # 환경 변수 로드
    load_dotenv()
    openai_key = st.secrets["OPENAI_API_KEY"]
    
    # google_credentials를 dict로 변환
    creds_info = dict(st.secrets["google_credentials"])
    
    # 임시 JSON 파일 생성
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        json.dump(creds_info, f)  # 🔥 여기서 dict만 가능
        f.flush()
        credentials = service_account.Credentials.from_service_account_file(f.name)

    def get_image_base64(image_path):
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded}"

    # 말풍선 스타일 함수 (아이콘 추가)
    def chat_message(role, message):
        if role == "user":
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end; align-items: flex-end; margin: 5px 0;">
                    <div style="background-color: #DCF8C6; padding: 10px 15px; 
                                border-radius: 15px 15px 0px 15px; max-width: 70%;
                                font-size: 16px; word-wrap: break-word;">
                        {message}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            image_base64 = get_image_base64("제목.png")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-start; align-items: flex-start; margin: 5px 0;">
                    <img src="{image_base64}" width="45" height="45" style="margin-right: 8px; border-radius: 50%;">
                    <div style="background-color: #FFFFFF; padding: 10px 15px; 
                                border-radius: 15px 15px 15px 0px; max-width: 70%;
                                border: 1px solid #ddd; font-size: 16px; 
                                word-wrap: break-word;">
                        {message}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Chroma DB를 안전하게 종료하기 위한 함수 정의
    def close_vectorstore():
        if "vectorstore" in st.session_state:
            print("✅ FAISS vectorstore는 별도 종료할 필요가 없습니다.")


    # 프로그램 종료 시 close_vectorstore 함수가 자동으로 호출되도록 등록
    atexit.register(close_vectorstore)

    def detect_text(image_path):
        client = vision.ImageAnnotatorClient(credentials=credentials)
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
    
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
    
        if response.error.message:
            raise Exception(f"Google Vision API 오류: {response.error.message}")
    
        texts = response.text_annotations
        if not texts:
            return ""
    
        return texts[0].description

    # 질문 유형 분석 함수
    def analyze_question_type(prompt):
        if "성분" in prompt or "분석" in prompt:
            return "식품표시기준.pdf"
        elif "식이 범위" in prompt or "식이범위" in prompt or "비건" in prompt:
            return "식이범위.pdf"
        elif "알러지" in prompt or "알레르기" in prompt:
            return "알러지.pdf"
        elif "환경 영향" in prompt or "환경영향" in prompt:
            return "AGRIBALYSE.csv"
        elif "수자원" in prompt or "수자원 영향" in prompt:
            return [
                "수자원문서.pdf"
            ]
        elif "일일 섭취량" in prompt or "칼로리" in prompt:
            return "칼로리.pdf"
        return None

    # 식품 하위 그룹
    FOOD_SUBGROUP_LIST = [
        "조리 보조 식품", "해조류", "조미료", "특별한 식이를 위한 식품", "향신료", "허브", "기타 재료", 
        "소스", "소금류", "유아용 시리얼 및 비스킷", "유아용 짠 이유식 및 식사류", "페이스트리와 다른 애피타이저", 
        "피자, 타르트, 그리고 크레페", "혼합요리", "채식 요리", "혼합 샐러드와 생야채", "샌드위치", "수프", 
        "기타 지방류", "버터", "어유 (생선기름)", "식물성 기름 및 지방", "마가린", "아침용 시리얼과 비스킷", 
        "밀가루와 반죽", "파스타, 쌀 및 곡물", "기타 육류 제품", "가공육", "생물과 갑각류", "계란", "날 생선", 
        "익힌 생선", "생선 및 해산물 가공 제품", "육가공품 대체품", "육류 대체품", "생고기", "익힌 고기", 
        "크림 및 크림 기반 특수 식품", "치즈", "우유", "신선한 유제품 및 유사 제품", "과일", "견과류 및 유지종자", 
        "채소", "콩류", "감자 및 기타 뿌리채소"
    ]

    # 환경 영향 범주별 관련 column 정의
    impact_categories = {
        "생물학적 영향": [
            "인간 건강에 미치는 독성 영향: 비암성 물질(제품 당 CTUh/kg)",
            "인간 건강에 미치는 독성 영향: 발암 물질(제품 당 CTUh/kg)",
        ],
        "대기 영향": [
            "기후 변화(제품 당 CO2 eq/kg)",
            "오존층 파괴(제품 당 CVC11 eq/kg)",
            "이온화 방사선(제품 당 U-235 eq/kg)",
            "오존의 광화학적 형성(제품 당 NMVOC eq/kg)",
            "미세 먼지(제품 당 질병 발생률/kg)",
        ],
        "토지 영향": [
            "육상 및 담수 산성화(제품 당 H+ eq/kg)",
            "육상 부영양화(제품 당 N eq/mol)",
            "토지 사용(제품 당 Pt/kg)",
            "화석 자원 고갈(제품 당 MJ/kg)",
            "광물 자원 고갈(제품 당 Sb eq/kg)",
        ],
        "수자원 영향" : [
            "담수의 부영양화(제품 당 P eq/kg)",
            "해양의 부영양화(제품 당 N eq/kg)",
            "담수 수생 생태계에 대한 생태 독성(제품 당 CTUe/kg)",
        ]
    }

    impact_factors = {
        "육상 및 담수 산성화(제품 당 H+ eq/kg)": {"nf": 55.56954123, "weight": 6.2},
        "기후 변화(제품 당 CO2 eq/kg)": {"nf": 7553.083163, "weight": 21.06},
        "담수 수생 생태계에 대한 생태 독성(제품 당 CTUe/kg)": {"nf": 56716.58634, "weight": 1.92},
        "담수의 부영양화(제품 당 P eq/kg)": {"nf": 1.606852128, "weight": 2.8},
        "해양의 부영양화(제품 당 N eq/kg)": {"nf": 19.54518155, "weight": 2.96},
        "육상 부영양화(제품 당 N eq/mol)": {"nf": 176.7549998, "weight": 3.71},
        "인간 건강에 미치는 독성 영향: 발암 물질(제품 당 CTUh/kg)": {"nf": 1.73E-05, "weight": 2.13},
        "인간 건강에 미치는 독성 영향: 비암성 물질(제품 당 CTUh/kg)": {"nf": 0.000129, "weight": 1.84},
        "이온화 방사선(제품 당 U-235 eq/kg)": {"nf": 4220.16339, "weight": 5.01},
        "토지 사용(제품 당 Pt/kg)": {"nf": 819498.1829, "weight": 7.94},
        "오존층 파괴(제품 당 CVC11 eq/kg)": {"nf": 0.052348383, "weight": 6.31},
        "미세 먼지(제품 당 질병 발생률/kg)": {"nf": 0.000595, "weight": 8.96},
        "오존의 광화학적 형성(제품 당 NMVOC eq/kg)": {"nf": 40.85919773, "weight": 4.78},
        "화석 자원 고갈(제품 당 MJ/kg)": {"nf": 65004.25966, "weight": 8.32},
        "광물 자원 고갈(제품 당 Sb eq/kg)": {"nf": 0.063622615, "weight": 7.55},
        "수자원 고갈(제품 당 m3 depriv./kg)": {"nf": 11468.70864, "weight": 8.51}
    }

    # 사용자 입력(prompt_text)에서 식품 하위 그룹(FOOD_SUBGROUP_LIST)을 추출하는 함수
    def match_food_subgroup_from_prompt(prompt_text):
        # FOOD_SUBGROUP_LIST에 있는 각 서브그룹을 순회
        for subgroup in FOOD_SUBGROUP_LIST:
            # 입력 텍스트에 해당 서브그룹 이름이 포함되어 있는지 대소문자 무시하고 확인
            if subgroup.lower() in prompt_text.lower():
                return subgroup  # 일치하는 서브그룹이 있으면 반환
        return None  # 일치하는 항목이 없으면 None 반환

    # 영향 카테고리별 열 추출 함수
    def extract_impact_columns(prompt):
        # 환경 영향 카테고리를 순차적으로 확인하여 해당 카테고리의 열을 반환
        for category, columns in impact_categories.items():  # impact_categories 딕셔너리 순회
            if category in prompt:  # 현재 카테고리명이 prompt에 포함되어 있으면
                return columns  # 해당 카테고리에 대응하는 열 목록 반환
        return []  # 일치하는 카테고리가 없으면 빈 리스트 반환 (오류 방지용 기본값)


    def calculate_environmental_impact(prompt, ocr_text):
        # 벡터 DB에서 "AGRIBALYSE.csv" 문서만 검색
        vectorstore = st.session_state["vectorstore"]

        # '환경 영향' 키워드가 포함된 질문만 처리
        document_name = analyze_question_type(prompt)

        print(f"문서 이름: {document_name}")

        if not document_name:
            no_match_response = (
                "❗죄송합니다. 해당 질문은 현재 지원하지 않습니다.\n"
                "다음과 같은 주제로 질문해 주세요:\n"
                "- 성분 분석, 비건 종류, 알레르기, 환경 영향, 수자원, 칼로리 등"
            )
            chat_message("assistant", no_match_response)
            st.session_state["memory"].chat_memory.add_ai_message(no_match_response)
            st.session_state.messages.append({"role": "assistant", "content": no_match_response})
            return None

        # FAISS에서는 search_kwargs에 filter 사용 불가 → 검색 후 수동 필터링
        retriever = vectorstore.as_retriever()
        relevant_docs = retriever.get_relevant_documents(prompt)

        # 문서 이름 기반 필터링 (ex: 'AGRIBALYSE.csv'만 선택)
        if isinstance(document_name, str):
            relevant_docs = [doc for doc in relevant_docs if doc.metadata.get("source") == document_name]
        elif isinstance(document_name, list):
            relevant_docs = [doc for doc in relevant_docs if doc.metadata.get("source") in document_name]

        print(f"관련 문서: {[doc.metadata.get('product_name') for doc in relevant_docs]}")

        # 식품군 필터링
        subgroup = match_food_subgroup_from_prompt(prompt)
        if subgroup:
            relevant_docs = [doc for doc in relevant_docs if doc.metadata.get('food_subgroup') == subgroup]

        print(f"식품군 필터링된 문서: {[doc.metadata.get('product_name') for doc in relevant_docs]}")

        # OCR 텍스트 기반 유사도 비교
        matching_docs = []
        for doc in relevant_docs:
            product_name = doc.metadata.get("product_name", "")
            similarity = difflib.SequenceMatcher(None, ocr_text, product_name).ratio()
            matching_docs.append((similarity, doc))

        print(f"유사도 계산된 문서: {[(doc[1].metadata.get('product_name'), doc[0]) for doc in matching_docs]}")

        matching_docs.sort(reverse=True, key=lambda x: x[0])
        if not matching_docs:
            print("유사한 문서를 찾을 수 없습니다.")
            return None

        most_similar_doc = matching_docs[0][1]
        print(f"가장 유사한 문서: {most_similar_doc.metadata.get('product_name')}")

        # 환경 영향 항목 추출
        selected_cols = extract_impact_columns(prompt)
        print(f"선택된 환경 영향 항목: {selected_cols}")

        impact_data = []

        if most_similar_doc:
            metadata = most_similar_doc.metadata
            impact_entry = {
                'food_subgroup': metadata.get('food_subgroup'),
                'product_name': metadata.get('product_name')
            }

            for col in selected_cols:
                impact_entry[col] = metadata.get(col, None)

            impact_data.append(impact_entry)

        print(f"환경 영향 데이터: {impact_data}")

        if impact_data:
            impact_df = pd.DataFrame(impact_data)
            print(f"결과 DataFrame: {impact_df}")
            return impact_df
        else:
            print("환경 영향 데이터가 없습니다.")
            return None
        

    def extract_values_from_prompt(prompt):
        print(f"입력된 prompt: {prompt}")
        items_values = re.findall(r"([^\-]+) - ([0-9.+E\-]+)", prompt)
        print(f"추출된 항목과 값: {items_values}")
        return items_values

    def get_user_inputs(prompt):
        print(f"처리할 prompt: {prompt}")
        items_values = extract_values_from_prompt(prompt)
        user_inputs = {}

        for item, value in items_values:
            item = item.strip()
            value = float(value)
            user_inputs[item] = value
            print(f"입력 값 저장: {item} -> {value}")

        return user_inputs

    def calculate_score(user_inputs):
        score = 0
        for factor, value in user_inputs.items():
            if factor in impact_factors:
                weight = impact_factors[factor]["weight"]
                nf = impact_factors[factor]["nf"]
                if nf != 0:
                    factor_score = (value / nf) * weight * 1000
                    score += factor_score
        return score

    # 환경 영향 계산 후 점수 계산 함수
    def calculate_environmental_impact_with_score(prompt):
        print(f"점수 계산 요청: {prompt}")  # 디버깅용 print
        if "점수" in prompt or "환경 점수" in prompt or "환경 영향 점수" in prompt:  # 점수 관련 질문만 처리
            user_inputs = get_user_inputs(prompt)  # 사용자로부터 입력값을 받음

            if user_inputs:
                # 점수 계산
                final_score = calculate_score(user_inputs)
                # 점수 결과 반환
                score_response = f"계산된 환경 영향 점수: {final_score:.6f} mPt"
                print(f"결과 반환: {score_response}")  # 디버깅용 print
                return score_response
            else:
                return "점수 계산을 위한 입력 값이 부족합니다."
        return None

    def extract_gram_from_prompt(prompt):
        # 사용자 입력에서 g 단위와 그에 해당하는 숫자를 추출 (예: "600g", "150g")
        match = re.search(r'(\d+)\s*g\s*당', prompt)
        return int(match.group(1)) if match else None

    def store_score_from_response(response, expected_gram=None):
        if "calorie_scores" not in st.session_state:
            st.session_state["calorie_scores"] = []

        if expected_gram is None:
            print("[❌ 무시됨] g 단위가 질문에 없음.")
            return

        # 예: '600g당 173kcal' 와 정확히 매칭
        pattern = fr'{expected_gram}\s*g\s*당.*?(\d+(?:\.\d+)?)\s*(?:kcal|칼로리)'  # 'g당 칼로리' 추출
        match = re.search(pattern, response)
        if match:
            score = float(match.group(1))
            st.session_state["calorie_scores"].append(score)
            print(f"[✅ 저장됨] {expected_gram}g당 {score} kcal")
            print(f"[📦 전체 목록] {st.session_state['calorie_scores']}")
        else:
            print(f"[❌ 저장 실패] 응답에 {expected_gram}g당 칼로리 정보가 없음.")


# Streamlit UI 시작----------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --- 사이드바 ---
    with st.sidebar:
        st.markdown("### 사용자 정보")
        user_info = st.session_state.get("user_info", {})
        st.markdown(f"**이름:** {user_info.get('name', '미입력')}")
        st.markdown(f"**비건 종류:** {', '.join(user_info.get('types', [])) if user_info.get('types') else '미입력'}")
        st.markdown(f"**나이:** {user_info.get('age', '미입력')}")
        st.markdown(f"**성별:** {user_info.get('gender', '미입력')}")
        st.markdown(f"**알러지:** {user_info.get('allergy', '없음')}")

        if st.button("정보 수정"):
            st.session_state.page = "info"
            st.session_state.from_chatbot = False
            st.rerun()

        uploaded_image = st.file_uploader("식품 라벨 이미지 업로드", type=["png", "jpg", "jpeg"])

    # 세션 상태 초기화
    if "memory" not in st.session_state:
        st.session_state["memory"] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        st.session_state["ocr_text"] = None
    if "calorie_answers" not in st.session_state:
        st.session_state["calorie_answers"] = []

    # 이미지 업로드 및 OCR 처리
    if uploaded_image is not None:
        if "prev_uploaded_filename" not in st.session_state or st.session_state["prev_uploaded_filename"] != uploaded_image.name:
            st.session_state["prev_uploaded_filename"] = uploaded_image.name
    
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(uploaded_image.getvalue())
                tmp_path = tmp_file.name
    
            try:
                ocr_text = detect_text(tmp_path)
                st.session_state["ocr_text"] = ocr_text
                st.session_state["ocr_done"] = True
                st.success("✅ OCR 처리 완료! 추출된 텍스트:")
                st.text_area("OCR 텍스트", ocr_text, height=300)
    
                system_message = f"아래는 식품 라벨 OCR 텍스트입니다:\n{ocr_text}"
                st.session_state["memory"].chat_memory.add_user_message(system_message)
    
            except Exception as e:
                st.error(f"OCR 처리 중 오류 발생: {e}")
                st.stop()
    
    # ✅ OCR 성공 여부와 관계없이 항상 벡터스토어 초기화
    if "vectorstore" not in st.session_state:
        zip_path = "/mount/src/-veganismchatbot/faiss_db_merged.zip"
        persist_dir = "/mount/src/-veganismchatbot/faiss_db_merged"
    
        if not os.path.exists(persist_dir):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(persist_dir)
                print(f"✅ 압축 해제 완료: {persist_dir}")
    
        inner = os.listdir(persist_dir)
        if len(inner) == 1 and os.path.isdir(os.path.join(persist_dir, inner[0])):
            persist_dir = os.path.join(persist_dir, inner[0])
            print(f"📂 이중 구조 감지 → 내부 경로로 이동: {persist_dir}")
            
        embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")
        st.session_state["vectorstore"] = FAISS.load_local(
            persist_dir,
            embedding_function,
            allow_dangerous_deserialization=True
        )
        print("✅ 벡터 DB 로드 완료 (문서 추가 없음)")
                

    # 초기 메시지 출력
    if "messages" not in st.session_state:
        st.session_state.messages = []
        chat_message("assistant", "에코 비건에 대해 무엇이든 물어보세요!")

    for msg in st.session_state.messages:
        chat_message(msg["role"], msg["content"])

    prompt = st.chat_input("질문을 입력하세요")

    if prompt:
        user_info_text = (
            f"사용자 정보:\n"
            f"- 이름: {user_info.get('name', '')}\n"
            f"- 비건 종류: {', '.join(user_info.get('types', []))}\n"
            f"- 나이: {user_info.get('age', '')}\n"
            f"- 성별: {user_info.get('gender', '')}\n"
            f"- 알러지: {user_info.get('allergy', '')}\n\n"
        )

        st.session_state.messages.append({"role": "user", "content": prompt})
        chat_message("user", prompt)


        # ✅ 종료 인사 감지 및 응답 → 즉시 return
        farewell_phrases = ["안녕", "안녕하세요", "질문"]
        if any(phrase in prompt.lower() for phrase in farewell_phrases):
            farewell_response = "안녕하세요. 비거니즘 챗봇입니다. 궁금한 것이 있으면 뭐든 물어봐주세요!"
            chat_message("assistant", farewell_response)
            st.session_state["memory"].chat_memory.add_ai_message(farewell_response)
            st.session_state.messages.append({"role": "assistant", "content": farewell_response})
            return 


        if any(p in prompt for p in ["총합", "하루", "모든 점수"]):
            total_score = sum(st.session_state.get("calorie_scores", []))
            if total_score > 0:
                response = f"지금까지 저장된 칼로리 총합은 약 {int(total_score)} kcal 입니다."
            else:
                response = "아직 칼로리 정보를 저장한 적이 없어요. 🤔"
            chat_message("assistant", response)
            st.session_state["memory"].chat_memory.add_ai_message(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.stop()

# 수정 줄 시작        
        keywords = ["수자원", "성분", "비건", "알러지", "환경 영향", "수자원", "칼로리", "식이범위", "감자칩", "환경 점수", "환경 영향 점수"]
# 수정 줄  끝


        # '점수' 키워드가 포함된 질문이면 점수 계산만 출력
        if "점수" in prompt or "환경 점수" in prompt or "환경 영향 점수" in prompt:
            result = calculate_environmental_impact_with_score(prompt)
            
            if result:  # 점수 계산 결과가 존재하면
                chat_message("assistant", result)  # 계산된 점수 출력
                st.session_state["memory"].chat_memory.add_ai_message(result)  # 계산된 결과 메모리에 추가
                st.session_state.messages.append({"role": "assistant", "content": result})  # 세션 메시지에 추가
            else:
                # 계산 값이 없을 경우
                error_message = "❗ 점수를 계산하기 위한 값이 부족합니다. 다시 시도해주세요."
                chat_message("assistant", error_message)  # 오류 메시지 출력
                st.session_state["memory"].chat_memory.add_ai_message(error_message)  # 오류 메시지 메모리에 추가
                st.session_state.messages.append({"role": "assistant", "content": error_message})  # 오류 메시지 세션에 추가
            return

        # 다른 키워드가 포함된 질문은 비건 관련 메시지 출력
        if not any(keyword in prompt for keyword in keywords):
            no_relevant_msg = (
                "죄송합니다. 해당 질문은 비거니즘에 관련된 질문이 아닙니다.😅😅 "
                "비건니즘에 관련된 질문이 있다면 언제든지 질문해주세요!"
            )
            chat_message("assistant", no_relevant_msg)  # 답변 출력
            st.session_state["memory"].chat_memory.add_ai_message(no_relevant_msg)  # 메모리에 저장
            st.session_state.messages.append({"role": "assistant", "content": no_relevant_msg})  # 세션 메시지에 추가
            return
        
        # ✅ 환경 영향 질문이 포함된 경우에만 환경 영향 계산 함수 실행
        if "환경 영향" in prompt or "환경영향" in prompt:  # 사용자가 입력한 prompt에서 '환경 영향' 또는 '환경영향'이 포함되어 있으면
            # 환경 영향 계산 함수 호출
            impact_df = calculate_environmental_impact(prompt, st.session_state["ocr_text"])  # 'calculate_environmental_impact' 함수 호출, 사용자의 질문과 OCR 텍스트를 전달하여 환경 영향 데이터 계산

            if impact_df is not None:  # 환경 영향 데이터가 정상적으로 반환되었으면
                # impact_df를 HTML 테이블로 변환하여 출력 형식 지정
                impact_response = f"<h5>환경 영향 데이터:</h5>{impact_df.to_html(index=False)}"
                chat_message("assistant", impact_response)  # assistant 역할로 생성된 환경 영향 데이터를 사용자에게 메시지로 출력
                st.session_state["memory"].chat_memory.add_ai_message(impact_response)  # 메시지를 채팅 기록에 추가
                st.session_state.messages.append({"role": "assistant", "content": impact_response})  # 메시지를 'assistant' 역할로 세션 메시지에 추가

            else:  # 만약 환경 영향 데이터가 None(빈 값)이라면
                chat_message("assistant", "❗죄송합니다. 환경 영향 데이터를 찾을 수 없습니다.")  # 데이터가 없다는 안내 메시지를 출력
            return  # 함수 실행을 종료하고, 더 이상 다른 코드가 실행되지 않도록 함
        
        if any(phrase in prompt for phrase in ["총합", "오늘", "하루", "총 점수", "전체 점수", "모든 점수"]):
            total_score = sum(st.session_state.get("calorie_scores", []))  # ✅ 수정된 부분
            if total_score > 0:
                response = f"지금까지 저장된 칼로리 총합은 약 {int(total_score)} kcal 입니다."
            else:
                response = "아직 칼로리 정보를 저장한 적이 없어요. 🤔 '(150g 당 칼로리는 몇이야?)'처럼 질문해 주세요."
            
            chat_message("assistant", response)
            st.session_state["memory"].chat_memory.add_ai_message(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            # 필요 시: 이 응답은 저장 안 해도 됨 (총합 결과이므로)
            return


        if "vectorstore" not in st.session_state or st.session_state["ocr_text"] is None:
            chat_message("assistant", "❗ 먼저 이미지 업로드 및 OCR 처리를 완료해 주세요.")
            st.stop()

        st.session_state["memory"].chat_memory.add_user_message(prompt)

        llm = ChatOpenAI(temperature=1)
        retriever = st.session_state["vectorstore"].as_retriever()

        document_name = analyze_question_type(prompt)
        if not isinstance(document_name, list):
            document_name = [document_name] if document_name else []
        document_name.append("user_ocr")  # OCR 문서 항상 포함

        # 🔍 FAISS: 검색 후 수동 필터링
        retrieved_docs = retriever.get_relevant_documents(prompt)
        filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("source") in document_name]

        # ✅ RAG 프롬프트 정의 (1번만)
        rag_prompt = ChatPromptTemplate.from_template("""
        당신은 비거니즘 관련 질문에 답하는 챗봇입니다.
        - 사용자의 비건 종류와 알러지를 고려해 최대한 정확히 답해주세요.

        사용자 질문: {question}

        OCR 텍스트: {ocr_text}

        참고 문서: {context_docs}
        """)


        # ✅ RagChain 정의 - FAISS 호환 버전
        rag_chain = (
            RunnableMap({
                "question": RunnablePassthrough(),
                "ocr_text": RunnablePassthrough(),
                "context_docs": lambda input: "\n\n".join(doc.page_content for doc in filtered_docs),
            })
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        # ✅ OCR 및 비건 관련 질문일 때만 사용자 정보를 포함
        ocr_related_keywords = ["알러지", "식이 범위", "식이범위"]
        include_user_info = any(keyword in prompt for keyword in ocr_related_keywords)

        # 사용자 정보 포함 여부에 따라 질문 구성
        question_input = (user_info_text if include_user_info else "") + "질문: " + prompt

        # ✅ 문서 검색 및 수동 필터링 (FAISS는 필터링 미지원)
        retrieved_docs = retriever.get_relevant_documents(prompt)
        filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("source") in document_name]

        # ✅ 최종 프롬프트 구성
        final_prompt = {
            "question": question_input,
            "ocr_text": st.session_state["ocr_text"],
            "context_docs": "\n\n".join(doc.page_content for doc in filtered_docs)  # 직접 텍스트로 구성
        }

        # 문서가 없거나 document_name이 None이면 예외 처리
        if document_name is None or not filtered_docs:
            unknown_response = "잘 모르겠습니다. 질문은 성분, 비건, 알러지, 환경 영향, 수자원, 칼로리 등과 관련되어야 합니다."
            chat_message("assistant", unknown_response)
            st.session_state["memory"].chat_memory.add_ai_message(unknown_response)
            st.session_state.messages.append({"role": "assistant", "content": unknown_response})
            st.stop()

        with st.spinner("Thinking..."):
            # 벡터 DB 기반 답변 생성 (이미 RagChain에서 filtered_docs를 context로 사용 중)
            answer_from_db = rag_chain.invoke(final_prompt)

        # ✅ 사용자 비건 종류에 따른 부연 설명 생성 함수
        def get_vegan_type_explanation(user_info):
            types = user_info.get("types", [])
            if not types:
                return "사용자의 비건 식단 정보를 기반으로 부연 설명을 작성해 주세요."

            type_descriptions = {
                "프루테리언": "과일, 씨앗, 견과류 중심의 식단",
                "비건": "모든 동물성 식품을 배제하는 식단",
                "오보": "달걀은 허용하지만 기타 동물성 식품은 금지되는 식단",
                "락토": "우유는 허용하지만 기타 동물성 식품은 금지되는 식단",
                "락토오보": "달걀과 우유는 허용되며 그 외 동물성 식품은 금지되는 식단",
                "페스코": "생선은 허용되지만 육류와 유제품은 금지되는 식단",
                "플렉시테리언": "가끔 동물성 식품을 섭취하는 유연한 식단"
            }

            descriptions = [type_descriptions.get(t, "") for t in types]
            description_text = " / ".join(filter(None, descriptions))

            return f"사용자는 {', '.join(types)} 식단을 따릅니다. ({description_text}) 이 식단 기준에 맞춰 부연 설명을 작성해 주세요."


        # ✅ GPT 프롬프트 구성 (초기 임시 프롬프트)
        gpt_prompt = (
            f"여기 벡터 DB 기반 성분 분석 결과가 있습니다:\n{answer_from_db}\n\n"
            f"{get_vegan_type_explanation(user_info)}"
        )

        # ✅ GPT로 질문 주제 분류
        def classify_question_with_gpt(question: str) -> str:
            classification_prompt = f"""
        다음 질문의 주제를 분류하세요. 항목: 비건(v), 알러지(a), 칼로리(n), 환경 영향(e)
        질문: "{question}"
        정답은 v, a, n, e 중 하나로만 대답하세요.
        """
            classification = llm.invoke([{"role": "user", "content": classification_prompt}]).content.strip().lower()
            return classification

        # ✅ 분류된 주제에 따라 GPT 프롬프트 재구성
        question_type = classify_question_with_gpt(prompt)

        if question_type == "v":
            gpt_prompt = (
                f"다음은 벡터 DB 기반 성분 분석 결과입니다:\n{answer_from_db}\n\n"
                f"{get_vegan_type_explanation(user_info)}"
            )
        elif question_type == "a":
            gpt_prompt = (
                f"다음 제품의 성분 정보:\n{answer_from_db}\n\n"
                f"이 제품에 알레르기 유발 성분이 있는지 설명해 주세요. "
                f"주의해야 할 알러지 유발 물질이 있다면 명확히 알려주세요."
            )
        elif question_type == "n":
            gpt_prompt = (
                f"다음 제품의 성분 정보:\n{answer_from_db}\n\n"
                f"이 제품의 칼로리 및 주요 영양 정보를 요약해 주세요. "
                f"하루 권장 섭취량과 비교해도 좋아요."
            )
        else:
            gpt_prompt = (
                f"다음 성분 정보를 바탕으로 사용자 질문에 대해 설명을 덧붙여 주세요:\n{answer_from_db}"
            )

        # ✅ GPT 모델에 프롬프트 전달 → 부연 설명 생성
        response = llm.invoke([{"role": "assistant", "content": gpt_prompt}])
        answer_from_gpt = response.content

        # ✅ 최종 응답 생성 및 출력
        combined_answer = (
            f"벡터 DB 및 OCR 기반 답변:\n{answer_from_db}\n\n"
            f"GPT 모델 기반 부연 설명:\n{answer_from_gpt}"
        )

        st.session_state.messages.append({"role": "assistant", "content": combined_answer})
        chat_message("assistant", combined_answer)

        # ✅ 여기에 조건부 저장 코드 추가
        expected_gram = extract_gram_from_prompt(prompt)

        if expected_gram:
            # GPT 기반 답변에서만 저장
            store_score_from_response(answer_from_gpt, expected_gram)

        # ✅ 문서 관련 정보도 출력 (FAISS는 수동 필터링 필요)
        retrieved_docs = retriever.get_relevant_documents(prompt)
        filtered_docs = [doc for doc in retrieved_docs if doc.metadata.get("source") in document_name]

        if filtered_docs:
            with st.expander("참고 문서"):
                for doc in filtered_docs:
                    source = doc.metadata.get("source", "출처 없음")
                    st.markdown(f"📄 **{source}**", help=doc.page_content) 
