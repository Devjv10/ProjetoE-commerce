from database.mongodb import create_client, get_database
from services.recommendations import run

# Históricos fictícios de entrada: as sugestões serão calculadas via Cypher.
HISTORY = {'c01': ['p01','p05'], 'c02': ['p01','p05','p06','p03'],
           'c03': ['p09','p07'], 'c04': ['p09','p07','p08','p11'],
           'c05': ['p02','p03','p06'], 'c06': ['p05','p06','p04','p12','p10']}


def seed():
    for label, property_name in [('Cliente','id'), ('Produto','id'), ('Categoria','nome')]:
        run(f'CREATE CONSTRAINT {label.lower()}_unique IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE')
    # Garante a unicidade do evento de compra também sob retentativas simultâneas (Neo4j 5.7+).
    run('CREATE CONSTRAINT compra_evento_unique IF NOT EXISTS FOR ()-[r:COMPROU]-() REQUIRE r.evento_id IS UNIQUE')
    with create_client() as client:
        db = get_database(client)
        products, customers = list(db.produtos.find()), list(db.clientes.find())
    if len(products) < 12 or len(customers) < 6:
        raise ValueError('Execute primeiro python -m scripts.seed_mongodb.')
    run('''UNWIND $clientes AS item
           MERGE (c:Cliente {id: item._id}) SET c.nome = item.nome''', clientes=customers)
    run('''UNWIND $produtos AS item
           MERGE (p:Produto {id: item._id}) SET p.nome = item.nome
           MERGE (cat:Categoria {nome: item.categoria})
           MERGE (p)-[:PERTENCE_A]->(cat)''', produtos=products)
    rows = [{'cliente': c, 'produto': p, 'evento': f'seed:{c}:{p}'} for c, ps in HISTORY.items() for p in ps]
    run('''UNWIND $historicos AS item
           MATCH (c:Cliente {id: item.cliente}), (p:Produto {id: item.produto})
           MERGE (c)-[r:COMPROU {evento_id: item.evento}]->(p)
           ON CREATE SET r.pedido_id = item.evento, r.quantidade = 1
           MERGE (c)-[a:AVALIOU]->(p) ON CREATE SET a.nota = 5''', historicos=rows)
    print('Neo4j: constraints, clientes, produtos, categorias, compras e avaliações carregados sem duplicação.')


if __name__ == '__main__':
    seed()
