# %% [markdown]
# # 04 · Prediksi Permintaan & Rekomendasi Restock (Tambahan / Side Quest)
# **Tujuan:** (a) memprediksi permintaan mingguan per cabang dan kategori, membandingkan beberapa model dengan metrik yang sama,
# (b) membuat daftar rekomendasi restock per cabang-produk dengan aturan *reorder point* (tanpa melatih model).
#
# **Catatan desain (menghindari kebocoran data):**
# - Pembagian data **berdasarkan waktu** (3 minggu terakhir = data uji); fitur hanya memakai nilai minggu-minggu *sebelumnya* (lag).
# - Label tidak dibuat dari rumus yang sama dengan fiturnya. Targetnya adalah permintaan nyata minggu berikutnya.
# - Rekomendasi restock memakai aturan statistik yang transparan, bukan model, sehingga mudah dijelaskan ke pemilik.
#
# > ⚠️ Data sintetis dengan hanya ±12 minggu; hasil ini **demonstrasi metode**, bukan prediksi nyata Sumber Urip.

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
import os, math, warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50); pd.set_option("display.width", 170)
CLEAN, ANALYSIS = "../data/clean", "../data/analysis"
FIG = f"{ANALYSIS}/figures"; os.makedirs(FIG, exist_ok=True)
try:
    display
except NameError:
    display = print
plt.rcParams.update({"figure.figsize": (9, 4.2), "axes.grid": True, "grid.alpha": .3, "axes.spines.top": False, "axes.spines.right": False})

tx = pd.read_csv(f"{CLEAN}/transactions.csv", parse_dates=["transaction_date"])
dt = pd.read_csv(f"{CLEAN}/transaction_details.csv")
pr = pd.read_csv(f"{CLEAN}/products.csv")
br = pd.read_csv(f"{CLEAN}/branches.csv")
iv = pd.read_csv(f"{CLEAN}/inventory.csv", parse_dates=["stock_date"])
fact = dt.merge(tx[["transaction_id", "transaction_date", "branch_id"]], on="transaction_id").merge(pr[["product_id", "product_name", "category", "minimum_stock"]], on="product_id")
last_date = tx.transaction_date.max()
print("Data sampai:", last_date.date())

# %% [markdown]
# ## 1. Deret waktu mingguan (unit terjual per cabang × kategori)
# Hanya minggu penuh (Senin–Minggu) yang dipakai.

# %%
fact["week_start"] = fact.transaction_date.dt.to_period("W-SUN").dt.start_time
weeks = [w for w in sorted(fact.week_start.unique()) if w >= tx.transaction_date.min() and w + pd.Timedelta(days=6) <= last_date]
weeks = pd.DatetimeIndex(weeks)
print(f"{len(weeks)} minggu penuh: {weeks.min().date()} s.d. {weeks.max().date()}")
grp = pd.MultiIndex.from_product([br.branch_id, sorted(pr.category.unique()), weeks], names=["branch_id", "category", "week_start"])
weekly = fact.groupby(["branch_id", "category", "week_start"]).quantity.sum().reindex(grp, fill_value=0).rename("units").reset_index()
weekly = weekly.merge(br[["branch_id", "branch_name"]], on="branch_id")
weekly.to_csv(f"{ANALYSIS}/weekly_demand_history.csv", index=False)
display(weekly.pivot_table(index="week_start", columns="category", values="units", aggfunc="sum").head())

# %% [markdown]
# ## 2. Fitur & pembagian data berdasarkan waktu

# %%
LAGS = [1, 2, 3, 4]
w = weekly.sort_values(["branch_id", "category", "week_start"]).copy()
g = w.groupby(["branch_id", "category"]).units
for k in LAGS: w[f"lag{k}"] = g.shift(k)
w["ma4"] = w[[f"lag{k}" for k in LAGS]].mean(axis=1)
w["t"] = w.groupby(["branch_id", "category"]).cumcount()
w["series"] = w.branch_id + "|" + w.category
model_df = w.dropna(subset=[f"lag{k}" for k in LAGS]).copy()
test_weeks = sorted(model_df.week_start.unique())[-3:]
train, test = model_df[~model_df.week_start.isin(test_weeks)], model_df[model_df.week_start.isin(test_weeks)]
print(f"train: {len(train)} baris | test: {len(test)} baris (minggu {pd.Timestamp(test_weeks[0]).date()} s.d. {pd.Timestamp(test_weeks[-1]).date()})")
X_cols = [f"lag{k}" for k in LAGS]
dummies = lambda d: pd.get_dummies(d.series).reindex(columns=sorted(w.series.unique()), fill_value=0).astype(float)
def Xmat(d): return pd.concat([d[X_cols].reset_index(drop=True), dummies(d).reset_index(drop=True)], axis=1)

