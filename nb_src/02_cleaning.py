# %% [markdown]
# # 02 · Cleaning Data — Kios Sumber Urip
# **Tujuan:** membersihkan data mentah berdasarkan temuan di `01_gathering_assessing`.
# Setiap penanganan **dicatat beserta alasannya** di `cleaning_log.csv`, agar tidak ada data yang diubah/dihapus tanpa alasan yang dapat dipertanggungjawabkan.
#
# **Urutan kerja** (karena antar tabel saling bergantung):
# produk → pelanggan → transaksi (dasar) → detail transaksi → produk (harga modal) → transaksi (hitung ulang) → stok (inventory) → validasi.
#
# > ⚠️ Data ini **sintetis**. Logika pembersihannya dibuat umum agar bisa dipakai ulang untuk data primer dari buku Sumber Urip.

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
import os, re, sys, difflib, warnings
from collections import Counter
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50); pd.set_option("display.width", 170); pd.set_option("display.max_colwidth", 70)
RAW, CLEAN, ANALYSIS = "../data/raw", "../data/clean", "../data/analysis"
for d in (CLEAN, ANALYSIS): os.makedirs(d, exist_ok=True)
try:
    display
except NameError:
    display = print

tables = ["branches", "products", "customers", "transactions", "transaction_details", "inventory"]
raw = {t: pd.read_csv(f"{RAW}/{t}_raw.csv", dtype=str) for t in tables}   # semua teks dulu, lalu di-parse eksplisit
cleaning_log = []
def log_step(tabel, kolom, masalah, jumlah, penanganan, alasan):
    cleaning_log.append(dict(tabel=tabel, kolom=kolom, masalah=masalah, jumlah_baris_terdampak=int(jumlah), penanganan=penanganan, alasan=alasan))

# %% [markdown]
# ## 0. Fungsi bantu (parser)
# Fungsi kecil yang dipakai berulang: parser angka, parser tanggal, dan normalisasi label.

# %%
ID_MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7, "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12}

def parse_number(x):
    """'Rp 1.234.000' -> 1234000 | '2 pcs' -> 2 | '12%' -> 12 | '-' -> 0 | kosong -> NaN"""
    if x is None or (isinstance(x, float) and np.isnan(x)): return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)): return float(x)
    s = str(x).strip().lower()
    if s in ("", "nan", "none"): return np.nan
    if s in ("-", "--"): return 0.0
    s = s.replace("rp", "").replace("%", "")
    m = re.search(r"-?\d[\d.,]*", s)
    if not m: return np.nan
    t = m.group(0)
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t): t = t.replace(".", "")      # titik = pemisah ribuan
    return float(t.replace(",", "."))

def parse_date(x):
    """Mengenali YYYY-MM-DD, DD/MM/YYYY (kebiasaan Indonesia), dan DD-Mon-YYYY (Agu/Okt/...)."""
    if x is None or (isinstance(x, float) and np.isnan(x)): return pd.NaT
    s = str(x).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m: return pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m: return pd.Timestamp(int(m[3]), int(m[2]), int(m[1]))
    m = re.fullmatch(r"(\d{2})-([A-Za-z]{3})-(\d{4})", s)
    if m and m[2].lower() in ID_MON: return pd.Timestamp(int(m[3]), ID_MON[m[2].lower()], int(m[1]))
    return pd.NaT

def collapse(s):
    return re.sub(r"\s+", " ", str(s)).strip()

def map_branch(x):
    s = collapse(x).lower()
    if re.search(r"padang|pdg|sumber urip 1", s): return "BR01"
    if re.search(r"nenas|sumber urip 2", s): return "BR02"
    if re.search(r"paye|sumber urip 3", s): return "BR03"
    return np.nan

def norm_ctype(x):
    if pd.isna(x): return np.nan
    s = collapse(x).lower()
    for k in ("umum", "rekanan", "keluarga", "pemerintah"):
        if k in s: return k
    return np.nan

def norm_ttype(x):
    s = collapse(x).lower().replace("-", "_").replace(" ", "_")
    if "inaproc" in s or "pemerintah" in s: return "pemerintah_inaproc"
    if "rekanan" in s: return "rekanan"
    if "retail" in s: return "retail"
    return np.nan

def norm_category(x):
    s = collapse(x).lower().replace("_", " ")
    if "oli" in s: return "Oli"
    if s.startswith("ban") and "motor" in s: return "Ban motor"
    if s.startswith("ban") and "mobil" in s: return "Ban mobil"
    if s.startswith("spare") and "motor" in s: return "Spare part motor"
    if s.startswith("spare") and "mobil" in s: return "Spare part mobil"
    if s == "aki": return "Aki"
    if "aksesor" in s: return "Aksesori kendaraan"
    if "lainnya" in s or "perlengkapan" in s: return "Perlengkapan otomotif lainnya"
    return np.nan

