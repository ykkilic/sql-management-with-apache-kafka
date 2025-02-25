import asyncio
import json
import uuid
from aiokafka import AIOKafkaProducer

class KafkaQueryProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None  # AIOKafkaProducer örneğine referans tutacağız.

    async def start(self):
        if self.producer is not None:
            print("[Producer] Kafka Producer zaten ayakta")
            return
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()
        print("[Producer] AIOKafkaProducer başlatıldı.")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            print("[Producer] AIOKafkaProducer durduruldu.")
        elif self.producer is None:
            print("[Producer] Kafka Producer zaten ayakta değil")

    def create_session_id(self) -> str:
        return str(uuid.uuid4())

    async def send_query_message(self, topic: str, session_id: str, action: str, query: str = None):
        if not self.producer:
            print("[Producer] Producer henüz başlatılmamış!")
            return

        message_value = {
            "session_id": session_id,
            "action": action
        }
        if query is not None:
            message_value["query"] = query

        message_bytes = json.dumps(message_value).encode("utf-8")

        await self.producer.send_and_wait(topic, message_bytes)
        print(f"[Producer] Mesaj gönderildi: session_id={session_id}, action={action}, query={query}")


producer = KafkaQueryProducer(bootstrap_servers="localhost:9092")