# %% [markdown]
# ## 3. Membandingkan model (metrik sama: MAE, RMSE, WAPE pada data uji)

# %%
def metrics(y, p):
    e = np.asarray(y) - np.asarray(p)
    return dict(MAE=np.mean(np.abs(e)), RMSE=np.sqrt(np.mean(e ** 2)), WAPE_pct=np.abs(e).sum() / np.sum(y) * 100)
preds = {"Naive (minggu lalu)": test.lag1.values, "Rata-rata 4 minggu": test.ma4.values}
lr = LinearRegression().fit(Xmat(train), train.units); preds["Linear Regression (lag + seri)"] = np.clip(lr.predict(Xmat(test)), 0, None)
rf = RandomForestRegressor(n_estimators=300, max_depth=5, min_samples_leaf=3, random_state=42).fit(Xmat(train), train.units); preds["Random Forest (lag + seri)"] = rf.predict(Xmat(test))
comp = pd.DataFrame({name: metrics(test.units.values, p) for name, p in preds.items()}).T.round(2).sort_values("MAE").reset_index().rename(columns={"index": "model"})
comp["terbaik"] = comp.model == comp.model.iloc[0]
comp.to_csv(f"{ANALYSIS}/model_comparison.csv", index=False)
display(comp)
best = comp.model.iloc[0]
print("Model terbaik berdasarkan MAE data uji:", best)

# %% [markdown]
# **Cara membaca:** bila model sederhana (naive / rata-rata 4 minggu) sama baiknya atau lebih baik daripada model ML, itu wajar untuk data pendek —
# pilih yang paling sederhana dan mudah dijelaskan. Tuliskan keterbatasan ini di README/laporan.

# %% [markdown]
# ## 4. Prediksi 4 minggu ke depan (rekursif) dengan model terbaik
# Model dilatih ulang pada seluruh data (train + test), lalu dipakai memprediksi minggu demi minggu.

# %%
full = model_df
lr_f = LinearRegression().fit(Xmat(full), full.units)
rf_f = RandomForestRegressor(n_estimators=300, max_depth=5, min_samples_leaf=3, random_state=42).fit(Xmat(full), full.units)
hist = {s: list(g_.sort_values("week_start").units) for s, g_ in w.groupby("series")}
first_future = weeks.max() + pd.Timedelta(days=7)
rows = []
for step in range(4):
    ws = first_future + pd.Timedelta(days=7 * step)
    feat = pd.DataFrame([{"series": s, **{f"lag{k}": h[-k] for k in LAGS}} for s, h in hist.items()])
    feat["ma4"] = feat[[f"lag{k}" for k in LAGS]].mean(axis=1)
    if best.startswith("Naive"): p = feat.lag1.values
    elif best.startswith("Rata"): p = feat.ma4.values
    elif best.startswith("Linear"): p = np.clip(lr_f.predict(Xmat(feat)), 0, None)
    else: p = rf_f.predict(Xmat(feat))
    for s, v in zip(feat.series, p):
        hist[s].append(float(v)); b, c = s.split("|")
        rows.append(dict(branch_id=b, category=c, week_start=ws.date(), forecast_units=round(float(v), 1), model=best))
fc = pd.DataFrame(rows).merge(br[["branch_id", "branch_name"]], on="branch_id")
fc.to_csv(f"{ANALYSIS}/demand_forecast.csv", index=False)
display(fc.pivot_table(index="week_start", columns="category", values="forecast_units", aggfunc="sum").round(0))

hist_tot = weekly.groupby("week_start").units.sum(); fc_tot = fc.groupby("week_start").forecast_units.sum()
fig, ax = plt.subplots()
ax.plot(hist_tot.index, hist_tot.values, marker="o", label="aktual (minggu penuh)")
ax.plot(pd.to_datetime(fc_tot.index), fc_tot.values, marker="o", ls="--", label=f"prediksi ({best})")
ax.set_title("Total unit terjual per minggu: aktual vs prediksi (data sintetis)"); ax.set_ylabel("unit"); ax.legend(); fig.autofmt_xdate()
plt.tight_layout(); plt.savefig(f"{FIG}/prediksi_permintaan.png", dpi=130); plt.show()

