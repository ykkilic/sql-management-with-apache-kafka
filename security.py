from fastapi import HTTPException, status, Depends
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
import redis
import jwt
import os

from database import redis_client

load_dotenv()

SECRET_KEY = os.getenv('SECURITY_SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

ACCESS_TOKEN_EXPIRE_MINUTES = 240
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Access token oluşturur ve ne kadar süreyle geçerli olacağını ayarlar
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Refresh token oluşturur ve ne kadar süre ile geçerli olacağını ayarlar
def create_refresh_token(data : dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp" : expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Refresh tokeni süresini takip etmek için redise atar
def save_refresh_token_to_redis(refresh_token: str, username: str, ttl_days: int = 7):
    key=f"refresh_token:{username}"
    redis_client.setex(key, timedelta(days=ttl_days), refresh_token)

# Refresh tokeni redisten okur
def get_refresh_token_from_redis(username: str):
    key=f"refresh_token:{username}"
    refresh_token = redis_client.get(key)
    if refresh_token:
        return refresh_token.decode('utf-8')
    return None

# Refresh tokenin süresinin geçip geçmediğini kontrol eder
def is_refresh_token_expired(username: str):
    key = f"refresh_token:{username}"
    ttl = redis_client.ttl(key)
    # Eğer TTL -1 ise, key sonsuza kadar geçerli
    if ttl== -1:
        return False
    # Eğer TTL -2 ise, key zaten silinmiş (geçersiz)
    if ttl == -2:
        return True
    # Eğer TTL < 0 isei key geçersiz süresi dolmuş
    if ttl <= 0:
        return False
    
# Rediste ki refresh tokeni kullanarak tokeni doğrular
def verify_refresh_token_in_redis(refresh_token: str, username: str):
    stored_token = redis_client.get(f"refresh_token:{username}")
    if stored_token is None:
        return False
    return stored_token == refresh_token

# Refresh tokenin süresinin geçip geçmediğini ve diğer gereklilikleri kontrol eder
def verify_refresh_token(refresh_token: str, username: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["exp"] < datetime.utcnow().timestamp():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
        if not verify_refresh_token_in_redis(refresh_token, username):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not valid in redis")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return True