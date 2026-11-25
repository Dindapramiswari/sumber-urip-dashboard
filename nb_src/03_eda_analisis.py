# %% [markdown]
# # 03 · Analisis Data (EDA) — Kios Sumber Urip
# **Tujuan:** menjawab pertanyaan bisnis dari data bersih dan menyiapkan tabel hasil analisis untuk dashboard serta tim lain.
#
# > ⚠️ **Data bersifat SINTETIS.** Angka dan temuan di notebook ini hanya **demonstrasi pipeline**, bukan kondisi nyata Sumber Urip.
# > Setelah data primer dari buku tersedia, jalankan ulang notebook ini; kesimpulan bisnis hanya boleh diambil dari data primer.
#
# ## Pertanyaan bisnis
# 1. Kategori dan produk apa yang menyumbang omzet terbesar, per cabang?
# 2. Produk mana yang *fast-moving* dan *slow-moving* (bahan prioritas pengelolaan stok)?
# 3. Berapa diskon yang diberikan per jenis pelanggan dan kategori, dan apakah masih dalam batas standar pemilik?
# 4. Bagaimana pola penjualan per hari dan per minggu di tiap cabang?
# 5. Kategori / jenis pelanggan mana yang margin laba kotornya tertinggi dan terendah setelah diskon dan fee rekanan?
# 6. Barang mana yang stoknya menipis (≤ stok minimum) pada akhir periode?

# %% [markdown]
# ## 0. Setup Google Colab (jalankan sel ini PERTAMA)
# Sel di bawah otomatis **me-mount Google Drive** dan pindah ke folder `notebooks/` proyek, supaya path relatif
# (`../data/raw`, `../data/clean`, `../src`) tetap benar. Di Jupyter lokal sel ini tidak melakukan apa-apa.
#
# **Syarat:** seluruh folder `ds_pipeline_sumber_urip/` (berisi `data/`, `notebooks/`, `src/`, dst.) sudah ada di Google Drive.
# Jika letaknya bukan di `MyDrive/ds_pipeline_sumber_urip`, ubah `PROJECT_DIR` di bawah.

# %%
import os, sys, glob
if "google.colab" in sys.modules:
    from google.colab import drive
    drive.mount("/content/drive")
    PROJECT_DIR = "/content/drive/MyDrive/ds_pipeline_sumber_urip"   # <-- UBAH jika folder Anda di tempat lain
    if not os.path.isdir(PROJECT_DIR):                                 # cari otomatis di seluruh Drive
        hit = glob.glob("/content/drive/MyDrive/**/ds_pipeline_sumber_urip", recursive=True)
        if hit: PROJECT_DIR = hit[0]
    assert os.path.isdir(f"{PROJECT_DIR}/data"), (
        f"Folder proyek tidak ditemukan di {PROJECT_DIR}. Upload folder ds_pipeline_sumber_urip ke Google Drive "
        "lalu perbaiki PROJECT_DIR.")
    os.chdir(f"{PROJECT_DIR}/notebooks")
print("Folder kerja:", os.getcwd())

# %%
import os, warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50); pd.set_option("display.width", 170); pd.set_option("display.max_colwidth", 60)
CLEAN, ANALYSIS = "../data/clean", "../data/analysis"
FIG = f"{ANALYSIS}/figures"
os.makedirs(FIG, exist_ok=True)
try:
    display
except NameError:
    display = print
rp = lambda x: "Rp " + f"{x:,.0f}".replace(",", ".")
plt.rcParams.update({"figure.figsize": (9, 4.2), "axes.grid": True, "grid.alpha": .3, "axes.spines.top": False, "axes.spines.right": False})

tx = pd.read_csv(f"{CLEAN}/transactions.csv", parse_dates=["transaction_date"])
dt = pd.read_csv(f"{CLEAN}/transaction_details.csv")
pr = pd.read_csv(f"{CLEAN}/products.csv")
iv = pd.read_csv(f"{CLEAN}/inventory.csv", parse_dates=["stock_date"])
br = pd.read_csv(f"{CLEAN}/branches.csv")
cu = pd.read_csv(f"{CLEAN}/customers.csv")
fact = (dt.merge(tx[["transaction_id", "transaction_date", "branch_id", "customer_type", "transaction_type", "customer_id"]], on="transaction_id")
          .merge(pr[["product_id", "product_name", "category", "brand", "discount_percentage"]], on="product_id")
          .merge(br[["branch_id", "branch_name"]], on="branch_id"))
