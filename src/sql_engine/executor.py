import time
from typing import Optional, Any, Dict
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

from security.safety_layer import SQLSafetyValidator

class SQLExecutionResult(BaseModel):
    """Holds structured outcome details from executing a SQL query."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = Field(..., description="Flag indicating if the query completed without error")
    data: Optional[pd.DataFrame] = Field(None, description="Pandas DataFrame containing output rows")
    row_count: int = Field(0, description="Total number of rows returned")
    execution_time_ms: float = Field(0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Detailed error description if query failed")

class SQLExecutor:
    """Safely executes SQL queries against the connection engine, returning structured Pandas data."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.validator = SQLSafetyValidator()

    def execute(self, sql: str) -> SQLExecutionResult:
        """
        Validates safety rules, runs the query, tracks performance metrics,
        and returns results wrapped in SQLExecutionResult.
        """
        # 1. Enforce safety validation
        is_safe, error_msg = self.validator.is_safe(sql)
        if not is_safe:
            return SQLExecutionResult(
                success=False,
                error_message=f"Safety Violation: {error_msg}",
                row_count=0,
                execution_time_ms=0.0
            )

        start_time = time.perf_counter()
        
        try:
            with self.engine.connect() as conn:
                # Read SQL query using Pandas utility with connection context
                # Need to use sqlalchemy text() container for execution safety/compatibility
                df = pd.read_sql_query(text(sql), conn)
                
            elapsed_time_ms = (time.perf_counter() - start_time) * 1000.0
            
            return SQLExecutionResult(
                success=True,
                data=df,
                row_count=len(df),
                execution_time_ms=round(elapsed_time_ms, 2)
            )
            
        except Exception as e:
            elapsed_time_ms = (time.perf_counter() - start_time) * 1000.0
            return SQLExecutionResult(
                success=False,
                error_message=str(e),
                row_count=0,
                execution_time_ms=round(elapsed_time_ms, 2)
            )
