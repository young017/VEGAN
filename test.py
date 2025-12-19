import streamlit as st
import sqlite3
from langchain.embeddings import OpenAIEmbeddings


st.write("Python sqlite3 version:", sqlite3.sqlite_version)
st.write("Python version:", sqlite3.version)
api_key = st.secrets["OPENAI_API_KEY"]
embedding_function = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=api_key)

import streamlit as st
import os
import zipfile
import traceback
import tempfile
from langchain.vectorstores import Chroma  # 일반적으로 langchain에서 import
from langchain.embeddings import OpenAIEmbeddings

st.title("🧠 Chroma 벡터스토어 로드 확인")

zip_path = "veganchroma_db.zip"
extract_path = os.path.join(tempfile.gettempdir(), "veganchroma_db")
db_file_path = os.path.join(extract_path, "chroma.sqlite3")

# 압축 해제 필요 여부 확인
if not os.path.exists(db_file_path):
    if os.path.exists(zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            st.success(f"✅ Chroma DB 압축 해제 완료: {extract_path}")
        except Exception as e:
            st.error(f"❌ 압축 해제 실패: {e}")
            st.text(traceback.format_exc())
    else:
        st.error(f"❌ 압축파일 '{zip_path}'를 찾을 수 없습니다.")
else:
    st.info(f"📁 이미 압축 해제됨: {extract_path}")

# 벡터스토어 로드 시도
try:
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")
    vectorstore = Chroma(persist_directory=extract_path, embedding_function=embedding_function)
    st.success("✅ 벡터스토어 로드 성공")
except Exception as e:
    st.error(f"❌ 벡터스토어 로드 실패: {e}")
    st.text(traceback.format_exc())
