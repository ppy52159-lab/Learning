import uvicorn
import jwt
import time
import shutil
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, col
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import init_db, get_session
from models import User, UserCreate, UserRead, Task, TaskCreate, TaskRead
from security import (
    hash_password,
    verify_password,
    create_access_token,
)
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code executed on startup:
    init_db()
    yield
    # Code executed on shutdown (if needed):
    pass
limiter = Limiter(key_func=get_remote_address)	
	
app = FastAPI(title="Task Master API",lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------
# 1. FILE SYSTEM & STATIC MOUNT
# ---------------------------------------------------------
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# ---------------------------------------------------------
# 2. CORS & TIMING MIDDLEWARE
# ---------------------------------------------------------
allowed_origins = [
    "http://localhost:3000",             # Local Next.js/React frontend
    "http://localhost:5173",             # Local Vite frontend
    "https://learning-production-dea9.up.railway.app"    # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Notice the 'await' keyword here!
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    print(f"LOG: {request.method} {request.url.path} - {process_time:.2f}ms")
    response.headers["X-Process-Time-MS"] = f"{process_time:.2f}"
    return response

# ---------------------------------------------------------
# 3. CUSTOM EXCEPTION HANDLING
# ---------------------------------------------------------
class TaskNotFoundException(Exception):
    def __init__(self, task_id: int):
        self.task_id = task_id

@app.exception_handler(TaskNotFoundException)
def task_not_found_handler(request: Request, exc: TaskNotFoundException):
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "error_code": "TASK_NOT_FOUND",
            "message": f"Task with ID {exc.task_id} was not found or does not belong to you."
        }
    )

# ---------------------------------------------------------
# 4. AUTHENTICATION & DEPENDENCIES
# ---------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# Pass lifespan into the FastAPI app initialization
def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user

# ---------------------------------------------------------
# 5. AUTH ROUTES
# ---------------------------------------------------------
@app.post("/api/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.username == user_in.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    db_user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password)
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@app.post("/api/login")
@limiter.limit("5/minute")
async def login(
	request: Request,
	form_data: OAuth2PasswordRequestForm = Depends(),
	session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
	
# ---------------------------------------------------------
# 6. PROFILE & FILE UPLOAD ROUTE
# ---------------------------------------------------------
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]

@app.post("/api/users/avatar", response_model=UserRead)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid format '{file.content_type}'. Allowed: JPEG, PNG, WebP."
        )

    file_extension = Path(file.filename).suffix.lower() or ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    destination_path = UPLOAD_DIR / unique_filename

    try:
        with destination_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Save relative static path to the database
    current_user.avatar_url = f"/static/{unique_filename}"
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return current_user

# ---------------------------------------------------------
# 7. TASK ROUTES (CRUD, PAGINATION, FILTERING)
# ---------------------------------------------------------
@app.post("/api/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_task = Task(
        title=task_in.title,
        description=task_in.description,
        is_completed=task_in.is_completed,
        user_id=current_user.id
    )
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

@app.get("/api/tasks", response_model=list[TaskRead])
def get_tasks(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, le=100),
    search: str | None = None,
    sort_desc: bool = False
):
    statement = select(Task).where(Task.user_id == current_user.id)

    if search:
        statement = statement.where(
            Task.title.contains(search) | Task.description.contains(search)
        )

    if sort_desc:
        statement = statement.order_by(col(Task.id).desc())
    else:
        statement = statement.order_by(col(Task.id).asc())

    statement = statement.offset(offset).limit(limit)
    tasks = session.exec(statement).all()
    return tasks

@app.get("/api/tasks/{task_id}", response_model=TaskRead)
def get_task_by_id(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    task = session.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise TaskNotFoundException(task_id=task_id)
    return task

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
	