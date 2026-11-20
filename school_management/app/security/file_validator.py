"""
EduManage Pro - Strict File Upload, Import & Backup Archive Validator
Protects against:
- Path traversal (`..`, mixed separators, drive jumps, symlink escapes)
- Null-byte & control character filename injection
- Spoofed extensions vs. binary magic-byte signatures
- Disallowed/executable file extensions (.exe, .bat, .ps1, .sh, .js, .php, .py, etc.)
- Oversized or empty payloads
"""

import os
from pathlib import Path
import re
from typing import Dict, Optional, Set, Tuple
import uuid


class FileValidationError(ValueError):
    """Raised when a file fails security, extension, path, size, or magic-byte verification."""


BLOCKED_EXECUTABLE_EXTENSIONS: Set[str] = {
    ".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".pif",
    ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".sh", ".bash", ".zsh", ".csh", ".dll", ".so", ".dylib",
    ".jar", ".class", ".py", ".pyc", ".php", ".asp", ".aspx",
    ".jsp", ".pl", ".rb", ".cgi", ".hta", ".reg", ".inf",
}

RESERVED_WINDOWS_NAMES: Set[str] = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

FILE_CATEGORY_RULES: Dict[str, Dict[str, object]] = {
    "image": {
        "extensions": {".png", ".jpg", ".jpeg", ".webp"},
        "max_bytes": 10 * 1024 * 1024,  # 10 MB
    },
    "document": {
        "extensions": {".pdf", ".png", ".jpg", ".jpeg", ".webp"},
        "max_bytes": 25 * 1024 * 1024,  # 25 MB
    },
    "migration": {
        "extensions": {".csv", ".xlsx", ".xlsm", ".db", ".sqlite", ".sqlite3"},
        "max_bytes": 100 * 1024 * 1024,  # 100 MB
    },
    "backup": {
        "extensions": {".ebk", ".zbk"},
        "max_bytes": 512 * 1024 * 1024,  # 512 MB
    },
}


