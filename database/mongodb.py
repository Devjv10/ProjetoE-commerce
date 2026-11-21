from pymongo import MongoClient

from config import setting, timeout_seconds


def create_client() -> MongoClient:
    timeout_ms = int(timeout_seconds() * 1000)
    return MongoClient(
        setting("MONGODB_URI", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
        socketTimeoutMS=timeout_ms,
    )


def get_database(client: MongoClient):
    return client[setting("MONGODB_DATABASE", "ecommerce_inteligente")]


def check_connection() -> None:
    with create_client() as client:
        get_database(client).command("ping")
