from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from .agent import query_agent

app = FastAPI(title="AI Business Data Assistant")



class QueryRequest(BaseModel):
    question:str

class QueryResponse(BaseModel):
    answer:str

@app.get("/health")
def health_check():
    return {"status":"ok"}

@app.post('/query',response_model=QueryResponse)
def ask_question(payload:QueryRequest):
    if not payload.question or not payload.question.strip():
        raise HttpException(status_code=400,detail="Question cannot be empty.")
    answer =query_agent(payload.question)
    return QueryResponse(answer=answer)









