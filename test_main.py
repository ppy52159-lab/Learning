import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
import io


# =========================================================
# 1. SETUP IN-MEMORY TEST DATABASE & TEST CLIENT
# =========================================================

# Use in-memory SQLite with StaticPool so all connections share the same memory DB
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

# Test session generator
def get_session_override():
    with Session(engine) as session:
        yield session

# Override the main app's get_session dependency
app.dependency_overrides[get_session] = get_session_override

# Create the TestClient
client = TestClient(app)


# Pytest fixture to reset tables before every test
@pytest.fixture(autouse=True)
def prepare_database():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


# =========================================================
# 2. TEST CASES
# =========================================================

def test_signup_user():
    """Test creating a new user account via POST /api/signup"""
    response = client.post(
        "/api/signup",
        json={"username": "testuser", "password": "password123"}
    )
    data = response.json()

    assert response.status_code == 201
    assert data["username"] == "testuser"
    assert "id" in data
    assert "password" not in data  # Ensure password is not leaked in output DTO!


def test_signup_duplicate_username_fails():
    """Test that registering a duplicate username returns HTTP 400"""
    # 1. Register first time
    client.post("/api/signup", json={"username": "testuser", "password": "123"})

    # 2. Try registering same username again
    response = client.post("/api/signup", json={"username": "testuser", "password": "456"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


def test_login_and_create_task():
    """Test user login, receiving JWT token, and creating a protected task"""
    # 1. Create User
    client.post("/api/signup", json={"username": "taskuser", "password": "mypassword"})

    # 2. Login to get JWT access token (OAuth2 uses Form Data, not JSON!)
    login_response = client.post(
        "/api/login",
        data={"username": "taskuser", "password": "mypassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 3. Use Token to Create a Task (Pass Bearer Token in headers)
    headers = {"Authorization": f"Bearer {token}"}
    task_response = client.post(
        "/api/tasks",
        json={"title": "Buy groceries", "description": "Milk and Eggs"},
        headers=headers
    )
    task_data = task_response.json()

    assert task_response.status_code == 201
    assert task_data["title"] == "Buy groceries"
    assert task_data["is_completed"] is False


def test_unauthorized_task_creation_fails():
    """Test that creating a task without a Bearer token returns HTTP 401"""
    response = client.post(
        "/api/tasks",
        json={"title": "Unauthorized Task", "description": "No Token"}
    )
    assert response.status_code == 401
def test_upload_avatar_success():
    """Test uploading a valid image avatar file as an authenticated user"""
    # 1. Register and Login to get a valid Bearer Token
    client.post("/api/signup", json={"username": "avatar_user", "password": "password123"})
    login_res = client.post("/api/login", data={"username": "avatar_user", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create mock in-memory image bytes (simulating a JPEG file download/file picker)
    # io.BytesIO creates a file-like byte buffer in RAM
    fake_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # Standard JPEG file magic header bytes
    
    # 3. Construct the files payload: (filename, file_bytes, content_type)
    files = {
        "file": ("profile.jpg", io.BytesIO(fake_image_bytes), "image/jpeg")
    }

    # 4. Perform the multipart/form-data upload request!
    response = client.post(
        "/api/users/avatar",
        headers=headers,
        files=files
    )

    data = response.json()

    # 5. Assertions
    assert response.status_code == 200
    assert "avatar_url" in data
    assert data["avatar_url"].startswith("/static/")
    assert data["avatar_url"].endswith(".jpg")


def test_upload_avatar_invalid_file_type_fails():
    """Test uploading a disallowed file format (e.g. executable .exe or text file) fails with 400"""
    # 1. Register and Login
    client.post("/api/signup", json={"username": "hacker_user", "password": "password123"})
    login_res = client.post("/api/login", data={"username": "hacker_user", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create mock text file bytes with non-image Content-Type
    fake_text_bytes = b"echo 'hacked'"
    files = {
        "file": ("script.sh", io.BytesIO(fake_text_bytes), "text/x-shellscript")
    }

    # 3. Attempt upload
    response = client.post(
        "/api/users/avatar",
        headers=headers,
        files=files
    )

    # 4. Assertion: Content type validation blocks it!
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]
		