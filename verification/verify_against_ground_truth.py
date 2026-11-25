# -*- coding: utf-8 -*-
"""Membandingkan hasil cleaning (data/clean) dengan data bersih asli (_kunci_jawaban/clean).
JALANKAN HANYA SETELAH selesai membersihkan data sendiri (ini kunci jawaban latihan).
   python verification/verify_against_ground_truth.py
Catatan: pada data primer dari buku Sumber Urip tidak ada kunci jawaban; gunakan validate_dataset.py."""
import os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = {"branches": "branch_id", "products": "product_id", "customers": "customer_id", "transactions": "transaction_id",
       "transaction_details": "detail_id", "inventory": "inventory_id"}
tot_bad = 0
for t, k in key.items():
    a = pd.read_csv(os.path.join(ROOT, "data/clean", f"{t}.csv"), dtype=str).set_index(k).sort_index()
    b = pd.read_csv(os.path.join(ROOT, "_kunci_jawaban/clean", f"{t}.csv"), dtype=str).set_index(k).sort_index()
    only_a, only_b = set(a.index) - set(b.index), set(b.index) - set(a.index)
    common = a.index.intersection(b.index)
    cols = [c for c in b.columns if c in a.columns]
    diff = {}
    for c in cols:
        x, y = a.loc[common, c].fillna(""), b.loc[common, c].fillna("")
        try:   # bandingkan numerik bila memungkinkan (mis. 0.05 vs 0.050)
            n = (pd.to_numeric(x) != pd.to_numeric(y)).sum() if (pd.to_numeric(x, errors="coerce").notna().all() and pd.to_numeric(y, errors="coerce").notna().all()) else (x != y).sum()
        except Exception:
            n = (x != y).sum()
        if n: diff[c] = int(n)
    status = "SAMA PERSIS" if not (only_a or only_b or diff) else "ada perbedaan"
    print(f"{t:22s} baris hasil={len(a):>5} baris kunci={len(b):>5} | hanya di hasil={len(only_a)} hanya di kunci={len(only_b)} | kolom berbeda={diff or '-'}  -> {status}")
    tot_bad += len(only_a) + len(only_b) + sum(diff.values())
print("\nTOTAL sel/baris berbeda:", tot_bad)