fact["gross_line"] = fact.quantity * fact.unit_price
fact["month"] = fact.transaction_date.dt.strftime("%Y-%m")
fact["week_start"] = fact.transaction_date.dt.to_period("W-SUN").dt.start_time
fact["weekday"] = fact.transaction_date.dt.dayofweek
print(f"{len(tx)} transaksi | {len(dt)} baris detail | {pr.shape[0]} produk | periode {tx.transaction_date.min().date()} s.d. {tx.transaction_date.max().date()}")

# %% [markdown]
# ## 0. Memeriksa ketepatan data sebelum dianalisis
# Total dari tabel transaksi harus sama dengan total dari detail; tidak boleh ada baris tanpa produk/cabang.

# %%
checks = {
    "omzet bersih: transaksi = detail": tx.net_amount.sum() == dt.subtotal.sum(),
    "diskon: transaksi = detail": tx.discount_amount.sum() == dt.discount.sum(),
    "tidak ada detail tanpa produk/cabang": len(fact) == len(dt),
    "laba kotor transaksi = laba detail - fee": tx.gross_profit.sum() == dt.profit.sum() - tx.other_cost.sum(),
}
for k, v in checks.items(): print(("OK   " if v else "GAGAL"), k)
assert all(checks.values())

# %% [markdown]
# ## 1. Omzet per kategori, cabang, dan bulan (Pertanyaan 1)

# %%
by_cat = fact.groupby("category").agg(omzet_bersih=("subtotal", "sum"), omzet_kotor=("gross_line", "sum"), unit_terjual=("quantity", "sum"), jumlah_baris=("detail_id", "count")).reset_index()
by_cat["share_omzet_pct"] = (by_cat.omzet_bersih / by_cat.omzet_bersih.sum() * 100).round(1)
by_cat = by_cat.sort_values("omzet_bersih", ascending=False)
by_cat.to_csv(f"{ANALYSIS}/sales_by_category.csv", index=False)
display(by_cat)

by_branch_month = tx.assign(month=tx.transaction_date.dt.strftime("%Y-%m")).groupby(["branch_id", "month"]).agg(
    jumlah_transaksi=("transaction_id", "count"), omzet_bersih=("net_amount", "sum"), laba_kotor=("gross_profit", "sum"), diskon=("discount_amount", "sum")).reset_index()
by_branch_month = by_branch_month.merge(br[["branch_id", "branch_name"]], on="branch_id")
by_branch_month.to_csv(f"{ANALYSIS}/sales_by_branch_month.csv", index=False)
display(by_branch_month)

cat_branch = fact.pivot_table(index="category", columns="branch_name", values="subtotal", aggfunc="sum", fill_value=0)
cat_branch.reset_index().to_csv(f"{ANALYSIS}/sales_category_by_branch.csv", index=False)
display((cat_branch / cat_branch.sum() * 100).round(1))

fig, ax = plt.subplots()
by_cat.sort_values("omzet_bersih").plot.barh(x="category", y="omzet_bersih", ax=ax, legend=False, color="#1F4E78")
ax.set_xlabel("Omzet bersih (Rp)"); ax.set_ylabel(""); ax.set_title("Omzet bersih per kategori (data sintetis)")
plt.tight_layout(); plt.savefig(f"{FIG}/omzet_per_kategori.png", dpi=130); plt.show()

# %% [markdown]
# ## 2. Produk terlaris, fast-moving & slow-moving (Pertanyaan 2)
# - **Fast-moving:** unit terjual ≥ persentil ke-75 *dalam kategorinya*. **Slow-moving:** ≤ persentil ke-25 atau terjual ≤ 2 kali.
# - **ABC:** A = produk yang bersama-sama menyumbang 80% omzet, B = 15% berikutnya, C = 5% sisanya.

