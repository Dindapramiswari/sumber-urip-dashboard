# %% [markdown]
# # 01 · Gathering & Assessing Data — Kios Sumber Urip
# **Tujuan:** memuat data mentah (raw), lalu menilai kualitasnya sebelum dibersihkan.
# Ini memenuhi checklist Main Quest Data Science: *Gathering Data* dan *Assessing Data*.
#
# > ⚠️ **Data di proyek ini adalah data SINTETIS (simulasi)**, dibuat tim untuk pengembangan dan pengujian.
# > Bukan data operasional nyata Sumber Urip. Saat data primer dari buku sudah didigitalkan, jalankan pipeline yang sama pada data tersebut.
#
# **Output notebook ini:** `data/analysis/assessing_report.csv` (daftar masalah data + rencana penanganan).

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
import os, re, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50); pd.set_option("display.width", 170); pd.set_option("display.max_colwidth", 60)
RAW, CLEAN, ANALYSIS = "../data/raw", "../data/clean", "../data/analysis"
os.makedirs(ANALYSIS, exist_ok=True)
try:
    display
except NameError:
    display = print

# %% [markdown]
# ## 1. Gathering Data
# Data mentah berasal dari 6 tabel: cabang, produk, pelanggan, transaksi, detail transaksi, dan stok (inventory).
# Pada proyek nyata, tabel ini dihasilkan dari digitalisasi buku/nota Sumber Urip.

# %%
tables = ["branches", "products", "customers", "transactions", "transaction_details", "inventory"]
# PENTING: semua kolom dibaca sebagai TEKS (dtype=str) supaya pandas tidak mengubah nilai diam-diam.
# Contoh jebakan: harga "192.000" (format Indonesia) akan terbaca sebagai 192.0 jika dibiarkan otomatis.
raw = {t: pd.read_csv(f"{RAW}/{t}_raw.csv", dtype=str) for t in tables}
for t, df in raw.items():
    print(f"{t:22s} -> {df.shape[0]:>5} baris x {df.shape[1]:>2} kolom")

# %%
display(raw["transactions"].head(5))

# %%
display(raw["transaction_details"].head(5))

# %% [markdown]
# ## 2. Assessing Data
# Kita memeriksa: (a) struktur & tipe data, (b) nilai kosong, (c) duplikat, (d) format tidak seragam,
# (e) label tidak konsisten, (f) outlier / kesalahan ketik, (g) relasi antar tabel (foreign key), (h) kesesuaian rumus.
# Setiap temuan dicatat ke tabel `findings`.

# %%
findings = []
def add(tabel, kolom, masalah, jumlah, rencana):
    jumlah = int(jumlah)
    if jumlah > 0:
        findings.append(dict(tabel=tabel, kolom=kolom, masalah=masalah, jumlah_baris=jumlah, rencana_penanganan=rencana))
num = lambda s: pd.to_numeric(s, errors="coerce")

def date_fmt(s):
    s = str(s).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): return "YYYY-MM-DD"
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s): return "DD/MM/YYYY"
    if re.fullmatch(r"\d{2}-[A-Za-z]{3}-\d{4}", s): return "DD-Mon-YYYY"
    return "tidak dikenali"

# %% [markdown]
# ### 2a. Tabel `transactions`

# %%
tr = raw["transactions"]
print("Tipe data:"); display(tr.dtypes.to_frame("dtype").T)
print("Nilai kosong per kolom:"); display(tr.isna().sum()[lambda s: s > 0])
print("Baris duplikat persis:", tr.duplicated().sum(), "| transaction_id duplikat:", tr.transaction_id.duplicated().sum())

# %%
print("Format tanggal:"); display(tr.transaction_date.map(date_fmt).value_counts())
print("Variasi penulisan cabang (%d variasi):" % tr.branch.nunique()); display(tr.branch.value_counts())

# %%
print("customer_type:"); display(tr.customer_type.value_counts(dropna=False))
print("transaction_type:"); display(tr.transaction_type.value_counts(dropna=False))

# %%
# Kolom angka yang seharusnya numerik tetapi terbaca sebagai teks
for c in ["total_items", "gross_amount", "discount_amount", "net_amount"]:
    n_text = (tr[c].notna() & num(tr[c]).isna()).sum()
    print(f"{c:16s} dtype={str(tr[c].dtype):8s} teks non-angka={n_text}")
    add("transactions", c, "angka tersimpan sebagai teks (mis. 'Rp 1.234.000', '3 item')", n_text, "ubah ke numerik dengan parser (hapus 'Rp', titik ribuan, satuan)")

# Pemeriksaan silang: gross_amount - net_amount harus sama dengan discount_amount
g, n, d = num(tr.gross_amount), num(tr.net_amount), num(tr.discount_amount)
ok = g.notna() & n.notna() & d.notna()
mismatch = ok & ((g - n) != d)
print("Baris dengan gross - net != discount:", mismatch.sum())
display(tr.loc[mismatch, ["transaction_id", "gross_amount", "discount_amount", "net_amount"]].head())