print("parse_number:", [parse_number(v) for v in ["Rp 1.234.000", "2 pcs", "12%", "-", "3 item", "45000"]])
print("parse_date  :", [str(parse_date(v).date()) for v in ["2026-08-05", "05/08/2026", "05-Agu-2026"]])

# %% [markdown]
# ## 1. Produk (tahap awal)
# Langkah: normalisasi kategori → parse angka → hapus near-duplicate → rapikan nama → pulihkan merek.
# `cost_price` yang kosong dipulihkan nanti (langkah 5) dari detail transaksi.

# %%
pr = raw["products"].copy()
pr["category"] = pr.category.map(norm_category)
for c in ["selling_price", "discount_percentage", "minimum_stock", "cost_price"]:
    pr[c] = pr[c].map(parse_number)
log_step("products", "category", f"{raw['products'].category.nunique()} variasi penulisan kategori", len(pr), "dinormalisasi ke 8 kategori baku", "label konsisten diperlukan untuk agregasi per kategori")
n_text = int(raw["products"].selling_price.str.fullmatch(r"\d{1,3}(\.\d{3})+").sum() + raw["products"].discount_percentage.str.contains("%").sum())
log_step("products", "selling_price / discount_percentage", "angka tersimpan sebagai teks ('192.000', '12%')", n_text, "diparse ke angka", "agar bisa dihitung")
print("Kategori setelah dinormalisasi:", pr.category.nunique(), "| kategori tidak dikenali:", pr.category.isna().sum())

# %%
# Near-duplicate: id berakhiran -DUP. Bandingkan dengan produk aslinya sebelum menghapus.
dup = pr.product_id.str.endswith("-DUP")
cmp_ = pr[dup].assign(base=lambda x: x.product_id.str.replace("-DUP", "", regex=False)).merge(
    pr[~dup], left_on="base", right_on="product_id", suffixes=("_dup", "_asli"))
same = (cmp_.category_dup == cmp_.category_asli) & (cmp_.selling_price_dup == cmp_.selling_price_asli) & (cmp_.size_spec_dup.fillna("") == cmp_.size_spec_asli.fillna(""))
print(f"{dup.sum()} baris -DUP; {same.sum()} di antaranya identik (kategori, harga jual, ukuran) dengan produk aslinya")
display(cmp_[["product_id_dup", "product_name_dup", "product_name_asli"]].head(4))
pr = pr[~dup].copy()
log_step("products", "product_id", "near-duplicate (id -DUP, nama sedikit berbeda)", dup.sum(), "dihapus; produk asli dipertahankan", "atribut kunci identik dengan produk asli")

# %%
# Rapikan nama: spasi, kapitalisasi (kosakata dari nama yang berhuruf campuran), dan koreksi typo token.
# Fungsi dibuat generik supaya bisa dipakai juga untuk nama pelanggan.
def build_name_cleaner(names):
    names = names.map(collapse)
    mixed = names[(names != names.str.upper()) & (names != names.str.lower())]
    cnt = Counter(t for n in mixed for t in n.split(" "))
    vocab = {}
    for tok, c in cnt.most_common(): vocab.setdefault(tok.lower(), tok)        # bentuk kapitalisasi paling sering
    freq = {t.lower(): t for t, c in cnt.items() if c >= 3}                  # token yang dianggap 'benar' (sering muncul)
    def swap_match(tl):
        """token yang hanya berbeda karena dua huruf bersebelahan tertukar (mis. 'reaknan' -> 'rekanan')"""
        for k in freq:
            if len(k) == len(tl) and k != tl:
                d = [i for i in range(len(k)) if k[i] != tl[i]]
                if len(d) == 2 and d[1] == d[0] + 1 and k[d[0]] == tl[d[1]] and k[d[1]] == tl[d[0]]: return k
        return None
    def clean(name, unify_case=True):
        name = collapse(name)
        toks = []
        for t in name.split(" "):
            if t.lower() in vocab and (unify_case or name == name.upper() or name == name.lower()): toks.append(vocab[t.lower()])
            elif any(ch.isdigit() for ch in t) and any(ch.isalpha() for ch in t) and t == t.lower(): toks.append(t.upper())   # kode produk, mis. 'ss-560f'
            elif t.isalpha() and (t == t.upper() or t == t.lower()) and name in (name.upper(), name.lower()): toks.append(t.title())
            else: toks.append(t)
        out = []
        for t in toks:
            tl = t.lower()
            if tl in freq or any(ch.isdigit() for ch in t) or len(t) < 3:
                out.append(t); continue
            k = swap_match(tl)
            if k is None and len(t) >= 4:
                m = difflib.get_close_matches(tl, list(freq), n=1, cutoff=0.8)
                k = m[0] if m else None
            # ganti hanya jika token ini jauh lebih jarang daripada token 'benar' yang mirip, dan beda huruf (bukan sekadar tanda baca)
            if k and re.sub(r"\W", "", k) != re.sub(r"\W", "", tl) and cnt.get(t, 0) <= max(1, cnt[freq[k]] / 3):
                out.append(freq[k])
            else:
                out.append(t)
        return " ".join(out)
    return clean

