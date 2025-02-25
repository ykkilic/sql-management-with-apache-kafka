from pydantic import BaseModel
from typing import Optional

class UserRegisterSchema(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