# %%
prod_sales = fact.groupby(["product_id", "product_name", "category"]).agg(unit_terjual=("quantity", "sum"), jumlah_baris=("detail_id", "count"),
                                                                         hari_terjual=("transaction_date", "nunique"), omzet_bersih=("subtotal", "sum"), laba_kotor_baris=("profit", "sum")).reset_index()
allp = pr[["product_id", "product_name", "category"]].merge(prod_sales.drop(columns=["product_name", "category"]), on="product_id", how="left").fillna(0)
allp["pctl_dalam_kategori"] = allp.groupby("category").unit_terjual.rank(pct=True)
allp["pergerakan"] = np.where((allp.pctl_dalam_kategori >= 0.75) & (allp.jumlah_baris > 2), "fast-moving",
                      np.where((allp.pctl_dalam_kategori <= 0.25) | (allp.jumlah_baris <= 2), "slow-moving", "medium"))
allp = allp.sort_values("omzet_bersih", ascending=False)
cum = allp.omzet_bersih.cumsum() / allp.omzet_bersih.sum()
allp["kelas_abc"] = np.where(cum <= 0.80, "A", np.where(cum <= 0.95, "B", "C"))
allp.to_csv(f"{ANALYSIS}/product_movement.csv", index=False)
print(allp.pergerakan.value_counts().to_dict(), "|", allp.kelas_abc.value_counts().to_dict())
top = allp.head(10)[["product_id", "product_name", "category", "unit_terjual", "omzet_bersih", "kelas_abc"]]
top.to_csv(f"{ANALYSIS}/top_products.csv", index=False)
display(top)

# %% [markdown]
# ## 3. Diskon per jenis pelanggan dan kategori (Pertanyaan 3)
# Diskon efektif = total diskon ÷ omzet kotor. Dibandingkan dengan **batas standar pemilik** (oli 12%, ban mobil 10%, ban motor 12%, spare part 20–25%; kategori lain = asumsi simulasi).

# %%
fact["std_disc_amount"] = fact.gross_line * fact.discount_percentage / 100
disc = fact.groupby(["customer_type", "category"]).agg(omzet_kotor=("gross_line", "sum"), diskon=("discount", "sum"), diskon_standar_maks=("std_disc_amount", "sum"),
                                                       baris=("detail_id", "count"), baris_berdiskon=("discount", lambda s: (s > 0).sum())).reset_index()
disc["diskon_efektif_pct"] = (disc.diskon / disc.omzet_kotor * 100).round(2)
disc["batas_standar_pct"] = (disc.diskon_standar_maks / disc.omzet_kotor * 100).round(2)
disc["pemakaian_batas_pct"] = (disc.diskon / disc.diskon_standar_maks * 100).round(1)
disc["share_baris_berdiskon_pct"] = (disc.baris_berdiskon / disc.baris * 100).round(1)
disc.to_csv(f"{ANALYSIS}/discount_analysis.csv", index=False)
display(disc[["customer_type", "category", "baris", "diskon_efektif_pct", "batas_standar_pct", "pemakaian_batas_pct", "share_baris_berdiskon_pct"]])
over = (fact.discount > fact.std_disc_amount + 100).sum()      # toleransi pembulatan Rp100
print("Baris dengan diskon MELEBIHI batas standar produk:", over)

by_type = fact.groupby("customer_type").agg(omzet_kotor=("gross_line", "sum"), diskon=("discount", "sum")).assign(diskon_efektif_pct=lambda x: (x.diskon / x.omzet_kotor * 100).round(2)).reset_index()
fig, ax = plt.subplots(figsize=(6.5, 3.8))
ax.bar(by_type.customer_type, by_type.diskon_efektif_pct, color="#2E75B6"); ax.set_ylabel("Diskon efektif (%)"); ax.set_title("Diskon efektif per jenis pelanggan (data sintetis)")
plt.tight_layout(); plt.savefig(f"{FIG}/diskon_per_jenis_pelanggan.png", dpi=130); plt.show()

# %% [markdown]
# ## 4. Pola penjualan: hari & minggu (Pertanyaan 4)