class SecureFileValidator:
    """Centralized file validation & path sanitization gate."""

    @staticmethod
    def sanitize_filename(filename: str, fallback_stem: str = "file") -> str:
        raw = str(filename or "").replace("\x00", "").strip()
        # Extract only basename safely regardless of platform separators
        base = raw.replace("\\", "/").split("/")[-1].strip()
        if not base or base in (".", ".."):
            return fallback_stem
        stem, ext = os.path.splitext(base)
        clean_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
        if not clean_stem or clean_stem.upper() in RESERVED_WINDOWS_NAMES:
            clean_stem = fallback_stem
        clean_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext).lower()
        if clean_ext and not clean_ext.startswith("."):
            clean_ext = "." + clean_ext
        return f"{clean_stem[:80]}{clean_ext[:12]}"

    @staticmethod
    def safe_join(base_dir: Path, relative_or_name: str) -> Path:
        raw = str(relative_or_name or "")
        if "\x00" in raw:
            raise FileValidationError("Filename contains illegal null byte.")
        norm_parts = raw.replace("\\", "/").split("/")
        if any(p == ".." for p in norm_parts):
            raise FileValidationError("Path traversal sequence ('..') is forbidden.")
        base_resolved = Path(base_dir).resolve()
        candidate = (base_resolved / raw).resolve()
        try:
            candidate.relative_to(base_resolved)
        except ValueError as exc:
            raise FileValidationError(f"Resolved path escapes target directory boundary: {raw}") from exc
        return candidate

    @staticmethod
    def build_safe_storage_path(base_dir: Path, prefix: str, original_filename: str) -> Path:
        safe_name = SecureFileValidator.sanitize_filename(original_filename, fallback_stem=prefix)
        safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "", prefix) or "item"
        unique_name = f"{safe_prefix}_{uuid.uuid4().hex[:8]}_{safe_name}"
        return SecureFileValidator.safe_join(base_dir, unique_name)

    @staticmethod
    def _check_magic_bytes(path: Path, ext: str) -> None:
        with open(path, "rb") as fh:
            header = fh.read(32)

        if not header:
            raise FileValidationError("File is empty (0 bytes).")

        if ext == ".png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise FileValidationError("File extension is .png but magic bytes do not match PNG signature.")
        elif ext in (".jpg", ".jpeg"):
            if not header.startswith(b"\xff\xd8\xff"):
                raise FileValidationError("File extension is JPEG but magic bytes do not match JPEG signature.")
        elif ext == ".webp":
            if not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
                raise FileValidationError("File extension is .webp but magic bytes do not match WEBP signature.")
        elif ext == ".pdf":
            if not header.lstrip().startswith(b"%PDF-"):
                raise FileValidationError("File extension is .pdf but magic bytes do not match PDF header (%PDF-).")
        elif ext in (".xlsx", ".xlsm"):
            if not header.startswith(b"PK\x03\x04"):
                raise FileValidationError("Excel workbook signature invalid (expected ZIP/OOXML container).")
        elif ext in (".db", ".sqlite", ".sqlite3"):
            if not header.startswith(b"SQLite format 3\x00"):
                raise FileValidationError("Database file does not start with valid 'SQLite format 3' header.")
        elif ext in (".ebk", ".zbk"):
            if not header.startswith(b"EDBK"):
                raise FileValidationError("Backup archive missing required EDBK container header.")
        elif ext == ".csv":
            # Ensure CSV is valid UTF-8 text without binary null bytes or executable MZ/ELF/ZIP signatures
            if header.startswith((b"MZ", b"\x7fELF", b"PK\x03\x04", b"%PDF-")):
                raise FileValidationError("CSV file contains disguised binary/executable file signature.")
            with open(path, "rb") as fh:
                sample = fh.read(65536)
            if b"\x00" in sample:
                raise FileValidationError("CSV file contains binary null bytes.")
            try:
                sample.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise FileValidationError("CSV file must be valid UTF-8 encoded text.") from exc

    @classmethod
    def validate_existing_file(
        cls,
        file_path: str,
        category: str,
        *,
        allowed_extensions: Optional[Set[str]] = None,
        max_bytes: Optional[int] = None,
        allow_symlink: bool = False,
    ) -> Tuple[Path, str, int]:
        """
        Validate an existing file on disk before reading, importing, copying, or restoring.
        Returns: (resolved_path, normalized_extension, size_bytes)
        """
        raw = str(file_path or "").strip()
        if not raw:
            raise FileValidationError("File path cannot be empty.")
        if "\x00" in raw:
            raise FileValidationError("Illegal null byte detected in file path.")
        if any(ord(c) < 32 for c in raw):
            raise FileValidationError("Control characters are not allowed in file paths.")

        p = Path(raw)
        if not p.exists():
            raise FileNotFoundError(f"Selected file does not exist: {raw}")
        if not allow_symlink and p.is_symlink():
            raise FileValidationError("Symbolic links are blocked for security reasons.")
        if not p.is_file():
            raise FileValidationError(f"Selected path is not a regular file: {raw}")

        ext = p.suffix.lower()
        if not ext:
            raise FileValidationError("Files without an extension are not permitted.")
        if ext in BLOCKED_EXECUTABLE_EXTENSIONS:
            raise FileValidationError(f"Executable or script file type '{ext}' is strictly blocked.")

        rules = FILE_CATEGORY_RULES.get(category)
        if not rules and allowed_extensions is None:
            raise ValueError(f"Unknown file validation category: {category}")

        eff_exts: Set[str] = allowed_extensions if allowed_extensions is not None else rules["extensions"]  # type: ignore[assignment]
        eff_max: int = max_bytes if max_bytes is not None else int(rules["max_bytes"])  # type: ignore[index]

        if ext not in eff_exts:
            raise FileValidationError(
                f"File extension '{ext}' is not permitted for '{category}'. Allowed: {', '.join(sorted(eff_exts))}"
            )

        size_bytes = p.stat().st_size
        if size_bytes <= 0:
            raise FileValidationError("Uploaded file is empty (0 bytes).")
        if size_bytes > eff_max:
            raise FileValidationError(
                f"File size ({size_bytes / (1024 * 1024):.2f} MB) exceeds maximum allowed limit "
                f"({eff_max / (1024 * 1024):.1f} MB) for '{category}'."
            )

        cls._check_magic_bytes(p, ext)
        return p.resolve(), ext, size_bytes