# %%
add("transactions", "(seluruh baris)", "baris duplikat persis", tr.duplicated().sum(), "hapus duplikat (pertahankan 1)")
add("transactions", "transaction_date", "format tanggal campur (YYYY-MM-DD, DD/MM/YYYY, DD-Mon-YYYY)", (tr.transaction_date.map(date_fmt) != "YYYY-MM-DD").sum(), "parse semua format menjadi tanggal baku YYYY-MM-DD")
add("transactions", "branch", "nama cabang tidak konsisten (%d variasi untuk 3 cabang)" % tr.branch.nunique(), len(tr), "petakan ke branch_id (BR01/BR02/BR03)")
add("transactions", "customer_type", "variasi penulisan jenis pelanggan", len(tr), "normalisasi ke umum/rekanan/keluarga/pemerintah")
add("transactions", "customer_type", "nilai kosong", tr.customer_type.isna().sum(), "isi dari tabel pelanggan berdasarkan customer_id")
add("transactions", "transaction_type", "variasi penulisan jenis transaksi", len(tr), "normalisasi ke retail/rekanan/pemerintah_inaproc")
add("transactions", "discount_amount", "nilai kosong", tr.discount_amount.isna().sum(), "hitung ulang dari jumlah diskon detail transaksi")
add("transactions", "gross_amount", "tidak konsisten dengan net_amount + discount_amount (dugaan salah ketik/outlier)", mismatch.sum(), "hitung ulang dari qty x harga satuan detail transaksi")

# %% [markdown]
# ### 2b. Tabel `transaction_details`

# %%
dt, pr = raw["transaction_details"], raw["products"]
print("Nilai kosong:"); display(dt.isna().sum()[lambda s: s > 0])
print("Baris duplikat persis:", dt.duplicated().sum(), "| detail_id duplikat:", dt.detail_id.duplicated().sum())
q = num(dt.quantity)
print("quantity teks non-angka:", (dt.quantity.notna() & q.isna()).sum(), "| quantity negatif:", (q < 0).sum())
display(dt.loc[q.isna() | (q < 0), ["detail_id", "quantity", "unit_price", "discount", "subtotal"]].head(8))

# %%
# Harga satuan vs harga jual di master produk
master_price = num(pr.drop_duplicates("product_id").set_index("product_id").selling_price.astype(str).str.replace(".", "", regex=False))
chk = dt.assign(master=dt.product_id.map(master_price), up=num(dt.unit_price))
bad_price = chk.master.notna() & (chk.up != chk.master)
print("unit_price != harga master:", bad_price.sum(), "| rasio unit_price/master pada baris tsb:", sorted((chk.up / chk.master)[bad_price].round(2).unique()))

# %%
orphan = ~dt.transaction_id.isin(tr.transaction_id)
print("Foreign key yatim (transaction_id tidak ada di transactions):", orphan.sum())
display(dt.loc[orphan, ["detail_id", "transaction_id", "product_id"]].head())
print("product_id kosong:", dt.product_id.isna().sum(), "| product_id tidak ada di master:", (dt.product_id.notna() & ~dt.product_id.isin(pr.product_id)).sum())

# %%
add("transaction_details", "(seluruh baris)", "baris duplikat persis", dt.duplicated().sum(), "hapus duplikat")
add("transaction_details", "quantity", "angka tersimpan sebagai teks ('2 pcs', '3x')", (dt.quantity.notna() & q.isna()).sum(), "parser angka")
add("transaction_details", "quantity", "bernilai negatif", (q < 0).sum(), "periksa dengan subtotal; jika subtotal positif, ubah ke nilai mutlak")
add("transaction_details", "unit_price", "berbeda dari harga jual master (rasio 10x, dugaan salah ketik)", bad_price.sum(), "ganti dengan harga jual master produk")
add("transaction_details", "subtotal", "nilai kosong", dt.subtotal.isna().sum(), "hitung ulang: qty x harga - diskon")
add("transaction_details", "product_id", "nilai kosong", dt.product_id.isna().sum(), "pulihkan dari product_name_input (pencocokan nama + harga)")
add("transaction_details", "transaction_id", "foreign key yatim", orphan.sum(), "rekonsiliasi dengan baris tetangga (detail_id berurutan) dan total transaksi")

# %% [markdown]
# ### 2c. Tabel `products`

# %%
print("Kategori (%d variasi):" % pr.category.nunique()); display(pr.category.value_counts())
print("Nilai kosong:"); display(pr.isna().sum()[lambda s: s > 0])
dupid = pr.product_id.str.endswith("-DUP")
print("product_id berakhiran '-DUP':", dupid.sum()); display(pr[dupid][["product_id", "product_name", "selling_price"]].head())
sp_text = pr.selling_price.astype(str).str.fullmatch(r"\d{1,3}(\.\d{3})+")   # contoh "192.000" (titik = pemisah ribuan)
dp_text = pr.discount_percentage.astype(str).str.contains("%")
name_issue = pr.product_name.str.contains(r"\s{2,}|^\s|\s$", regex=True) | (pr.product_name == pr.product_name.str.upper()) | (pr.product_name == pr.product_name.str.lower())
print("selling_price teks:", sp_text.sum(), "| discount_percentage teks '%':", dp_text.sum(), "| nama bermasalah (spasi/kapital):", name_issue.sum())

