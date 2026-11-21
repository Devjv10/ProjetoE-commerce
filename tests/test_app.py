import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class AppTests(unittest.TestCase):
    def test_catalog_empty_without_exception(self):
        with patch('services.products.customers', return_value=[]), patch('services.products.categories', return_value=[]), patch('services.products.list_products', return_value=([], 'MongoDB')):
            app = AppTest.from_file(APP).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('Nenhum produto' in x.value for x in app.info))

    def test_database_failures_do_not_expose_exception_text(self):
        with patch('services.products.customers', side_effect=RuntimeError('senha-secreta')), patch('services.products.categories', side_effect=RuntimeError('senha-secreta')):
            app = AppTest.from_file(APP).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 2)
        self.assertTrue(all('senha-secreta' not in x.value for x in app.error))


if __name__ == '__main__':
    unittest.main()
