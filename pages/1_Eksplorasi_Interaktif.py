# -*- coding: utf-8 -*-
"""Dashboard Streamlit - Kios Sumber Urip (Data Science)
Jalankan:  streamlit run dashboard/app.py
Data bawaan dibaca dari data/clean dan data/analysis (hasil notebook 01-04). Data baru dapat diunggah lewat sidebar."""
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CLEAN, ANALYSIS = ROOT / "data" / "clean", ROOT / "data" / "analysis"
st.set_page_config(page_title="Dashboard Sumber Urip", page_icon="🛠️", layout="wide")

rp = lambda x: "Rp " + f"{x:,.0f}".replace(",", ".")
REQ_TX = ["transaction_id", "transaction_date", "branch_id", "customer_type"]
REQ_DT = ["transaction_id", "product_id", "quantity", "unit_price", "discount", "subtotal", "cost_subtotal", "profit"]


# ------------------------------------------------------------------ pemuatan data
@st.cache_data
def load_default():
    tx = pd.read_csv(CLEAN / "transactions.csv", parse_dates=["transaction_date"])
    dt = pd.read_csv(CLEAN / "transaction_details.csv")
    pr = pd.read_csv(CLEAN / "products.csv")
    br = pd.read_csv(CLEAN / "branches.csv")
    return tx, dt, pr, br


@st.cache_data
def load_analysis(name):
    f = ANALYSIS / f"{name}.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame()


def validate_upload(tx, dt):
    """Mengembalikan daftar pesan kesalahan; kosong = lolos."""
    errors = []
    for need, df, nm in ((REQ_TX, tx, "transaksi"), (REQ_DT, dt, "detail transaksi")):
        miss = [c for c in need if c not in df.columns]
        if miss:
            errors.append(f"File {nm} kekurangan kolom: {', '.join(miss)}")
    if errors:
        return errors
    if tx.transaction_id.duplicated().any():
        errors.append("transaction_id pada file transaksi ada yang duplikat.")
    if pd.to_datetime(tx.transaction_date, errors="coerce").isna().any():
        errors.append("Ada transaction_date yang tidak valid (gunakan format YYYY-MM-DD).")
    for c in ["quantity", "unit_price", "discount", "subtotal", "cost_subtotal", "profit"]:
        if pd.to_numeric(dt[c], errors="coerce").isna().any():
            errors.append(f"Kolom {c} pada detail transaksi harus berupa angka (jalankan notebook cleaning dahulu).")
    if not dt.transaction_id.isin(tx.transaction_id).all():
        errors.append("Ada detail transaksi yang transaction_id-nya tidak ada di file transaksi.")
    return errors


def build_fact(tx, dt, pr, br):
    f = dt.merge(tx[["transaction_id", "transaction_date", "branch_id", "customer_type"]], on="transaction_id")
    f = f.merge(pr[["product_id", "product_name", "category", "discount_percentage"]], on="product_id", how="left")
    f = f.merge(br[["branch_id", "branch_name"]], on="branch_id", how="left")
    f["gross_line"] = f.quantity * f.unit_price
    f["week_start"] = f.transaction_date.dt.to_period("W-SUN").dt.start_time
    f["category"] = f.category.fillna("(tidak dikenal)")
    f["branch_name"] = f.branch_name.fillna(f.branch_id)
    return f


