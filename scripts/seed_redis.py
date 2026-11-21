from services.products import list_products
from database.redis_db import create_client
from services.products import prefix


def seed():
    with create_client() as redis:
        redis.set(f'{prefix()}:demo:info', 'E-Commerce Inteligente', ex=86400)
    products, source = list_products()
    print(f'Redis: marcador de demonstração com TTL; cache aquecido com {len(products)} produtos ({source}).')
    print('Sessões e carrinhos são criados ao identificar um cliente; nenhum carrinho existente foi apagado.')


if __name__ == '__main__':
    seed()
