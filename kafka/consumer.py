import asyncio
import json
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv
import os
import time

import jwt
from sqlalchemy import text

from database import redis_client, SessionLocal
from database import db_host, db_port, db_name, db_username, db_password

load_dotenv()

class KafkaQueryConsumer:
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "postgres_consumer_group",
        topic: str = "postgres_queries",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topic = topic
        self.consumer = None
        self.running = False

        self.session_connections = {}

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest"
        )
        await self.consumer.start()
        self.running = True
        print("[Consumer] AIOKafkaConsumer başlatıldı, topik dinleniyor...")

    async def stop(self):
        self.running = False
        if self.consumer:
            await self.consumer.stop()

        for sid in list(self.session_connections.keys()):
            self._close_session(sid)

        print("[Consumer] Durduruldu ve session'lar kapatıldı.")

    async def consume_loop(self):
        try:
            while self.running:
                results = await self.consumer.getmany(timeout_ms=1000)

                for tp, messages in results.items():
                    for msg in messages:
                        await self._handle_message(msg)
        except Exception as e:
            print(f"[Consumer] consume_loop hatası: {e}")
        

    async def _handle_message(self, msg):
        msg_str = msg.value.decode("utf-8")
        try:
            msg_value = json.loads(msg_str)
        except json.JSONDecodeError as e:
            print(f"[Consumer] JSON parse hatası: {e}")
            return

        self._process_message(msg_value)

    def _process_message(self, msg_value: dict):
        session_id = msg_value.get("session_id")
        action = msg_value.get("action")

        if not session_id:
            print("[Consumer] Geçersiz session_id!")
            return

        session = self._get_or_create_session(session_id)
        
        if action == "execute":
            query = msg_value.get("query")
            if not query:
                print("[Consumer] 'execute' action'ında sorgu (query) alanı boş.")
                return
            try:
                if query.strip().lower().startswith("select"):
                    result = session.execute(text(query))
                    rows = result.fetchall()
                    colnames = result.keys()
                    
                    rows_as_dicts = [dict(zip(colnames, row)) for row in rows]
                    json_data = json.dumps(rows_as_dicts)
                    
                    key = f"sql_result:{session_id}"
                    redis_client.set(key, json_data)
                    
                    print("[Consumer] SELECT sorgusu çalıştırıldı ve sonuçlar Redis'e kaydedildi")
                else:
                    session.execute(text(query))
                    
                print(f"[Consumer] [{session_id}] Sorgu çalıştırıldı: {query}")
            except Exception as e:
                session.rollback()
                print(f"[Consumer] [{session_id}] Sorgu hatası: {e}")

        elif action == "commit":
            try:
                session.commit()
                print(f"[Consumer] [{session_id}] Transaction commit edildi.")
            except Exception as e:
                session.rollback()
                print(f"[Consumer] [{session_id}] Commit hatası: {e}")

        elif action == "rollback":
            try:
                session.rollback()
                print(f"[Consumer] [{session_id}] Transaction rollback yapıldı.")
            except Exception as e:
                print(f"[Consumer] [{session_id}] Rollback hatası: {e}")

        else:
            print(f"[Consumer] Tanımlanmamış action: {action}")

    def _get_or_create_session(self, session_id: str):
        if session_id in self.session_connections:
            return self.session_connections[session_id]

        session = SessionLocal()
        self.session_connections[session_id] = session
        print(f"[Consumer] Yeni session açıldı: {session_id}")
        return session

    def _close_session(self, session_id: str):
        if session_id in self.session_connections:
            session = self.session_connections[session_id]
            session.close()
            del self.session_connections[session_id]
            print(f"[Consumer] Session kapatıldı: {session_id}")
