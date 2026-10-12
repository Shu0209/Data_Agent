from data_agent.utils.llm import choose_llm

llm_obj=choose_llm("low")

result=llm_obj.invoke("Hey how are you what model are you using")
print(result.content)