"""As recomendações são calculadas pelo grafo, sem lista de respostas em Python."""
from neo4j import Query
from config import setting, timeout_seconds
from database.neo4j_db import create_driver
from services.cart import authenticate
from services.products import get_product

RECOMMENDATIONS = '''
MATCH (eu:Cliente {id: $cliente_id})-[interesse:COMPROU|AVALIOU]->(comum:Produto)
WHERE type(interesse) = 'COMPROU' OR interesse.nota >= 4
WITH DISTINCT eu, comum
MATCH (outro:Cliente)-[afinidade:COMPROU|AVALIOU]->(comum)
WHERE outro <> eu AND (type(afinidade) = 'COMPROU' OR afinidade.nota >= 4)
WITH DISTINCT eu, outro, comum
MATCH (outro)-[:COMPROU]->(sugestao:Produto)-[:PERTENCE_A]->(categoria:Categoria)
WHERE NOT EXISTS { MATCH (eu)-[:COMPROU]->(sugestao) }
  AND NOT EXISTS { MATCH (eu)-[negativa:AVALIOU]->(sugestao) WHERE negativa.nota <= 2 }
RETURN sugestao.id AS produto_id, sugestao.nome AS nome,
       categoria.nome AS categoria, count(DISTINCT outro) AS clientes_similares,
       collect(DISTINCT comum.nome) AS interesses_comuns
ORDER BY clientes_similares DESC, nome
LIMIT 6
'''


def run(query, **parameters):
    with create_driver() as driver:
        with driver.session(database=setting('NEO4J_DATABASE', 'neo4j')) as session:
            return session.run(Query(query, timeout=timeout_seconds()), **parameters).data()


def recommend(token):
    customer = authenticate(token)
    return run(RECOMMENDATIONS, cliente_id=customer['cliente_id'])


def rate(token, product_id, rating):
    if type(rating) is not int or not 1 <= rating <= 5:
        raise ValueError('A avaliação deve ser de 1 a 5.')
    customer = authenticate(token)
    product = get_product(product_id)
    run('''
        MERGE (c:Cliente {id: $cliente_id}) SET c.nome = $cliente_nome
        MERGE (p:Produto {id: $produto_id}) SET p.nome = $nome
        MERGE (cat:Categoria {nome: $categoria})
        MERGE (p)-[:PERTENCE_A]->(cat)
        MERGE (c)-[r:AVALIOU]->(p) SET r.nota = $nota, r.atualizado_em = datetime()
    ''', cliente_id=customer['cliente_id'], cliente_nome=customer['nome'],
        produto_id=product_id, nome=product['nome'], categoria=product['categoria'], nota=rating)


def record_purchase(order):
    # Cada relação pertence a um pedido. Repetir a consulta não duplica compras.
    run('''
        MERGE (c:Cliente {id: $cliente_id}) SET c.nome = $cliente_nome
        WITH c
        UNWIND $itens AS item
        MERGE (p:Produto {id: item.produto_id}) SET p.nome = item.nome
        MERGE (cat:Categoria {nome: item.categoria})
        MERGE (p)-[:PERTENCE_A]->(cat)
        MERGE (c)-[r:COMPROU {evento_id: $pedido_id + ':' + item.produto_id}]->(p)
        SET r.pedido_id = $pedido_id
        SET r.quantidade = item.quantidade, r.preco_centavos = item.preco_centavos
    ''', cliente_id=order['cliente_id'], cliente_nome=order['cliente_nome'],
        pedido_id=order['_id'], itens=order['itens'])
