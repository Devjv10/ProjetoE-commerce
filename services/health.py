"""Diagnóstico somente de leitura, sem esconder falhas com dados simulados."""

from database import mongodb, neo4j_db, redis_db


def check_connections() -> list[dict]:
    results = []
    for name, check in (
        ("MongoDB", mongodb.check_connection),
        ("Redis", redis_db.check_connection),
        ("Neo4j", neo4j_db.check_connection),
    ):
        try:
            check()
        except Exception as error:
            # Mensagens dos drivers podem incluir endereços e credenciais.
            results.append({"banco": name, "ok": False, "detalhe": (
                f"Falha ({type(error).__name__}). Confira o serviço, a rede e o .env."
            )})
        else:
            results.append({"banco": name, "ok": True, "detalhe": "Conexão confirmada."})
    return results
