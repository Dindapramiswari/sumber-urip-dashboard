# -*- coding: utf-8 -*-
"""Validasi dataset Sumber Urip (22 pemeriksaan). Dapat dipakai sebagai modul atau script.
   python src/validate_dataset.py data/clean          -> memeriksa tabel bersih
"""
import os, sys
import pandas as pd

def load_tables(folder, suffix=""):
    rd = lambda n: pd.read_csv(os.path.join(folder, f"{n}{suffix}.csv"), dtype=str)
    return [rd(n) for n in ["branches", "products", "customers", "transactions", "transaction_details", "inventory"]]

def run_validation(folder, suffix="", verbose=True):
    br, pr, cu, tx, dt, iv = load_tables(folder, suffix)
    num = lambda s: pd.to_numeric(s, errors="coerce")
    res = []
    def check(name, ok, detail=""):
        res.append((name, bool(ok), detail))
    check("1. transaction_id unik", tx.transaction_id.is_unique, f"duplikat={tx.transaction_id.duplicated().sum()}")
    check("2. detail_id unik", dt.detail_id.is_unique, f"duplikat={dt.detail_id.duplicated().sum()}")
    check("3. product_id unik", pr.product_id.is_unique, f"duplikat={pr.product_id.duplicated().sum()}")
    check("4a. FK transactions.branch_id -> branches", tx.branch_id.isin(br.branch_id).all() if "branch_id" in tx.columns else False)
    check("4b. FK transactions.customer_id -> customers", tx.customer_id.isin(cu.customer_id).all())
    check("4c. FK details.transaction_id -> transactions", dt.transaction_id.isin(tx.transaction_id).all(), f"yatim={(~dt.transaction_id.isin(tx.transaction_id)).sum()}")
    check("4d. FK details.product_id -> products", dt.product_id.isin(pr.product_id).all(), f"yatim={(~dt.product_id.isin(pr.product_id)).sum()}")
    check("4e. FK inventory.branch_id -> branches", iv.branch_id.isin(br.branch_id).all())
    check("4f. FK inventory.product_id -> products", iv.product_id.isin(pr.product_id).all())
    bad = sum(((num(dt[c]) < 0) | num(dt[c]).isna()).sum() for c in ["quantity", "unit_price", "subtotal", "cost_subtotal"]) + \
          sum(((num(pr[c]) < 0) | num(pr[c]).isna()).sum() for c in ["cost_price", "selling_price"])
    check("5. tidak ada harga/kuantitas negatif atau non-numerik", bad == 0, f"baris bermasalah={bad}")
    d = dt.copy()
    for c in ["quantity", "unit_price", "discount", "subtotal", "cost_subtotal", "profit"]: d[c] = num(d[c])
    d["gross_line"] = d.unit_price * d.quantity
    agg = d.groupby("transaction_id").agg(net=("subtotal", "sum"), disc=("discount", "sum"), cost=("cost_subtotal", "sum"),
                                           q=("quantity", "sum"), gross=("gross_line", "sum")).reset_index()
    m = tx.merge(agg, on="transaction_id", how="left")
    for c in ["gross_amount", "discount_amount", "net_amount", "total_cost", "total_items", "other_cost", "gross_profit"]: m[c] = num(m[c])
    check("6. gross_amount = jumlah(qty x unit_price)", (m.gross_amount == m.gross).all(), f"tidak cocok={(m.gross_amount != m.gross).sum()}")
    check("7. net_amount = jumlah subtotal detail", (m.net_amount == m.net).all(), f"tidak cocok={(m.net_amount != m.net).sum()}")
    check("8. discount_amount = jumlah diskon detail & net = gross - diskon", ((m.discount_amount == m.disc) & (m.net_amount == m.gross_amount - m.discount_amount)).all())
    check("9. total_cost = jumlah cost_subtotal", (m.total_cost == m.cost).all())
    check("10. gross_profit = net - total_cost - other_cost", (m.gross_profit == m.net_amount - m.total_cost - m.other_cost).all())
    check("11. total_items = jumlah quantity", (m.total_items == m.q).all())
    check("12. profit detail = subtotal - cost_subtotal", (d.profit == d.subtotal - d.cost_subtotal).all())
    iv2 = iv.copy()
    for c in ["initial_stock", "stock_in", "stock_out", "ending_stock"]: iv2[c] = num(iv2[c])
    ok13 = (iv2.ending_stock == iv2.initial_stock + iv2.stock_in - iv2.stock_out)
    check("13. ending_stock = initial + in - out", ok13.all(), f"tidak cocok={(~ok13).sum()}")
    check("14. stok tidak negatif", (iv2[["initial_stock", "ending_stock"]] >= 0).all().all())
    dd = pd.to_datetime(tx.transaction_date, errors="coerce")
    inrange = dd.between("2026-08-01", "2026-10-31")
    check("15. tanggal transaksi dalam periode 2026-08-01..2026-10-31", inrange.all(), f"di luar/invalid={(~inrange).sum()}")
    check("16. semua baris berlabel synthetic", (tx.data_source.str.lower().str.strip() == "synthetic").all() and (iv.data_source.str.lower().str.strip() == "synthetic").all())
    iv3 = iv2.sort_values(["branch_id", "product_id", "stock_date"]).copy()
    iv3["prev_end"] = iv3.groupby(["branch_id", "product_id"]).ending_stock.shift()
    cont = (iv3.prev_end.isna() | (iv3.prev_end == iv3.initial_stock))
    check("17. stok awal bulan = stok akhir bulan sebelumnya", cont.all(), f"tidak cocok={(~cont).sum()}")
    so = d.merge(tx[["transaction_id", "transaction_date", "branch_id"]], on="transaction_id")
    so["ym"] = so.transaction_date.str[:7]
    so = so.groupby(["ym", "branch_id", "product_id"]).quantity.sum().rename("q_detail").reset_index()
    iv4 = iv2.copy(); iv4["ym"] = iv4.stock_date.str[:7]
    chk = iv4.merge(so, on=["ym", "branch_id", "product_id"], how="left").fillna({"q_detail": 0})
    check("18. stock_out inventory = jumlah quantity detail transaksi", (chk.stock_out == chk.q_detail).all(), f"tidak cocok={(chk.stock_out != chk.q_detail).sum()}")
    check("19. harga satuan detail = harga jual master produk", (d.merge(pr[["product_id", "selling_price"]].assign(selling_price=lambda x: num(x.selling_price)), on="product_id", how="left")
          .pipe(lambda x: x.unit_price == x.selling_price)).all())
    check("20. kategori produk hanya 8 nilai baku", pr.category.nunique() == 8, f"nilai unik={pr.category.nunique()}")
    check("21. customer_type hanya 4 nilai baku", tx.customer_type.notna().all() and set(tx.customer_type.unique()) <= {"umum", "rekanan", "keluarga", "pemerintah"})
    check("22. tidak ada nilai kosong pada kolom kunci", tx[["transaction_id", "transaction_date", "branch_id", "customer_type", "net_amount"]].notna().all().all() and
          dt[["detail_id", "transaction_id", "product_id", "quantity", "subtotal"]].notna().all().all())
    if verbose:
        w = max(len(r[0]) for r in res)
        for n, ok, det in res:
            print(("PASS  " if ok else "FAIL  ") + n.ljust(w), det)
        print(f"\n{folder}: {sum(r[1] for r in res)}/{len(res)} pemeriksaan lolos")
    return res

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "data/clean"
    suffix = sys.argv[2] if len(sys.argv) > 2 else ""
    r = run_validation(folder, suffix)
    sys.exit(0 if all(x[1] for x in r) else 1)