# %%
daily = tx.groupby(["branch_id", "transaction_date"]).agg(jumlah_transaksi=("transaction_id", "count"), omzet_bersih=("net_amount", "sum")).reset_index()
daily = daily.merge(br[["branch_id", "branch_name"]], on="branch_id")
daily.to_csv(f"{ANALYSIS}/sales_by_day.csv", index=False)
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
daily["hari"] = daily.transaction_date.dt.dayofweek.map(dict(enumerate(HARI)))
wk = daily.groupby(["branch_name", "hari"]).agg(rata2_transaksi=("jumlah_transaksi", "mean"), rata2_omzet=("omzet_bersih", "mean")).reset_index()
wk["hari"] = pd.Categorical(wk.hari, HARI, ordered=True); wk = wk.sort_values(["branch_name", "hari"])
wk.to_csv(f"{ANALYSIS}/weekday_pattern.csv", index=False)
display(wk.pivot(index="hari", columns="branch_name", values="rata2_transaksi").round(1))

weekly = tx.assign(week_start=tx.transaction_date.dt.to_period("W-SUN").dt.start_time).groupby(["branch_id", "week_start"]).net_amount.sum().reset_index().merge(br[["branch_id", "branch_name"]], on="branch_id")
# hanya minggu PENUH (Senin-Minggu) yang digambar; minggu pertama/terakhir biasanya terpotong dan menyesatkan
full_wk = (weekly.week_start >= tx.transaction_date.min()) & (weekly.week_start + pd.Timedelta(days=6) <= tx.transaction_date.max())
weekly = weekly[full_wk]
fig, ax = plt.subplots()
for name, g in weekly.groupby("branch_name"): ax.plot(g.week_start, g.net_amount, marker="o", label=name)
ax.set_title("Omzet bersih mingguan per cabang (data sintetis)"); ax.set_ylabel("Rp"); ax.legend(); fig.autofmt_xdate()
plt.tight_layout(); plt.savefig(f"{FIG}/omzet_mingguan_per_cabang.png", dpi=130); plt.show()

payday = tx.assign(gajian=(tx.transaction_date.dt.day >= 25) | (tx.transaction_date.dt.day <= 3)).groupby("gajian").agg(hari=("transaction_date", "nunique"), transaksi=("transaction_id", "count"))
payday["transaksi_per_hari"] = (payday.transaksi / payday.hari).round(1)
display(payday)

# %% [markdown]
# ## 5. Margin laba kotor (Pertanyaan 5)
# Margin kategori dihitung dari laba baris (sebelum fee). Margin per jenis pelanggan dihitung dari laba transaksi (setelah fee rekanan).

# %%
mc = fact.groupby("category").agg(omzet_bersih=("subtotal", "sum"), laba_kotor=("profit", "sum")).reset_index()
mc["margin_pct"] = (mc.laba_kotor / mc.omzet_bersih * 100).round(2)
mc = mc.sort_values("margin_pct", ascending=False); mc.to_csv(f"{ANALYSIS}/margin_by_category.csv", index=False)
mt = tx.groupby("customer_type").agg(omzet_bersih=("net_amount", "sum"), laba_kotor=("gross_profit", "sum"), fee=("other_cost", "sum")).reset_index()
mt["margin_pct"] = (mt.laba_kotor / mt.omzet_bersih * 100).round(2); mt.to_csv(f"{ANALYSIS}/margin_by_customer_type.csv", index=False)
display(mc); display(mt)
fig, ax = plt.subplots()
ax.bar(mc.category, mc.margin_pct, color="#548235"); ax.set_ylabel("Margin laba kotor (%)"); ax.set_title("Margin per kategori (harga modal sintetis)")
plt.xticks(rotation=25, ha="right"); plt.tight_layout(); plt.savefig(f"{FIG}/margin_per_kategori.png", dpi=130); plt.show()

# %% [markdown]
# ## 6. Status stok akhir periode (Pertanyaan 6)

# %%
last = iv[iv.stock_date == iv.stock_date.max()].merge(pr[["product_id", "product_name", "category", "minimum_stock"]], on="product_id").merge(br[["branch_id", "branch_name"]], on="branch_id")
last["status_stok"] = np.where(last.ending_stock <= 0, "habis", np.where(last.ending_stock <= last.minimum_stock, "menipis (<= minimum)", "aman"))
last = last.rename(columns={"ending_stock": "stok_akhir"})
last[["branch_id", "branch_name", "product_id", "product_name", "category", "stok_akhir", "minimum_stock", "status_stok", "stock_date"]].to_csv(f"{ANALYSIS}/stock_status.csv", index=False)
print(last.groupby(["branch_name", "status_stok"]).size().unstack(fill_value=0))
display(last[last.status_stok != "aman"].sort_values(["branch_name", "stok_akhir"])[["branch_name", "product_name", "stok_akhir", "minimum_stock", "status_stok"]].head(10))

