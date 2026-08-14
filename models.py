from sqlmodel import SQLModel, Field, Relationship

# =========================================================
# USER MODELS & SCHEMAS
# =========================================================

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    avatar_url: str | None = None

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    avatar_url: str | None = Field(default=None)

    tasks: list["Task"] = Relationship(back_populates="owner")


# =========================================================
# TASK MODELS & SCHEMAS
# =========================================================

class TaskBase(SQLModel):
    title: str
    description: str
    is_completed: bool = False
	
	
class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: int
    user_id: int

class Task(TaskBase, table=True):
    # 1. Primary Key (THIS WAS MISSING OR OVERWRITTEN!)
    id: int | None = Field(default=None, primary_key=True)
    
    # 2. Foreign Key linking task to a user
    user_id: int = Field(foreign_key="user.id")
    claimed_by: int | None = Field(default=None, foreign_key="user.id")
    
    # 3. Relationship
    owner: User | None = Relationship(back_populates="tasks")
    
    # 4. NEW FIELD ADDED FOR ALEMBIC
    priority: str = Field(default="medium")
		