# ------------------------------------------------------------------ sidebar: sumber data & filter
st.title("🛠️ Dashboard Penjualan & Stok — Kios Sumber Urip")
st.sidebar.header("Sumber data")
mode = st.sidebar.radio("Pilih sumber data", ["Data bawaan (hasil pipeline)", "Unggah file CSV"])
tx, dt, pr, br = load_default()
using_upload = False
if mode == "Unggah file CSV":
    st.sidebar.caption("Unggah file hasil cleaning (skema sama dengan data/clean).")
    up_tx = st.sidebar.file_uploader("transactions.csv", type=["csv"])
    up_dt = st.sidebar.file_uploader("transaction_details.csv", type=["csv"])
    st.sidebar.download_button("Unduh contoh format transactions.csv", data=tx.head(20).to_csv(index=False).encode("utf-8"), file_name="contoh_transactions.csv", mime="text/csv")
    if up_tx is not None and up_dt is not None:
        try:
            tx_u, dt_u = pd.read_csv(up_tx), pd.read_csv(up_dt)
            errs = validate_upload(tx_u, dt_u)
        except Exception as e:  # file rusak / bukan CSV
            errs = [f"File tidak dapat dibaca: {e}"]
        if errs:
            for e in errs:
                st.error(e)
            st.warning("Data unggahan tidak dipakai. Menampilkan data bawaan.")
        else:
            tx_u["transaction_date"] = pd.to_datetime(tx_u.transaction_date)
            for c in ["quantity", "unit_price", "discount", "subtotal", "cost_subtotal", "profit"]:
                dt_u[c] = pd.to_numeric(dt_u[c])
            tx, dt, using_upload = tx_u, dt_u, True
            st.success(f"Data unggahan dipakai: {len(tx):,} transaksi, {len(dt):,} baris detail.")
    else:
        st.info("Unggah kedua file untuk memakai data sendiri. Sementara ini ditampilkan data bawaan.")

fact = build_fact(tx, dt, pr, br)
if "data_source" in tx.columns and (tx.data_source.astype(str).str.lower() == "synthetic").all():
    st.warning("⚠️ **DATA SINTETIS (demonstrasi).** Angka di dashboard ini hasil simulasi, bukan kondisi nyata Sumber Urip.")
elif using_upload:
    st.info("Sumber data: file unggahan.")

