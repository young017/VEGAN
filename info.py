import streamlit as st

def show():
    st.markdown(
        """
        <p style="text-align:center; font-size:18px; color:#555;">
            정보 수정
        </p>
        """,
        unsafe_allow_html=True
    )

    vegan_types = {
        "프루테리언": ["fruit.png"],
        "비건": ["fruit.png", "veg.png"],
        "락토": ["fruit.png", "veg.png", "milk.png"],
        "오보": ["fruit.png", "veg.png", "egg.png"],
        "락토오보": ["fruit.png", "veg.png", "egg.png", "milk.png"]
    }


    from_chatbot = st.session_state.get("from_chatbot", False)
    user_info = st.session_state.get("user_info", {})

    # 값 가져오기 (기본값 처리 포함)
    name_val = user_info.get("name", "")
    allergy_val = user_info.get("allergy", "")
    gender_val = user_info.get("gender", "")
    age_val = user_info.get("age", "1")
    vegan_list = user_info.get("types", [])
    vegan_val = vegan_list[0] if vegan_list else vegan_types[0]

    with st.form(key="user_form"):
        name = st.text_input("이름", value=name_val, placeholder="홍길동")

        selected_type = st.radio(
            "비건 종류",
            options=vegan_types,
            index=vegan_types.index(vegan_val) if vegan_val in vegan_types else 0
        )

        age = st.selectbox(
            "나이",
            options=[str(i) for i in range(1, 101)],
            index=int(age_val) - 1 if age_val.isdigit() else 0
        )

        allergy = st.text_input("알러지", value=allergy_val)

        gender_index = ["남성", "여성"].index(gender_val) if gender_val in ["남성", "여성"] else 0
        gender = st.radio("성별", options=["남성", "여성"], index=gender_index, horizontal=True)

        submit = st.form_submit_button("제출하기")

        if submit:
            if not name:
                st.error("❗ 이름을 입력해주세요.")
            elif not selected_type:
                st.error("❗ 비건 종류를 선택해주세요.")
            else:
                st.session_state.user_info = {
                    "name": name,
                    "types": [selected_type],
                    "age": age,
                    "gender": gender,
                    "allergy": allergy
                }
                st.success("🎉 정보가 성공적으로 제출되었습니다.")
                st.session_state.page = "chatbot"
                st.session_state.from_chatbot = True
                st.rerun()
