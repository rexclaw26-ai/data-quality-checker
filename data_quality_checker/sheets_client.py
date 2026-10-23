"""Google Sheets client for Data Quality Tracker."""
import os, json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_service(credentials_path=None):
    creds = None
    default_path = os.path.expanduser("~/.config/gws/credentials.json")
    path = credentials_path or os.environ.get("GOOGLE_CREDENTIALS", default_path)
    if os.path.exists(path):
        data = json.load(open(path))
        creds = Credentials.from_authorized_user_info(data, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
    if not creds or not creds.valid:
        raise RuntimeError(f"No valid credentials at {path} - run 'gws auth login'")
    return build("sheets", "v4", credentials=creds)

def read_validation_rules(spreadsheet_id, service=None):
    svc = service or get_service()
    result = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="Validation Rules!A2:H").execute()
    rows = result.get("values", [])
    rules_by_dataset = {}
    for r in rows:
        if len(r) < 8:
            r += [""] * (8 - len(r))
        rule_id, dataset_id, column, rule_type, rule_def, threshold, severity, active = r[:8]
        if active.upper() != "Y":
            continue
        entry = {"rule_id": rule_id, "column": column, "type": rule_type, "severity": severity or "error"}
        if rule_type=="regex":
            entry["pattern"] = rule_def
        elif rule_type=="range":
            # threshold like "0-120" or definition
            entry["definition"] = rule_def
            entry["threshold"] = threshold
            try:
                if "-" in threshold:
                    a,b = threshold.split("-",1)
                    entry["min"]= float(a.strip()); entry["max"]= float(b.strip())
                elif rule_def:
                    # fallback parse rule_def
                    pass
            except: pass
        elif rule_type=="freshness":
            try: entry["max_age_days"]= int(threshold or rule_def or 7)
            except: entry["max_age_days"]=7
        else:
            entry["definition"]= rule_def
            entry["threshold"]= threshold
        rules_by_dataset.setdefault(dataset_id, []).append(entry)
    return rules_by_dataset

def log_issues(spreadsheet_id, issues, service=None):
    svc = service or get_service()
    values = []
    for iss in issues:
        values.append([
            iss.get("issue_id",""),
            iss.get("dataset_id",""),
            iss.get("rule_id",""),
            iss.get("detected_at",""),
            iss.get("severity",""),
            iss.get("description",""),
            str(iss.get("failed_rows","")),
            iss.get("status","OPEN"),
            iss.get("assigned_to","")
        ])
    if not values:
        return
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range="Issues!A:I", valueInputOption="RAW", body={"values": values}
    ).execute()

def update_dataset_status(spreadsheet_id, dataset_id, status, row_count, service=None):
    svc = service or get_service()
    result = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="Datasets!A2:A").execute()
    rows = result.get("values", [])
    for idx, r in enumerate(rows, start=2):
        if r and r[0]==dataset_id:
            svc.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"Datasets!H{idx}:I{idx}", valueInputOption="RAW", body={"values": [[status, row_count]]}
            ).execute()
            from datetime import datetime, timezone
            svc.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"Datasets!G{idx}", valueInputOption="RAW", body={"values": [[datetime.now(timezone.utc).isoformat()]]}
            ).execute()
            break
