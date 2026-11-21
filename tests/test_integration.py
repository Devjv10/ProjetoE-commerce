"""RUN_INTEGRATION=1 usa MongoDB e Redis reais em namespaces descartáveis.
RUN_NEO4J_TESTS=1 inclui o grafo real, com clientes exclusivos para o teste.
Falhas deliberadas são injetadas com mocks e identificadas nos nomes dos testes.
"""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from database.mongodb import create_client, get_database
from database.redis_db import create_client as redis_client
from scripts.seed_mongodb import seed
from services import cart, checkout, products, recommendations


@unittest.skipUnless(os.getenv('RUN_INTEGRATION') == '1', 'Requer RUN_INTEGRATION=1 e bancos reais')
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tag = 'test_' + uuid.uuid4().hex
        cls.environment = patch.dict(os.environ, {'MONGODB_DATABASE': cls.tag, 'REDIS_PREFIX': cls.tag})
        cls.environment.start()
        seed()
        cls.customer = {'_id': cls.tag, 'nome': 'Cliente de teste'}

    @classmethod
    def tearDownClass(cls):
        with create_client() as mongo:
            mongo.drop_database(cls.tag)
        with redis_client() as redis:
            for key in redis.scan_iter(match=cls.tag + ':*'):
                redis.delete(key)
        cls.environment.stop()

    def setUp(self):
        self.token = cart.login(self.customer)

    def test_catalog_cache_ttl_and_invalidation(self):
        first, _ = products.list_products('Notebook')
        second, source = products.list_products('Notebook')
        self.assertEqual(len(first), 2)
        self.assertEqual(first, second)
        self.assertEqual(source, 'Redis (cache)')
        self.assertEqual(len(products.list_products(category='Áudio')[0]), 2)
        self.assertEqual(products.list_products('.*')[0], [])  # Busca literal, não regex do usuário.
        with redis_client() as redis:
            keys = list(redis.scan_iter(match=products.prefix() + ':products:*'))
            self.assertTrue(all(0 < redis.ttl(key) <= 60 for key in keys))
        with create_client() as mongo:
            get_database(mongo).produtos.update_one({'_id': 'p01'}, {'$set': {'nome': 'Nome alterado'}})
        seed()  # Restaura e muda a revisão, invalidando consultas anteriores.
        self.assertEqual(products.list_products('Notebook')[1], 'MongoDB')

    def test_cart_isolation_quantities_and_removal(self):
        other = cart.login(self.customer)
        cart.change_cart(self.token, 'p01', 2)
        cart.change_cart(self.token, 'p01', 1, add=True)
        self.assertEqual(cart.read_cart(other)['items'], {})
        self.assertEqual(cart.read_cart(self.token)['items'], {'p01': 3})
        self.assertEqual(cart.cart_lines(cart.read_cart(self.token))[0]['subtotal_centavos'], 429900 * 3)
        cart.change_cart(self.token, 'p01', 0)
        self.assertEqual(cart.read_cart(self.token)['items'], {})
        cart.change_cart(self.token, 'p02', 1)
        cart.change_cart(self.token, clear=True)
        self.assertEqual(cart.read_cart(self.token)['items'], {})
        with redis_client() as redis:
            redis.delete(cart.session_key(self.token))
        with self.assertRaises(ValueError):
            cart.read_cart(self.token)

    def test_concurrent_cart_additions(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: cart.change_cart(self.token, 'p06', 1, add=True), range(8)))
        self.assertEqual(cart.read_cart(self.token)['items']['p06'], 8)

    def test_injected_graph_failure_preserves_order_and_cart(self):
        cart.change_cart(self.token, 'p01', 1)
        with patch('services.checkout.record_purchase', side_effect=RuntimeError('grafo indisponível')):
            with self.assertRaises(RuntimeError):
                checkout.complete(self.token)
        frozen = cart.read_cart(self.token)
        self.assertTrue(frozen['pending'])
        with self.assertRaises(ValueError):
            cart.change_cart(self.token, 'p02', 1)
        with create_client() as mongo:
            order = get_database(mongo).pedidos.find_one({'_id': frozen['id']})
        self.assertEqual(order['status'], 'pendente_grafo')
        with patch('services.checkout.record_purchase') as record:
            result = checkout.complete(self.token)
            again = checkout.complete(self.token, result['_id'])
            self.assertEqual(record.call_count, 1)
        self.assertEqual(result['status'], 'concluido')
        self.assertEqual(again['_id'], result['_id'])
        self.assertEqual(cart.read_cart(self.token)['items'], {})
        # Repetir um pedido concluído não limpa o novo carrinho.
        cart.change_cart(self.token, 'p02', 1)
        checkout.complete(self.token, result['_id'])
        self.assertEqual(cart.read_cart(self.token)['items'], {'p02': 1})

    def test_injected_mongo_failure_recovers_draft_after_new_login(self):
        cart.change_cart(self.token, 'p03', 1)
        draft = cart.freeze(self.token)
        with patch('services.checkout.create_client', side_effect=RuntimeError('Mongo indisponível')):
            with self.assertRaises(RuntimeError):
                checkout.complete(self.token)
        cart.logout(self.token)
        new_token = cart.login(self.customer)
        self.assertTrue(any(x['_id'] == draft['_id'] for x in cart.pending_drafts(self.customer['_id'])))
        with patch('services.checkout.record_purchase'):
            result = checkout.complete(new_token, draft['_id'])
        self.assertEqual(result['status'], 'concluido')

    def test_injected_redis_cleanup_failure_is_resumable(self):
        cart.change_cart(self.token, 'p04', 2)
        with patch('services.checkout.record_purchase') as record, patch('services.checkout.clear_completed', side_effect=RuntimeError('Redis indisponível')):
            with self.assertRaises(RuntimeError):
                checkout.complete(self.token)
            self.assertEqual(record.call_count, 1)
        order_id = cart.read_cart(self.token)['id']
        with create_client() as mongo:
            self.assertEqual(get_database(mongo).pedidos.find_one({'_id': order_id})['status'], 'pendente_limpeza')
        with patch('services.checkout.record_purchase') as record:
            result = checkout.complete(self.token, order_id)
            record.assert_not_called()
        self.assertEqual(result['status'], 'concluido')
        self.assertEqual(cart.read_cart(self.token)['items'], {})

    @unittest.skipUnless(os.getenv('RUN_NEO4J_TESTS') == '1', 'Requer Neo4j configurado e RUN_NEO4J_TESTS=1')
    def test_real_graph_recommendation_rating_and_checkout(self):
        from scripts.seed_neo4j import seed as seed_graph
        seed_graph()
        peer = dict(self.customer, _id=self.tag + '_peer')
        peer_token = cart.login(peer)
        try:
            cart.change_cart(self.token, 'p01', 1)
            order = checkout.complete(self.token)
            self.assertEqual(order['status'], 'concluido')
            cart.change_cart(peer_token, 'p01', 1)
            cart.change_cart(peer_token, 'p02', 1)
            checkout.complete(peer_token)
            matches = recommendations.recommend(self.token)
            self.assertIn('p02', [x['produto_id'] for x in matches])
            recommendations.rate(self.token, 'p02', 1)
            self.assertNotIn('p02', [x['produto_id'] for x in recommendations.recommend(self.token)])
            checkout.complete(self.token, order['_id'])
            rows = recommendations.run('MATCH (:Cliente {id: $id})-[r:COMPROU]->() RETURN count(r) AS n', id=self.tag)
            self.assertEqual(rows[0]['n'], 1)
            self.assertEqual(cart.read_cart(self.token)['items'], {})
        finally:
            recommendations.run('MATCH (c:Cliente) WHERE c.id IN $ids DETACH DELETE c', ids=[self.tag, self.tag + '_peer'])


if __name__ == '__main__':
    unittest.main()
