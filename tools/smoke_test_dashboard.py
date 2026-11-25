# -*- coding: utf-8 -*-
"""Uji asap dashboard TANPA Streamlit terpasang: Streamlit diganti objek tiruan yang mengembalikan nilai bawaan widget.
Tujuannya memastikan logika pandas di pages/1_Eksplorasi_Interaktif.py tidak error. Jalankan:  python tools/smoke_test_dashboard.py
(Pengujian tampilan sebenarnya tetap perlu:  streamlit run pages/1_Eksplorasi_Interaktif.py)"""
import contextlib, os, runpy, sys, types
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
calls = {}
MODE = os.environ.get("SMOKE_MODE", "default")   # default | upload_ok | upload_bad

class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name): return Fake().__getattr__(name)

class Fake(types.ModuleType):
    def __init__(self): super().__init__("streamlit"); self.sidebar = self; self.session_state = {}
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        def fn(*a, **k):
            calls[name] = calls.get(name, 0) + 1
            if name == "radio":
                opts = a[1] if len(a) > 1 else k.get("options"); return opts[1] if MODE.startswith("upload") else opts[0]
            if name == "selectbox":
                opts = a[1] if len(a) > 1 else k.get("options"); idx = k.get("index", 0); return opts[idx]
            if name == "multiselect": return k.get("default", [])
            if name == "date_input": return k.get("value")
            if name == "file_uploader":
                if not MODE.startswith("upload"): return None
                label = a[0]; path = os.path.join(ROOT, "data", "clean", label)
                if MODE == "upload_bad" and label == "transaction_details.csv":
                    import io; return io.StringIO(open(path, encoding="utf8").read().replace("subtotal", "subtotal_x", 1))
                return open(path, encoding="utf8")
            if name == "download_button": return None
            if name == "tabs": return [Ctx() for _ in a[0]]
            if name == "columns":
                n = a[0] if isinstance(a[0], int) else len(a[0]); return [Ctx() for _ in range(n)]
            if name == "expander": return Ctx()
            if name == "stop": raise RuntimeError("st.stop() dipanggil")
            return None
        return fn
    def cache_data(self, *a, **k):
        if a and callable(a[0]): return a[0]
        return lambda f: f

sys.modules["streamlit"] = Fake()
runpy.run_path(os.path.join(ROOT, "pages", "1_Eksplorasi_Interaktif.py"), run_name="__main__")
if MODE != "default":
    print(f"Mode {MODE}: success={calls.get('success', 0)} error={calls.get('error', 0)}")
    assert (calls.get("success", 0) == 1) if MODE == "upload_ok" else (calls.get("error", 0) >= 1)
    print("UJI ASAP DASHBOARD (", MODE, "): LOLOS"); sys.exit(0)
need = ["set_page_config", "title", "metric", "line_chart", "bar_chart", "dataframe", "tabs", "multiselect"]
missing = [n for n in need if n not in calls]
print("Pemanggilan komponen:", dict(sorted(calls.items())))
assert not missing, f"komponen tidak terpanggil: {missing}"
print("\nUJI ASAP DASHBOARD: LOLOS (logika data berjalan tanpa error)")