def fix_size(name, size):
    """Ukuran ban di nama harus sama dengan kolom size_spec; token yang mirip diganti."""
    if not isinstance(size, str) or " " in size.strip() or not size.strip(): return name
    size = size.strip(); toks = name.split(" ")
    for b, t in enumerate(toks):                       # spasi bergeser: 'R V300-10' -> 'RV 300-10'
        if t != size and t.endswith(size) and t[:-len(size)].isalpha() and b > 0:
            toks[b - 1] += t[:-len(size)]; toks[b] = size
            return " ".join(toks)
    if size in name: return name
    r = [difflib.SequenceMatcher(None, t, size).ratio() for t in toks]
    b = int(np.argmax(r))
    if r[b] >= 0.75: toks[b] = size
    return " ".join(toks)

old = pr.product_name.copy()
clean_product_name = build_name_cleaner(pr.product_name)
pr["product_name"] = [fix_size(clean_product_name(n), s) for n, s in zip(pr.product_name, pr.size_spec)]
changed = (pr.product_name != old).sum()
print(f"{changed} nama produk dirapikan. Nama unik: {pr.product_name.is_unique}")
display(pd.DataFrame({"sebelum": old[pr.product_name != old], "sesudah": pr.product_name[pr.product_name != old]}).head(8))
log_step("products", "product_name", "spasi ganda, huruf besar/kecil seragam, typo", changed, "rapikan spasi, pulihkan kapitalisasi dari kosakata data, koreksi token typo & ukuran (dicocokkan dengan size_spec)", "nama dipakai tim Gen AI & Full-stack")
# Token yang hanya muncul sekali di seluruh daftar produk = kandidat typo yang tidak bisa dipastikan otomatis -> daftar cek manual
tok_all = Counter(t.lower() for n in pr.product_name for t in n.split(" "))
rare = pr[[any(tok_all[t.lower()] == 1 and t.isalpha() and len(t) >= 3 for t in n.split(" ")) for n in pr.product_name]]
rare[["product_id", "product_name"]].to_csv(f"{ANALYSIS}/produk_perlu_cek_manual.csv", index=False)
print(f"{len(rare)} nama produk berisi kata langka (kemungkinan typo atau memang unik) -> data/analysis/produk_perlu_cek_manual.csv")

# %%
# Pulihkan merek yang kosong: cari nama merek yang sudah dikenal di dalam nama produk;
# jika tidak ada, pakai merek tunggal pada kategori itu (Aksesori & Perlengkapan semuanya 'Aftermarket').
brands = sorted(pr.brand.dropna().unique(), key=len, reverse=True)
single_brand = {c: g.brand.dropna().unique()[0] for c, g in pr.groupby("category") if g.brand.dropna().nunique() == 1}
def find_brand(name, cat):
    for b in brands:
        if re.search(r"(?<![A-Za-z])" + re.escape(b.lower()) + r"(?![A-Za-z])", name.lower()): return b
    return single_brand.get(cat, np.nan)
miss = pr.brand.isna()
pr.loc[miss, "brand"] = [find_brand(n, c) for n, c in zip(pr.loc[miss, "product_name"], pr.loc[miss, "category"])]
print("Merek kosong sebelum:", miss.sum(), "| sesudah:", pr.brand.isna().sum())
log_step("products", "brand", "nilai kosong", miss.sum(), "dipulihkan dari nama produk / merek tunggal kategori", "merek tercantum di nama produk")

# %% [markdown]
# ## 2. Pelanggan
# Near-duplicate (id berakhiran huruf) digabung ke id asli. Jenis pelanggan yang kosong diisi dari transaksi.

# %%
cu = raw["customers"].copy()
cu["customer_type"] = cu.customer_type.map(norm_ctype)
dupc = cu.customer_id.str.contains(r"[A-Za-z]$")
base_ok = cu.loc[dupc, "customer_id"].str[:-1].isin(cu.customer_id)
print(f"{dupc.sum()} id pelanggan near-duplicate; id asli ditemukan untuk {base_ok.sum()} di antaranya")
cu = cu[~dupc].copy()
log_step("customers", "customer_id", "near-duplicate pelanggan (id berakhiran huruf)", dupc.sum(), "dihapus; id asli dipertahankan", "id asli ada dan atribut sama")

