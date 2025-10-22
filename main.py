from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import models
from database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware
from models import User, Task
import json
import os
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
from dotenv import load_dotenv
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
import logging

load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Templates & static
templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="User & Task Management API",
    description="This API manages users and their associated tasks. You can perform CRUD operations on users and tasks.",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(level=logging.DEBUG)

# CORS middleware
origins = [
    "http://localhost",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database - create tables if not exist
models.Base.metadata.create_all(bind=engine)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------
# Pydantic Schemas
# -----------------------

class ChatbotInput(BaseModel):
    user_input: str

class UserCreate(BaseModel):
    username: str = Field(..., description="A unique username for the user.")
    email: str = Field(..., description="The user's email address.")
    first_name: str = Field(..., description="The user's first name.")
    last_name: str = Field(..., description="The user's last name.")
    phone_num: str = Field(..., description="The user's phone number.") 
    password: str = Field(..., description="The user's password.") 

class UserBase(BaseModel):
    id: Optional[int]
    username: str = Field(..., description="A unique username for the user.")
    email: str = Field(..., description="The user's email address.")
    first_name: str = Field(..., description="The user's first name.")
    last_name: str = Field(..., description="The user's last name.")
    phone_num: str = Field(..., description="The user's phone number.")

    class Config:
        orm_mode = True

class UserListResponse(BaseModel):
    total: int
    users: List[UserBase]

class UserUpdate(BaseModel):
    username: Optional[str]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_num: Optional[str]

class TaskBase(BaseModel):
    id: Optional[int]
    title: str = Field(..., description="Short title of the task.")
    content: str = Field(..., description="Detailed description of the task.")
    user_id: int = Field(..., description="ID of the user who owns this task.")
    is_completed: bool = Field(..., description="Whether the task is completed or not.")

    class Config:
        orm_mode = True

class TaskUpdate(BaseModel):
    title: Optional[str]
    content: Optional[str]
    is_completed: Optional[bool]

# -----------------------
# LLM Tool-calling logic
# -----------------------

def find_endpoint_by_operation_id(openapi_schema, operation_id):
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            if details.get("operationId") == operation_id:
                return path, method
    return None

def convert_openapi_to_functions(openapi_schema):
    tools = []
    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            operation_id = details.get("operationId")
            if not operation_id:
                continue

            parameters = details.get("parameters", [])
            properties = {}
            required = []

            for param in parameters:
                name = param.get("name")
                schema = param.get("schema", {})
                param_type = schema.get("type", "string")
                description = param.get("description", "")

                if name:
                    properties[name] = {
                        "type": param_type,
                        "description": description or f"{name} parameter"
                    }
                    if param.get("required", False):
                        required.append(name)

            tool_function = {
                "type": "function",
                "function": {
                    "name": operation_id,
                    "description": details.get("summary", f"Call {operation_id}"),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }

            tools.append(tool_function)
    return tools

def ask_gpt_tool_calling(user_input: str):
    """The main function that handles the AI interaction, tool-calling, and API execution."""
    try:
        url = "https://spog-open-ai.openai.azure.com/openai/deployments/SPOG-Dev/chat/completions?api-version=2025-01-01-preview"
        api_key = os.getenv("OPEN_API_KEY")

        headers = {
            'Content-Type': 'application/json',
            'api-key': api_key
        }

        openapi_schema = requests.get("http://localhost:8000/openapi.json").json()
        tools = convert_openapi_to_functions(openapi_schema)

        messages = [
            {"role": "system", "content": '''You are a backend assistant that uses tools (via the provided OpenAPI schema) to answer user queries by calling the appropriate API endpoint.

Your responsibilities:
1. Understand the user's intent from natural language input.
2. Select the correct API endpoint as defined in the OpenAPI schema.
3. Extract and provide all required parameters in the correct format when invoking the tool.
             
For creating a task (POST /tasks/), extract and use the following fields:
-title (string): the task title
-content (string): the task description
-user_id (integer): the ID of the user to assign the task to
-is_completed (boolean): whether the task is completed

Interpret user language into is_completed as follows:
Phrases like: "not completed", "incomplete", "not done", "still pending" → false
Phrases like: "completed", "done", "finished", "already completed" → true

Always:
-Include all required parameters
-Generate valid JSON (no trailing commas, no smart quotes)
-Match parameter names exactly as specified in the OpenAPI schema

 If the user input is missing any required field, ask for the missing field(s) clearly before making the API call.
- When listing users or tasks, display each field on its own line using <br>.
- Bold the field name using <b>...</b>.
- Add an extra <br> between each item for spacing.

'''
            },
            {"role": "user", "content": user_input}
        ]

        payload = {
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)

        if response.status_code != 200:
            return {"error": f"Request failed: {response.status_code}, {response.text}"}

        resp_json = response.json()
        if "choices" not in resp_json:
            return {"error": f"'choices' not found in response: {resp_json}"}

        message = resp_json['choices'][0]['message']
        tool_calls = message.get("tool_calls", [])
        
        if tool_calls:
            tool_call = tool_calls[0]
            operation_id = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            endpoint_info = find_endpoint_by_operation_id(openapi_schema, operation_id)
            if not endpoint_info:
                return {"error": f"No endpoint found for operationId: {operation_id}"}

            path, method = endpoint_info
            method = method.lower()
            full_url = f"http://localhost:8000{path}"

            # Substitute path parameters (e.g., /users/{user_id})
            for param, value in arguments.items():
                if f"{{{param}}}" in full_url:
                    full_url = full_url.replace(f"{{{param}}}", str(value))

            path_params = {k for k in arguments if f"{{{k}}}" in path}
            payload_api = {k: v for k, v in arguments.items() if k not in path_params}

            # Execute the internal API call based on the LLM's command
            if method == "get":
                api_response = requests.get(full_url, params=payload_api)
            elif method == "post":
                api_response = requests.post(full_url, json=payload_api)
            elif method == "put":
                api_response = requests.put(full_url, json=payload_api)
            elif method == "delete":
                api_response = requests.delete(full_url, params=payload_api)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            api_result = api_response.json() if api_response.content else {}

            followup_messages = messages + [
                message,
                {"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(api_result)}
            ]

            followup_payload = {"messages": followup_messages}
            followup_response = requests.post(url, headers=headers, data=json.dumps(followup_payload))

            if followup_response.status_code != 200:
                return {"error": f"Follow-up failed: {followup_response.status_code}, {followup_response.text}"}

            followup_resp_json = followup_response.json()
            if "choices" not in followup_resp_json:
                return {"error": f"'choices' not found in follow-up response: {followup_resp_json}"}

            return {"response": followup_resp_json['choices'][0]['message']['content']}
        else:
            return {"response": message.get('content', '')}

    except Exception as e:
        logging.exception("ask_gpt_tool_calling error")
        return {"error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chatbot_gpt/")
def ask_chatbot_gpt(input_data: ChatbotInput):
    response = ask_gpt_tool_calling(input_data.user_input)
    return {"response": response}

@app.post("/users/", response_model=UserBase, status_code=status.HTTP_201_CREATED,
          summary="Create a new user",
          description="Register a new user in the system. Provide essential user information including email and phone number.")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    
    existing = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    hashed = pwd_context.hash(user.password)

    db_user = models.User(
       username=user.username,
       email=user.email,
       first_name=user.first_name,
       last_name=user.last_name,
       phone_num=user.phone_num,
       hashed_password=hashed
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError as e:
        db.rollback()
        logging.exception("IntegrityError while creating user")
        raise HTTPException(status_code=400, detail="Database integrity error: possibly duplicate value.")
    except Exception as e:
        db.rollback()
        logging.exception("Unexpected error while creating user")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return db_user

@app.get(
    "/users",
    response_model=UserListResponse ,
    summary="Get all users",
    description="Retrieve the details of all users. You can also filter by username using the 'name' query parameter."
)
def get_all_users(
    db: Session = Depends(get_db),
    name: Optional[str] = Query(None, description="Filter or get users by username."),
    email_add: Optional[str] = Query(None, description="Filter or get users details by their email."),
    phone_num: Optional[str] = Query(None, description="Filter or get users details by their phone number.")
):
    query = db.query(User)
    if name:
        query = query.filter(User.username.ilike(f"%{name}%"))
    if email_add:
        query = query.filter(User.email.ilike(f"%{email_add}%"))
    if phone_num:
        query = query.filter(User.phone_num.ilike(f"%{phone_num}%"))

    total = query.count()
    users = query.all()
    return {
        "total": total,
        "users": users
    }

@app.get("/users/{user_id}", response_model=UserBase,
         summary="Get a user by ID",
         description="Retrieve the user details using their unique ID. Returns 404 if not found.")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=UserBase,
         summary="Update user info",
         description="Modify existing user information like name, email, or phone number.")
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logging.exception("Error updating user")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return user

@app.delete("/users/{user_id}", status_code=200,
            summary="Delete a user",
            description="Remove a user permanently using their ID. All tasks associated will be affected.")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        logging.exception("Error deleting user")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"detail": "User deleted successfully."}

@app.post("/tasks/", response_model=TaskBase, status_code=status.HTTP_201_CREATED,
          summary="Create a new task",
          description="Assign a new task to a user. Provide a title, content, and the user ID.")
def create_task(task: TaskBase, db: Session = Depends(get_db)):
   
    owner = db.query(models.User).filter(models.User.id == task.user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User (owner) not found for given user_id")

    db_task = models.Task(**task.dict())
    try:
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
    except IntegrityError:
        db.rollback()
        logging.exception("IntegrityError while creating task")
        raise HTTPException(status_code=400, detail="Database integrity error when creating task.")
    except Exception:
        db.rollback()
        logging.exception("Unexpected error while creating task")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return db_task

@app.get(
    "/tasks",
    response_model=List[TaskBase],
    summary="Get all tasks",
    description="Retrieve the details of all tasks. You can filter tasks by title, content, completion status, and the username of the user who created them."
)
def get_all_tasks(
    name: Optional[str] = Query(None, description="Filter tasks by the username of the user who created them."),
    task_title: Optional[str] = Query(None, description="Filter tasks by title."),
    task_content: Optional[str] = Query(None, description="Filter tasks by content."),
    is_completed: Optional[bool] = Query(None, description="Filter tasks by completion status."),
    user_id: Optional[int] = Query(None, description="Filter tasks by user ID."),
    db: Session = Depends(get_db)
):
    query = db.query(Task)

    if name:
        query = query.join(User).filter(User.username.ilike(f"%{name}%"))
    if task_title:
        query = query.filter(Task.title.ilike(f"%{task_title}%"))
    if task_content:
        query = query.filter(Task.content.ilike(f"%{task_content}%"))
    if is_completed is not None:
        query = query.filter(Task.is_completed == is_completed)
    if user_id:
        query = query.filter(Task.user_id == user_id)
    
    tasks = query.all()
    return tasks

@app.get("/tasks/{task_id}", response_model=TaskBase,
         summary="Get task by ID",
         description="Fetch details of a specific task using its ID. Returns task information including user ID.")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=TaskBase,
         summary="Update a task",
         description="Edit the details of an existing task such as title, content, or completion status.")
def update_task(task_id: int, task_data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task_data.dict(exclude_unset=True).items():
        setattr(task, key, value)
    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        logging.exception("Error updating task")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return task

 
@app.delete("/tasks/{task_id}", status_code=200,
            summary="Delete a task",
            description="Delete a task permanently by providing its ID. Useful for cleaning up old or completed tasks.")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        db.delete(task)
        db.commit()
    except Exception:
        db.rollback()
        logging.exception("Error deleting task")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"detail": "Task deleted successfully."}
