import os
import sys
import unittest
import pandas as pd
from sqlalchemy import create_engine

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from database.connection import DatabaseConnectionManager, SQLiteConfig
from sql_engine.executor import SQLExecutor
from visualization.recommender import ChartRecommender
from sample_data.generate_sample_db import generate_sample_database

class TestPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = "sample_data/ecommerce_test_p3.db"
        generate_sample_database(cls.db_path)
        cls.config = SQLiteConfig(db_path=cls.db_path)
        cls.manager = DatabaseConnectionManager(cls.config)
        cls.engine = cls.manager.connect()

    @classmethod
    def tearDownClass(cls):
        cls.manager.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.executor = SQLExecutor(self.engine)
        self.recommender = ChartRecommender()

    def test_safe_query_execution(self):
        sql = "SELECT * FROM users;"
        result = self.executor.execute(sql)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertEqual(result.row_count, 2)
        self.assertGreater(result.execution_time_ms, 0.0)
        self.assertIn("Alice Smith", result.data["name"].values)

    def test_unsafe_query_blocked(self):
        sql = "DELETE FROM users WHERE user_id = 1;"
        result = self.executor.execute(sql)

        self.assertFalse(result.success)
        self.assertIn("Safety Violation", result.error_message)
        self.assertEqual(result.row_count, 0)

    def test_invalid_sql_execution(self):
        sql = "SELECT non_existent_column FROM users;"
        result = self.executor.execute(sql)

        self.assertFalse(result.success)
        self.assertNotIn("Safety Violation", result.error_message)
        self.assertIsNotNone(result.error_message)
        self.assertEqual(result.row_count, 0)

    def test_chart_recommender_line(self):
        # Setup mock time-series dataframe
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=5),
            "revenue": [100.5, 120.0, 95.2, 140.8, 150.0]
        })
        
        chart_type, fig, alts = self.recommender.recommend_and_create_chart(df)
        self.assertEqual(chart_type, "line")
        self.assertIsNotNone(fig)
        self.assertIn("bar", alts)

    def test_chart_recommender_pie_and_bar(self):
        # Setup mock categorical data with low cardinality
        df_low_card = pd.DataFrame({
            "category": ["Electronics", "Books", "Clothing"],
            "orders": [12, 45, 23]
        })
        
        chart_type, fig, alts = self.recommender.recommend_and_create_chart(df_low_card)
        self.assertEqual(chart_type, "pie")
        self.assertIsNotNone(fig)
        self.assertIn("bar", alts)

        # Setup mock categorical data with high cardinality
        df_high_card = pd.DataFrame({
            "product_id": [f"P_{i}" for i in range(15)],
            "views": list(range(15))
        })
        chart_type_hc, fig_hc, alts_hc = self.recommender.recommend_and_create_chart(df_high_card)
        self.assertEqual(chart_type_hc, "bar")
        self.assertIsNotNone(fig_hc)

    def test_chart_recommender_scatter(self):
        # Setup two numeric columns
        df = pd.DataFrame({
            "price": [10.0, 20.0, 30.0, 40.0],
            "units_sold": [100, 80, 50, 20]
        })
        chart_type, fig, alts = self.recommender.recommend_and_create_chart(df)
        self.assertEqual(chart_type, "scatter")
        self.assertIsNotNone(fig)

if __name__ == "__main__":
    unittest.main()