st.sidebar.header("Filter")
dmin, dmax = fact.transaction_date.min().date(), fact.transaction_date.max().date()
rng = st.sidebar.date_input("Rentang tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax)
if isinstance(rng, (list, tuple)) and len(rng) == 2:
    d0, d1 = rng
else:
    d0 = d1 = rng if not isinstance(rng, (list, tuple)) else rng[0]
branches = sorted(fact.branch_name.unique()); cats = sorted(fact.category.unique()); ctypes = sorted(fact.customer_type.dropna().unique())
sel_b = st.sidebar.multiselect("Cabang", branches, default=branches)
sel_c = st.sidebar.multiselect("Kategori", cats, default=cats)
sel_t = st.sidebar.multiselect("Jenis pelanggan", ctypes, default=ctypes)

f = fact[(fact.transaction_date.dt.date >= d0) & (fact.transaction_date.dt.date <= d1) & fact.branch_name.isin(sel_b) & fact.category.isin(sel_c) & fact.customer_type.isin(sel_t)]
if f.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Ubah filter di sidebar.")
    st.stop()

tab_ring, tab_prod, tab_disk, tab_stok, tab_pred, tab_info = st.tabs(["Ringkasan", "Produk & Kategori", "Diskon & Margin", "Stok & Restock", "Prediksi", "Tentang Data"])

# ------------------------------------------------------------------ tab 1: ringkasan
with tab_ring:
    omzet, gross, disc, laba = f.subtotal.sum(), f.gross_line.sum(), f.discount.sum(), f.profit.sum()
    n_tx = f.transaction_id.nunique()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Omzet bersih", rp(omzet))
    c2.metric("Laba kotor (sebelum fee)", rp(laba))
    c3.metric("Margin", f"{laba / omzet * 100:.1f}%" if omzet else "-")
    c4.metric("Jumlah transaksi", f"{n_tx:,}".replace(",", "."))
    c5.metric("Diskon efektif", f"{disc / gross * 100:.1f}%" if gross else "-")
    st.caption("Laba pada dashboard ini dihitung per baris barang (sebelum fee bengkel rekanan) agar konsisten dengan filter kategori.")
    st.subheader("Omzet bersih mingguan per cabang")
    st.caption("Minggu pertama dan terakhir pada rentang data bisa belum penuh (7 hari), sehingga tampak lebih rendah.")
    wk = f.groupby(["week_start", "branch_name"]).subtotal.sum().unstack(fill_value=0)
    st.line_chart(wk)
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Omzet per cabang")
        st.bar_chart(f.groupby("branch_name").subtotal.sum())
    with colB:
        st.subheader("Rata-rata transaksi per hari dalam seminggu")
        d = f.drop_duplicates("transaction_id").copy() if "transaction_id" in f else f
        daily = d.groupby(d.transaction_date.dt.date).transaction_id.nunique()
        hari = ["1 Senin", "2 Selasa", "3 Rabu", "4 Kamis", "5 Jumat", "6 Sabtu", "7 Minggu"]   # angka agar urutan hari tidak diacak abjad
        by_dow = daily.groupby(pd.to_datetime(daily.index).dayofweek).mean().reindex(range(7)).fillna(0)
        by_dow.index = hari
        st.bar_chart(by_dow)

# ------------------------------------------------------------------ tab 2: produk & kategori
with tab_prod:
    st.subheader("Omzet bersih per kategori")
    cat = f.groupby("category").agg(omzet_bersih=("subtotal", "sum"), unit=("quantity", "sum")).sort_values("omzet_bersih", ascending=False)
    cat["share_%"] = (cat.omzet_bersih / cat.omzet_bersih.sum() * 100).round(1)
    colA, colB = st.columns([2, 3])
    with colA:
        st.dataframe(cat)
    with colB:
        st.bar_chart(cat.omzet_bersih)
    st.subheader("Produk teratas")
    n_top = st.sidebar.selectbox("Jumlah produk teratas", [5, 10, 20, 50], index=1)
    ukuran = st.selectbox("Urutkan berdasarkan", ["omzet_bersih", "unit_terjual"])
    top = f.groupby(["product_id", "product_name", "category"]).agg(unit_terjual=("quantity", "sum"), omzet_bersih=("subtotal", "sum")).reset_index().sort_values(ukuran, ascending=False).head(int(n_top))
    st.dataframe(top)
    mv = load_analysis("product_movement")
    if not mv.empty and not using_upload:
        st.subheader("Fast-moving / slow-moving & kelas ABC (seluruh periode)")
        pick = st.selectbox("Tampilkan pergerakan", ["fast-moving", "slow-moving", "medium"])
        st.dataframe(mv[mv.pergerakan == pick][["product_id", "product_name", "category", "unit_terjual", "omzet_bersih", "kelas_abc"]].head(50))

# ------------------------------------------------------------------ tab 3: diskon & margin
with tab_disk:
    st.subheader("Diskon efektif (%) per jenis pelanggan × kategori")
    g = f.groupby(["customer_type", "category"]).agg(gross=("gross_line", "sum"), diskon=("discount", "sum")).reset_index()
    g["diskon_efektif_%"] = (g.diskon / g.gross * 100).round(2)
    st.dataframe(g.pivot(index="category", columns="customer_type", values="diskon_efektif_%"))
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Diskon efektif per jenis pelanggan")
        bt = f.groupby("customer_type").agg(gross=("gross_line", "sum"), diskon=("discount", "sum"))
        st.bar_chart((bt.diskon / bt.gross * 100).round(2))
    with colB:
        st.subheader("Margin laba kotor per kategori (%)")
        mc = f.groupby("category").agg(omzet=("subtotal", "sum"), laba=("profit", "sum"))
        st.bar_chart((mc.laba / mc.omzet * 100).round(2))
    if f.discount_percentage.notna().any():
        over = f[f.discount > f.gross_line * f.discount_percentage / 100 + 100]
        st.metric("Baris dengan diskon melebihi batas standar produk", f"{len(over)}")
        if len(over):
            st.dataframe(over[["transaction_id", "product_name", "customer_type", "gross_line", "discount", "discount_percentage"]].head(100))

# ------------------------------------------------------------------ tab 4: stok & restock
with tab_stok:
    rec = load_analysis("restock_recommendation")
    if rec.empty or using_upload:
        st.info("Rekomendasi restock tersedia untuk data bawaan (hasil notebook 04). Jalankan notebook 04 pada data Anda untuk memperbaruinya.")
    else:
        st.caption(f"Data stok per {rec.tanggal_data_stok.iloc[0]} · asumsi lead time {int(rec.asumsi_lead_time_hari.iloc[0])} hari · {rec.data_source.iloc[0]}")
        cnt = rec.status_restock.value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Habis", int(cnt.get("Habis", 0))); c2.metric("Restock segera", int(cnt.get("Restock segera", 0)))
        c3.metric("Waspada", int(cnt.get("Waspada", 0))); c4.metric("Aman", int(cnt.get("Aman", 0)))
        b_opts = sorted(rec.branch_name.unique()); s_opts = ["Habis", "Restock segera", "Waspada", "Aman"]
        sb = st.multiselect("Cabang (stok)", b_opts, default=b_opts)
        ss = st.multiselect("Status", s_opts, default=["Habis", "Restock segera"])
        view = rec[rec.branch_name.isin(sb) & rec.status_restock.isin(ss)]
        st.dataframe(view[["branch_name", "product_name", "category", "stok_sekarang", "minimum_stock", "rata2_permintaan_harian", "hari_cakupan_stok", "titik_pesan", "status_restock", "saran_jumlah_pesan"]])
        st.download_button("Unduh daftar restock (CSV)", data=view.to_csv(index=False).encode("utf-8"), file_name="restock_recommendation.csv", mime="text/csv")
        with st.expander("Cara menghitung rekomendasi"):
            st.write("Titik pesan = permintaan harian × lead time + stok pengaman (1,65 × simpangan baku × √lead time), minimal sama dengan stok minimum. "
                     "Status: Habis (stok 0) → Restock segera (≤ titik pesan) → Waspada (≤ 1,5× titik pesan) → Aman.")

# ------------------------------------------------------------------ tab 5: prediksi
with tab_pred:
    fc, hist, mcmp = load_analysis("demand_forecast"), load_analysis("weekly_demand_history"), load_analysis("model_comparison")
    if fc.empty or hist.empty or using_upload:
        st.info("Prediksi tersedia untuk data bawaan (hasil notebook 04).")
    else:
        st.caption("Prediksi unit terjual per minggu. Data sintetis & pendek (±12 minggu): gunakan sebagai demonstrasi metode.")
        pc = st.selectbox("Kategori", sorted(fc.category.unique()))
        pb = st.selectbox("Cabang", ["Semua cabang"] + sorted(fc.branch_name.unique()))
        h = hist[hist.category == pc]; p = fc[fc.category == pc]
        if pb != "Semua cabang":
            h, p = h[h.branch_name == pb], p[p.branch_name == pb]
        a = h.groupby("week_start").units.sum().rename("aktual"); q = p.groupby("week_start").forecast_units.sum().rename("prediksi")
        both = pd.concat([a, q], axis=1).sort_index()
        both.index = pd.to_datetime(both.index)
        st.line_chart(both)
        st.subheader("Perbandingan model (data uji = 3 minggu terakhir)")
        st.dataframe(mcmp)
        st.caption("Model terbaik dipilih berdasarkan MAE terkecil. Jika model sederhana menang, itu wajar untuk data pendek.")

# ------------------------------------------------------------------ tab 6: tentang data
with tab_info:
    st.subheader("Tentang data & proses")
    st.write("Pipeline: **01** gathering & assessing → **02** cleaning → **03** analisis (EDA) → **04** prediksi & restock → **05** serah terima ke tim Full-stack & Gen AI.")
    ar, cl = load_analysis("assessing_report"), load_analysis("cleaning_log")
    if not ar.empty:
        st.markdown("**Masalah data yang ditemukan (assessing)**"); st.dataframe(ar)
    if not cl.empty:
        st.markdown("**Penanganan yang dilakukan (cleaning log)**"); st.dataframe(cl)
    st.markdown("**Keterbatasan**: data sintetis; harga modal sintetis; periode 3 bulan; belum ada data retur/servis. Ganti dengan data primer dari buku Sumber Urip sebelum dipakai untuk keputusan.")
