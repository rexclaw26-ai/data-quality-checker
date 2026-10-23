import re
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any

class DataQualityChecker:
    """Validate datasets for completeness, uniqueness, validity, freshness."""

    def __init__(self, df: pd.DataFrame, dataset_id: str = "unknown"):
        self.df = df
        self.dataset_id = dataset_id
        self.issues: List[Dict[str, Any]] = []

    def check_not_null(self, column: str, severity="error"):
        nulls = self.df[column].isna().sum() if column in self.df.columns else len(self.df)
        if nulls > 0:
            self.issues.append({
                "rule_type": "not_null",
                "column": column,
                "severity": severity,
                "description": f"{nulls} nulls in {column}",
                "failed_rows": int(nulls),
                "status": "FAIL"
            })
            return False
        return True

    def check_unique(self, column: str, severity="error"):
        if column not in self.df.columns:
            self.issues.append({"rule_type":"unique","column":column,"severity":severity,"description":f"Column {column} missing","failed_rows": len(self.df),"status":"FAIL"})
            return False
        dups = self.df.duplicated(subset=[column]).sum()
        if dups > 0:
            self.issues.append({"rule_type":"unique","column":column,"severity":severity,"description":f"{dups} duplicate values in {column}","failed_rows": int(dups),"status":"FAIL"})
            return False
        return True

    def check_regex(self, column: str, pattern: str, severity="warning"):
        if column not in self.df.columns:
            return False
        regex = re.compile(pattern)
        mask = self.df[column].dropna().astype(str).apply(lambda x: not bool(regex.match(x)))
        failed = mask.sum()
        if failed > 0:
            self.issues.append({"rule_type":"regex","column":column,"severity":severity,"description":f"{failed} values in {column} fail pattern {pattern}","failed_rows": int(failed),"status":"FAIL"})
            return False
        return True

    def check_range(self, column: str, min_val=None, max_val=None, severity="error"):
        if column not in self.df.columns:
            return False
        s = pd.to_numeric(self.df[column], errors='coerce')
        failed = 0
        if min_val is not None:
            failed += (s < min_val).sum()
        if max_val is not None:
            failed += (s > max_val).sum()
        if failed > 0:
            self.issues.append({"rule_type":"range","column":column,"severity":severity,"description":f"{failed} values out of range [{min_val},{max_val}] in {column}","failed_rows": int(failed),"status":"FAIL"})
            return False
        return True

    def check_freshness(self, column: str, max_age_days: int, severity="warning"):
        if column not in self.df.columns:
            return False
        try:
            s = pd.to_datetime(self.df[column], errors='coerce', utc=True)
            now = datetime.now(timezone.utc)
            age = (now - s).dt.days
            failed = (age > max_age_days).sum()
            if failed > 0:
                self.issues.append({"rule_type":"freshness","column":column,"severity":severity,"description":f"{failed} rows older than {max_age_days}d in {column}","failed_rows": int(failed),"status":"FAIL"})
                return False
        except Exception as e:
            self.issues.append({"rule_type":"freshness","column":column,"severity":severity,"description":f"Freshness check error: {e}","failed_rows": 0,"status":"ERROR"})
            return False
        return True

    def run_rules(self, rules: List[Dict[str, Any]]):
        for r in rules:
            col = r.get("column")
            t = r.get("type")
            sev = r.get("severity","error")
            if t == "not_null":
                self.check_not_null(col, sev)
            elif t == "unique":
                self.check_unique(col, sev)
            elif t == "regex":
                self.check_regex(col, r.get("pattern",""), sev)
            elif t == "range":
                self.check_range(col, r.get("min"), r.get("max"), sev)
            elif t == "freshness":
                self.check_freshness(col, r.get("max_age_days", 7), sev)
            else:
                self.issues.append({"rule_type": t, "column": col, "severity": sev, "description": f"Unknown rule type {t}", "failed_rows": 0, "status":"ERROR"})
        return self.issues

    def summary(self):
        total = len(self.issues)
        errors = sum(1 for i in self.issues if i["severity"]=="error")
        return {"dataset_id": self.dataset_id, "row_count": len(self.df), "issues_found": total, "errors": errors, "warnings": total-errors, "status": "FAIL" if total>0 else "PASS"}
