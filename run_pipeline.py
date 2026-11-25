# -*- coding: utf-8 -*-
"""Menjalankan seluruh notebook secara berurutan TANPA Jupyter (cukup Python + pandas).
   python run_pipeline.py            -> jalankan semua langkah
   python run_pipeline.py 01 02      -> jalankan sebagian
Setiap sel kode notebook dieksekusi apa adanya; hasilnya sama seperti menjalankan notebook di Jupyter/Colab."""
import json, os, sys, time, traceback
os.environ.setdefault("MPLBACKEND", "Agg")
ROOT = os.path.dirname(os.path.abspath(__file__))
NB = os.path.join(ROOT, "notebooks")
wanted = sys.argv[1:]
files = sorted(f for f in os.listdir(NB) if f.endswith(".ipynb") and (not wanted or any(f.startswith(w) for w in wanted)))
os.chdir(NB)
for f in files:
    print(f"\n{'='*100}\n>>> {f}\n{'='*100}")
    nb = json.load(open(f, encoding="utf8"))
    ns = {"display": print, "__name__": "__main__"}
    t0 = time.time()
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code": continue
        code = "".join(c["source"])
        code = "\n".join(l for l in code.split("\n") if not l.lstrip().startswith(("%", "!")))
        try:
            exec(compile(code, f"{f}[sel {i}]", "exec"), ns)
        except Exception:
            print(f"\n!!! GAGAL pada {f}, sel ke-{i}:\n{code[:400]}\n"); traceback.print_exc(); sys.exit(1)
    print(f"\n<<< {f} selesai ({time.time()-t0:.1f} dtk)")
print("\nSEMUA LANGKAH SELESAI")
