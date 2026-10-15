# ⚡ AI Data Agent — Backend

Autonomous SQL Analytics Agent Backend powered by **LangGraph**, **Groq (GPT-OSS-120B / 20B)**, **PostgreSQL**, and **FastAPI**.

---

## 🌟 Key Features

1. **FastAPI REST API & Interactive Swagger Docs:**
   - `POST /query`: Execute natural language questions with full agent workflow pipeline.
   - `GET /health`: Diagnostics and live database status.
   - `GET /tables`: List all database tables with row and column counts.
   - `GET /tables/{table_name}`: Inspect table column schemas and sample records.
2. **Multi-Step LangGraph Agent:**
   - **Question Curation (`curate_ques`):** Cleans and refines user queries.
   - **Schema Context (`prompt_query_context`):** Extracts PostgreSQL database schema and sample data.
   - **SQL Synthesis (`generate_sql`):** Generates PostgreSQL queries adhering to schema rules.
   - **Security Judge (`judge`):** Structured output security guardrail enforcing read-only SELECT queries and rejecting destructive SQL (DROP, DELETE, UPDATE, etc.).
   - **Execution & Answer (`execute_sql` & `final_answer`):** Executes queries and synthesizes natural language insights.
3. **CLI & Interactive Chat:**
   - Run queries directly from terminal with formatted outputs.
   - Interactive terminal chat loop with `data-agent -i`.

---

## 🚀 How to Run the Backend

### 1. Start the FastAPI REST API Server

From the project root:

```powershell
uv --directory Backend run python -m data_agent.main --port 8000
```

The interactive API documentation is available at: **`http://localhost:8000/docs`**

### 2. Run a Single Query via CLI

```powershell
uv --directory Backend run python -m data_agent.main -q "What are the available payment methods?"
```

### 3. Launch Interactive Terminal Chat

```powershell
uv --directory Backend run python -m data_agent.main -i
```
