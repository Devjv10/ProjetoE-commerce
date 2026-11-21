"""MongoDB é a fonte dos produtos; Redis guarda consultas por 60 segundos."""
import hashlib
import json
import re

from redis.exceptions import RedisError
from database.mongodb import create_client, get_database
from database.redis_db import create_client as redis_client
from config import setting

CACHE_TTL = 60


def prefix():
    return setting('REDIS_PREFIX', 'ecommerce')


def list_products(search='', category='Todas'):
    search = search.strip()[:100]
    with create_client() as mongo:
        db = get_database(mongo)
        # A revisão no MongoDB impede reutilizar cache antigo até quando Redis caiu na carga.
        metadata = db.metadata.find_one({'_id': 'catalogo'}) or {}
        version = metadata.get('version', '0')
        digest = hashlib.sha256(json.dumps([search.casefold(), category]).encode()).hexdigest()
        key = f'{prefix()}:products:{version}:{digest}'
        try:
            with redis_client() as redis:
                cached = redis.get(key)
            if cached:
                return json.loads(cached), 'Redis (cache)'
        except RedisError:
            pass
        query = {}
        if search:
            query['nome'] = {'$regex': re.escape(search), '$options': 'i'}
        if category != 'Todas':
            query['categoria'] = category
        products = list(db.produtos.find(query).sort('nome', 1))
    try:
        with redis_client() as redis:
            redis.set(key, json.dumps(products, ensure_ascii=False), ex=CACHE_TTL)
    except RedisError:
        return products, 'MongoDB (cache indisponível)'
    return products, 'MongoDB'


def get_product(product_id):
    with create_client() as mongo:
        product = get_database(mongo).produtos.find_one({'_id': product_id})
    if not product:
        raise ValueError('Produto não encontrado. Atualize o catálogo.')
    return product


def categories():
    with create_client() as mongo:
        return sorted(get_database(mongo).produtos.distinct('categoria'))


def customers():
    with create_client() as mongo:
        return list(get_database(mongo).clientes.find().sort('nome', 1))


def money(cents):
    return f'R$ {cents / 100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
