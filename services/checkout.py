"""Checkout retomável: MongoDB -> Neo4j -> Redis, com um ID por carrinho."""
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError

from database.mongodb import create_client, get_database
from services.cart import authenticate, freeze, clear_completed, pending_drafts
from services.recommendations import record_purchase


def complete(token, order_id=None):
    customer = authenticate(token)
    with create_client() as client:
        db = get_database(client)
        if order_id:
            order = db.pedidos.find_one({'_id': order_id, 'cliente_id': customer['cliente_id']})
            if not order:
                order = next((x for x in pending_drafts(customer['cliente_id']) if x['_id'] == order_id), None)
            if not order:
                raise ValueError('Pedido não encontrado para este cliente.')
        else:
            order = freeze(token)
        if order['cliente_id'] != customer['cliente_id']:
            raise ValueError('Pedido pertence a outro cliente.')
        initial = dict(order, status='pendente_grafo', criado_em=datetime.now(timezone.utc))
        try:
            db.pedidos.update_one({'_id': order['_id']}, {'$setOnInsert': initial}, upsert=True)
        except DuplicateKeyError:
            pass  # Outra chamada já gravou exatamente esse ID de carrinho.
        saved = db.pedidos.find_one({'_id': order['_id']})
        if saved['status'] == 'concluido':
            return saved
        if saved['status'] == 'pendente_grafo':
            record_purchase(saved)
            db.pedidos.update_one({'_id': saved['_id'], 'status': 'pendente_grafo'},
                                 {'$set': {'status': 'pendente_limpeza'}})
        clear_completed(saved)
        db.pedidos.update_one({'_id': saved['_id'], 'status': 'pendente_limpeza'},
                             {'$set': {'status': 'concluido', 'concluido_em': datetime.now(timezone.utc)}})
        return db.pedidos.find_one({'_id': saved['_id']})


def orders(token):
    customer = authenticate(token)
    with create_client() as client:
        return list(get_database(client).pedidos.find({'cliente_id': customer['cliente_id']}).sort('criado_em', -1).limit(30))
