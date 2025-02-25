from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import json

from kafka import producer
from database import redis_client
from schemas.s_queries import QueryRequest
from utils import User, get_current_user

router = APIRouter(
    prefix="/sql",
    tags=["sql"]
)

active_sessions = {}

@router.post("/execute-query")
async def exec_query(request: QueryRequest, current_user: User=Depends(get_current_user)):
    try:
        print(current_user.session_id)
        if not current_user.session_id:
            return JSONResponse(
                status_code=404,
                content={"detail" : "Session not found"}
            )
        await producer.send_query_message(
            topic="postgres_queries",
            session_id=current_user.session_id,
            action="execute",
            query=request.query
        )
        return JSONResponse(
            status_code=200,
            content={"detail" : "Query queued"}
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

@router.get("/get-results")
async def get_results(current_user: User=Depends(get_current_user)):
    try:
        session_id = current_user.session_id
        data = redis_client.get(f"sql_result:{session_id}")
        if not data:
            return JSONResponse(
                status_code=404,
                content={"detail" : "Data not found"}
            )
        rows = json.loads(data)
        return JSONResponse(
            status_code=200,
            content={"data" : jsonable_encoder(rows)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail" : "Internal Server Error"}
        )

@router.post("/commit")
async def commit_query(current_user: User=Depends(get_current_user)):
    try:
        session_id = current_user.session_id
        if session_id not in active_sessions:
            return JSONResponse(
                status_code=404,
                content={"detail" : "Session not found"}
            )
        await producer.send_query_message(
            topic="postgres_queries",
            session_id=session_id,
            action="commit"
        )
        return JSONResponse(
            status_code=200,
            content={"detail" : "query queued"}
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

@router.post("/rollback")
async def rollback_query(current_user: User=Depends(get_current_user)):
    try:
        session_id = current_user.session_id
        if session_id not in active_sessions:
            return JSONResponse(
                status_code=404,
                content={"detail" : "Session Not Found"}
            )
        await producer.send_query_message(
            topic="postgres_queries",
            session_id=session_id,
            action="rollback"
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={"detail" : "Internal Server Error"}
        )

