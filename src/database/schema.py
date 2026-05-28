from typing import Dict, Any, List
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

class DatabaseSchemaExtractor:
    """Extracts table structure, columns, types, and constraints to generate schema context for RAG pipelines."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.inspector = inspect(self.engine)

    def extract_schema(self) -> Dict[str, Any]:
        """
        Dynamically extracts schema metadata from the database.
        Returns a structured dictionary format:
        {
            "tables": {
                "table_name": {
                    "columns": [
                        {"name": "col_name", "type": "VARCHAR", "nullable": True, "default": None}, ...
                    ],
                    "primary_keys": ["col_name"],
                    "foreign_keys": [
                        {"constrained_columns": ["col_1"], "referred_table": "parent_tbl", "referred_columns": ["id"]}
                    ]
                }
            }
        }
        """
        schema_info = {"tables": {}}
        table_names = self.inspector.get_table_names()

        for table in table_names:
            columns = []
            for col in self.inspector.get_columns(table):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col.get("default") is not None else None
                })

            pk = self.inspector.get_pk_constraint(table)
            primary_keys = pk.get("constrained_columns", [])

            fks = []
            for fk in self.inspector.get_foreign_keys(table):
                fks.append({
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                })

            schema_info["tables"][table] = {
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": fks
            }

        return schema_info

    def generate_llm_prompt_context(self, schema_info: Dict[str, Any]) -> str:
        """
        Formats schema metadata dictionary into a highly readable text representation
        optimized for LLM prompt context injection.
        """
        context_lines = []
        context_lines.append("=== DATABASE SCHEMA ===")
        
        tables = schema_info.get("tables", {})
        if not tables:
            return "No tables found in database."

        for table_name, details in tables.items():
            context_lines.append(f"\nTable: {table_name}")
            
            # Form column lists
            col_strings = []
            pks = details.get("primary_keys", [])
            
            for col in details.get("columns", []):
                col_name = col["name"]
                col_type = col["type"]
                null_str = "NULL" if col["nullable"] else "NOT NULL"
                
                # Highlight if it's a primary key
                pk_marker = " (PK)" if col_name in pks else ""
                col_strings.append(f"  - {col_name} ({col_type}) {null_str}{pk_marker}")
            
            context_lines.extend(col_strings)

            # Highlight foreign keys
            fks = details.get("foreign_keys", [])
            if fks:
                context_lines.append("  Foreign Keys:")
                for fk in fks:
                    local_cols = ", ".join(fk["constrained_columns"])
                    ref_table = fk["referred_table"]
                    ref_cols = ", ".join(fk["referred_columns"])
                    context_lines.append(f"    - {local_cols} -> {ref_table}({ref_cols})")
                    
        return "\n".join(context_lines)
