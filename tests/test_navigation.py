"""Navegação real em Streamlit com MongoDB/Redis; grafo simulado explicitamente."""
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from database.mongodb import create_client
from database.redis_db import create_client as redis_client
from scripts.seed_mongodb import seed


@unittest.skipUnless(os.getenv('RUN_INTEGRATION') == '1', 'Requer MongoDB e Redis locais')
class NavigationTests(unittest.TestCase):
    def test_four_pages_with_injected_graph_response(self):
        tag = 'test_ui_' + uuid.uuid4().hex
        with patch.dict(os.environ, {'MONGODB_DATABASE': tag, 'REDIS_PREFIX': tag}):
            try:
                seed()
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=20)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len([x for x in app.button if x.label == 'Adicionar ao carrinho']), 12)
                app.text_input[0].set_value('Notebook').run()
                self.assertEqual(len([x for x in app.button if x.label == 'Adicionar ao carrinho']), 2)
                self.assertTrue(any(x.label == 'Iniciar sessão' for x in app.button), ([x.label for x in app.button], [x.value for x in app.error], [x.value for x in app.info]))
                next(x for x in app.button if x.label == 'Iniciar sessão').click().run()
                app.button(key='catalog_p01').click().run()
                app.radio(key='page').set_value('Carrinho').run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(app.number_input[0].value, 1)
                app.number_input[0].set_value(2)
                next(x for x in app.button if x.label == 'Atualizar').click().run()
                self.assertEqual(app.number_input[0].value, 2)
                with patch('services.recommendations.recommend', return_value=[]):
                    app.radio(key='page').set_value('Recomendações').run()
                    self.assertEqual(len(app.exception), 0)
                    self.assertEqual(app.slider[0].value, 5)
                app.radio(key='page').set_value('Checkout').run()
                with patch('services.checkout.record_purchase'):
                    next(x for x in app.button if x.label == 'Confirmar compra').click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(any('Compra confirmada' in x.value for x in app.success))
                app.radio(key='page').set_value('Carrinho').run()
                self.assertTrue(any('carrinho está vazio' in x.value for x in app.info))
            finally:
                with create_client() as mongo:
                    mongo.drop_database(tag)
                with redis_client() as redis:
                    for key in redis.scan_iter(match=tag + ':*'):
                        redis.delete(key)
