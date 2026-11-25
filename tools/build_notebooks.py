# -*- coding: utf-8 -*-
"""Mengubah nb_src/*.py (format 'percent' / jupytext) menjadi notebooks/*.ipynb"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, DST = os.path.join(ROOT, "nb_src"), os.path.join(ROOT, "notebooks")

def parse(text):
    cells, cur, kind = [], [], None
    def flush():
        if kind is None: return
        body = "\n".join(cur).strip("\n")
        if kind == "markdown":
            body = "\n".join(re.sub(r"^# ?", "", l) for l in body.split("\n"))
        if body.strip():
            cells.append((kind, body))
    for line in text.split("\n"):
        if line.startswith("# %%"):
            flush(); cur = []; kind = "markdown" if "[markdown]" in line else "code"
        else:
            cur.append(line)
    flush()
    return cells

def to_nb(cells):
    nb = {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    for i, (k, body) in enumerate(cells):
        src = [l + "\n" for l in body.split("\n")]; src[-1] = src[-1].rstrip("\n")
        c = {"cell_type": k, "id": f"c{i:03d}", "metadata": {}, "source": src}
        if k == "code": c.update({"execution_count": None, "outputs": []})
        nb["cells"].append(c)
    return nb

if __name__ == "__main__":
    os.makedirs(DST, exist_ok=True)
    for f in sorted(os.listdir(SRC)):
        if f.endswith(".py"):
            nb = to_nb(parse(open(os.path.join(SRC, f), encoding="utf8").read()))
            out = os.path.join(DST, f.replace(".py", ".ipynb"))
            json.dump(nb, open(out, "w", encoding="utf8"), ensure_ascii=False, indent=1)
            print("ditulis", out, len(nb["cells"]), "sel")
