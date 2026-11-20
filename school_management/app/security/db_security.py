"""
EduManage Pro - Secure Database Query & SQL Injection Prevention Utilities
Enforces:
- Strict SQL identifier validation & allowlist quoting when table/column names must be dynamic
- Wildcard escaping for LIKE/ILIKE search predicates
- Safe column/direction allowlisting for dynamic ORDER BY sorting
- Inspection helper verifying queries do not contain raw unsafe string concatenation patterns
"""

import re
from typing import Any, Iterable, Optional, Set, Tuple


class SQLSecurityError(ValueError):
    """Raised when a dynamic identifier, sort expression, or query fails SQL safety validation."""


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

_FORBIDDEN_SQL_TOKENS: Set[str] = {
    "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "UNION", "EXEC", "EXECUTE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "INTO", "OUTFILE",
}


class DatabaseSecurityValidator:
    """Central SQL injection prevention and safe query helper."""

    @staticmethod
    def validate_identifier(
        ident: str,
        *,
        allowed: Optional[Iterable[str]] = None,
        allow_sql_keyword: bool = False,
    ) -> str:
        clean = (ident or "").strip()
        if not clean or not _IDENT_RE.match(clean):
            raise SQLSecurityError(f"Invalid SQL identifier: '{ident}'")
        if not allow_sql_keyword and clean.upper() in _FORBIDDEN_SQL_TOKENS:
            raise SQLSecurityError(f"Reserved SQL keyword cannot be used as identifier: '{clean}'")
        if allowed is not None and clean not in set(allowed):
            raise SQLSecurityError(f"Identifier '{clean}' is not in the permitted allowlist.")
        return clean

    @staticmethod
    def safe_quote_identifier(ident: str, *, allowed: Optional[Iterable[str]] = None) -> str:
        clean = DatabaseSecurityValidator.validate_identifier(ident, allowed=allowed)
        return '"' + clean.replace('"', '""') + '"'

    @staticmethod
    def escape_like_pattern(search_term: str, escape_char: str = "\\") -> str:
        """Escape wildcard characters in user-supplied search strings before LIKE/ILIKE."""
        if not search_term:
            return ""
        s = str(search_term)
        s = s.replace(escape_char, escape_char + escape_char)
        s = s.replace("%", escape_char + "%")
        s = s.replace("_", escape_char + "_")
        return s

    @staticmethod
    def safe_order_by(
        model_cls: Any,
        column_name: str,
        direction: str = "asc",
        allowed_columns: Optional[Iterable[str]] = None,
    ) -> Any:
        """Resolve an ORM column sort expression strictly from an allowlist."""
        clean_col = DatabaseSecurityValidator.validate_identifier(column_name, allowed=allowed_columns)
        if not hasattr(model_cls, clean_col):
            raise SQLSecurityError(f"Column '{clean_col}' does not exist on model '{model_cls.__name__}'.")
        col_attr = getattr(model_cls, clean_col)
        dir_norm = (direction or "asc").strip().lower()
        if dir_norm not in ("asc", "desc"):
            raise SQLSecurityError(f"Invalid sort direction '{direction}'. Expected 'asc' or 'desc'.")
        return col_attr.asc() if dir_norm == "asc" else col_attr.desc()

    @staticmethod
    def check_query_safety(sql: str) -> Tuple[bool, str]:
        """Flag multi-statement injection or comment smuggling tokens inside SQL text."""
        raw = (sql or "").strip()
        if not raw:
            return False, "Empty SQL statement."
        if ";" in raw.rstrip(";"):
            return False, "Multiple SQL statements in a single call are prohibited."
        if "--" in raw or "/*" in raw or "*/" in raw:
            return False, "SQL inline comments are disallowed in dynamic statements."
        return True, "SQL check passed."
