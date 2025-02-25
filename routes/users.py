from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text, select
import security
from database import get_db, Session
from models import Users, Roles, UserSessions
from schemas.s_users import Token, UserRegisterSchema
from kafka import producer

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/register")
async def register(data: UserRegisterSchema, db: Session = Depends(get_db)):
    try:
        db_user = db.query(Users).filter(Users.email == data.email).first()
        if db_user:
            return JSONResponse(
                status_code=409,
                content={"detail" : "User Already exists"}
            )
        new_user = Users(
            username=data.username,
            email=data.email,
            password=data.password,
            role_id=1
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        uuid = producer.create_session_id()
        new_user_session = UserSessions(
            user_id=new_user.id,
            session_id=uuid
        )
        db.add(new_user_session)
        db.commit()
        db.refresh(new_user_session)
        return JSONResponse(
            status_code=200,
            content={"detail" : "User registered successfully"}
        )
    except Exception as e:
        print(e)
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail" : "Internal Server Error"}
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.email == email, Users.password == password).first()
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail" : "Incorrect username or password"}
            )
        user_role = db.query(Roles).filter(Roles.id == user.role_id).first()
        user_session = db.query(UserSessions).filter(UserSessions.user_id == user.id).first()
        
        access_token_data = {"email" : user.email, "role" : user_role.role_name, "session_id" : user_session.session_id}
        access_token = security.create_access_token(access_token_data)
        
        return JSONResponse(status_code=200, content={"access_token" : access_token, "token_type" : "bearer"})
    except Exception as e:
        print(str(e))
        return JSONResponse(status_code=500, content={
            "detail" : "Internal Server Error",
            "error" : f"{str(e)}"
        })