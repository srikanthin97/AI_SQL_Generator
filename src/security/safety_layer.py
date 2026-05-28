import re
from typing import Tuple

class SQLSafetyValidator:
    """Enforces strict read-only execution policy and protects against SQL injection/unsafe operations."""

    # Keywords that are strictly forbidden in read-only analysis
    FORBIDDEN_KEYWORDS = [
        "insert", "update", "delete", "drop", "truncate", "alter", "create",
        "replace", "rename", "grant", "revoke", "upsert", "merge", "call",
        "exec", "execute", "load", "import", "copy", "attach", "detach"
    ]

    @staticmethod
    def strip_comments(sql: str) -> str:
        """Removes SQL comments (inline '--' and block '/* ... */') to prevent bypasses."""
        # Remove multiline comments
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        # Remove single line comments
        sql = re.sub(r"--.*?\n", "\n", sql)
        sql = re.sub(r"--.*?$", "", sql)
        return sql.strip()

    def is_safe(self, sql: str) -> Tuple[bool, str]:
        """
        Validates whether the SQL statement is safe and read-only.
        Returns:
            (True, "") if the SQL is safe.
            (False, "Error message") if the SQL violates safety policies.
        """
        if not sql or not sql.strip():
            return False, "Query is empty."

        # 1. Strip comments for accurate analysis
        clean_sql = self.strip_comments(sql)
        if not clean_sql:
            return False, "Query contains only comments."

        # 2. Block multiple statements (semicolon check)
        # Allow trailing semicolon, but block semicolon in the middle of text
        semicolons = [m.start() for m in re.finditer(r";", clean_sql)]
        if semicolons:
            # If there's a semicolon not at the very end of the cleaned SQL
            for idx in semicolons:
                if idx < len(clean_sql) - 1 and clean_sql[idx + 1:].strip() != "":
                    return False, "Multiple SQL statements are not allowed."

        # 3. Normalize whitespace and case for analysis
        normalized_sql = re.sub(r"\s+", " ", clean_sql).lower().strip()

        # 4. Enforce query structure - must start with SELECT or WITH (for CTEs)
        # SQLite / PostgreSQL queries must be queries, not administration or data mutation.
        if not (normalized_sql.startswith("select") or normalized_sql.startswith("with")):
            return False, "Query must start with SELECT or WITH (CTE)."

        # 5. Check for blacklisted keywords using word boundaries to avoid false positives
        for keyword in self.FORBIDDEN_KEYWORDS:
            pattern = rf"\b{keyword}\b"
            if re.search(pattern, normalized_sql):
                return False, f"Unsafe keyword detected in query: '{keyword.upper()}'."

        # 6. Basic SQL injection pattern blocking
        # e.g. blocking union-based injection trying to read database system tables (like sqlite_master or pg_shadow)
        # inside user-generated parts, though the LLM is the driver.
        system_tables_pattern = r"\b(sqlite_master|sqlite_temp_master|pg_shadow|pg_user|pg_authid|information_schema)\b"
        if re.search(system_tables_pattern, normalized_sql):
            return False, "Access to system tables or catalogs is forbidden."

        return True, ""
