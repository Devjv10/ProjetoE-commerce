from neo4j import GraphDatabase, Query

from config import setting, timeout_seconds


def create_driver():
    return GraphDatabase.driver(
        setting("NEO4J_URI", "bolt://localhost:7687"),
        auth=(setting("NEO4J_USERNAME", "neo4j"), setting("NEO4J_PASSWORD")),
        connection_timeout=timeout_seconds(),
        connection_acquisition_timeout=timeout_seconds(),
        max_transaction_retry_time=0,
    )


def check_connection() -> None:
    with create_driver() as driver:
        driver.verify_connectivity()
        with driver.session(database=setting("NEO4J_DATABASE", "neo4j")) as session:
            session.run(Query("RETURN 1 AS ok", timeout=timeout_seconds())).consume()
