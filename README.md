# Data Quality Checker

Python toolkit for data engineering projects — validates datasets for **completeness, uniqueness, validity, freshness** and logs to Google Sheets.

## Quick start
```bash
pip install -r requirements.txt
python run_checks.py --rules rules.example.yaml
# Log to Google Sheets:
python run_checks.py --rules rules.example.yaml --sheets-id 1OKSMjbpqgEk0X4F3sT8FWKuXBe4jqztESf9yV5pLSMI
# Or read rules from Sheets:
python run_checks.py --use-sheets-rules --sheets-id 1OKSMjbpqgEk0X4F3sT8FWKuXBe4jqztESf9yV5pLSMI
```

## Google Sheets Tracker
- **Datasets** — registry (name, path, format, owner, status)
- **Validation Rules** — per-dataset rules (not_null, unique, regex, range, freshness)
- **Issues** — auto-logged failures from `run_checks.py`

Sheet: https://docs.google.com/spreadsheets/d/1OKSMjbpqgEk0X4F3sT8FWKuXBe4jqztESf9yV5pLSMI/edit

## Rules YAML format
See `rules.example.yaml`
