import re
from typing import Optional
from llm.provider import BaseLLMProvider

class NLToSQLTranslator:
    """Translates natural language questions into optimized, database-dialect-compliant SQL queries."""

    def __init__(self, llm_provider: BaseLLMProvider, dialect: str = "sqlite"):
        self.llm_provider = llm_provider
        self.dialect = dialect.lower().strip()

    def _get_system_prompt(self, schema_context: str) -> str:
        """Constructs system prompt containing instructions, schema context, and dialect settings."""
        return f"""You are a Principal AI & Data Engineer. Your task is to translate a user's natural language question into a single, syntactically correct, and optimized SQL query for a {self.dialect.upper()} database.

Use the following schema metadata to construct the query:
{schema_context}

CRITICAL INSTRUCTIONS:
1. You MUST generate ONLY read-only queries (e.g., SELECT statements or WITH CTE statements).
2. Never write commands that modify the database state (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.).
3. Return ONLY the raw SQL code. Do not include any text before, after, or explaining the SQL.
4. If you write markdown code blocks, write them as ```sql <SQL_QUERY> ```.
5. Pay attention to foreign keys for proper JOIN operations.
6. Return a query that matches exactly what the user is asking.
"""

    def clean_sql_response(self, response: str) -> str:
        """Cleans and extracts SQL query from the LLM response, stripping markdown backticks."""
        text = response.strip()
        
        # Match ```sql ... ``` block
        match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # Match ``` ... ``` block
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return text

    def translate(self, question: str, schema_context: str) -> str:
        """Translates the natural language query into SQL."""
        system_prompt = self._get_system_prompt(schema_context)
        prompt = f"User Question: {question}\nGenerate SQL query:"
        
        raw_response = self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.0
        )
        
        return self.clean_sql_response(raw_response)
