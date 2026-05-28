import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from security.safety_layer import SQLSafetyValidator
from sql_engine.translator import NLToSQLTranslator
from sql_engine.explainer import SQLExplainer
from llm.provider import BaseLLMProvider

class TestPhase2(unittest.TestCase):
    def setUp(self):
        self.validator = SQLSafetyValidator()
        self.mock_provider = MagicMock(spec=BaseLLMProvider)

    def test_comment_stripping(self):
        sql_with_inline = "SELECT * FROM users; -- get all users"
        self.assertEqual(self.validator.strip_comments(sql_with_inline), "SELECT * FROM users;")

        sql_with_block = "SELECT /* column list */ name, email FROM users;"
        self.assertEqual(self.validator.strip_comments(sql_with_block), "SELECT  name, email FROM users;")

    def test_safety_validator_safe_queries(self):
        # Safe SELECT query
        safe_sql_1 = "SELECT user_id, name FROM users WHERE email = 'test@example.com';"
        is_safe, err = self.validator.is_safe(safe_sql_1)
        self.assertTrue(is_safe)
        self.assertEqual(err, "")

        # Safe CTE query
        safe_sql_2 = """
        WITH product_sales AS (
            SELECT product_id, SUM(quantity) as total_qty
            FROM order_items
            GROUP BY product_id
        )
        SELECT p.title, s.total_qty
        FROM products p
        JOIN product_sales s ON p.product_id = s.product_id;
        """
        is_safe, err = self.validator.is_safe(safe_sql_2)
        self.assertTrue(is_safe)

    def test_safety_validator_unsafe_queries(self):
        # Blocking DROP
        unsafe_drop = "SELECT * FROM users; DROP TABLE users;"
        is_safe, err = self.validator.is_safe(unsafe_drop)
        self.assertFalse(is_safe)
        self.assertIn("Multiple SQL statements", err)

        # Blocking single statement DROP
        unsafe_drop_single = "DROP TABLE users;"
        is_safe, err = self.validator.is_safe(unsafe_drop_single)
        self.assertFalse(is_safe)
        self.assertIn("must start with SELECT or WITH", err)

        # Blocking UPDATE (embedded keyword)
        unsafe_update = "SELECT user_id FROM users; UPDATE users SET name = 'Hacker';"
        is_safe, err = self.validator.is_safe(unsafe_update)
        self.assertFalse(is_safe)

        # Blocking UPDATE with word boundary keyword check
        unsafe_update_cte = """
        WITH cte AS (
            SELECT * FROM users
        )
        UPDATE users SET email = 'hacked';
        """
        is_safe, err = self.validator.is_safe(unsafe_update_cte)
        self.assertFalse(is_safe)
        self.assertIn("Unsafe keyword detected", err)

        # Allowing safe table name/column containing forbidden keyword part (e.g. "updated_at" or "deleted")
        safe_embedded_words = "SELECT updated_at, deleted_status FROM orders;"
        is_safe, err = self.validator.is_safe(safe_embedded_words)
        self.assertTrue(is_safe)

        # Blocking system catalog queries (SQL injection checks)
        unsafe_catalog = "SELECT * FROM sqlite_master;"
        is_safe, err = self.validator.is_safe(unsafe_catalog)
        self.assertFalse(is_safe)
        self.assertIn("system tables or catalogs", err)

    def test_translator_engine_cleaning(self):
        translator = NLToSQLTranslator(self.mock_provider)
        
        # Test markdown wrapper cleaning
        raw_output_1 = "```sql\nSELECT * FROM products;\n```"
        self.assertEqual(translator.clean_sql_response(raw_output_1), "SELECT * FROM products;")

        raw_output_2 = "```\nSELECT * FROM users;\n```"
        self.assertEqual(translator.clean_sql_response(raw_output_2), "SELECT * FROM users;")

        raw_output_3 = "SELECT * FROM orders;"
        self.assertEqual(translator.clean_sql_response(raw_output_3), "SELECT * FROM orders;")

    def test_translator_and_explainer_execution(self):
        # Setup mock behavior
        self.mock_provider.generate.side_effect = [
            "```sql\nSELECT * FROM users;\n```",  # Translation response
            "This query retrieves all columns from the users table."  # Explanation response
        ]

        translator = NLToSQLTranslator(self.mock_provider)
        explainer = SQLExplainer(self.mock_provider)

        sql = translator.translate("Show all users", "schema context")
        self.assertEqual(sql, "SELECT * FROM users;")
        self.mock_provider.generate.assert_called_once()

        self.mock_provider.generate.reset_mock()
        explanation = explainer.explain(sql, "schema context")
        self.assertEqual(explanation, "This query retrieves all columns from the users table.")
        self.mock_provider.generate.assert_called_once()

if __name__ == "__main__":
    unittest.main()
