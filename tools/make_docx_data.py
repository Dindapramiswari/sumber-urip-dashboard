# -*- coding: utf-8 -*-
"""Mengumpulkan angka & tabel dari hasil pipeline menjadi docs/_docx_data.json (dipakai tools/build_docx.js)."""
import json, os, subprocess, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, H = os.path.join(ROOT, "data/analysis"), os.path.join(ROOT, "handoff")
rd = lambda p: pd.read_csv(os.path.join(ROOT, p))
rec = lambda df: json.loads(df.to_json(orient="records", force_ascii=False))
out = {}
out["assessing"] = rec(rd("data/analysis/assessing_report.csv"))
out["cleaning"] = rec(rd("data/analysis/cleaning_log.csv"))
out["kpi"] = dict(zip(rd("data/analysis/kpi_summary.csv").metrik, rd("data/analysis/kpi_summary.csv").nilai))
out["model"] = rec(rd("data/analysis/model_comparison.csv"))
rs = rd("data/analysis/restock_recommendation.csv")
out["restock"] = rec(rs.groupby(["branch_name", "status_restock"]).size().unstack(fill_value=0).reset_index())
out["by_cat"] = rec(rd("data/analysis/sales_by_category.csv"))
out["margin_cat"] = rec(rd("data/analysis/margin_by_category.csv"))
out["manifest"] = rec(rd("handoff/HANDOFF_MANIFEST.csv"))
ds = rd("handoff/for_genai/intent_dataset.csv")
out["intent_split"] = rec(pd.crosstab(ds.intent, ds.split).reset_index())
out["intent_total"] = int(len(ds))
raw_rows = {t: int(len(pd.read_csv(os.path.join(ROOT, f"data/raw/{t}_raw.csv"), dtype=str))) for t in ["branches", "products", "customers", "transactions", "transaction_details", "inventory"]}
clean_rows = {t: int(len(rd(f"data/clean/{t}.csv"))) for t in raw_rows}
out["raw_rows"], out["clean_rows"] = raw_rows, clean_rows
sys.path.insert(0, os.path.join(ROOT, "src"))
from validate_dataset import run_validation
res = run_validation(os.path.join(ROOT, "data/clean"), verbose=False)
out["validation"] = [dict(nama=n, lolos=bool(o)) for n, o, _ in res]
r = subprocess.run([sys.executable, os.path.join(ROOT, "verification/verify_against_ground_truth.py")], capture_output=True, text=True)
out["verification_text"] = r.stdout
out["figures"] = sorted(os.listdir(os.path.join(A, "figures")))
json.dump(out, open(os.path.join(ROOT, "docs/_docx_data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", {k: (len(v) if hasattr(v, "__len__") else v) for k, v in out.items() if k not in ("kpi", "verification_text")})
