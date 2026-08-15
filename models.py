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

    tasks: list["Task"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "[Task.user_id]"}
    )


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
    claimed_by: int | None = None
    priority: str = "medium"

class Task(TaskBase, table=True):
    # 1. Primary Key
    id: int | None = Field(default=None, primary_key=True)
    
    # 2. Foreign Keys linking task to users
    user_id: int = Field(foreign_key="user.id")
    claimed_by: int | None = Field(default=None, foreign_key="user.id")
    
    # 3. Relationship
    owner: User | None = Relationship(
        back_populates="tasks",
        sa_relationship_kwargs={"foreign_keys": "[Task.user_id]"}
    )
    
    # 4. Field for Alembic migration
    priority: str = Field(default="medium")

		