import os
import sys
import unittest

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from database.connection import DatabaseConnectionManager, SQLiteConfig
from database.schema import DatabaseSchemaExtractor
from sample_data.generate_sample_db import generate_sample_database

class TestPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = "sample_data/ecommerce_test.db"
        generate_sample_database(cls.db_path)
        cls.config = SQLiteConfig(db_path=cls.db_path)
        cls.manager = DatabaseConnectionManager(cls.config)

    @classmethod
    def tearDownClass(cls):
        # Close connection manager before deleting file
        cls.manager.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def test_connection_and_validation(self):
        # Test connecting and testing connection
        self.assertTrue(self.manager.test_connection())

    def test_schema_extraction(self):
        engine = self.manager.connect()
        extractor = DatabaseSchemaExtractor(engine)
        schema_info = extractor.extract_schema()

        # Validate tables presence
        self.assertIn("users", schema_info["tables"])
        self.assertIn("products", schema_info["tables"])
        self.assertIn("orders", schema_info["tables"])
        self.assertIn("order_items", schema_info["tables"])

        # Validate column data
        users_table = schema_info["tables"]["users"]
        columns = {col["name"]: col for col in users_table["columns"]}
        
        self.assertIn("user_id", columns)
        self.assertIn("email", columns)
        
        # Verify primary key detection
        self.assertEqual(users_table["primary_keys"], ["user_id"])

        # Verify foreign keys detection
        orders_table = schema_info["tables"]["orders"]
        fks = orders_table["foreign_keys"]
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0]["referred_table"], "users")
        self.assertEqual(fks[0]["constrained_columns"], ["user_id"])
        self.assertEqual(fks[0]["referred_columns"], ["user_id"])

    def test_prompt_formatting(self):
        engine = self.manager.connect()
        extractor = DatabaseSchemaExtractor(engine)
        schema_info = extractor.extract_schema()
        context = extractor.generate_llm_prompt_context(schema_info)
        
        # Simple string matching to check formatted schema output
        self.assertIn("Table: users", context)
        self.assertIn("Table: order_items", context)
        self.assertIn("user_id (INTEGER)", context)
        self.assertIn(" (PK)", context)
        self.assertIn("user_id -> users(user_id)", context)

if __name__ == "__main__":
    unittest.main()