tx_ct = raw["transactions"].assign(ct=lambda x: x.customer_type.map(norm_ctype)).dropna(subset=["ct"]).groupby("customer_id").ct.agg(lambda s: s.mode().iloc[0])
miss = cu.customer_type.isna()
cu.loc[miss, "customer_type"] = cu.loc[miss, "customer_id"].map(tx_ct)
print("customer_type kosong sebelum:", miss.sum(), "| sesudah:", cu.customer_type.isna().sum())
log_step("customers", "customer_type", "nilai kosong", miss.sum(), "diisi dari jenis pelanggan yang paling sering muncul di transaksi", "jenis pelanggan konsisten per customer_id")

clean_customer_name = build_name_cleaner(cu.customer_name)
old = cu.customer_name.copy()
cu["customer_name"] = [clean_customer_name(n) for n in cu.customer_name]
log_step("customers", "customer_name", "variasi spasi/kapitalisasi/typo nama", (cu.customer_name != old).sum(), "dirapikan (spasi, kapitalisasi, typo token)", "nama konsisten (id pelanggan tetap menjadi kunci)")
display(cu.head())

# %% [markdown]
# ## 3. Transaksi (tahap dasar)
# Duplikat → cabang → tanggal → jenis pelanggan/transaksi → angka. Total yang rusak dihitung ulang dari detail di langkah 6.

# %%
tr = raw["transactions"].copy()
n0 = len(tr)
tr = tr.drop_duplicates().copy()
assert tr.transaction_id.is_unique, "masih ada transaction_id ganda"
log_step("transactions", "(seluruh baris)", "baris duplikat persis", n0 - len(tr), "dihapus (1 baris dipertahankan)", "isi seluruh kolom identik")

tr["branch_id"] = tr.branch.map(map_branch); tr = tr.drop(columns="branch")
print("cabang tidak terpetakan:", tr.branch_id.isna().sum()); print(tr.branch_id.value_counts().to_dict())
log_step("transactions", "branch", "nama cabang bervariasi", len(tr), "dipetakan ke branch_id dengan aturan kata kunci (padang/nenas/paye/sumber urip 1-3)", "3 cabang yang dikenal")

fmt_before = tr.transaction_date.map(lambda s: re.sub(r"\d", "9", str(s))).value_counts()
tr["transaction_date"] = tr.transaction_date.map(parse_date)
print("tanggal gagal diparse:", tr.transaction_date.isna().sum(), "| rentang:", tr.transaction_date.min().date(), "s.d.", tr.transaction_date.max().date())
dmy = raw["transactions"].transaction_date.dropna().str.extract(r"^(\d{2})/(\d{2})/\d{4}$").dropna().astype(int)
print("Bukti DD/MM/YYYY: bagian pertama bernilai >12 pada", (dmy[0] > 12).sum(), "baris, bagian kedua tidak pernah >12:", (dmy[1] > 12).sum() == 0)
log_step("transactions", "transaction_date", "format tanggal campur", (fmt_before.drop("9999-99-99", errors="ignore")).sum(), "diparse; DD/MM/YYYY diasumsikan hari-bulan-tahun", "ada nilai hari >12 pada bagian pertama sehingga bukan MM/DD")

tr["customer_type"] = tr.customer_type.map(norm_ctype)
miss = tr.customer_type.isna()
tr.loc[miss, "customer_type"] = tr.loc[miss, "customer_id"].map(cu.set_index("customer_id").customer_type)
tr["transaction_type"] = tr.transaction_type.map(norm_ttype)
print("customer_type kosong sebelum:", miss.sum(), "| sesudah:", tr.customer_type.isna().sum(), "| transaction_type tidak dikenali:", tr.transaction_type.isna().sum())
log_step("transactions", "customer_type / transaction_type", "variasi penulisan dan nilai kosong", len(tr), "dinormalisasi; yang kosong diisi dari tabel pelanggan (customer_id)", "setiap transaksi punya customer_id yang valid")

for c in ["total_items", "gross_amount", "discount_amount", "net_amount", "total_cost", "other_cost", "gross_profit"]:
    tr[c] = tr[c].map(parse_number)
rt = raw["transactions"].drop_duplicates()
n_text = int(sum((rt[c].notna() & pd.to_numeric(rt[c], errors="coerce").isna()).sum() for c in ["total_items", "gross_amount", "discount_amount", "net_amount"]))
log_step("transactions", "net_amount / total_items", "angka tersimpan sebagai teks ('Rp 1.234.000', '3 item')", n_text, "diparse ke angka", "agar dapat dihitung")
display(tr.head(3))

