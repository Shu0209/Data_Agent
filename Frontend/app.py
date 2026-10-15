
import uuid

import requests
import streamlit as st


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Data Agent",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Data Agent")
st.caption("Ask questions about your database using natural language.")


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.header("Settings")

    backend_url = st.text_input(
        "FastAPI Backend URL",
        value="http://127.0.0.1:8000",
    ).strip().rstrip("/")

    show_sql = st.toggle(
        "Show generated SQL",
        value=True,
    )

    show_execution_result = st.toggle(
        "Show SQL execution result",
        value=False,
    )

    st.divider()

    st.caption("Conversation")
    st.code(st.session_state.thread_id, language=None)

    if st.button("New conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()

    st.divider()

    st.caption("Backend API")
    st.code(f"{backend_url}/query", language=None)


# --------------------------------------------------
# Display previous messages
# --------------------------------------------------

for item in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(item["question"])

    with st.chat_message("assistant"):
        if item.get("error"):
            st.error(item["error"])
        else:
            st.markdown(item.get("final_answer") or "No answer returned.")

            with st.expander("Query details"):
                st.write("**Safety decision**")
                safety = item.get("is_safe", "No")
                if safety == "Yes":
                    st.success("Approved by SQL judge")
                else:
                    st.warning(f"Not approved: {safety}")

                st.write("**Judge comments**")
                st.write(item.get("comments") or "No comments returned.")

                if show_sql:
                    st.write("**Generated SQL**")
                    sql = item.get("generated_sql_query")
                    if sql:
                        st.code(sql, language="sql")
                    else:
                        st.info("No SQL query was returned.")

                if show_execution_result:
                    st.write("**SQL execution result**")
                    st.code(
                        str(item.get("sql_query_execution_result", "")),
                        language="text",
                    )


# --------------------------------------------------
# Chat input and API request
# --------------------------------------------------

question = st.chat_input("Ask a question about your database...")

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your question..."):
            try:
                response = requests.post(
                    f"{backend_url}/query",
                    json={
                        "user_input": question,
                        "thread_id": st.session_state.thread_id,
                    },
                    timeout=120,
                )

                if response.ok:
                    result = response.json()

                    if result.get("final_answer"):
                        st.markdown(result["final_answer"])
                    else:
                        st.warning(
                            "The backend returned no final answer."
                        )

                    with st.expander("Query details"):
                        safety = result.get("is_safe", "No")

                        st.write("**Safety decision**")
                        if safety == "Yes":
                            st.success("Approved by SQL judge")
                        else:
                            st.warning(f"Not approved: {safety}")

                        st.write("**Judge comments**")
                        st.write(
                            result.get("comments")
                            or "No comments returned."
                        )

                        if show_sql:
                            st.write("**Generated SQL**")
                            sql = result.get("generated_sql_query")
                            if sql:
                                st.code(sql, language="sql")
                            else:
                                st.info("No SQL query was returned.")

                        if show_execution_result:
                            st.write("**SQL execution result**")
                            st.code(
                                str(
                                    result.get(
                                        "sql_query_execution_result", ""
                                    )
                                ),
                                language="text",
                            )

                    st.session_state.chat_history.append({
                        "question": question,
                        "final_answer": result.get("final_answer", ""),
                        "is_safe": result.get("is_safe", "No"),
                        "comments": result.get("comments", ""),
                        "generated_sql_query": result.get(
                            "generated_sql_query", ""
                        ),
                        "sql_query_execution_result": result.get(
                            "sql_query_execution_result", ""
                        ),
                    })

                else:
                    try:
                        detail = response.json().get(
                            "detail", response.text
                        )
                    except ValueError:
                        detail = response.text

                    error_message = (
                        f"Backend returned HTTP {response.status_code}: "
                        f"{detail}"
                    )
                    st.error(error_message)

                    st.session_state.chat_history.append({
                        "question": question,
                        "error": error_message,
                    })

            except requests.exceptions.Timeout:
                error_message = (
                    "The request timed out. The agent may still be "
                    "processing your question. Please try again."
                )
                st.error(error_message)

                st.session_state.chat_history.append({
                    "question": question,
                    "error": error_message,
                })

            except requests.exceptions.ConnectionError:
                error_message = (
                    "Could not connect to the FastAPI backend. "
                    "Make sure your backend is running."
                )
                st.error(error_message)

                st.session_state.chat_history.append({
                    "question": question,
                    "error": error_message,
                })

            except (requests.exceptions.RequestException, ValueError) as exc:
                error_message = f"Request failed: {exc}"
                st.error(error_message)

                st.session_state.chat_history.append({
                    "question": question,
                    "error": error_message,
                })

    st.rerun()
