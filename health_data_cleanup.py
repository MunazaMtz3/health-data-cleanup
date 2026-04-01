"""
health_data_cleanup.py
======================
EHR Data Quality Auditor

Reads a raw patient CSV export, validates each field against healthcare
data standards, flags issues by severity, outputs a cleaned CSV and a
detailed audit report.

Simulates real-world Health IT data cleanup work — EHR systems frequently
export malformed or incomplete data that must be validated before import,
reporting, or sharing with payers.

Author: Munaza Mumtaz
"""

import csv
import re
import os
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_FILE  = "data/patients_raw.csv"
OUTPUT_FILE = "output/patients_cleaned.csv"
REPORT_FILE = "output/audit_report.txt"

VALID_GENDERS = {"Male", "Female", "Non-binary", "Prefer not to say"}
VALID_STATES  = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC"
}

MIN_BIRTH_YEAR = 1900
MAX_BIRTH_YEAR = date.today().year  # date of birth cannot be in the future

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_phone(phone: str) -> tuple[bool, str]:
    """Accepts formats: 703-555-1001 or 7035551001 (10 digits)."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return True, f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"  # normalize
    return False, phone


def validate_email(email: str) -> tuple[bool, str]:
    """Basic RFC-style email check."""
    pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email)), email


def validate_dob(dob_str: str) -> tuple[bool, str, str]:
    """
    Returns (is_valid, normalized_date_str, error_message).
    Expects YYYY-MM-DD. Rejects future dates and implausibly old dates.
    """
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        if dob.year < MIN_BIRTH_YEAR:
            return False, dob_str, f"Birth year {dob.year} is before {MIN_BIRTH_YEAR}"
        if dob > date.today():
            return False, dob_str, "Date of birth is in the future"
        return True, dob_str, ""
    except ValueError:
        return False, dob_str, f"Cannot parse date: '{dob_str}'"


def validate_zip(zip_code: str) -> tuple[bool, str]:
    """US ZIP code: 5 digits or ZIP+4 (12345-6789)."""
    pattern = r"^\d{5}(-\d{4})?$"
    return bool(re.match(pattern, zip_code.strip())), zip_code


def validate_state(state: str) -> bool:
    return state.upper() in VALID_STATES


def validate_gender(gender: str) -> bool:
    return gender in VALID_GENDERS


# ---------------------------------------------------------------------------
# Issue tracker
# ---------------------------------------------------------------------------

class Issue:
    """Represents a single data quality issue on a patient record."""
    CRITICAL = "CRITICAL"   # record cannot be used / imported
    WARNING  = "WARNING"    # record usable but needs review
    INFO     = "INFO"       # minor / cosmetic

    def __init__(self, patient_id: str, field: str, severity: str, detail: str):
        self.patient_id = patient_id
        self.field      = field
        self.severity   = severity
        self.detail     = detail

    def __str__(self):
        return f"  [{self.severity}] {self.field}: {self.detail}"


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_patients(input_path: str) -> tuple[list[dict], list[Issue], dict]:
    """
    Read raw CSV, validate each record, return:
      - cleaned rows (with normalized values where possible)
      - list of all issues found
      - summary counts
    """
    cleaned_rows = []
    all_issues   = []
    summary      = {"total": 0, "critical": 0, "warning": 0, "info": 0,
                    "clean": 0, "records_with_issues": 0}

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            summary["total"] += 1
            pid    = row.get("patient_id", "UNKNOWN")
            issues = []

            # -- Phone --
            phone = row.get("phone", "").strip()
            if not phone:
                issues.append(Issue(pid, "phone", Issue.WARNING, "Missing phone number"))
            else:
                ok, normalized = validate_phone(phone)
                if ok:
                    row["phone"] = normalized   # normalize format
                else:
                    issues.append(Issue(pid, "phone", Issue.WARNING,
                                        f"Invalid format: '{phone}'"))

            # -- Email --
            email = row.get("email", "").strip()
            if not email:
                issues.append(Issue(pid, "email", Issue.WARNING, "Missing email address"))
            else:
                ok, _ = validate_email(email)
                if not ok:
                    issues.append(Issue(pid, "email", Issue.WARNING,
                                        f"Invalid format: '{email}'"))

            # -- Date of Birth --
            dob = row.get("date_of_birth", "").strip()
            if not dob:
                issues.append(Issue(pid, "date_of_birth", Issue.CRITICAL,
                                    "Missing date of birth"))
            else:
                ok, normalized, err = validate_dob(dob)
                if ok:
                    row["date_of_birth"] = normalized
                else:
                    issues.append(Issue(pid, "date_of_birth", Issue.CRITICAL, err))

            # -- Gender --
            gender = row.get("gender", "").strip()
            if not gender:
                issues.append(Issue(pid, "gender", Issue.INFO, "Missing gender"))
            elif not validate_gender(gender):
                issues.append(Issue(pid, "gender", Issue.WARNING,
                                    f"Non-standard value: '{gender}' — "
                                    f"expected one of {VALID_GENDERS}"))

            # -- Last Name --
            last_name = row.get("last_name", "").strip()
            if not last_name:
                issues.append(Issue(pid, "last_name", Issue.CRITICAL,
                                    "Missing last name"))

            # -- Insurance Policy Number --
            policy = row.get("insurance_policy_no", "").strip()
            if not policy:
                issues.append(Issue(pid, "insurance_policy_no", Issue.WARNING,
                                    "Missing insurance policy number — "
                                    "required for billing"))

            # -- State --
            state = row.get("state", "").strip()
            if not state:
                issues.append(Issue(pid, "state", Issue.WARNING, "Missing state"))
            elif not validate_state(state):
                issues.append(Issue(pid, "state", Issue.CRITICAL,
                                    f"Invalid state code: '{state}'"))

            # -- ZIP Code --
            zip_code = row.get("zip_code", "").strip()
            if not zip_code:
                issues.append(Issue(pid, "zip_code", Issue.WARNING, "Missing ZIP code"))
            else:
                ok, _ = validate_zip(zip_code)
                if not ok:
                    issues.append(Issue(pid, "zip_code", Issue.WARNING,
                                        f"Invalid ZIP format: '{zip_code}'"))

            # -- Tally --
            if issues:
                summary["records_with_issues"] += 1
                for issue in issues:
                    all_issues.append(issue)
                    if issue.severity == Issue.CRITICAL:
                        summary["critical"] += 1
                    elif issue.severity == Issue.WARNING:
                        summary["warning"] += 1
                    else:
                        summary["info"] += 1
            else:
                summary["clean"] += 1

            cleaned_rows.append(row)

    return cleaned_rows, all_issues, summary


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_cleaned_csv(rows: list[dict], output_path: str):
    if not rows:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def write_audit_report(issues: list[Issue], summary: dict, report_path: str):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("=" * 65)
    lines.append("  EHR DATA QUALITY AUDIT REPORT")
    lines.append(f"  Generated: {now}")
    lines.append("=" * 65)
    lines.append("")

    # Summary block
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total records processed : {summary['total']}")
    lines.append(f"  Clean records           : {summary['clean']}")
    lines.append(f"  Records with issues     : {summary['records_with_issues']}")
    lines.append(f"  Critical issues         : {summary['critical']}")
    lines.append(f"  Warnings                : {summary['warning']}")
    lines.append(f"  Informational           : {summary['info']}")
    lines.append("")

    # Severity guide
    lines.append("SEVERITY GUIDE")
    lines.append("-" * 40)
    lines.append("  CRITICAL — Record cannot be safely imported or used")
    lines.append("             (missing name, invalid DOB, invalid state)")
    lines.append("  WARNING  — Record usable but requires follow-up")
    lines.append("             (missing email, bad phone format, no policy #)")
    lines.append("  INFO     — Minor gap, low priority")
    lines.append("")

    # Issues by patient
    lines.append("ISSUES BY PATIENT RECORD")
    lines.append("-" * 40)

    if not issues:
        lines.append("  No issues found. All records passed validation.")
    else:
        # Group by patient_id
        by_patient: dict[str, list[Issue]] = {}
        for issue in issues:
            by_patient.setdefault(issue.patient_id, []).append(issue)

        for pid, patient_issues in by_patient.items():
            has_critical = any(i.severity == Issue.CRITICAL for i in patient_issues)
            flag = " *** CRITICAL ***" if has_critical else ""
            lines.append(f"\nPatient {pid}{flag}")
            for issue in patient_issues:
                lines.append(str(issue))

    lines.append("")
    lines.append("=" * 65)
    lines.append("END OF REPORT")
    lines.append("=" * 65)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Also print to console
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"Reading: {INPUT_FILE}")
    cleaned_rows, issues, summary = process_patients(INPUT_FILE)

    print(f"Writing cleaned CSV: {OUTPUT_FILE}")
    write_cleaned_csv(cleaned_rows, OUTPUT_FILE)

    print(f"Writing audit report: {REPORT_FILE}\n")
    write_audit_report(issues, summary, REPORT_FILE)


if __name__ == "__main__":
    main()
