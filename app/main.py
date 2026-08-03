from fastapi import FastAPI,HTTPException ,Depends
from pydantic import BaseModel
from .agent import query_agent
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jose import JWTError,jwt
from .security import decode_access_token ,verify_password,create_access_token
from .models import User
from .database import AdminSession, admin_engine, Base
from .seed import run_seed
from sqlalchemy import select
from .security import hash_password
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="AI Business Data Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://text-to-sql-frontend-nu.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

class RegisterRequest(BaseModel):
    username: str
    password: str


def _init_db_if_needed():
    try:
        run_seed()
    except Exception:
        pass


@app.post("/register")
def register(payload: RegisterRequest):
    if len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    _init_db_if_needed()

    with AdminSession() as session:
        existing = session.execute(
            select(User).where(User.username == payload.username)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="Username already taken.")

        new_user = User(
            username=payload.username,
            hashed_password=hash_password(payload.password),
            role="user",  # hardcoded — public signup se koi admin nahi ban sakta
        )
        session.add(new_user)
        session.commit()

    return {"message": "User registered successfully. Please log in."}

def get_current_user(token:str = Depends(oauth2_scheme)) -> dict:
    """JWT token ko verify karta hai aur current user ka info return karta hai."""
    try:
        payload = decode_access_token(token)
        username:str = payload.get("sub")
        role:str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token.")
        return {"username":username,"role":role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

@app.get("/health")
def health_check():
    return {"status":"ok"}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    _init_db_if_needed()
    with AdminSession() as session:
        user = session.execute(
            select(User).where(User.username == form_data.username)
        ).scalar_one_or_none()

        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect username or password")

        token = create_access_token(username=user.username, role=user.role)
        return {"access_token": token, "token_type": "bearer"}
    

@app.post("/query", response_model=QueryResponse)
def ask_question(payload: QueryRequest, current_user: dict = Depends(get_current_user)):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    answer = query_agent(payload.question)
    return QueryResponse(answer=answer)









