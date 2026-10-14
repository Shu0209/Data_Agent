from data_agent.agents.graph import ai_data_agent
if __name__=="__main__":
    input_schema = {
        "messages": [],
        "user_input": "What are the different types of Payment methods we have in our database",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }


    config ={
        "configurable": {
            "thread_id": "sql-agent-test-1"
        }
    }
    



    response=ai_data_agent.invoke(input_schema,config=config)

    print("\n========== FINAL ANSWER ==========")
    print(response["final_answer"])


    print("\n========== GENERATED SQL ==========")
    print(response["generated_sql_query"])


    print("\n========== SQL EXECUTION RESULT ==========")
    print(response["sql_query_execution_result"])


    print("\n========== Judge DECISION ==========")
    print(f"Safe: {response['is_safe']}")
    print(f"Comments: {response['comments']}")

    print("\n========== PROMPT QUERY CONTEXT ==========")
    print(response["prompt_query_context"])



    print("\n========== MESSAGE HISTORY ==========")
    for message in response["messages"]:
        print(f"{message.type}: {message.content}")

