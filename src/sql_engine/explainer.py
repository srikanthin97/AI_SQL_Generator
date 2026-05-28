from typing import Optional
from llm.provider import BaseLLMProvider

class SQLExplainer:
    """Translates complex SQL statements into easy-to-understand business explanations."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider

    def explain(self, sql: str, schema_context: Optional[str] = None) -> str:
        """Generates a business explanation for the given SQL query."""
        system_prompt = """You are a helpful Data Analyst. Your job is to explain the provided SQL query in clear, non-technical business language.
Focus on explaining:
1. What data is being retrieved.
2. Which tables are joined (and what the relationship represents).
3. Any filtering conditions or constraints.
4. Any aggregations or summary statistics calculated (e.g. sums, averages, counts).

Keep your response structured, professional, and easy to read. Avoid technical jargon where possible, but maintain precision. Do not output code blocks in your explanation, only Markdown text.
"""
        prompt = f"SQL Query to explain:\n{sql}"
        if schema_context:
            prompt += f"\n\nDatabase schema context for reference:\n{schema_context}"
            
        return self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2
        )
