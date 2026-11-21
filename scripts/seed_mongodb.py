"""Carga idempotente: IDs estáveis e upsert, sem apagar pedidos."""
import json
import uuid
from pathlib import Path
from database.mongodb import create_client, get_database

ROOT = Path(__file__).resolve().parents[1]


def seed():
    with create_client() as client:
        db = get_database(client)
        db.produtos.create_index('categoria')
        db.produtos.create_index('nome')
        db.pedidos.create_index([('cliente_id', 1), ('criado_em', -1)])
        db.pedidos.create_index('status')
        for filename, collection in [('products.json', db.produtos), ('customers.json', db.clientes)]:
            for document in json.loads((ROOT / 'data' / filename).read_text()):
                collection.update_one({'_id': document['_id']}, {'$set': document}, upsert=True)
        db.metadata.update_one({'_id': 'catalogo'}, {'$set': {'version': uuid.uuid4().hex}}, upsert=True)
    print('MongoDB: 12 produtos e 6 clientes cadastrados; índices e revisão do cache atualizados.')


if __name__ == '__main__':
    seed()