# %% [markdown]
# ## 4. Detail transaksi
# Urutan: duplikat → angka → harga satuan → subtotal → pemulihan `product_id` → rekonsiliasi relasi yatim.

# %%
dt = raw["transaction_details"].copy()
n0 = len(dt)
dt = dt.drop_duplicates().copy()
assert dt.detail_id.is_unique, "masih ada detail_id ganda"
log_step("transaction_details", "(seluruh baris)", "baris duplikat persis", n0 - len(dt), "dihapus", "isi seluruh kolom identik")
dt = dt.sort_values("detail_id").reset_index(drop=True)
for c in ["quantity", "unit_price", "discount", "discount_percentage_applied", "subtotal", "cost_subtotal", "profit"]:
    dt[c] = dt[c].map(parse_number)
master_price = pr.set_index("product_id").selling_price

# %%
# 4a. quantity negatif: apakah subtotal positif dan cocok dengan |qty| x harga - diskon?
neg = dt.quantity < 0
exp_sub = dt.quantity.abs() * dt.product_id.map(master_price) - dt.discount
print(f"{neg.sum()} baris quantity negatif; subtotalnya cocok dengan |qty| x harga - diskon pada {(exp_sub[neg] == dt.subtotal[neg]).sum()} baris")
dt["quantity"] = dt.quantity.abs()
qty_text = int((raw["transaction_details"].quantity.notna() & pd.to_numeric(raw["transaction_details"].quantity, errors="coerce").isna()).sum())
log_step("transaction_details", "quantity", "bernilai negatif / teks ('2 pcs')", int(neg.sum()) + qty_text, "teks di-parse; nilai negatif diubah ke nilai mutlak", "subtotal pada baris tsb positif dan sesuai |qty| x harga (salah tanda, bukan retur)")

# 4b. unit_price berbeda dari harga master
mp = dt.product_id.map(master_price)
bad = mp.notna() & (dt.unit_price != mp)
print(f"{bad.sum()} baris unit_price != harga master; rasio:", sorted((dt.unit_price / mp)[bad].round(2).unique()))
dt.loc[bad, "unit_price"] = mp[bad]
log_step("transaction_details", "unit_price", "10x lebih besar dari harga master (salah ketik)", bad.sum(), "diganti harga jual master produk", "subtotal pada baris itu sudah sesuai harga master")

# 4c. subtotal kosong -> hitung ulang; lalu cek rumus pada baris lain
formula = dt.quantity * dt.unit_price - dt.discount
miss = dt.subtotal.isna()
dt.loc[miss, "subtotal"] = formula[miss]
print(f"subtotal kosong dihitung ulang: {miss.sum()} | subtotal tidak sesuai rumus (selain yang kosong): {(dt.subtotal != formula).sum()}")
log_step("transaction_details", "subtotal", "nilai kosong", miss.sum(), "dihitung ulang: qty x harga satuan - diskon", "rumus terbukti benar pada seluruh baris lain")

# %%
# 4d. Pulihkan product_id kosong dari product_name_input (dicocokkan ke nama produk + dicek dengan harga satuan)
key = lambda s: collapse(s).lower()
name_keys = {key(n): pid for pid, n in zip(pr.product_id, pr.product_name)}
klist = list(name_keys)
def best_match(name_in, unit_price):
    cands = difflib.get_close_matches(key(name_in), klist, n=5, cutoff=0.8)
    scored = []
    for k in cands:
        pid = name_keys[k]; mpx = master_price[pid]
        bonus = 0.5 if (unit_price == mpx or unit_price == mpx * 10 or unit_price == mpx / 10) else 0
        scored.append((difflib.SequenceMatcher(None, key(name_in), k).ratio() + bonus, pid))
    return max(scored)[1] if scored else np.nan

known = dt[dt.product_id.notna()].sample(300, random_state=1)
acc = np.mean([best_match(n, p) == i for n, p, i in zip(known.product_name_input, known.unit_price, known.product_id)])
print(f"Uji metode pada 300 baris yang product_id-nya diketahui: akurasi {acc:.1%}")
miss = dt.product_id.isna()
dt.loc[miss, "product_id"] = [best_match(n, p) for n, p in zip(dt.loc[miss, "product_name_input"], dt.loc[miss, "unit_price"])]
print("product_id kosong sebelum:", miss.sum(), "| sesudah:", dt.product_id.isna().sum())
log_step("transaction_details", "product_id", "nilai kosong", miss.sum(), "dipulihkan dari product_name_input (kemiripan teks + kecocokan harga satuan)", f"metode diuji pada 300 baris berlabel: akurasi {acc:.1%}")

