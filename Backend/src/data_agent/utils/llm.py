from langchain_openai import ChatOpenAI
from data_agent.config import settings

def choose_llm(level:str):
    if level.strip().lower()=="high":
        llm=ChatOpenAI(base_url=settings.groq_model_api_base,
                       model=settings.groq_model1,
                       temperature=0,
                       api_key=settings.groq_api_key)

    elif level.strip().lower()=="low":
        llm=ChatOpenAI(base_url=settings.groq_model_api_base,
                               model=settings.groq_model2,
                               temperature=0,
                               api_key=settings.groq_api_key)
    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm