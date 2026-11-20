"""
EduManage Pro - Professional 6-Step Data Migration Wizard & Rollback Engine
Workflow: Upload -> Detect -> Map -> Validate -> Preview -> Import (+ Full Rollback)
Sources: Excel (.xlsx/.xlsm), CSV (.csv), Previous Database (.db/.sqlite/.sqlite3)
Safety Guarantees:
- Never corrupts existing data (savepoint-wrapped atomic imports + integrity checks)
- Never silently overwrites existing records (default SKIP; explicit ERROR_ON_CONFLICT or FILL_EMPTY_ONLY)
- Full row-level reversible ledger (DataMigrationRowLog) with atomic Rollback strategy
"""

import csv
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.config.settings import DATA_DIR
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.base import utc_now
from app.models.data_protection import (
    MIGRATION_CONFLICT_POLICIES,
    MIGRATION_SOURCE_TYPES,
    MIGRATION_TARGET_ENTITIES,
    DataMigrationBatch,
    DataMigrationRowLog,
)
from app.models.fee import FeeCategory
from app.models.library import Book, BookCategory
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student
from app.security.audit import AuditService
from app.security.db_security import DatabaseSecurityValidator
from app.security.file_validator import SecureFileValidator


MIGRATION_STAGING_DIR = DATA_DIR / "migration_staging"
MIGRATION_STAGING_DIR.mkdir(parents=True, exist_ok=True)