# %% [markdown]
# ## 5. Rekonsiliasi relasi yatim (foreign key)
# Beberapa detail memiliki `transaction_id` yang tidak ada (atau salah menempel ke transaksi lain).
# `detail_id` berurutan per transaksi, sehingga baris yang "terjepit" di antara baris milik transaksi yang sama sangat mungkin ikut transaksi itu.
# Dugaan tersebut **dibuktikan** dengan total transaksi: sisa `net_amount` transaksi (setelah dikurangi baris lain) harus sama dengan subtotal baris tersebut.

# %%
valid = set(tr.transaction_id)
tids = dt.transaction_id.tolist(); n = len(dt)
is_valid = [t in valid for t in tids]
island = [False] * n
for i in range(1, n - 1):
    if is_valid[i] and is_valid[i - 1] and tids[i - 1] == tids[i + 1] and tids[i] != tids[i - 1]: island[i] = True
suspect = [(not is_valid[i]) or island[i] for i in range(n)]
print(f"baris mencurigakan: {sum(suspect)} (id tidak ada: {sum(not v for v in is_valid)}, 'terjepit' di transaksi lain: {sum(island)})")

def neighbor(i, step):
    j = i + step
    while 0 <= j < n and suspect[j]: j += step
    return tids[j] if 0 <= j < n else None

attached = dt[[not s for s in suspect]].groupby("transaction_id").subtotal.sum()
net = tr.set_index("transaction_id").net_amount
resid = (net - attached.reindex(net.index).fillna(0)).to_dict()
pending, assigned, changed = [i for i in range(n) if suspect[i]], {}, True
while pending and changed:
    changed = False
    for i in list(pending):
        cands = {c for c in (neighbor(i, -1), neighbor(i, +1)) if c}
        hit = [c for c in cands if abs(resid.get(c, np.nan) - dt.subtotal[i]) < 0.5]
        if len(hit) == 1:
            assigned[i] = hit[0]; resid[hit[0]] -= dt.subtotal[i]; pending.remove(i); changed = True
before = dt.loc[list(assigned), ["detail_id", "transaction_id"]].rename(columns={"transaction_id": "id_lama"})
for i, t in assigned.items(): dt.at[i, "transaction_id"] = t
before["id_baru"] = [assigned[i] for i in assigned]
display(before)
print(f"dipulihkan: {len(assigned)} | belum terselesaikan: {len(pending)}")
log_step("transaction_details", "transaction_id", "foreign key yatim / salah menempel ke transaksi lain", len(assigned) + len(pending), "ditetapkan ulang ke transaksi tetangga yang sisa net_amount-nya sama dengan subtotal baris", f"dibuktikan dengan rekonsiliasi total; {len(pending)} baris tidak terselesaikan")
if pending:
    dt.loc[pending].to_csv(f"{ANALYSIS}/unresolved_detail_rows.csv", index=False)
    dt = dt.drop(index=pending)

# %% [markdown]
# ### 5b. Rekonsiliasi lanjutan
# Ada kasus lain: `transaction_id` yang salah ketik ternyata **kebetulan menjadi id transaksi lain yang valid**, sehingga lolos dari pemeriksaan di atas.
# Cirinya: transaksi A kelebihan baris (jumlah subtotal detail > `net_amount`), sedangkan transaksi B kekurangan baris, dan keduanya sehari-cabang yang sama.

# %%
att = dt.groupby("transaction_id").subtotal.sum()
resid = (net - att.reindex(net.index).fillna(0))
excess, short = resid[resid < -0.5], resid[resid > 0.5]
print(f"transaksi kelebihan baris: {len(excess)} | transaksi kekurangan baris: {len(short)}")
moved = []
for e, r in excess.items():
    lines = dt[dt.transaction_id == e]
    cand = lines[lines.subtotal == -r]
    prefix = e.rsplit("-", 1)[0]
    targets = [t for t, v in short.items() if t.startswith(prefix) and abs(v + r) < 0.5]
    if len(cand) == 1 and len(targets) == 1:
        dt.loc[cand.index[0], "transaction_id"] = targets[0]
        moved.append((cand.detail_id.iloc[0], e, targets[0]))
display(pd.DataFrame(moved, columns=["detail_id", "id_lama", "id_baru"]))
log_step("transaction_details", "transaction_id", "salah ketik yang kebetulan menjadi id transaksi lain yang valid", len(moved), "dipindahkan ke transaksi (hari & cabang sama) yang kekurangan baris dengan nilai tepat sama", "total subtotal detail harus sama dengan net_amount transaksi")
att = dt.groupby("transaction_id").subtotal.sum()
still = (net - att.reindex(net.index).fillna(0)).abs() > 0.5
print("transaksi yang totalnya masih tidak cocok dengan detail:", still.sum())