# %% [markdown]
# ## 7. Ringkasan KPI & temuan otomatis

# %%
kpi = {
    "periode_awal": str(tx.transaction_date.min().date()), "periode_akhir": str(tx.transaction_date.max().date()),
    "jumlah_transaksi": int(len(tx)), "unit_terjual": int(dt.quantity.sum()),
    "omzet_kotor": int(tx.gross_amount.sum()), "total_diskon": int(tx.discount_amount.sum()), "omzet_bersih": int(tx.net_amount.sum()),
    "laba_kotor": int(tx.gross_profit.sum()), "margin_laba_kotor_pct": round(tx.gross_profit.sum() / tx.net_amount.sum() * 100, 2),
    "diskon_efektif_pct": round(tx.discount_amount.sum() / tx.gross_amount.sum() * 100, 2),
    "rata2_nilai_transaksi": int(tx.net_amount.mean()), "total_fee_rekanan": int(tx.other_cost.sum()),
    "produk_stok_menipis_atau_habis": int((last.status_stok != "aman").sum()), "sumber_data": "synthetic",
}
pd.DataFrame({"metrik": list(kpi), "nilai": list(kpi.values())}).to_csv(f"{ANALYSIS}/kpi_summary.csv", index=False)
top_cat = by_cat.iloc[0]; best_m, worst_m = mc.iloc[0], mc.iloc[-1]
br_tot = by_branch_month.groupby("branch_name").omzet_bersih.sum().sort_values(ascending=False)
print("TEMUAN (otomatis, DATA SINTETIS):")
print(f"1. Kategori omzet terbesar: {top_cat.category} ({top_cat.share_omzet_pct}% dari omzet bersih {rp(kpi['omzet_bersih'])}).")
print(f"2. Cabang omzet tertinggi: {br_tot.index[0]} ({rp(br_tot.iloc[0])}); terendah: {br_tot.index[-1]} ({rp(br_tot.iloc[-1])}).")
print(f"3. {int((allp.pergerakan == 'fast-moving').sum())} produk fast-moving, {int((allp.pergerakan == 'slow-moving').sum())} slow-moving; {int((allp.kelas_abc == 'A').sum())} produk kelas A menyumbang 80% omzet.")
print(f"4. Diskon efektif keseluruhan {kpi['diskon_efektif_pct']}%; jenis pelanggan dengan diskon efektif tertinggi: {by_type.sort_values('diskon_efektif_pct').iloc[-1].customer_type}.")
print(f"5. Margin laba kotor keseluruhan {kpi['margin_laba_kotor_pct']}%; tertinggi: {best_m.category} ({best_m.margin_pct}%), terendah: {worst_m.category} ({worst_m.margin_pct}%).")
print(f"6. {kpi['produk_stok_menipis_atau_habis']} kombinasi cabang-produk berstatus menipis/habis pada {last.stock_date.max().date()}.")

# %% [markdown]
# ## Kesimpulan & rekomendasi (kerangka)
# Rekomendasi berikut berlaku **jika pola yang sama terbukti pada data primer** dari buku Sumber Urip:
# 1. **Fokuskan stok** pada produk kelas A / fast-moving dan tinjau ulang produk slow-moving yang modalnya besar.
# 2. **Standarkan batas diskon** per kategori & jenis pelanggan (tabel `discount_analysis.csv`) agar kasir tidak menunggu konfirmasi pemilik.
# 3. **Pantau stok menipis** per cabang dengan daftar rekomendasi restock (`04_prediksi_permintaan_restock`).
# 4. Evaluasi margin kategori dengan diskon tinggi (spare part) dan dampak fee bengkel rekanan.
#
# Keterbatasan: data sintetis; harga modal sintetis; periode hanya 3 bulan; tidak ada musiman nyata; tidak ada data retur/servis.
