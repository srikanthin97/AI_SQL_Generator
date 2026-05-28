import os
import sys
import unittest
from unittest.mock import MagicMock
import logging

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from database.connection import DatabaseConnectionManager, SQLiteConfig
from analytics.agent import AIDataAnalystAgent
from utils.logging_config import setup_logging
from llm.provider import BaseLLMProvider
from sample_data.generate_sample_db import generate_sample_database

class TestPhase5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = "sample_data/ecommerce_test_p5.db"
        generate_sample_database(cls.db_path)
        cls.config = SQLiteConfig(db_path=cls.db_path)
        cls.manager = DatabaseConnectionManager(cls.config)
        cls.engine = cls.manager.connect()
        setup_logging()

    @classmethod
    def tearDownClass(cls):
        cls.manager.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.mock_provider = MagicMock(spec=BaseLLMProvider)
        self.agent = AIDataAnalystAgent(self.mock_provider, self.engine)

    def test_logging_setup(self):
        # Verify app.log file was created in logs/
        self.assertTrue(os.path.exists("logs/app.log"))

    def test_planner_node_success(self):
        # Configure mock response for JSON queries list
        mock_plan_json = """
        [
          {
            "step_number": 1,
            "description": "Get all products",
            "sql_query": "SELECT * FROM products;"
          }
        ]
        """
        self.mock_provider.generate.return_value = mock_plan_json
        
        state = {
            "question": "Which items are in database?",
            "schema_context": "=== Schema ===",
            "plan": [],
            "execution_results": [],
            "final_report": "",
            "error": None
        }
        
        output = self.agent.planner_node(state)
        self.assertEqual(len(output["plan"]), 1)
        self.assertEqual(output["plan"][0]["step_number"], 1)
        self.assertEqual(output["plan"][0]["sql_query"], "SELECT * FROM products;")
        self.assertIsNone(output["error"])

    def test_executor_node(self):
        # Feed mock state with plan steps to execute
        state = {
            "question": "Show products",
            "schema_context": "",
            "plan": [
                {
                    "step_number": 1,
                    "description": "Fetch products",
                    "sql_query": "SELECT * FROM products;"
                }
            ],
            "execution_results": [],
            "final_report": "",
            "error": None
        }
        
        output = self.agent.executor_node(state)
        results = output["execution_results"]
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[0]["row_count"], 3)  # Setup seeder writes Laptop, Mouse, Keyboard
        self.assertIn("Laptop", results[0]["data_summary"])

    def test_synthesizer_node(self):
        self.mock_provider.generate.return_value = "Executive Summary: Products are available."
        state = {
            "question": "Show products",
            "schema_context": "",
            "plan": [],
            "execution_results": [
                {
                    "step_number": 1,
                    "description": "Fetch products",
                    "sql_query": "SELECT * FROM products;",
                    "success": True,
                    "row_count": 3,
                    "data_summary": "| title |\n| Laptop |\n| Mouse |\n| Keyboard |"
                }
            ],
            "final_report": "",
            "error": None
        }
        output = self.agent.synthesizer_node(state)
        self.assertEqual(output["final_report"], "Executive Summary: Products are available.")

if __name__ == "__main__":
    unittest.main()