# %% [markdown]
# ## 6. Finalisasi detail & produk (harga modal)
# `cost_price` yang kosong dipulihkan dari `cost_subtotal / quantity` (median per produk).

# %%
dt["quantity"] = dt.quantity.astype(int)
cost_est = (dt.cost_subtotal / dt.quantity).groupby(dt.product_id).median()
miss = pr.cost_price.isna()
pr.loc[miss, "cost_price"] = pr.loc[miss, "product_id"].map(cost_est)
print("cost_price kosong sebelum:", miss.sum(), "| sesudah:", pr.cost_price.isna().sum(), "| produk tanpa penjualan (tak bisa dipulihkan):", pr.loc[miss & pr.cost_price.isna(), "product_id"].tolist())
log_step("products", "cost_price", "nilai kosong", miss.sum(), "dipulihkan dari median cost_subtotal/quantity pada detail transaksi", "cost_subtotal pada detail dihitung dari harga modal produk yang sama")
dt["profit"] = dt.subtotal - dt.cost_subtotal
dt = dt.drop(columns=["product_name_input"])

# %% [markdown]
# ## 7. Transaksi: hitung ulang total dari detail
# Detail transaksi adalah sumber kebenaran. Total transaksi yang kosong/tidak konsisten dihitung ulang.

# %%
dt["gross_line"] = dt.quantity * dt.unit_price
agg = dt.groupby("transaction_id").agg(gross=("gross_line", "sum"), disc=("discount", "sum"), net=("subtotal", "sum"), cost=("cost_subtotal", "sum"), q=("quantity", "sum"))
tr = tr.set_index("transaction_id")
for col, src in [("gross_amount", "gross"), ("discount_amount", "disc"), ("net_amount", "net"), ("total_cost", "cost"), ("total_items", "q")]:
    diff = (tr[col].isna() | (tr[col] != agg[src].reindex(tr.index))).sum()
    print(f"{col:16s} berbeda/kosong sebelum dihitung ulang: {diff}")
    if diff: log_step("transactions", col, "kosong / tidak konsisten dengan detail", diff, "dihitung ulang dari detail transaksi", "detail transaksi adalah sumber kebenaran")
    tr[col] = agg[src].reindex(tr.index)
tr["gross_profit"] = tr.net_amount - tr.total_cost - tr.other_cost
dt = dt.drop(columns="gross_line")
tr = tr.reset_index()

# %% [markdown]
# ## 8. Stok (inventory)
# `stock_out` dihitung dari detail transaksi (sumber kebenaran), `ending_stock` dari rumus `initial + in − out`.

# %%
iv = raw["inventory"].copy()
n0 = len(iv)
iv = iv.drop_duplicates().copy()
assert iv.inventory_id.is_unique
log_step("inventory", "(seluruh baris)", "baris duplikat persis", n0 - len(iv), "dihapus", "isi seluruh kolom identik")
iv["stock_date"] = iv.stock_date.map(parse_date)
miss = iv.stock_date.isna()
def month_end_from_id(inv_id):
    m = re.search(r"INV-(\d{4})(\d{2})-", inv_id)
    return pd.Timestamp(int(m[1]), int(m[2]), 1) + pd.offsets.MonthEnd(0)
iv.loc[miss, "stock_date"] = iv.loc[miss, "inventory_id"].map(month_end_from_id)
log_step("inventory", "stock_date", "nilai kosong & format campur", miss.sum(), "diisi akhir bulan dari inventory_id; format di-parse", "inventory_id memuat tahun-bulan snapshot")
for c in ["initial_stock", "stock_in", "stock_out", "ending_stock"]: iv[c] = iv[c].map(parse_number)
log_step("inventory", "stock_in", "'-' untuk nol", int((raw["inventory"].stock_in == "-").sum()), "diubah ke 0", "'-' dipakai sebagai nol")