# %%
add("products", "category", "variasi penulisan kategori (%d variasi untuk 8 kategori)" % pr.category.nunique(), len(pr), "normalisasi ke 8 kategori baku")
add("products", "product_id", "near-duplicate produk (id berakhiran -DUP)", dupid.sum(), "hapus baris -DUP setelah dibandingkan dengan produk asli")
add("products", "brand", "nilai kosong", pr.brand.isna().sum(), "pulihkan dari nama produk / daftar merek")
add("products", "cost_price", "nilai kosong", pr.cost_price.isna().sum(), "pulihkan dari cost_subtotal / quantity pada detail transaksi")
add("products", "selling_price", "tersimpan sebagai teks dengan titik ribuan", sp_text.sum(), "parser angka")
add("products", "discount_percentage", "tersimpan sebagai teks ('12%')", dp_text.sum(), "parser angka")
add("products", "product_name", "spasi ganda / huruf besar-kecil / typo", name_issue.sum(), "rapikan spasi, kapitalisasi, koreksi token")

# %% [markdown]
# ### 2d. Tabel `inventory`

# %%
iv = raw["inventory"]
print("Nilai kosong:"); display(iv.isna().sum()[lambda s: s > 0])
print("Baris duplikat persis:", iv.duplicated().sum())
print("Format tanggal:"); display(iv.stock_date.dropna().map(date_fmt).value_counts())
si_text = iv.stock_in.notna() & num(iv.stock_in).isna()
so_neg = num(iv.stock_out) < 0
ending_bad = num(iv.ending_stock) != (num(iv.initial_stock) + num(iv.stock_in).fillna(0) - num(iv.stock_out))
print("stock_in teks:", si_text.sum(), "| stock_out negatif:", so_neg.sum(), "| ending_stock != initial+in-out:", ending_bad.sum())

# %%
add("inventory", "(seluruh baris)", "baris duplikat persis", iv.duplicated().sum(), "hapus duplikat")
add("inventory", "stock_date", "nilai kosong", iv.stock_date.isna().sum(), "isi dari inventory_id (yyyymm) menjadi akhir bulan")
add("inventory", "stock_date", "format tanggal campur", (iv.stock_date.dropna().map(date_fmt) != "YYYY-MM-DD").sum(), "parser tanggal")
add("inventory", "stock_in", "tersimpan sebagai teks ('-' untuk nol)", si_text.sum(), "ubah '-' menjadi 0")
add("inventory", "stock_out", "bernilai negatif", so_neg.sum(), "hitung ulang dari jumlah quantity detail transaksi")
add("inventory", "ending_stock", "tidak sesuai rumus initial + in - out", ending_bad.sum(), "hitung ulang dengan rumus")

# %% [markdown]
# ### 2e. Tabel `customers`

# %%
cu = raw["customers"]
print(cu.isna().sum()[lambda s: s > 0]); print("id berakhiran huruf (near-duplicate):", cu.customer_id.str.contains(r"[A-Z]$").sum())
display(cu[cu.customer_id.str.contains(r"[A-Z]$")])
add("customers", "customer_id", "near-duplicate pelanggan (id berakhiran huruf)", cu.customer_id.str.contains(r"[A-Z]$").sum(), "gabungkan ke id asli")
add("customers", "customer_type", "nilai kosong", cu.customer_type.isna().sum(), "isi dari jenis pelanggan pada transaksi")
add("customers", "customer_name", "variasi penulisan nama", len(cu), "rapikan spasi dan kapitalisasi")

# %% [markdown]
# ## 3. Laporan Assessing
# Tabel berikut adalah ringkasan seluruh temuan dan rencana penanganan. Ini yang menjadi dasar notebook `02_cleaning`.

# %%
report = pd.DataFrame(findings)
report.insert(0, "no", range(1, len(report) + 1))
report.to_csv(f"{ANALYSIS}/assessing_report.csv", index=False)
print(f"{len(report)} jenis masalah data ditemukan.")
display(report)

# %% [markdown]
# ### Kesimpulan assessing
# - Data mentah **belum layak dianalisis**: ada duplikat, nilai kosong, format campur, label tidak konsisten, outlier, relasi yatim, dan angka yang tidak sesuai rumus.
# - Semua masalah **dapat ditangani dengan alasan yang dapat dipertanggungjawabkan** (rekonsiliasi dengan tabel lain atau rumus), tanpa menghapus data secara sembarangan.
# - Langkah berikutnya: `02_cleaning.ipynb`.
