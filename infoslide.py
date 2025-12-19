import streamlit as st

def show():
    # 세션 상태 초기화
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "user_input" not in st.session_state:
        st.session_state.user_input = {}
    if "gender" not in st.session_state:
        st.session_state.gender = None
    if "selected_type" not in st.session_state:
        st.session_state.selected_type = None

    vegan_types = [
        "프루테리언(🍎)",
        "비건(🍎🥦)",
        "락토(🍎🥦🥛)",
        "오보(🍎🥦🍳)",
        "락토오보(🍎🥦🍳🥛)"
    ]

    steps = ["이름", "성별", "나이", "비건 종류", "알러지"]
    total_steps = len(steps)

    step = st.session_state.step

    # 진행률 바와 뒤로가기 버튼 같은 줄에 배치
    back_col, prog_col = st.columns([1, 10])
    with back_col:
        if step > 0:
            if st.button("<"):
                st.session_state.step -= 1
                st.rerun()
    with prog_col:
        percent = int((step / total_steps) * 100)
        st.markdown(f"""
            <div style="margin-top: 10px;">
                <div style="height: 25px; width: 100%; background-color: #e0e0e0; border-radius: 10px;">
                    <div style="height: 100%; width: {percent}%; background-color: #4CAF50;
                                border-radius: 10px; text-align: center; color: white;
                                font-weight: bold; line-height: 25px;">
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 말풍선 메시지 정의
    messages = {
        0: """안녕하세요! 저는 이오예요!\n 
            이오는 ‘이롭다’와 ‘오래가다’를 결합한 순한글 이름으로,\n
            사람과 지구 모두에게 이로운 선택이 오래 지속되길 바라는 마음을 담았습니다.\n
            자연을 존중하고 지속가능한 삶을 추구하는 비건 철학과,\n
            에코 라이프스타일의 가치를 지혜롭게 전하는 대화 파트너로서\n
            ‘이오’는 당신의 건강과 지구의 내일을 함께 생각합니다. """,
        1: "이름을 알려주세요.",
        2: "성별을 알려주세요.",
        3: "나이를 알려주세요.",
        4: "당신의 비건 유형을 알려주세요.",
        5: "알러지가 있다면 알려주세요.",
    }

    st.markdown("")
    st.markdown("")
    st.markdown("")

    # 이미지와 말풍선을 같은 행에 배치 (말꼬리 포함)
    spacer_col, left_col, right_col = st.columns([0.5, 1, 4])
    with left_col:
        st.image("제목.png", width=100)
    with right_col:
        st.markdown(f"""
            <div style="position: relative; display: inline-block; padding: 15px 20px;
                        border: 2px solid #ccc; border-radius: 15px;
                        font-size: 18px; color: #333; background-color: transparent;
                        margin-top: 20px; margin-left: 40px;">
                {messages[step]}
                <div style="content: ''; position: absolute; top: 20px; left: -20px;
                            width: 0; height: 0; border-top: 10px solid transparent;
                            border-bottom: 10px solid transparent;
                            border-right: 20px solid #ccc;">
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 입력 필드
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if step == 1:
            name = st.text_input("이름", placeholder="홍길동", value=st.session_state.user_input.get("name", ""))
        elif step == 2:
            st.markdown(f"**{st.session_state.user_input.get('gender', '없음')}**")
            gender_col1, gender_col2 = st.columns([0.25, 1])
            with gender_col1:
                if st.button("남성"):
                    st.session_state.gender = "남성"
                    st.session_state.user_input["gender"] = "남성"
            with gender_col2:
                if st.button("여성"):
                    st.session_state.gender = "여성"
                    st.session_state.user_input["gender"] = "여성"
        elif step == 3:
            age = st.selectbox("나이", options=[str(i) for i in range(1, 101)], index=(int(st.session_state.user_input.get("age", "1"))-1) if st.session_state.user_input.get("age") else 0)
        elif step == 4:
            st.markdown(f"**{', '.join(st.session_state.user_input.get('types', ['없음']))}**")
            for vt in vegan_types:
                if st.button(vt):
                    st.session_state.selected_type = vt
                    st.session_state.user_input["types"] = [vt]
            
        elif step == 5:
            allergy = st.text_input("알러지", placeholder="없음 또는 알러지 종류 입력", value=st.session_state.user_input.get("allergy", ""))

    # 계속하기 / 제출하기 버튼
    button_col1, spacer, button_col2 = st.columns([5, 1, 1])
    with button_col2:
        if step == 0:
            if st.button("계속하기"):
                st.session_state.step += 1
                st.rerun()
        elif step == 1:
            if st.button("계속하기"):
                if not name.strip():
                    st.warning("이름을 입력해주세요.")
                else:
                    st.session_state.user_input["name"] = name.strip()
                    st.session_state.step += 1
                    st.rerun()
        elif step == 2:
            if st.button("계속하기"):
                if st.session_state.user_input.get("gender") is None:
                    st.warning("성별을 선택해주세요.")
                else:
                    st.session_state.step += 1
                    st.rerun()
        elif step == 3:
            if st.button("계속하기"):
                st.session_state.user_input["age"] = age
                st.session_state.step += 1
                st.rerun()
        elif step == 4:
            if st.button("계속하기"):
                if not st.session_state.user_input.get("types"):
                    st.warning("비건 종류를 선택해주세요.")
                else:
                    st.session_state.step += 1
                    st.rerun()
        elif step == 5:
            if st.button("제출하기"):
                st.session_state.user_input["allergy"] = allergy
                st.session_state.user_info = st.session_state.user_input
                st.success("🎉 정보가 성공적으로 제출되었습니다.")
                st.session_state.page = "chatbot"
                st.session_state.from_chatbot = True
                st.session_state.step = 0
                st.rerun()
