from fastapi import Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import jwt
import io
from datetime import datetime, timedelta
from typing import Optional
from security import SECRET_KEY, ALGORITHM
from database import Session, get_db
from models import Users, Roles

class User:
    def __init__(self, email: str, role: str, session_id: str):
        self.email = email
        self.role = role
        self.session_id = session_id
        

# Token'dan kullanıcı bilgisi çıkaran yardımcı fonksiyon
def get_current_user(
        authorization: Optional[str] = Header(None),
        db : Session = Depends(get_db)
        ) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    
    token = authorization.split(" ")[1]  
    print("Here")
    try:
        # Token'i doğrula ve çöz
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("email")
        role: Optional[str] = payload.get("role")
        session_id: Optional[str] = payload.get("session_id")

        db_user = db.query(Users).filter(Users.email == email).first()
        db_role = db.query(Roles).filter(Roles.role_name == role).first()

        if db_user is None or db_role is None:
            return JSONResponse(
                status_code=404,
                content={"Role or user not found"}
            )
        
        return User(email=email, role=role, session_id=session_id)

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")