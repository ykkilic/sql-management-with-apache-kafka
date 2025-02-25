from kafka import KafkaQueryConsumer
import asyncio


async def main():
    consumer = KafkaQueryConsumer(
            group_id="postgres_consumer_group",
            topic="postgres_queries",
    )

    await consumer.start()

    await consumer.consume_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Consumer] Dışarıdan durdurma sinyali alındı.")