"""Run data quality checks from YAML or Google Sheets and log results."""
import argparse, yaml, pandas as pd
from datetime import datetime, timezone
from data_quality_checker.checker import DataQualityChecker
from data_quality_checker.sheets_client import get_service, read_validation_rules, log_issues, update_dataset_status

def load_yaml(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("datasets", [])

def run_for_dataset(dataset_cfg, spreadsheet_id=None):
    ds_id = dataset_cfg["id"]
    path = dataset_cfg["path"]
    df = pd.read_csv(path)
    checker = DataQualityChecker(df, dataset_id=ds_id)
    issues = checker.run_rules(dataset_cfg.get("rules", []))
    summ = checker.summary()
    print(f"[{ds_id}] {summ['status']} - {summ['issues_found']} issues ({summ['errors']} errors, {summ['warnings']} warnings), rows={summ['row_count']}")
    for iss in issues:
        print(f"  - {iss['severity']}: {iss['description']}")
    if spreadsheet_id:
        svc = get_service()
        now = datetime.now(timezone.utc).isoformat()
        sheet_issues = []
        for iss in issues:
            sheet_issues.append({
                "issue_id": f"{ds_id}-{iss['rule_type']}-{iss['column']}-{now[:10]}",
                "dataset_id": ds_id,
                "rule_id": f"{iss['rule_type']}:{iss['column']}",
                "detected_at": now,
                "severity": iss["severity"],
                "description": iss["description"],
                "failed_rows": iss["failed_rows"],
                "status": "OPEN",
                "assigned_to": ""
            })
        if sheet_issues:
            log_issues(spreadsheet_id, sheet_issues, service=svc)
        update_dataset_status(spreadsheet_id, ds_id, summ["status"], summ["row_count"], service=svc)
    return summ, issues

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rules", default="rules.example.yaml")
    p.add_argument("--sheets-id", default=None, help="Google Sheets spreadsheetId to log to")
    p.add_argument("--use-sheets-rules", action="store_true", help="Read rules from Sheets instead of YAML")
    args = p.parse_args()
    if args.use_sheets_rules and args.sheets_id:
        svc = get_service()
        rules_by_ds = read_validation_rules(args.sheets_id, service=svc)
        for ds_id, rules in rules_by_ds.items():
            cfg = {"id": ds_id, "path": f"data/{ds_id}.csv", "rules": rules}
            run_for_dataset(cfg, spreadsheet_id=args.sheets_id)
    else:
        for cfg in load_yaml(args.rules):
            run_for_dataset(cfg, spreadsheet_id=args.sheets_id)
