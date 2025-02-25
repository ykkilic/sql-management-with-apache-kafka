from fastapi import Request, HTTPException, FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from datetime import datetime, timezone
import time
from dotenv import load_dotenv
import os
import logging
from typing import List

from database import get_db, Base, engine, Session
from models import Users, RolePermission, Pages
from kafka import producer

import routes.management as management
import routes.users as users

load_dotenv()

SECRET_KEY = os.getenv("SECURITY_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

class TokenValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: List[str]):
        super().__init__(app)
        self.excluded_paths = excluded_paths

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        try:
            db: Session = next(get_db())
            # Eğer istek excluded paths içinde değilse token doğrulaması yapılır
            if not any(request.url.path.startswith(path) for path in self.excluded_paths):
                # logging.debug("Token validation is required for this path.")

                # Authorization header'ını kontrol et
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.lower().startswith("bearer "):
                    print("1")
                    raise HTTPException(
                        status_code=401,
                        detail="Access token required"
                    )
                
                token = auth_header.split(" ")[1]
                # print(token)
                self.verify_token(token)

                decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": True})
                user_email = decoded_token.get("email")

                current_url = ("/"+request.headers.get("x-current-url").split("/")[-1])
                user = db.query(Users).filter(Users.email == user_email).first()

                check_page_exists = db.query(Pages).filter(Pages.page_url == current_url).first()
                if not user:
                    print("2")
                    return JSONResponse(
                        status_code=401,
                        content={"error" : "user not found"}
                    )
                if not current_url:
                    print(3)
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Not Found Current URL Path", "status_code": 401}
                    )
                
                if not check_page_exists:
                    print(4)
                    return JSONResponse(
                        status_code = 401,
                        content={"error" : "Not found current page"}
                    )
                
                check_permission = db.query(RolePermission).join(Pages).filter(Pages.page_url == current_url, RolePermission.role_id == user.role_id).all()
                if not check_permission:                    
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail" : "You dont have permission"}
                    )
                
                
            else:
                logging.debug("Path is excluded from token validation.")

            # Bir sonraki middleware veya endpoint'e geç
            response = await call_next(request)
            return response

        except HTTPException as exc:
            # Hata durumunda JSON yanıt döndür
            logging.error(f"HTTPException: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        except Exception as e:
            # Beklenmedik bir hata durumunda genel bir yanıt döndür
            logging.error(f"Unexpected Error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error": str(e)},
            )

    def verify_token(self, token: str) -> None:
        try:
            # Token'ı doğrula
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": True})

            # Exp kontrolü
            exp = payload.get("exp")
            if exp is None:
                raise HTTPException(
                    status_code=401,
                    detail="Token does not have an expiration time"
                )
            
            # Current time ve exp zamanlarını karşılaştır
            current_time = time.time() 
            if current_time > exp:
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )

        except jwt.ExpiredSignatureError:
            logging.error("Token expired")
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            logging.error("Invalid token")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

origins = []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"]
    )
excluded_path=[
    "/users/register",
    "/users/token",
]
app.add_middleware(TokenValidationMiddleware, excluded_paths=excluded_path)

@app.on_event("startup")
async def start_up():
    Base.metadata.create_all(bind=engine)
    await producer.start()

@app.on_event("shutdown")
async def shutdown():
    await producer.stop()

app.include_router(management.router)
app.include_router(users.router)