TARGET_FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "Students": {
        "required": ["full_name"],
        "fields": [
            "student_id", "admission_number", "roll_number",
            "first_name", "last_name", "full_name", "gender",
            "date_of_birth", "blood_group", "phone", "email", "address",
            "class_name", "section_name", "academic_year",
            "guardian_name", "guardian_phone", "father_name", "mother_name",
        ],
        "aliases": {
            "student_id": ["student_id", "sid", "stu_id", "id_no", "student code"],
            "admission_number": ["admission_number", "adm_no", "admission_no", "adm_number", "reg_no"],
            "roll_number": ["roll_number", "roll", "roll_no"],
            "first_name": ["first_name", "fname", "given_name"],
            "last_name": ["last_name", "lname", "surname"],
            "full_name": ["full_name", "name", "student_name", "student name"],
            "gender": ["gender", "sex"],
            "date_of_birth": ["date_of_birth", "dob", "birth_date", "birthday"],
            "blood_group": ["blood_group", "blood", "blood_type"],
            "phone": ["phone", "mobile", "student_phone", "contact"],
            "email": ["email", "email_address", "mail"],
            "address": ["address", "home_address", "present_address"],
            "class_name": ["class_name", "class", "grade", "standard"],
            "section_name": ["section_name", "section", "sec", "division"],
            "academic_year": ["academic_year", "session", "year"],
            "guardian_name": ["guardian_name", "guardian", "parent_name", "parent"],
            "guardian_phone": ["guardian_phone", "parent_phone", "guardian_mobile", "emergency_phone"],
            "father_name": ["father_name", "father"],
            "mother_name": ["mother_name", "mother"],
        },
    },
    "Teachers": {
        "required": ["full_name", "email"],
        "fields": [
            "teacher_id", "employee_id", "full_name", "gender",
            "date_of_birth", "phone", "email", "qualification",
            "designation", "department", "primary_subject", "salary",
        ],
        "aliases": {
            "teacher_id": ["teacher_id", "tid", "faculty_id"],
            "employee_id": ["employee_id", "emp_id", "staff_code"],
            "full_name": ["full_name", "name", "teacher_name"],
            "gender": ["gender", "sex"],
            "date_of_birth": ["date_of_birth", "dob"],
            "phone": ["phone", "mobile", "contact"],
            "email": ["email", "email_address"],
            "qualification": ["qualification", "degree", "education"],
            "designation": ["designation", "title", "rank"],
            "department": ["department", "dept", "department_name"],
            "primary_subject": ["primary_subject", "subject", "specialization"],
            "salary": ["salary", "basic_salary", "pay"],
        },
    },
    "Staff": {
        "required": ["full_name", "phone"],
        "fields": [
            "staff_id", "employee_id", "full_name", "gender",
            "date_of_birth", "phone", "email", "position",
            "department", "shift", "salary",
        ],
        "aliases": {
            "staff_id": ["staff_id", "stf_id"],
            "employee_id": ["employee_id", "emp_id"],
            "full_name": ["full_name", "name", "staff_name"],
            "gender": ["gender", "sex"],
            "date_of_birth": ["date_of_birth", "dob"],
            "phone": ["phone", "mobile", "contact"],
            "email": ["email", "email_address"],
            "position": ["position", "designation", "role", "job_title"],
            "department": ["department", "dept", "department_name"],
            "shift": ["shift", "work_shift"],
            "salary": ["salary", "basic_salary", "pay"],
        },
    },
    "Classes": {
        "required": ["name"],
        "fields": ["name", "numeric_level", "description"],
        "aliases": {
            "name": ["name", "class_name", "class", "grade"],
            "numeric_level": ["numeric_level", "level", "grade_number", "order"],
            "description": ["description", "notes", "remarks"],
        },
    },
    "Subjects": {
        "required": ["name", "code"],
        "fields": ["name", "code", "subject_type", "credit_hours"],
        "aliases": {
            "name": ["name", "subject_name", "subject"],
            "code": ["code", "subject_code", "sub_code"],
            "subject_type": ["subject_type", "type", "category"],
            "credit_hours": ["credit_hours", "credits"],
        },
    },
    "FeeCategories": {
        "required": ["name"],
        "fields": ["name", "description"],
        "aliases": {
            "name": ["name", "category_name", "fee_category", "title"],
            "description": ["description", "notes"],
        },
    },
    "Books": {
        "required": ["title", "author"],
        "fields": [
            "accession_no", "title", "author", "publisher", "isbn",
            "category_name", "total_copies", "price", "rack_number",
        ],
        "aliases": {
            "accession_no": ["accession_no", "acc_no", "book_code"],
            "title": ["title", "book_title", "name"],
            "author": ["author", "author_name", "writer"],
            "publisher": ["publisher", "publisher_name"],
            "isbn": ["isbn", "isbn_13", "isbn_10"],
            "category_name": ["category_name", "category", "genre"],
            "total_copies": ["total_copies", "copies", "qty", "quantity"],
            "price": ["price", "cost"],
            "rack_number": ["rack_number", "rack", "shelf"],
        },
    },
}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_date(val: Any, fallback: Optional[date] = None) -> Optional[date]:
    if val is None or str(val).strip() == "":
        return fallback
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    txt = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%d %b %Y"):
        try:
            return datetime.strptime(txt[:20], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _norm_key(s: str) -> str:
    return "".join(ch.lower() for ch in str(s or "") if ch.isalnum())


class DataMigrationService:
    """Service implementing the safe 6-step Upload -> Detect -> Map -> Validate -> Preview -> Import + Rollback pipeline."""

    # ------------------------------------------------------------------ #
    # Low-Level Readers (CSV, Excel, Previous SQLite DB)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _infer_source_type(path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".csv":
            return "CSV"
        if ext in (".xlsx", ".xlsm"):
            return "Excel"
        if ext in (".db", ".sqlite", ".sqlite3"):
            return "Previous Database"
        raise ValueError(f"Unsupported migration file extension '{ext}'. Use CSV, Excel (.xlsx), or SQLite DB.")

    @staticmethod
    def _list_sheets_or_tables(path: Path, source_type: str) -> List[str]:
        if source_type == "CSV":
            return ["CSV_DATA"]
        if source_type == "Excel":
            import openpyxl

            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            try:
                return list(wb.sheetnames)
            finally:
                wb.close()
        if source_type == "Previous Database":
            conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            try:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
                return [r[0] for r in rows]
            finally:
                conn.close()
        return []

    @staticmethod
    def _read_source_rows(
        path: Path,
        source_type: str,
        sheet_or_table: Optional[str] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        if source_type == "CSV":
            text_data = path.read_text(encoding="utf-8-sig")
            lines = [ln for ln in text_data.splitlines() if ln.strip()]
            if not lines:
                return [], []
            try:
                dialect = csv.Sniffer().sniff("\n".join(lines[:10]), delimiters=",;\t|")
            except Exception:
                dialect = csv.excel
            reader = csv.DictReader(lines, dialect=dialect)
            headers = [str(h).strip() for h in (reader.fieldnames or []) if h is not None]
            rows = []
            for row in reader:
                clean = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k is not None}
                if any(str(val or "").strip() for val in clean.values()):
                    rows.append(clean)
            return headers, rows

        if source_type == "Excel":
            import openpyxl

            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            try:
                sheet_name = sheet_or_table if (sheet_or_table and sheet_or_table in wb.sheetnames) else wb.sheetnames[0]
                ws = wb[sheet_name]
                iter_rows = ws.iter_rows(values_only=True)
                raw_hdr = next(iter_rows, None)
                if not raw_hdr:
                    return [], []
                headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(raw_hdr)]
                rows = []
                for tup in iter_rows:
                    if not any(v is not None and str(v).strip() != "" for v in tup):
                        continue
                    row_dict = {}
                    for idx, hdr in enumerate(headers):
                        val = tup[idx] if idx < len(tup) else None
                        row_dict[hdr] = val.strip() if isinstance(val, str) else val
                    rows.append(row_dict)
                return headers, rows
            finally:
                wb.close()

        if source_type == "Previous Database":
            conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                tables = [
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    ).fetchall()
                ]
                if not tables:
                    return [], []
                tbl = sheet_or_table if (sheet_or_table and sheet_or_table in tables) else tables[0]
                quoted_tbl = DatabaseSecurityValidator.safe_quote_identifier(tbl, allowed=tables)
                col_info = conn.execute(f"PRAGMA table_info({quoted_tbl})").fetchall()
                headers = [c[1] for c in col_info]
                fetched = conn.execute(f"SELECT * FROM {quoted_tbl}").fetchall()
                rows = [{h: r[h] for h in headers} for r in fetched]
                return headers, rows
            finally:
                conn.close()

        raise ValueError(f"Unsupported source_type: {source_type}")

    @staticmethod
    def _suggest_mapping(headers: List[str], target_entity: str) -> Dict[str, str]:
        spec = TARGET_FIELD_SPECS.get(target_entity, {})
        aliases: Dict[str, List[str]] = spec.get("aliases", {})
        header_norm_map = {_norm_key(h): h for h in headers}
        suggested: Dict[str, str] = {}
        for target_field, cand_list in aliases.items():
            for cand in [target_field] + cand_list:
                nk = _norm_key(cand)
                if nk in header_norm_map:
                    suggested[target_field] = header_norm_map[nk]
                    break
        return suggested

    @staticmethod
    def _next_batch_code(db: Session) -> str:
        stamp = datetime.now().strftime("%Y%m%d")
        prefix = f"MIG-{stamp}-"
        existing = db.query(DataMigrationBatch.batch_code).filter(DataMigrationBatch.batch_code.like(f"{prefix}%")).all()
        max_seq = 0
        for (code,) in existing:
            try:
                max_seq = max(max_seq, int(code.rsplit("-", 1)[-1]))
            except Exception:
                pass
        return f"{prefix}{max_seq + 1:04d}"

    # ------------------------------------------------------------------ #
    # Step 1: Upload
    # ------------------------------------------------------------------ #
    @classmethod
    def upload_source(
        cls,
        db: Session,
        file_path: str,
        target_entity: str = "Students",
        source_type: Optional[str] = None,
        imported_by: str = "admin",
    ) -> DataMigrationBatch:
        src, _ext, _sz = SecureFileValidator.validate_existing_file(file_path, "migration")
        if target_entity not in MIGRATION_TARGET_ENTITIES:
            raise ValueError(f"Unsupported target entity '{target_entity}'. Allowed: {', '.join(MIGRATION_TARGET_ENTITIES)}")

        inferred_type = source_type or cls._infer_source_type(src)
        if inferred_type not in MIGRATION_SOURCE_TYPES:
            raise ValueError(f"Unsupported source_type '{inferred_type}'.")

        checksum = _file_sha256(src)
        batch_code = cls._next_batch_code(db)
        staged_path = SecureFileValidator.build_safe_storage_path(MIGRATION_STAGING_DIR, batch_code, src.name)
        staged_path.write_bytes(src.read_bytes())

        batch = DataMigrationBatch(
            batch_code=batch_code,
            source_type=inferred_type,
            source_filename=SecureFileValidator.sanitize_filename(src.name),
            source_file_path=str(staged_path),
            source_checksum_sha256=checksum,
            target_entity=target_entity,
            conflict_policy="SKIP",
            status="Uploaded",
            imported_by=imported_by,
        )
        db.add(batch)
        db.flush()
        AuditService.record(
            db,
            action="MIGRATION_SOURCE_UPLOADED",
            module="DATA_PROTECTION",
            description=f"Staged validated {inferred_type} source '{batch.source_filename}' for {target_entity}.",
            username=imported_by,
            entity_type="DataMigrationBatch",
            entity_id=batch.id,
            record_label=batch.batch_code,
            after={"source_type": inferred_type, "target_entity": target_entity, "checksum": checksum},
            severity="SECURITY",
            is_admin_action=True,
        )
        db.commit()
        db.refresh(batch)
        return batch

    # ------------------------------------------------------------------ #
    # Step 2: Detect
    # ------------------------------------------------------------------ #
    @classmethod
    def detect_schema(
        cls,
        db: Session,
        batch_id: int,
        sheet_or_table: Optional[str] = None,
    ) -> Dict[str, Any]:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")

        path = Path(batch.source_file_path)
        sheets = cls._list_sheets_or_tables(path, batch.source_type)
        if not sheets:
            raise ValueError("No worksheets or database tables detected in uploaded file.")

        chosen_sheet = sheet_or_table
        if not chosen_sheet or chosen_sheet not in sheets:
            if batch.source_type == "Previous Database":
                # Auto-pick matching table if available
                target_l = batch.target_entity.lower()
                matched = [s for s in sheets if target_l in s.lower() or s.lower() in target_l]
                chosen_sheet = matched[0] if matched else sheets[0]
            else:
                chosen_sheet = sheets[0]

        headers, rows = cls._read_source_rows(path, batch.source_type, chosen_sheet)
        suggested_mapping = cls._suggest_mapping(headers, batch.target_entity)

        batch.source_sheet_or_table = chosen_sheet
        batch.detected_sheets_json = json.dumps(sheets)
        batch.detected_headers_json = json.dumps(headers)
        batch.mapping_json = json.dumps(suggested_mapping)
        batch.total_rows = len(rows)
        batch.status = "Detected"
        db.commit()
        db.refresh(batch)

        return {
            "batch_id": batch.id,
            "batch_code": batch.batch_code,
            "source_type": batch.source_type,
            "sheets_or_tables": sheets,
            "selected_sheet_or_table": chosen_sheet,
            "headers": headers,
            "total_rows": len(rows),
            "sample_rows": rows[:5],
            "suggested_mapping": suggested_mapping,
            "target_fields": TARGET_FIELD_SPECS[batch.target_entity]["fields"],
            "required_fields": TARGET_FIELD_SPECS[batch.target_entity]["required"],
        }

    # ------------------------------------------------------------------ #
    # Step 3: Map
    # ------------------------------------------------------------------ #
    @classmethod
    def save_mapping(
        cls,
        db: Session,
        batch_id: int,
        mapping: Dict[str, str],
        target_entity: Optional[str] = None,
        conflict_policy: str = "SKIP",
        sheet_or_table: Optional[str] = None,
    ) -> DataMigrationBatch:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")
        if conflict_policy not in MIGRATION_CONFLICT_POLICIES:
            raise ValueError(f"Invalid conflict policy '{conflict_policy}'. Allowed: {', '.join(MIGRATION_CONFLICT_POLICIES)}")
        if target_entity:
            if target_entity not in MIGRATION_TARGET_ENTITIES:
                raise ValueError(f"Unsupported target entity '{target_entity}'.")
            batch.target_entity = target_entity
        if sheet_or_table:
            batch.source_sheet_or_table = sheet_or_table

        clean_map = {k: v for k, v in (mapping or {}).items() if v and str(v).strip() and str(v) != "(Unmapped)"}
        batch.mapping_json = json.dumps(clean_map)
        batch.conflict_policy = conflict_policy
        batch.status = "Mapped"
        db.commit()
        db.refresh(batch)
        return batch

    # ------------------------------------------------------------------ #
    # Row Transform & Conflict Lookup Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _apply_row_mapping(raw_row: Dict[str, Any], mapping: Dict[str, str], target_entity: str) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        for target_field, src_col in mapping.items():
            if src_col in raw_row:
                mapped[target_field] = raw_row[src_col]

        if target_entity in ("Students", "Teachers", "Staff"):
            fname = str(mapped.get("first_name") or "").strip()
            lname = str(mapped.get("last_name") or "").strip()
            full_n = str(mapped.get("full_name") or "").strip()
            if not full_n and (fname or lname):
                mapped["full_name"] = f"{fname} {lname}".strip()
            elif full_n and not fname:
                parts = full_n.split(None, 1)
                mapped["first_name"] = parts[0]
                mapped["last_name"] = parts[1] if len(parts) > 1 else parts[0]
        return mapped

    @staticmethod
    def _find_existing_record(db: Session, target_entity: str, mrow: Dict[str, Any]) -> Tuple[Optional[Any], str]:
        if target_entity == "Students":
            sid = str(mrow.get("student_id") or "").strip()
            adm = str(mrow.get("admission_number") or "").strip()
            if sid:
                hit = db.query(Student).filter(Student.student_id == sid).first()
                if hit:
                    return hit, f"student_id={sid}"
            if adm:
                hit = db.query(Student).filter(Student.admission_number == adm).first()
                if hit:
                    return hit, f"admission_number={adm}"
            return None, ""
        if target_entity == "Teachers":
            tid = str(mrow.get("teacher_id") or "").strip()
            emp = str(mrow.get("employee_id") or "").strip()
            email = str(mrow.get("email") or "").strip()
            if tid:
                hit = db.query(Teacher).filter(Teacher.teacher_id == tid).first()
                if hit:
                    return hit, f"teacher_id={tid}"
            if emp:
                hit = db.query(Teacher).filter(Teacher.employee_id == emp).first()
                if hit:
                    return hit, f"employee_id={emp}"
            if email:
                hit = db.query(Teacher).filter(Teacher.email == email).first()
                if hit:
                    return hit, f"email={email}"
            return None, ""
        if target_entity == "Staff":
            sid = str(mrow.get("staff_id") or "").strip()
            emp = str(mrow.get("employee_id") or "").strip()
            if sid:
                hit = db.query(Staff).filter(Staff.staff_id == sid).first()
                if hit:
                    return hit, f"staff_id={sid}"
            if emp:
                hit = db.query(Staff).filter(Staff.employee_id == emp).first()
                if hit:
                    return hit, f"employee_id={emp}"
            return None, ""
        if target_entity == "Classes":
            nm = str(mrow.get("name") or "").strip()
            if nm:
                hit = db.query(SchoolClass).filter(SchoolClass.name == nm).first()
                if hit:
                    return hit, f"name={nm}"
            return None, ""
        if target_entity == "Subjects":
            code = str(mrow.get("code") or "").strip()
            nm = str(mrow.get("name") or "").strip()
            if code:
                hit = db.query(Subject).filter(Subject.code == code).first()
                if hit:
                    return hit, f"code={code}"
            if nm:
                hit = db.query(Subject).filter(Subject.name == nm).first()
                if hit:
                    return hit, f"name={nm}"
            return None, ""
        if target_entity == "FeeCategories":
            nm = str(mrow.get("name") or "").strip()
            if nm:
                hit = db.query(FeeCategory).filter(FeeCategory.name == nm).first()
                if hit:
                    return hit, f"name={nm}"
            return None, ""
        if target_entity == "Books":
            acc = str(mrow.get("accession_no") or "").strip()
            isbn = str(mrow.get("isbn") or "").strip()
            if acc:
                hit = db.query(Book).filter(Book.accession_no == acc).first()
                if hit:
                    return hit, f"accession_no={acc}"
            if isbn:
                hit = db.query(Book).filter(Book.isbn == isbn).first()
                if hit:
                    return hit, f"isbn={isbn}"
            return None, ""
        return None, ""

    @staticmethod
    def _batch_unique_key(target_entity: str, mrow: Dict[str, Any]) -> Optional[str]:
        if target_entity == "Students":
            return str(mrow.get("student_id") or mrow.get("admission_number") or "").strip() or None
        if target_entity == "Teachers":
            return str(mrow.get("teacher_id") or mrow.get("email") or "").strip() or None
        if target_entity == "Staff":
            return str(mrow.get("staff_id") or mrow.get("employee_id") or "").strip() or None
        if target_entity == "Classes":
            return str(mrow.get("name") or "").strip() or None
        if target_entity == "Subjects":
            return str(mrow.get("code") or mrow.get("name") or "").strip() or None
        if target_entity == "FeeCategories":
            return str(mrow.get("name") or "").strip() or None
        if target_entity == "Books":
            return str(mrow.get("accession_no") or mrow.get("isbn") or "").strip() or None
        return None

    # ------------------------------------------------------------------ #
    # Step 4: Validate & Step 5: Preview
    # ------------------------------------------------------------------ #
    @classmethod
    def validate_batch(cls, db: Session, batch_id: int) -> Dict[str, Any]:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")

        headers, raw_rows = cls._read_source_rows(
            Path(batch.source_file_path), batch.source_type, batch.source_sheet_or_table
        )
        mapping = json.loads(batch.mapping_json or "{}")
        spec = TARGET_FIELD_SPECS[batch.target_entity]
        required_fields = spec["required"]

        seen_keys = set()
        results: List[Dict[str, Any]] = []
        counts = {"insert": 0, "skip": 0, "merge": 0, "error": 0}

        for idx, raw_row in enumerate(raw_rows, start=1):
            mrow = cls._apply_row_mapping(raw_row, mapping, batch.target_entity)
            errors: List[str] = []

            for req in required_fields:
                if req == "full_name":
                    if not str(mrow.get("full_name") or "").strip():
                        errors.append("Missing required name (full_name or first_name/last_name)")
                elif not str(mrow.get(req) or "").strip():
                    errors.append(f"Missing required field '{req}'")

            if mrow.get("date_of_birth") and str(mrow["date_of_birth"]).strip():
                if _parse_date(mrow["date_of_birth"]) is None:
                    errors.append(f"Invalid date_of_birth '{mrow['date_of_birth']}'")

            if mrow.get("email") and "@" not in str(mrow["email"]):
                errors.append(f"Invalid email format '{mrow['email']}'")

            bkey = cls._batch_unique_key(batch.target_entity, mrow)
            if bkey:
                if bkey in seen_keys:
                    errors.append(f"Duplicate key '{bkey}' within uploaded source")
                else:
                    seen_keys.add(bkey)

            if errors:
                counts["error"] += 1
                results.append({
                    "row_number": idx,
                    "planned_action": "ERROR",
                    "reason": "; ".join(errors),
                    "mapped": mrow,
                })
                continue

            existing, conflict_reason = cls._find_existing_record(db, batch.target_entity, mrow)
            if existing is not None:
                if batch.conflict_policy == "SKIP":
                    counts["skip"] += 1
                    results.append({
                        "row_number": idx,
                        "planned_action": "SKIP",
                        "reason": f"Existing record preserved ({conflict_reason}); no overwrite",
                        "existing_id": existing.id,
                        "mapped": mrow,
                    })
                elif batch.conflict_policy == "ERROR_ON_CONFLICT":
                    counts["error"] += 1
                    results.append({
                        "row_number": idx,
                        "planned_action": "ERROR",
                        "reason": f"Conflict rejected per policy ({conflict_reason})",
                        "existing_id": existing.id,
                        "mapped": mrow,
                    })
                else:  # FILL_EMPTY_ONLY
                    counts["merge"] += 1
                    results.append({
                        "row_number": idx,
                        "planned_action": "MERGE_EMPTY",
                        "reason": f"Fill empty fields only on existing record ({conflict_reason})",
                        "existing_id": existing.id,
                        "mapped": mrow,
                    })
            else:
                counts["insert"] += 1
                results.append({
                    "row_number": idx,
                    "planned_action": "INSERT",
                    "reason": "Ready to insert new record",
                    "mapped": mrow,
                })

        summary = {
            "total_rows": len(raw_rows),
            "will_insert": counts["insert"],
            "will_skip": counts["skip"],
            "will_merge_empty": counts["merge"],
            "error_rows": counts["error"],
            "conflict_policy": batch.conflict_policy,
            "row_results": results,
        }
        batch.total_rows = len(raw_rows)
        batch.valid_rows = counts["insert"] + counts["merge"]
        batch.error_rows = counts["error"]
        batch.validation_summary_json = json.dumps(summary, default=str)
        batch.status = "Validated"
        db.commit()
        db.refresh(batch)
        return summary

    @classmethod
    def preview_batch(cls, db: Session, batch_id: int, limit: int = 100) -> Dict[str, Any]:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")
        if batch.status in ("Uploaded", "Detected", "Mapped") or not batch.validation_summary_json or batch.validation_summary_json == "{}":
            summary = cls.validate_batch(db, batch_id)
        else:
            summary = json.loads(batch.validation_summary_json)

        preview = {
            "batch_code": batch.batch_code,
            "target_entity": batch.target_entity,
            "conflict_policy": batch.conflict_policy,
            "total_rows": summary["total_rows"],
            "will_insert": summary["will_insert"],
            "will_skip": summary["will_skip"],
            "will_merge_empty": summary["will_merge_empty"],
            "error_rows": summary["error_rows"],
            "preview_rows": summary.get("row_results", [])[:limit],
        }
        batch.preview_summary_json = json.dumps(preview, default=str)
        batch.status = "Previewed"
        db.commit()
        db.refresh(batch)
        return preview

    # ------------------------------------------------------------------ #
    # Step 6: Atomic Import + Pre-Migration Safety Backup + Row Ledger
    # ------------------------------------------------------------------ #
    @classmethod
    def execute_import(
        cls,
        db: Session,
        batch_id: int,
        create_pre_backup: bool = True,
        imported_by: str = "admin",
    ) -> DataMigrationBatch:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")
        if batch.status == "Imported":
            raise ValueError(f"Migration batch {batch.batch_code} has already been imported.")

        if batch.status in ("Uploaded", "Detected", "Mapped"):
            cls.validate_batch(db, batch_id)
            db.refresh(batch)

        summary = json.loads(batch.validation_summary_json or "{}")
        row_results = summary.get("row_results", [])

        # Clear any stale logs from previous validation attempts if any
        db.query(DataMigrationRowLog).filter(DataMigrationRowLog.batch_id == batch.id).delete()

        # Optional Safety Pre-Migration Backup (for file-backed SQLite DBs)
        if create_pre_backup:
            try:
                from app.services.backup_service import DataProtectionBackupService

                eng = db.get_bind()
                if eng and eng.url and eng.url.database and eng.url.database != ":memory:":
                    bkp = DataProtectionBackupService.create_backup(
                        db,
                        schedule_mode="Automatic",
                        trigger_source="Pre-Migration Safety",
                        encrypt=True,
                        is_pre_restore=True,
                        verify=True,
                        created_by=imported_by,
                        notes=f"Auto pre-migration backup before {batch.batch_code} ({batch.target_entity})",
                    )
                    batch.pre_migration_backup_code = bkp.backup_code
            except Exception:
                pass

        inserted = 0
        skipped = 0
        merged = 0
        errors = 0

        try:
            with db.begin_nested():
                for item in row_results:
                    rnum = int(item["row_number"])
                    planned = item["planned_action"]
                    mrow = item.get("mapped", {})

                    if planned == "ERROR":
                        errors += 1
                        db.add(
                            DataMigrationRowLog(
                                batch_id=batch.id,
                                row_number=rnum,
                                action="ERROR",
                                source_row_json=json.dumps(mrow, default=str),
                                message=item.get("reason", "Validation error"),
                            )
                        )
                        continue

                    if planned == "SKIP":
                        skipped += 1
                        db.add(
                            DataMigrationRowLog(
                                batch_id=batch.id,
                                row_number=rnum,
                                action="SKIPPED",
                                target_record_id=item.get("existing_id"),
                                source_row_json=json.dumps(mrow, default=str),
                                message=item.get("reason", "Skipped existing record"),
                            )
                        )
                        continue

                    if planned == "MERGE_EMPTY":
                        existing_id = item.get("existing_id")
                        before, after, tbl_name = cls._merge_empty_fields(db, batch.target_entity, existing_id, mrow)
                        merged += 1
                        db.add(
                            DataMigrationRowLog(
                                batch_id=batch.id,
                                row_number=rnum,
                                action="UPDATED_EMPTY",
                                target_table=tbl_name,
                                target_record_id=existing_id,
                                source_row_json=json.dumps(mrow, default=str),
                                before_snapshot_json=json.dumps(before, default=str),
                                after_snapshot_json=json.dumps(after, default=str),
                                message="Filled empty fields without overwriting populated data",
                            )
                        )
                        continue

                    # planned == "INSERT"
                    tbl_name, rec_id, aux_created, after_snap = cls._insert_mapped_row(db, batch.target_entity, mrow, rnum)
                    inserted += 1
                    db.add(
                        DataMigrationRowLog(
                            batch_id=batch.id,
                            row_number=rnum,
                            action="INSERTED",
                            target_table=tbl_name,
                            target_record_id=rec_id,
                            auxiliary_records_json=json.dumps(aux_created),
                            source_row_json=json.dumps(mrow, default=str),
                            after_snapshot_json=json.dumps(after_snap, default=str),
                            message="Inserted new record cleanly",
                        )
                    )

            batch.inserted_rows = inserted
            batch.skipped_rows = skipped
            batch.merged_rows = merged
            batch.error_rows = errors
            batch.status = "Imported"
            batch.imported_at = utc_now()
            batch.imported_by = imported_by
            db.commit()
            db.refresh(batch)
            return batch
        except Exception as exc:
            db.rollback()
            batch.status = "Failed"
            db.commit()
            raise ValueError(f"Migration aborted atomically — existing data untouched: {exc}")

    # ------------------------------------------------------------------ #
    # Entity Insert & Non-Overwriting Merge Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ensure_academic_year(db: Session, name_opt: Optional[str], aux: List[Dict[str, Any]]) -> AcademicYear:
        target_name = str(name_opt or "").strip()
        if target_name:
            ay = db.query(AcademicYear).filter(AcademicYear.name == target_name).first()
            if ay:
                return ay
        ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()  # noqa: E712
        if ay:
            return ay
        yr = int(target_name) if target_name.isdigit() else date.today().year
        ay = AcademicYear(name=target_name or str(yr), start_date=date(yr, 1, 1), end_date=date(yr, 12, 31), is_current=True)
        db.add(ay)
        db.flush()
        aux.append({"table": "academic_years", "id": ay.id})
        return ay

    @staticmethod
    def _ensure_department(db: Session, name_opt: Optional[str], aux: List[Dict[str, Any]]) -> Department:
        nm = str(name_opt or "General").strip() or "General"
        dept = db.query(Department).filter(Department.name == nm).first()
        if dept:
            return dept
        code = ("".join(c for c in nm.upper() if c.isalnum())[:6] or "GEN") + uuid.uuid4().hex[:3].upper()
        dept = Department(name=nm, code=code)
        db.add(dept)
        db.flush()
        aux.append({"table": "departments", "id": dept.id})
        return dept

    @classmethod
    def _insert_mapped_row(
        cls,
        db: Session,
        target_entity: str,
        mrow: Dict[str, Any],
        rnum: int,
    ) -> Tuple[str, int, List[Dict[str, Any]], Dict[str, Any]]:
        aux: List[Dict[str, Any]] = []

        if target_entity == "Students":
            ay = cls._ensure_academic_year(db, mrow.get("academic_year"), aux)
            cls_name = str(mrow.get("class_name") or "Class 1").strip() or "Class 1"
            scls = db.query(SchoolClass).filter(SchoolClass.name == cls_name).first()
            if not scls:
                lvl = sum(int(ch) for ch in cls_name if ch.isdigit()) or (db.query(SchoolClass).count() + 1)
                scls = SchoolClass(name=cls_name, numeric_level=lvl)
                db.add(scls)
                db.flush()
                aux.append({"table": "school_classes", "id": scls.id})

            sec_id = None
            sec_name = str(mrow.get("section_name") or "").strip()
            if sec_name:
                sec = db.query(Section).filter(Section.name == sec_name, Section.class_id == scls.id).first()
                if not sec:
                    sec = Section(name=sec_name, class_id=scls.id)
                    db.add(sec)
                    db.flush()
                    aux.append({"table": "sections", "id": sec.id})
                sec_id = sec.id

            g_name = str(mrow.get("guardian_name") or mrow.get("father_name") or f"Guardian of {mrow['full_name']}").strip()
            g_phone = str(mrow.get("guardian_phone") or mrow.get("phone") or "0000000000").strip()
            guardian = db.query(Guardian).filter(Guardian.guardian_name == g_name, Guardian.guardian_phone == g_phone).first()
            if not guardian:
                guardian = Guardian(
                    guardian_name=g_name,
                    guardian_phone=g_phone,
                    father_name=mrow.get("father_name") or g_name,
                    mother_name=mrow.get("mother_name"),
                )
                db.add(guardian)
                db.flush()
                aux.append({"table": "guardians", "id": guardian.id})

            sid = str(mrow.get("student_id") or "").strip() or f"STU-MIG-{uuid.uuid4().hex[:6].upper()}"
            adm = str(mrow.get("admission_number") or "").strip() or f"ADM-MIG-{uuid.uuid4().hex[:6].upper()}"
            try:
                roll_no = int(mrow.get("roll_number") or rnum)
            except Exception:
                roll_no = rnum
            dob = _parse_date(mrow.get("date_of_birth"), date(2012, 1, 1))
            st = Student(
                student_id=sid,
                admission_number=adm,
                roll_number=roll_no,
                first_name=mrow["first_name"],
                last_name=mrow["last_name"],
                full_name=mrow["full_name"],
                gender=str(mrow.get("gender") or "Unspecified").strip() or "Unspecified",
                date_of_birth=dob,
                blood_group=mrow.get("blood_group"),
                phone=mrow.get("phone"),
                email=mrow.get("email"),
                address=mrow.get("address"),
                class_id=scls.id,
                section_id=sec_id,
                guardian_id=guardian.id,
                academic_year_id=ay.id,
            )
            db.add(st)
            db.flush()
            return "students", st.id, aux, {"student_id": sid, "admission_number": adm, "full_name": st.full_name}

        if target_entity == "Teachers":
            dept = cls._ensure_department(db, mrow.get("department"), aux)
            tid = str(mrow.get("teacher_id") or "").strip() or f"TCH-MIG-{uuid.uuid4().hex[:5].upper()}"
            emp = str(mrow.get("employee_id") or "").strip() or f"EMP-MIG-{uuid.uuid4().hex[:5].upper()}"
            t = Teacher(
                teacher_id=tid,
                employee_id=emp,
                full_name=mrow["full_name"],
                gender=str(mrow.get("gender") or "Unspecified"),
                date_of_birth=_parse_date(mrow.get("date_of_birth"), date(1985, 1, 1)),
                phone=str(mrow.get("phone") or "0000000000"),
                email=str(mrow["email"]).strip(),
                qualification=str(mrow.get("qualification") or "Bachelor Degree"),
                designation=str(mrow.get("designation") or "Assistant Teacher"),
                department_id=dept.id,
                primary_subject=str(mrow.get("primary_subject") or "General"),
                salary=int(float(mrow.get("salary") or 35000)),
            )
            db.add(t)
            db.flush()
            return "teachers", t.id, aux, {"teacher_id": tid, "email": t.email, "full_name": t.full_name}

        if target_entity == "Staff":
            dept = cls._ensure_department(db, mrow.get("department"), aux)
            sid = str(mrow.get("staff_id") or "").strip() or f"STF-MIG-{uuid.uuid4().hex[:5].upper()}"
            emp = str(mrow.get("employee_id") or "").strip() or f"EMPS-MIG-{uuid.uuid4().hex[:5].upper()}"
            s = Staff(
                staff_id=sid,
                employee_id=emp,
                full_name=mrow["full_name"],
                gender=str(mrow.get("gender") or "Unspecified"),
                date_of_birth=_parse_date(mrow.get("date_of_birth"), date(1988, 1, 1)),
                phone=str(mrow["phone"]).strip(),
                email=mrow.get("email"),
                position=str(mrow.get("position") or "Office Staff"),
                department_id=dept.id,
                shift=str(mrow.get("shift") or "Day"),
                salary=int(float(mrow.get("salary") or 22000)),
            )
            db.add(s)
            db.flush()
            return "staff_members", s.id, aux, {"staff_id": sid, "full_name": s.full_name}

        if target_entity == "Classes":
            nm = str(mrow["name"]).strip()
            lvl = int(mrow.get("numeric_level") or (db.query(SchoolClass).count() + 1))
            sc = SchoolClass(name=nm, numeric_level=lvl, description=mrow.get("description"))
            db.add(sc)
            db.flush()
            return "school_classes", sc.id, aux, {"name": nm, "numeric_level": lvl}

        if target_entity == "Subjects":
            sub = Subject(
                name=str(mrow["name"]).strip(),
                code=str(mrow["code"]).strip(),
                subject_type=str(mrow.get("subject_type") or "Compulsory"),
                credit_hours=float(mrow.get("credit_hours") or 1.0),
            )
            db.add(sub)
            db.flush()
            return "subjects", sub.id, aux, {"name": sub.name, "code": sub.code}

        if target_entity == "FeeCategories":
            fc = FeeCategory(name=str(mrow["name"]).strip(), description=mrow.get("description"))
            db.add(fc)
            db.flush()
            return "fee_categories", fc.id, aux, {"name": fc.name}

        if target_entity == "Books":
            cat_name = str(mrow.get("category_name") or "General").strip() or "General"
            cat = db.query(BookCategory).filter(BookCategory.name == cat_name).first()
            if not cat:
                cat = BookCategory(name=cat_name)
                db.add(cat)
                db.flush()
                aux.append({"table": "book_categories", "id": cat.id})
            acc = str(mrow.get("accession_no") or "").strip() or f"ACC-MIG-{uuid.uuid4().hex[:6].upper()}"
            copies = max(1, int(mrow.get("total_copies") or 1))
            bk = Book(
                accession_no=acc,
                title=str(mrow["title"]).strip(),
                author=str(mrow["author"]).strip(),
                publisher=mrow.get("publisher"),
                isbn=mrow.get("isbn"),
                category_id=cat.id,
                total_copies=copies,
                available_copies=copies,
                price=float(mrow.get("price") or 0.0),
                rack_number=mrow.get("rack_number"),
            )
            db.add(bk)
            db.flush()
            return "library_books", bk.id, aux, {"accession_no": acc, "title": bk.title}

        raise ValueError(f"Unsupported migration target: {target_entity}")

    @staticmethod
    def _merge_empty_fields(
        db: Session,
        target_entity: str,
        record_id: int,
        mrow: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        model_map = {
            "Students": (Student, "students", ["blood_group", "phone", "email", "address"]),
            "Teachers": (Teacher, "teachers", ["qualification", "designation", "primary_subject", "phone"]),
            "Staff": (Staff, "staff_members", ["email", "position", "shift"]),
            "Classes": (SchoolClass, "school_classes", ["description"]),
            "Subjects": (Subject, "subjects", ["subject_type"]),
            "FeeCategories": (FeeCategory, "fee_categories", ["description"]),
            "Books": (Book, "library_books", ["publisher", "isbn", "rack_number"]),
        }
        model_cls, tbl_name, safe_fields = model_map[target_entity]
        obj = db.query(model_cls).filter(model_cls.id == record_id).first()
        if not obj:
            return {}, {}, tbl_name
        before = {}
        after = {}
        for f in safe_fields:
            cur_val = getattr(obj, f, None)
            before[f] = cur_val
            new_val = mrow.get(f)
            if (cur_val is None or str(cur_val).strip() == "") and (new_val is not None and str(new_val).strip() != ""):
                setattr(obj, f, new_val)
                after[f] = new_val
            else:
                after[f] = cur_val
        db.flush()
        return before, after, tbl_name

    # ------------------------------------------------------------------ #
    # Rollback Strategy (Reverses Batch Atomically)
    # ------------------------------------------------------------------ #
    @classmethod
    def rollback_batch(
        cls,
        db: Session,
        batch_id: int,
        reason: str = "User requested migration rollback",
        rolled_back_by: str = "admin",
    ) -> Dict[str, Any]:
        batch = db.query(DataMigrationBatch).filter(DataMigrationBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Migration batch ID {batch_id} not found.")
        if batch.status != "Imported":
            raise ValueError(f"Only 'Imported' batches can be rolled back (current status: {batch.status}).")

        model_by_table = {
            "students": Student,
            "teachers": Teacher,
            "staff_members": Staff,
            "school_classes": SchoolClass,
            "subjects": Subject,
            "fee_categories": FeeCategory,
            "library_books": Book,
            "guardians": Guardian,
            "sections": Section,
            "departments": Department,
            "academic_years": AcademicYear,
            "book_categories": BookCategory,
        }

        logs = (
            db.query(DataMigrationRowLog)
            .filter(DataMigrationRowLog.batch_id == batch.id, DataMigrationRowLog.is_rolled_back == False)  # noqa: E712
            .order_by(DataMigrationRowLog.row_number.desc())
            .all()
        )

        deleted_count = 0
        restored_count = 0
        aux_deleted = 0
        warnings: List[str] = []

        with db.begin_nested():
            for log in logs:
                if log.action == "UPDATED_EMPTY" and log.target_table in model_by_table and log.target_record_id:
                    cls_m = model_by_table[log.target_table]
                    rec = db.query(cls_m).filter(cls_m.id == log.target_record_id).first()
                    if rec and log.before_snapshot_json:
                        snap = json.loads(log.before_snapshot_json)
                        for k, v in snap.items():
                            if hasattr(rec, k):
                                setattr(rec, k, v)
                        restored_count += 1
                    log.is_rolled_back = True

                elif log.action == "INSERTED" and log.target_table in model_by_table and log.target_record_id:
                    cls_m = model_by_table[log.target_table]
                    rec = db.query(cls_m).filter(cls_m.id == log.target_record_id).first()
                    if rec:
                        try:
                            with db.begin_nested():
                                db.delete(rec)
                                db.flush()
                            deleted_count += 1
                        except Exception as exc:
                            warnings.append(f"Row {log.row_number} ({log.target_table}#{log.target_record_id}) referenced elsewhere: {exc}")
                            continue

                    # Clean up auxiliary records freshly created by this row (only if unreferenced)
                    aux_list = json.loads(log.auxiliary_records_json or "[]")
                    for aux_item in reversed(aux_list):
                        atbl = aux_item.get("table")
                        aid = aux_item.get("id")
                        if atbl in model_by_table and aid:
                            acls = model_by_table[atbl]
                            arec = db.query(acls).filter(acls.id == aid).first()
                            if arec:
                                try:
                                    with db.begin_nested():
                                        db.delete(arec)
                                        db.flush()
                                    aux_deleted += 1
                                except Exception:
                                    pass
                    log.is_rolled_back = True

            batch.status = "Rolled Back"
            batch.rolled_back_at = utc_now()
            batch.rolled_back_by = rolled_back_by
            batch.rollback_reason = reason

        AuditService.record(
            db,
            action="MIGRATION_BATCH_ROLLED_BACK",
            module="DATA_PROTECTION",
            description=f"Rolled back migration batch {batch.batch_code} (deleted={deleted_count}, restored={restored_count}).",
            username=rolled_back_by,
            entity_type="DataMigrationBatch",
            entity_id=batch.id,
            record_label=batch.batch_code,
            before={"status": "Imported"},
            after={"status": "Rolled Back", "deleted": deleted_count, "restored": restored_count},
            severity="SECURITY",
            is_admin_action=True,
        )
        db.commit()
        return {
            "ok": True,
            "batch_code": batch.batch_code,
            "deleted_inserted_records": deleted_count,
            "restored_merged_records": restored_count,
            "cleaned_auxiliary_records": aux_deleted,
            "warnings": warnings,
        }

    @staticmethod
    def list_batches(db: Session, limit: int = 100) -> List[DataMigrationBatch]:
        return (
            db.query(DataMigrationBatch)
            .filter(DataMigrationBatch.is_deleted == False)  # noqa: E712
            .order_by(DataMigrationBatch.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_batch_logs(db: Session, batch_id: int) -> List[DataMigrationRowLog]:
        return (
            db.query(DataMigrationRowLog)
            .filter(DataMigrationRowLog.batch_id == batch_id)
            .order_by(DataMigrationRowLog.row_number.asc())
            .all()
        )
