# EHR Data Quality Auditor

A Python script that simulates real-world Health IT data cleanup work — reading a raw patient CSV export, validating each field against healthcare data standards, and producing a cleaned output file and a detailed audit report.

EHR systems frequently export malformed or incomplete data before it can be imported into another system, used for reporting, or shared with payers. This tool automates that validation layer.

---

## What It Does

1. **Reads** a raw patient CSV (simulating an EHR export)
2. **Validates** every field against configurable rules
3. **Normalizes** correctable values (e.g. `7035551001` → `703-555-1001`)
4. **Flags** issues by severity: `CRITICAL`, `WARNING`, or `INFO`
5. **Outputs** a cleaned CSV and a plain-text audit report

---

## Sample Output

```
=================================================================
  EHR DATA QUALITY AUDIT REPORT
  Generated: 2025-01-15 10:32:11
=================================================================

SUMMARY
----------------------------------------
  Total records processed : 15
  Clean records           : 5
  Records with issues     : 10
  Critical issues         : 4
  Warnings                : 6
  Informational           : 0

ISSUES BY PATIENT RECORD
----------------------------------------

Patient P007 *** CRITICAL ***
  [CRITICAL] last_name: Missing last name

Patient P008 *** CRITICAL ***
  [CRITICAL] date_of_birth: Date of birth is in the future

Patient P010
  [WARNING] email: Invalid format: 'mariagarcia'

Patient P014 *** CRITICAL ***
  [CRITICAL] state: Invalid state code: 'XX'
```

---

## Validations Performed

| Field | Rule |
|---|---|
| `phone` | Must be 10 digits; auto-normalizes to `XXX-XXX-XXXX` |
| `email` | Must match standard email format |
| `date_of_birth` | Must be valid date, not future, not before 1900 |
| `gender` | Must match accepted values (Male, Female, Non-binary, Prefer not to say) |
| `last_name` | Required — missing = CRITICAL |
| `insurance_policy_no` | Required for billing — missing = WARNING |
| `state` | Must be valid 2-letter US state code |
| `zip_code` | Must be 5-digit or ZIP+4 format |

---

## Severity Levels

| Level | Meaning |
|---|---|
| `CRITICAL` | Record cannot be safely imported or used |
| `WARNING` | Record usable but requires staff follow-up |
| `INFO` | Minor gap, low priority |

---

## Project Structure

```
health-data-cleanup/
├── health_data_cleanup.py   # Main script
├── data/
│   └── patients_raw.csv     # Raw input (synthetic data only)
├── output/
│   ├── patients_cleaned.csv # Cleaned output with normalized values
│   └── audit_report.txt     # Full issue report
└── README.md
```

---

## How to Run

**Requirements:** Python 3.10+ (no external libraries — standard library only)

```bash
# Clone the repo
git clone https://github.com/yourusername/health-data-cleanup.git
cd health-data-cleanup

# Run the script
python health_data_cleanup.py
```

Output files will appear in the `output/` folder.

---

## Technologies Used

- **Python 3.10+** — core scripting language
- **csv module** — reading and writing patient data files
- **re module** — regex-based field validation
- **datetime module** — date parsing and range validation
- **HIPAA awareness** — no real PHI used; validation rules reflect real EHR data standards

---

## Healthcare IT Context

This project reflects common real-world scenarios in Health IT:

- **EHR data migration** — validating patient records before import into a new system
- **Payer submissions** — ensuring claims data meets format requirements before submission
- **Data quality audits** — identifying gaps in patient demographics for compliance reporting
- **Interoperability** — cleaning data before HL7/FHIR exchange

---

## Disclaimer

All patient data in `patients_raw.csv` is entirely synthetic and computer-generated. No real PHI is present anywhere in this project.