# %% [markdown]
# ## 5. Rekomendasi restock per cabang-produk (aturan reorder point)
# - Permintaan harian rata-rata (*d*) dan simpangan bakunya (*s*) dihitung dari **28 hari terakhir** (hari tanpa penjualan dihitung 0).
# - **Lead time** pemasok diasumsikan **3 hari** (asumsi simulasi; ganti setelah dikonfirmasi pemilik).
# - Stok pengaman = 1,65 × s × √lead time (tingkat layanan ±95%). **Titik pesan (ROP)** = d × lead time + stok pengaman, minimal sama dengan `minimum_stock`.
# - Status: *Habis* (stok ≤ 0) → *Restock segera* (stok ≤ ROP) → *Waspada* (stok ≤ 1,5 × ROP) → *Aman*.
# - Saran jumlah pesan = (ROP + kebutuhan 7 hari) − stok sekarang.

# %%
LEAD_TIME_DAYS, Z, WINDOW = 3, 1.65, 28
start = last_date - pd.Timedelta(days=WINDOW - 1)
recent = fact[fact.transaction_date >= start]
day = recent.groupby(["branch_id", "product_id", "transaction_date"]).quantity.sum().reset_index()
agg = day.groupby(["branch_id", "product_id"]).quantity.agg(total="sum", ssq=lambda s: (s ** 2).sum()).reset_index()
agg["d"] = agg.total / WINDOW
agg["s"] = np.sqrt(np.maximum(agg.ssq / WINDOW - agg.d ** 2, 0))
cur = iv[iv.stock_date == iv.stock_date.max()][["branch_id", "product_id", "ending_stock"]].rename(columns={"ending_stock": "stok_sekarang"})
rec = cur.merge(agg[["branch_id", "product_id", "d", "s"]], on=["branch_id", "product_id"], how="left").fillna({"d": 0, "s": 0})
rec = rec.merge(pr[["product_id", "product_name", "category", "minimum_stock"]], on="product_id").merge(br[["branch_id", "branch_name"]], on="branch_id")
rec["stok_pengaman"] = np.ceil(Z * rec.s * math.sqrt(LEAD_TIME_DAYS))
rec["titik_pesan"] = np.maximum(np.ceil(rec.d * LEAD_TIME_DAYS + rec.stok_pengaman), rec.minimum_stock).astype(int)
rec["hari_cakupan_stok"] = np.where(rec.d > 0, (rec.stok_sekarang / rec.d.replace(0, np.nan)).round(1), np.nan)
rec["status_restock"] = np.select([rec.stok_sekarang <= 0, rec.stok_sekarang <= rec.titik_pesan, rec.stok_sekarang <= 1.5 * rec.titik_pesan],
                                  ["Habis", "Restock segera", "Waspada"], "Aman")
rec["saran_jumlah_pesan"] = np.where(rec.status_restock == "Aman", 0, np.maximum(0, rec.titik_pesan + np.ceil(rec.d * 7) - rec.stok_sekarang)).astype(int)
rec["rata2_permintaan_harian"] = rec.d.round(2)
out = rec[["branch_id", "branch_name", "product_id", "product_name", "category", "stok_sekarang", "minimum_stock", "rata2_permintaan_harian", "hari_cakupan_stok",
           "titik_pesan", "status_restock", "saran_jumlah_pesan"]].assign(_urut=lambda x: x.status_restock.map({"Habis": 0, "Restock segera": 1, "Waspada": 2, "Aman": 3})).sort_values(["_urut", "branch_name", "hari_cakupan_stok"]).drop(columns="_urut")
out["asumsi_lead_time_hari"] = LEAD_TIME_DAYS; out["tanggal_data_stok"] = iv.stock_date.max().date(); out["data_source"] = "synthetic"
out.to_csv(f"{ANALYSIS}/restock_recommendation.csv", index=False)
print(out.groupby(["branch_name", "status_restock"]).size().unstack(fill_value=0))
display(out[out.status_restock.isin(["Habis", "Restock segera"])].head(12))

# %% [markdown]
# ### Kesimpulan & keterbatasan
# - Perbandingan model ada di `model_comparison.csv`; model terpilih dipakai untuk `demand_forecast.csv`.
# - Rekomendasi restock bersifat **aturan statistik** dan bergantung pada asumsi lead time 3 hari serta data 28 hari terakhir.
# - Karena data sintetis dan pendek, jangan dipresentasikan sebagai prediksi nyata Sumber Urip; ganti dengan data primer sebelum dipakai untuk keputusan.
