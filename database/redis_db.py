from redis import Redis

from config import setting, timeout_seconds


def create_client() -> Redis:
    return Redis.from_url(
        setting("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=timeout_seconds(),
        socket_timeout=timeout_seconds(),
        retry_on_timeout=False,
    )


def check_connection() -> None:
    with create_client() as client:
        client.ping()
