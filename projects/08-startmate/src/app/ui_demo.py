# src/app/ui_demo.py
import streamlit as st
from graph.flow import build_graph
from core.schemas import State

st.set_page_config(page_title="Patent-RAG", layout="wide")
st.title("당신의 창업을 돕는 StartMate \n 특허와 IP에 대해 질문하세요!")

graph = build_graph()

if "history" not in st.session_state:
    st.session_state["history"] = []

# 기존 대화를 먼저 렌더
for turn in st.session_state["history"]:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

# 채팅 입력
query = st.chat_input("질문을 입력하세요…")
if query:
    # 1) 사용자 메시지 즉시 push
    st.session_state["history"].append({"role": "user", "content": query})

    # 2) 그래프 실행(과거 히스토리 포함)
    state = State(query=query.strip(), history=st.session_state["history"])
    out: State = graph.invoke(state)  # type: ignore

    # 3) 어시스턴트 메시지 push
    st.session_state["history"].append({"role": "assistant", "content": out.answer or ""})

    # 4) 방금 턴 렌더
    with st.chat_message("assistant"):
        st.markdown(out.answer or "(no answer)")

    # 선택: Trace/Debug 섹션
    with st.expander("Trace / Debug"):
        st.json({
            "route": out.route.model_dump() if out.route else {},
            "branch": out.debug.get("branch") if out.debug else None,
            "timings": out.timings,
            "retrieve": out.debug.get("retrieve") if out.debug else None,
            "router": out.debug.get("router") if out.debug else None,
        })
