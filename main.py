import streamlit as st
import start
import infoslide as infoslide
import chatbot as chatbot
import info as info

def main():
    if "page" not in st.session_state:
        st.session_state.page = "start"

    if st.session_state.page == "start":
        start.show()
    elif st.session_state.page == "infoslide":
        infoslide.show()
    elif st.session_state.page == "chatbot":
        chatbot.show()
    elif st.session_state.page == "info":
        info.show()

if __name__ == "__main__":
    main()