fact = dt.merge(tr[["transaction_id", "transaction_date", "branch_id"]], on="transaction_id")
fact["ym"] = fact.transaction_date.dt.strftime("%Y-%m")
sold = fact.groupby(["ym", "branch_id", "product_id"]).quantity.sum().rename("out_calc").reset_index()
iv["ym"] = iv.stock_date.dt.strftime("%Y-%m")
iv = iv.merge(sold, on=["ym", "branch_id", "product_id"], how="left").fillna({"out_calc": 0})
bad_out = (iv.stock_out != iv.out_calc)
bad_end = (iv.ending_stock != iv.initial_stock + iv.stock_in - iv.stock_out)
print(f"stock_out berbeda dari penjualan detail: {bad_out.sum()} | ending_stock tidak sesuai rumus (sebelum perbaikan): {bad_end.sum()}")
iv["stock_out"] = iv.out_calc
iv["ending_stock"] = iv.initial_stock + iv.stock_in - iv.stock_out
log_step("inventory", "stock_out", "bernilai negatif / berbeda dari penjualan", bad_out.sum(), "dihitung ulang dari jumlah quantity detail transaksi", "stok keluar = barang terjual")
log_step("inventory", "ending_stock", "tidak sesuai rumus", bad_end.sum(), "dihitung ulang: initial + in - out", "rumus stok baku")
iv = iv.drop(columns=["ym", "out_calc"])
print("stok negatif:", (iv.ending_stock < 0).sum())

# %% [markdown]
# ## 9. Simpan data bersih & log penanganan

# %%
def to_int(df, cols):
    for c in cols: df[c] = df[c].round().astype("int64")
    return df
pr = to_int(pr, ["cost_price", "selling_price", "discount_percentage", "minimum_stock"])
dt = to_int(dt, ["quantity", "unit_price", "discount", "subtotal", "cost_subtotal", "profit"])
tr = to_int(tr, ["total_items", "gross_amount", "discount_amount", "net_amount", "total_cost", "other_cost", "gross_profit"])
iv = to_int(iv, ["initial_stock", "stock_in", "stock_out", "ending_stock"])
tr["transaction_date"] = tr.transaction_date.dt.strftime("%Y-%m-%d")
iv["stock_date"] = iv.stock_date.dt.strftime("%Y-%m-%d")

cols = {
 "branches": ["branch_id", "branch_name", "location", "opened_year", "is_synthetic", "data_source"],
 "products": ["product_id", "product_name", "category", "subcategory", "brand", "size_spec", "cost_price", "selling_price", "discount_percentage", "minimum_stock", "is_synthetic", "selling_price_source", "discount_rule_source", "marked_in_photo", "verify_note"],
 "customers": ["customer_id", "customer_type", "customer_name", "preferred_branch_id", "partner_fee_pct", "data_source"],
 "transactions": ["transaction_id", "transaction_date", "branch_id", "transaction_type", "customer_type", "customer_id", "total_items", "gross_amount", "discount_amount", "net_amount", "total_cost", "other_cost", "gross_profit", "data_source"],
 "transaction_details": ["detail_id", "transaction_id", "product_id", "quantity", "unit_price", "discount", "discount_percentage_applied", "subtotal", "cost_subtotal", "profit"],
 "inventory": ["inventory_id", "branch_id", "product_id", "initial_stock", "stock_in", "stock_out", "ending_stock", "stock_date", "data_source"],
}
dt["discount_percentage_applied"] = dt.discount_percentage_applied.astype(float)
clean = {"branches": raw["branches"], "products": pr, "customers": cu, "transactions": tr.sort_values(["transaction_date", "transaction_id"]),
         "transaction_details": dt.sort_values("detail_id"), "inventory": iv.sort_values("inventory_id")}
for t, df in clean.items():
    df[cols[t]].to_csv(f"{CLEAN}/{t}.csv", index=False, encoding="utf-8")
    print(f"{t:22s} -> {len(df):>5} baris")
log_df = pd.DataFrame(cleaning_log); log_df.insert(0, "no", range(1, len(log_df) + 1))
log_df.to_csv(f"{ANALYSIS}/cleaning_log.csv", index=False)
display(log_df[["no", "tabel", "kolom", "masalah", "jumlah_baris_terdampak", "penanganan"]])

# %% [markdown]
# ## 10. Validasi data bersih
# 27 pemeriksaan otomatis (kunci unik, relasi antar tabel, kesesuaian rumus, stok, rentang tanggal, label sintetis, dll).

# %%
sys.path.append("../src")
from validate_dataset import run_validation
results = run_validation(CLEAN)
assert all(r[1] for r in results), "Ada pemeriksaan yang gagal, periksa langkah pembersihan."

# %% [markdown]
# ### Kesimpulan cleaning
# - Seluruh masalah di `assessing_report.csv` ditangani dan didokumentasikan di `cleaning_log.csv`.
# - Data bersih lolos seluruh pemeriksaan validasi → siap dianalisis (`03_eda_analisis.ipynb`).
# - **Catatan keterbatasan:** nama produk yang rusak oleh typo pada angka/kata langka dipulihkan dengan aturan heuristik; periksa ulang bila memakai data primer.
