"""Sessões e carrinhos reais no Redis; WATCH evita perder alterações concorrentes."""
import hashlib
import json
import secrets
import uuid
from redis.exceptions import WatchError

from database.redis_db import create_client
from services.products import prefix, get_product

SESSION_TTL = 3600
CART_TTL = 86400


def session_key(token):
    return f'{prefix()}:session:{hashlib.sha256(token.encode()).hexdigest()}'


def cart_key(customer_id):
    # O chamador passa o ID exclusivo da sessão, não o ID do cliente.
    return f'{prefix()}:cart:{customer_id}'


def login(customer):
    token = secrets.token_urlsafe(32)
    session = {'cliente_id': customer['_id'], 'nome': customer['nome'], 'sessao_id': uuid.uuid4().hex}
    with create_client() as redis:
        redis.set(session_key(token), json.dumps(session), ex=SESSION_TTL)
    return token


def authenticate(token):
    if not token:
        raise ValueError('Selecione um cliente e inicie uma sessão.')
    with create_client() as redis:
        raw = redis.getex(session_key(token), ex=SESSION_TTL)
    if not raw:
        raise ValueError('Sessão expirada. Identifique-se novamente na barra lateral.')
    return json.loads(raw)


def logout(token):
    with create_client() as redis:
        redis.delete(session_key(token))


def read_cart(token):
    session = authenticate(token)
    with create_client() as redis:
        raw = redis.get(cart_key(session['sessao_id']))
    return json.loads(raw) if raw else {'id': None, 'items': {}, 'pending': False}


def change_cart(token, product_id=None, quantity=None, add=False, clear=False):
    session = authenticate(token)
    if not clear:
        if type(quantity) is not int or not 0 <= quantity <= 99:
            raise ValueError('A quantidade deve ser de 0 a 99.')
        get_product(product_id)
    key = cart_key(session['sessao_id'])
    with create_client() as redis:
        for _ in range(8):
            try:
                with redis.pipeline() as pipe:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    cart = json.loads(raw) if raw else {'id': uuid.uuid4().hex, 'items': {}, 'pending': False}
                    if cart['pending']:
                        raise ValueError('Há uma compra em processamento. Retome-a no Checkout antes de alterar o carrinho.')
                    if clear:
                        cart['items'] = {}
                    else:
                        value = quantity + cart['items'].get(product_id, 0) if add else quantity
                        if value > 99:
                            raise ValueError('Limite de 99 unidades por produto.')
                        if value:
                            cart['items'][product_id] = value
                        else:
                            cart['items'].pop(product_id, None)
                    pipe.multi()
                    pipe.set(key, json.dumps(cart), ex=CART_TTL)
                    pipe.execute()
                    return cart
            except WatchError:
                continue
    raise ValueError('Carrinho alterado em outra operação. Tente novamente.')


def cart_lines(cart):
    lines = []
    for product_id, quantity in cart['items'].items():
        product = get_product(product_id)
        lines.append({'produto_id': product_id, 'nome': product['nome'], 'quantidade': quantity,
                      'categoria': product['categoria'], 'preco_centavos': product['preco_centavos'],
                      'subtotal_centavos': product['preco_centavos'] * quantity})
    return lines


def freeze(token):
    """Congela um retrato antes do primeiro efeito externo; retentativas usam o mesmo ID."""
    session = authenticate(token)
    key = cart_key(session['sessao_id'])
    with create_client() as redis:
        for _ in range(8):
            try:
                with redis.pipeline() as pipe:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if not raw:
                        raise ValueError('O carrinho está vazio.')
                    cart = json.loads(raw)
                    if cart['pending']:
                        return cart['order']
                    if not cart['items']:
                        raise ValueError('O carrinho está vazio.')
                    lines = cart_lines(cart)
                    order = {'_id': cart['id'], 'cliente_id': session['cliente_id'],
                             'cliente_nome': session['nome'], 'carrinho_chave': key,
                             'itens': lines, 'total_centavos': sum(x['subtotal_centavos'] for x in lines)}
                    cart.update(pending=True, order=order)
                    pipe.multi()
                    # Sem TTL enquanto houver pedido pendente: falhas não descartam o retrato.
                    pipe.set(key, json.dumps(cart))
                    pipe.execute()
                    return order
            except WatchError:
                continue
    raise ValueError('Carrinho mudou durante o checkout. Confira e tente novamente.')


def clear_completed(order):
    # Compare-and-delete atômico: uma retentativa nunca apaga um carrinho novo.
    script = '''
    local raw = redis.call('GET', KEYS[1])
    if not raw then return 0 end
    local cart = cjson.decode(raw)
    if cart.id == ARGV[1] and cart.pending then
        return redis.call('DEL', KEYS[1])
    end
    return 0
    '''
    with create_client() as redis:
        redis.eval(script, 1, order['carrinho_chave'], order['_id'])


def pending_drafts(customer_id):
    """Recupera inclusive falha anterior à gravação MongoDB ou sessão expirada."""
    drafts = []
    with create_client() as redis:
        for key in redis.scan_iter(match=f'{prefix()}:cart:*', count=100):
            raw = redis.get(key)
            if raw:
                cart = json.loads(raw)
                if cart.get('pending') and cart['order']['cliente_id'] == customer_id:
                    drafts.append(cart['order'])
    return drafts
