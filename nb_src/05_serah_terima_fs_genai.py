# %% [markdown]
# # 05 · Serah Terima Data ke Tim Full-stack & Tim Gen AI
# **Tujuan:** mengemas hasil kerja Data Science menjadi paket data yang **siap dipakai** tim lain, lengkap dengan kontrak data dan kamus data.
#
# | Penerima | Folder | Isi utama |
# |---|---|---|
# | Tim **Full-stack** | `handoff/for_fullstack/` | data awal (seed) database, aturan diskon, stok terkini, hasil analisis untuk dashboard (CSV + JSON), kontrak API |
# | Tim **Gen AI** | `handoff/for_genai/` | dataset intent berlabel (train/val/test), kamus alias produk/cabang, basis pengetahuan produk (RAG), aturan diskon, kontrak data |
#
# > ⚠️ Semua data **sintetis**. Kolom `data_source` dipertahankan agar label ini tidak hilang. Kolom **harga modal (`cost_price`) dipisahkan** karena rahasia usaha (hanya untuk peran pemilik).

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
import os, re, json, shutil, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50); pd.set_option("display.width", 170); pd.set_option("display.max_colwidth", 80)
CLEAN, ANALYSIS, HANDOFF = "../data/clean", "../data/analysis", "../handoff"
FS, AI = f"{HANDOFF}/for_fullstack", f"{HANDOFF}/for_genai"
for d in (f"{FS}/seed", f"{FS}/dashboard_data", AI): os.makedirs(d, exist_ok=True)
try:
    display
except NameError:
    display = print
rd = lambda t: pd.read_csv(f"{CLEAN}/{t}.csv")
br, pr, cu, tx, dt, iv = (rd(t) for t in ["branches", "products", "customers", "transactions", "transaction_details", "inventory"])
manifest = []
def save(df, path, penerima, tujuan):
    df.to_csv(path, index=False, encoding="utf-8")
    manifest.append(dict(penerima=penerima, file=path.replace("../handoff/", ""), baris=len(df), kolom=len(df.columns), tujuan=tujuan))

# %% [markdown]
# ## A. Paket untuk Tim Full-stack
# ### A1. Data awal (seed) database

# %%
last = iv[iv.stock_date == iv.stock_date.max()]
save(br, f"{FS}/seed/branches.csv", "Full-stack", "master cabang")
save(pr.drop(columns=["cost_price", "marked_in_photo", "verify_note"]), f"{FS}/seed/products.csv", "Full-stack", "katalog produk (TANPA harga modal) untuk kasir & pemilik")
save(pr[["product_id", "cost_price"]], f"{FS}/seed/product_costs_OWNER_ONLY.csv", "Full-stack", "harga modal; HANYA boleh diakses peran pemilik")
save(cu, f"{FS}/seed/customers.csv", "Full-stack", "master pelanggan/bengkel rekanan (fiktif) + partner_fee_pct")
save(last[["branch_id", "product_id", "ending_stock", "stock_date"]].rename(columns={"ending_stock": "stock_qty", "stock_date": "as_of_date"}).merge(pr[["product_id", "minimum_stock"]], on="product_id"),
     f"{FS}/seed/inventory_current.csv", "Full-stack", "stok terkini per cabang-produk (stok awal aplikasi)")
save(tx, f"{FS}/seed/transactions_history.csv", "Full-stack", "riwayat transaksi sintetis 3 bulan (opsional, untuk demo/dashboard)")
save(dt, f"{FS}/seed/transaction_details_history.csv", "Full-stack", "detail riwayat transaksi sintetis (opsional)")

# %% [markdown]
# ### A2. Aturan harga & diskon (untuk mesin harga di backend)
# Aturan **batas** per produk ada di `products.discount_percentage`. Tabel di bawah menjelaskan perilaku bawaan per jenis pelanggan.
# Angka perilaku diambil dari rata-rata data sintetis dan **perlu dikonfirmasi pemilik** sebelum dipakai di produksi.

# %%
da = pd.read_csv(f"{ANALYSIS}/discount_analysis.csv")
beh = da.groupby("customer_type").agg(pemakaian_batas_pct=("pemakaian_batas_pct", "mean"), baris_berdiskon_pct=("share_baris_berdiskon_pct", "mean")).round(1).reset_index()
rules = pd.DataFrame([
    ("umum", "negosiasi", 0, 100, "Tanpa diskon bawaan; kasir boleh memberi diskon sampai batas standar produk bila pelanggan menawar."),
    ("rekanan", "otomatis", 100, 100, "Diskon penuh sesuai batas standar produk. Fee bengkel rekanan kecil (customers.partner_fee_pct = 5%) dicatat sebagai biaya toko (other_cost), BUKAN diskon."),
    ("keluarga", "otomatis", 100, 100, "Mengikuti harga rekanan. Kasus 'gratis' / harga khusus hanya boleh diset oleh pemilik dengan catatan alasan."),
    ("pemerintah", "negosiasi", 75, 100, "Pembelian via INAPROC dengan harga hasil negosiasi; cukup dicatat sebagai tipe pelanggan (tanpa integrasi INAPROC)."),
], columns=["customer_type", "mode_diskon", "default_pct_dari_batas", "maks_pct_dari_batas", "catatan"]).merge(beh, on="customer_type", how="left")
rules["status_aturan"] = "ASUMSI SIMULASI - perlu konfirmasi pemilik"
cat_std = pr.groupby("category").agg(batas_standar_min_pct=("discount_percentage", "min"), batas_standar_maks_pct=("discount_percentage", "max"), sumber_aturan=("discount_rule_source", "first")).reset_index()
cat_std["catatan"] = np.where(cat_std.category.str.startswith("Spare part"), "20% atau 25% ditentukan per produk (kolom products.discount_percentage); aturan pemilik belum merinci kapan 20/25", "")
display(rules); display(cat_std)
save(rules, f"{FS}/seed/discount_rules_by_customer_type.csv", "Full-stack", "perilaku diskon per jenis pelanggan (untuk mesin harga)")
save(cat_std, f"{FS}/seed/discount_limit_by_category.csv", "Full-stack", "batas diskon standar per kategori")

# %% [markdown]
# ### A3. Hasil analisis untuk dashboard (CSV + satu file JSON)
# Backend dapat membaca `dashboard_summary.json` dan menyajikannya di endpoint, lalu Frontend menampilkannya sebagai dasbor.

# %%
files = ["kpi_summary", "sales_by_category", "sales_by_branch_month", "sales_by_day", "sales_category_by_branch", "top_products", "product_movement",
         "discount_analysis", "margin_by_category", "margin_by_customer_type", "weekday_pattern", "stock_status", "restock_recommendation",
         "demand_forecast", "weekly_demand_history", "model_comparison"]
for f in files:
    df = pd.read_csv(f"{ANALYSIS}/{f}.csv")
    save(df, f"{FS}/dashboard_data/{f}.csv", "Full-stack", "data dasbor/analisis")
rec = pd.read_csv(f"{ANALYSIS}/restock_recommendation.csv")
fc = pd.read_csv(f"{ANALYSIS}/demand_forecast.csv")
def recs(df): return json.loads(df.to_json(orient="records", force_ascii=False))
summary = {
    "meta": {"data_source": "synthetic", "catatan": "DATA SINTETIS untuk demonstrasi; bukan data operasional nyata Sumber Urip.",
             "periode": [str(tx.transaction_date.min()), str(tx.transaction_date.max())], "tanggal_data_stok": str(iv.stock_date.max().date()) if hasattr(iv.stock_date.max(), "date") else str(iv.stock_date.max())},
    "kpi": {r.metrik: (int(r.nilai) if str(r.nilai).lstrip("-").isdigit() else (float(r.nilai) if re.fullmatch(r"-?\d+\.\d+", str(r.nilai)) else r.nilai)) for r in pd.read_csv(f"{ANALYSIS}/kpi_summary.csv").itertuples()},
    "penjualan_per_kategori": recs(pd.read_csv(f"{ANALYSIS}/sales_by_category.csv")),
    "penjualan_per_cabang_bulan": recs(pd.read_csv(f"{ANALYSIS}/sales_by_branch_month.csv")),
    "produk_teratas": recs(pd.read_csv(f"{ANALYSIS}/top_products.csv")),
    "diskon_per_jenis_pelanggan_kategori": recs(pd.read_csv(f"{ANALYSIS}/discount_analysis.csv")),
    "margin_per_kategori": recs(pd.read_csv(f"{ANALYSIS}/margin_by_category.csv")),
    "ringkasan_restock": recs(rec.groupby(["branch_name", "status_restock"]).size().rename("jumlah_produk").reset_index()),
    "peringatan_stok_teratas": recs(rec[rec.status_restock.isin(["Habis", "Restock segera"])].head(30)),
    "prediksi_permintaan_mingguan": recs(fc),
    "perbandingan_model_prediksi": recs(pd.read_csv(f"{ANALYSIS}/model_comparison.csv")),
}
with open(f"{FS}/dashboard_data/dashboard_summary.json", "w", encoding="utf-8") as f: json.dump(summary, f, ensure_ascii=False, indent=1)
manifest.append(dict(penerima="Full-stack", file="for_fullstack/dashboard_data/dashboard_summary.json", baris=len(summary), kolom=0, tujuan="satu file JSON berisi seluruh hasil analisis untuk endpoint dasbor"))
print("JSON ditulis; bagian:", list(summary))

# %% [markdown]
# ## B. Paket untuk Tim Gen AI
# ### B1. Kamus alias produk, cabang, dan jenis pelanggan
# Dipakai untuk menormalkan cara kasir/pelanggan menyebut barang ("ban irc 80/90-17 nr 80", "oli yamalube matic") menjadi `product_id`.

# %%
def aliases(r):
    name = r.product_name; low = name.lower(); size = str(r.size_spec) if pd.notna(r.size_spec) else ""
    out = {("nama lengkap", low)}
    if r.brand == "IRC" and r.subcategory.startswith("ban luar"):
        typ = name.split(" ")[-1]; pat = name.replace("IRC", "", 1).replace(size, "").replace(typ, "").strip().lower()
        out |= {("irc pola ukuran", f"irc {pat} {size}"), ("ban irc ukuran", f"ban irc {size} {pat}"), ("pola ukuran", f"{pat} {size}"), ("ukuran pola", f"{size} {pat}")}
        if typ.lower() == "tubeless": out.add(("ban tubeless", f"ban {size} {pat} tubeless"))
    elif r.subcategory == "ban dalam":
        out |= {("ban dalam", f"ban dalam {low.split('ban dalam')[-1].strip()}"), ("ban dalam irc", "ban dalam irc " + low.split("ban dalam")[-1].strip())}
    elif r.category in ("Oli",):
        out |= {("pakai kata oli", "oli " + low), ("tanpa merek", low.replace(str(r.brand).lower(), "").strip())}
    elif r.category == "Ban mobil":
        out |= {("ban mobil", "ban mobil " + low), ("ukuran", size.lower())}
    else:
        out |= {("tanpa merek", re.sub(str(r.brand).lower(), "", low).strip()), ("pakai kata kunci", low.replace(" motor", "").replace(" mobil", "").strip())}
    return sorted((t, a) for t, a in out if a and len(a) >= 3)      # diurutkan agar hasil selalu sama (reproducible)
rows = [dict(product_id=r.product_id, canonical_name=r.product_name, category=r.category, brand=r.brand, alias=a, alias_type=t) for r in pr.itertuples() for t, a in aliases(r)]
alias_df = pd.DataFrame(rows).drop_duplicates(["product_id", "alias"])
save(alias_df, f"{AI}/product_alias_dictionary.csv", "Gen AI", "alias nama produk -> product_id (normalisasi entitas produk)")
branch_alias = pd.DataFrame([("BR01", a) for a in ["padang kerta", "pdg kerta", "pk", "sumber urip 1", "cabang 1", "cabang padang kerta"]] +
                            [("BR02", a) for a in ["jalan nenas", "jl nenas", "jln nenas", "nenas", "sumber urip 2", "cabang 2", "cabang jalan nenas"]] +
                            [("BR03", a) for a in ["paye", "cabang paye", "sumber urip 3", "cabang 3"]], columns=["branch_id", "alias"])
ctype_alias = pd.DataFrame([("umum", a) for a in ["umum", "pelanggan umum", "biasa", "eceran", "retail"]] + [("rekanan", a) for a in ["rekanan", "bengkel rekanan", "bengkel langganan", "mitra bengkel", "bengkel kecil"]] +
                           [("keluarga", a) for a in ["keluarga", "saudara"]] + [("pemerintah", a) for a in ["pemerintah", "instansi", "dinas", "inaproc", "kantor pemerintah"]], columns=["customer_type", "alias"])
save(branch_alias, f"{AI}/branch_aliases.csv", "Gen AI", "alias nama cabang -> branch_id (sebagian alias adalah dugaan, perlu dikonfirmasi)")
save(ctype_alias, f"{AI}/customer_type_aliases.csv", "Gen AI", "alias jenis pelanggan")
display(alias_df.sample(8, random_state=3))

# %% [markdown]
# ### B2. Dataset intent berlabel (train / val / test)
# Intent: `tanya_harga`, `tanya_diskon`, `cek_stok`, `lainnya` (sapaan, jam buka/alamat, di luar konteks, dll.).
# - Kalimat dibuat dari **template × nama produk/cabang** di katalog (sintetis), dengan variasi gaya bahasa kasir (singkatan, huruf kecil, typo ringan).
# - **Anti-kebocoran:** 2 template per intent *hanya* muncul di data **test** (template tak pernah dilihat saat latihan); sisanya dibagi acak 75/12,5/12,5.
# - Kolom entitas (`entity_product_id`, `entity_branch_id`, `entity_customer_type`) disediakan untuk ekstraksi entitas / slot filling.

# %%
rng = np.random.default_rng(2026)
alias_pool = alias_df.groupby("product_id").alias.apply(list).to_dict()
CT_PHRASE = {"rekanan": ["bengkel rekanan", "bengkel langganan"], "pemerintah": ["instansi pemerintah", "dinas"], "keluarga": ["keluarga"], "umum": ["pelanggan umum"]}
BR_PHRASE = {b: g.alias.tolist() for b, g in branch_alias.groupby("branch_id")}
T = {
 "tanya_harga": ["harga {p} berapa?", "{p} harganya berapa ya", "brp harga {p}", "berapa {p}?", "info harga {p} dong", "{p} berapaan kak?", "price list {p}",
                 "kak harga {p} brp", "minta harga {p}", "harga {p} sekarang", "{p} harga satuannya berapa", "tolong cek harga {p}", "harga {p} di {b} berapa"],
 "tanya_diskon": ["{p} bisa diskon berapa?", "ada diskon untuk {p}?", "diskon {p} berapa persen", "bisa nego {p}?", "kalau {t}, diskon {p} berapa?", "potongan harga {p} ada ga",
                  "harga khusus {t} untuk {p} berapa", "{p} kalau ambil banyak dapat diskon?", "boleh kurang ga {p}", "{p} bisa dikasih harga {t}?"],
 "cek_stok": ["stok {p} ada?", "{p} ready ga?", "cek stok {p} di {b}", "{p} masih ada di {b}?", "sisa {p} di {b} berapa", "{p} kosong ga di {b}", "available {p}?",
              "di {b} ada {p} ga", "{p} ada ngga kak", "stok {p} di {b} berapa"],
}
LAINNYA = [("sapaan", s) for s in ["halo", "hai kak", "selamat pagi", "selamat siang kak", "selamat sore", "permisi", "assalamualaikum", "om swastiastu", "halo admin", "test"]] + \
          [("terima kasih", s) for s in ["terima kasih", "makasih kak", "ok siap makasih", "oke noted", "sip terima kasih banyak"]] + \
          [("jam buka {b}", s) for s in ["jam buka {b} jam berapa?", "{b} buka sampai jam berapa", "hari minggu {b} buka ga?", "{b} tutup jam berapa"]] + \
          [("alamat {b}", s) for s in ["alamat {b} di mana?", "lokasi cabang {b} dimana ya", "share lokasi {b} dong", "{b} dekat apa ya"]] + \
          [("servis", s) for s in ["bisa servis motor di sini?", "motor saya mogok kenapa ya", "ganti oli sekalian pasang berapa lama", "ada montir yang ready sekarang?", "mobil saya bunyi kasar di roda"]] + \
          [("pesan antar / pembayaran", s) for s in ["bisa pesan antar ke rumah?", "bisa bayar pakai transfer?", "terima qris ga", "bisa kredit ga", "ongkir ke kerobokan berapa"]] + \
          [("di luar konteks", s) for s in ["siapa presiden indonesia", "cuaca hari ini bagaimana", "resep nasi goreng enak", "tolong buatkan puisi", "apa itu bitcoin", "cara belajar python",
                                           "rekomendasi film bagus", "berapa kurs dolar hari ini", "terjemahkan ke bahasa inggris", "skor bola semalam", "siapa penemu lampu",
                                           "bagaimana cara investasi saham", "ceritakan lelucon", "apa ibukota australia", "bantu kerjakan tugas matematika saya"]]
LAINNYA += [("sapaan", s) for s in ["selamat malam", "pagi kak", "hai admin sumber urip", "halo bengkel", "kak mau tanya", "boleh tanya ga", "halo min", "siang kak"]] + \
          [("terima kasih", s) for s in ["thanks ya", "terima kasih infonya", "oke makasih banyak", "baik kak terima kasih"]] + \
          [("jam buka {b}", s) for s in ["{b} buka jam berapa", "jam operasional {b}", "hari libur {b} buka?", "{b} buka tiap hari ga"]] + \
          [("alamat {b}", s) for s in ["{b} di sebelah mana", "gmaps {b} dong", "arah ke {b} lewat mana", "nomor wa {b} berapa"]] + \
          [("servis", s) for s in ["bisa pasang ban sekalian?", "berapa lama ganti kampas rem", "tambal ban bisa ga", "rem motor saya blong gimana", "aki mobil saya tekor kenapa", "bisa tune up motor?"]] + \
          [("pesan antar / pembayaran", s) for s in ["bisa cod ga", "kirim luar kota bisa?", "bisa transfer bca?", "ada garansi ga", "bisa tukar kalau salah ukuran", "bisa bikin nota atas nama bengkel?"]] + \
          [("di luar konteks", s) for s in ["siapa juara piala dunia 2022", "cara membuat kue bolu", "apa kabar", "kamu AI ya", "ceritakan tentang sejarah bali", "harga emas hari ini", "tolong rangkum berita hari ini",
                                           "bagaimana cara diet sehat", "jelaskan teori relativitas", "kapan hari raya galungan", "nomor telepon polisi berapa", "buatkan kode python untuk kalkulator"]]
def swap_typo(s):
    i = int(rng.integers(2, max(3, len(s) - 2))); return s[:i] + s[i + 1] + s[i] + s[i + 2:] if len(s) > 5 else s
def noise(s):
    r = rng.random()
    if r < 0.15: s = swap_typo(s)
    elif r < 0.30: s = s.replace("?", "")
    elif r < 0.40: s = s.upper() if rng.random() < .3 else s.capitalize()
    if rng.random() < 0.08: s = s.replace("kak", "ka").replace("berapa", "brp")
    return s.strip()

prods = pr.product_id.tolist()
rows = []
TARGET = {"tanya_harga": 650, "tanya_diskon": 650, "cek_stok": 650}
for intent, temps in T.items():
    for ti, tpl in enumerate(temps):
        for _ in range(TARGET[intent] // len(temps) + 8):
            pid = prods[int(rng.integers(len(prods)))]
            b = list(BR_PHRASE)[int(rng.integers(3))]; ct = list(CT_PHRASE)[int(rng.integers(4))]
            txt = tpl.format(p=rng.choice(alias_pool[pid]), b=rng.choice(BR_PHRASE[b]), t=rng.choice(CT_PHRASE[ct]))
            rows.append(dict(text=noise(txt), intent=intent, template_id=f"{intent}_T{ti:02d}", entity_product_id=pid,
                             entity_branch_id=b if "{b}" in tpl else None, entity_customer_type=ct if "{t}" in tpl else None, domain="in_domain"))
for li, (grp, tpl) in enumerate(LAINNYA):
    reps = 10 if "{b}" in tpl else 6
    for _ in range(reps):
        b = list(BR_PHRASE)[int(rng.integers(3))]
        rows.append(dict(text=noise(tpl.format(b=rng.choice(BR_PHRASE[b]))), intent="lainnya", template_id=f"lainnya_T{li:02d}", entity_product_id=None,
                         entity_branch_id=b if "{b}" in tpl else None, entity_customer_type=None, domain="out_of_domain" if grp == "di luar konteks" else "in_domain"))
ds = pd.DataFrame(rows).drop_duplicates("text").reset_index(drop=True)
# pembagian: 2 template per intent khusus test; sisanya acak 75/12.5/12.5
unseen = {i: sorted(ds[ds.intent == i].template_id.unique())[-2:] for i in ds.intent.unique()}
ds["split"] = np.where(ds.apply(lambda r: r.template_id in unseen[r.intent], axis=1), "test", None)
rest = ds.split.isna()
ds.loc[rest, "split"] = rng.choice(["train", "val", "test"], size=rest.sum(), p=[.75, .125, .125])
ds["source"] = "synthetic_template"
ds = ds.sample(frac=1, random_state=7).reset_index(drop=True)
ds.insert(0, "id", [f"INT-{i+1:05d}" for i in range(len(ds))])
assert ds.text.is_unique
print(pd.crosstab(ds.intent, ds.split))
print("template yang hanya ada di test (tidak terlihat saat latihan):", unseen)
save(ds, f"{AI}/intent_dataset.csv", "Gen AI", "dataset klasifikasi intent berlabel + entitas, dengan kolom split")
labels = pd.DataFrame([("tanya_harga", "Menanyakan harga barang", "harga oli yamalube matic berapa?"), ("tanya_diskon", "Menanyakan diskon / nego / harga khusus", "bisa diskon berapa kalau bengkel rekanan?"),
                       ("cek_stok", "Menanyakan ketersediaan / sisa stok di cabang", "stok ban irc 80/90-17 ada di paye?"), ("lainnya", "Sapaan, jam buka, alamat, servis, pemesanan antar, dan pertanyaan di luar konteks usaha", "siapa presiden indonesia")],
                      columns=["intent", "deskripsi", "contoh"])
labels["jumlah_contoh"] = labels.intent.map(ds.intent.value_counts())
save(labels, f"{AI}/intent_labels.csv", "Gen AI", "definisi label intent")
display(ds.groupby("intent").head(3)[["text", "intent", "split", "entity_branch_id", "domain"]])

# %% [markdown]
# ### B3. Basis pengetahuan produk (untuk RAG) dan aturan diskon
# Satu dokumen per produk. **Stok tidak dimasukkan** ke teks (berubah tiap saat) — ambil dari API/`inventory_current.csv`. Harga modal tidak disertakan.

# %%
def kb_text(r):
    src = "pricelist HET IRC Tire 15 Juni 2026" if "irc" in str(r.selling_price_source).lower() else "harga simulasi (data sintetis)"
    sz = f" Ukuran/spesifikasi: {r.size_spec}." if pd.notna(r.size_spec) and str(r.size_spec).strip() else ""
    return (f"{r.product_name} adalah produk kategori {r.category} bermerek {r.brand}.{sz} Harga jual daftar Rp {r.selling_price:,.0f}".replace(",", ".") +
            f" ({src}). Diskon standar maksimum yang boleh diberikan: {r.discount_percentage}% dari harga jual. Data ini sintetis untuk demonstrasi.")
kb = pr.assign(doc_id=lambda d: "KB-" + d.product_id, text=lambda d: [kb_text(r) for r in d.itertuples()])[["doc_id", "product_id", "text", "category", "brand", "selling_price", "discount_percentage"]]
kb["data_source"] = "synthetic"
save(kb, f"{AI}/knowledge_base_products.csv", "Gen AI", "dokumen per produk untuk RAG (tanpa stok & harga modal)")
save(rules, f"{AI}/discount_rules_by_customer_type.csv", "Gen AI", "aturan diskon (untuk menjawab pertanyaan diskon)")
save(cat_std, f"{AI}/discount_limit_by_category.csv", "Gen AI", "batas diskon per kategori")
save(last[["branch_id", "product_id", "ending_stock", "stock_date"]].rename(columns={"ending_stock": "stock_qty", "stock_date": "as_of_date"}), f"{AI}/inventory_current_for_answers.csv", "Gen AI", "stok terkini (jawaban cek_stok sebaiknya via API backend, ini hanya contoh)")
print(kb.text.iloc[0])

# %% [markdown]
# ## C. Kamus data & manifest
# Kamus data dibuat otomatis dari seluruh file yang diserahkan; deskripsi kolom diisi untuk kolom yang umum.

# %%
DESC = {"product_id": "ID produk (PK)", "product_name": "Nama produk baku", "category": "Kategori produk (8 nilai baku)", "subcategory": "Subkategori", "brand": "Merek",
        "size_spec": "Ukuran/spesifikasi", "selling_price": "Harga jual daftar (Rp)", "discount_percentage": "Batas diskon standar produk (%)", "minimum_stock": "Batas stok minimum (unit)",
        "cost_price": "Harga modal (Rp) - RAHASIA, hanya pemilik", "branch_id": "ID cabang (BR01 Padang Kerta, BR02 Jalan Nenas, BR03 Paye)", "branch_name": "Nama cabang",
        "customer_id": "ID pelanggan", "customer_type": "umum / rekanan / keluarga / pemerintah", "partner_fee_pct": "Fee bengkel rekanan kecil (0.05 = 5%)", "stock_qty": "Jumlah stok", "as_of_date": "Tanggal data stok",
        "transaction_id": "ID transaksi", "detail_id": "ID baris detail", "quantity": "Jumlah", "unit_price": "Harga satuan (Rp)", "subtotal": "Omzet bersih baris (Rp)", "net_amount": "Omzet bersih transaksi (Rp)",
        "gross_amount": "Omzet kotor (Rp)", "discount_amount": "Total diskon (Rp)", "gross_profit": "Laba kotor setelah fee (Rp)", "other_cost": "Fee bengkel rekanan (Rp)", "data_source": "synthetic = data simulasi",
        "text": "Kalimat pertanyaan", "intent": "Label intent", "split": "train / val / test", "template_id": "ID template pembuat kalimat (untuk split anti-kebocoran)", "entity_product_id": "Produk yang disebut (jika ada)",
        "entity_branch_id": "Cabang yang disebut (jika ada)", "entity_customer_type": "Jenis pelanggan yang disebut (jika ada)", "domain": "in_domain / out_of_domain", "alias": "Cara lain menyebut produk/cabang",
        "alias_type": "Jenis alias", "doc_id": "ID dokumen RAG", "status_restock": "Habis / Restock segera / Waspada / Aman", "saran_jumlah_pesan": "Saran jumlah pesan ke pemasok (unit)", "titik_pesan": "Reorder point (unit)",
        "forecast_units": "Prediksi unit terjual per minggu", "week_start": "Senin awal minggu", "omzet_bersih": "Omzet bersih (Rp)", "jumlah_transaksi": "Jumlah transaksi", "stok_sekarang": "Stok terkini"}
dd = []
for m in manifest:
    f = f"{HANDOFF}/{m['file']}"
    if f.endswith(".csv"):
        df = pd.read_csv(f)
        for c in df.columns:
            ex = df[c].dropna().astype(str).iloc[0] if df[c].notna().any() else ""
            dd.append(dict(penerima=m["penerima"], file=m["file"], kolom=c, tipe=str(df[c].dtype), contoh=ex[:60], deskripsi=DESC.get(c, "")))
pd.DataFrame(dd).to_csv(f"{HANDOFF}/DATA_DICTIONARY_ALL.csv", index=False)
mf = pd.DataFrame(manifest); mf.to_csv(f"{HANDOFF}/HANDOFF_MANIFEST.csv", index=False)
print(f"{len(mf)} file diserahkan: Full-stack={int((mf.penerima == 'Full-stack').sum())}, Gen AI={int((mf.penerima == 'Gen AI').sum())}")
display(mf)

# %% [markdown]
# ## D. Kontrak data (dokumen singkat untuk tiap tim)

# %%
fs_md = f"""# Kontrak Data: Data Science → Tim Full-stack
**Status:** data SINTETIS (demonstrasi). Semua file memuat label `data_source = synthetic`. Jangan tampilkan sebagai data nyata Sumber Urip.

## Isi paket (`for_fullstack/`)
| Folder | Isi | Cara pakai |
|---|---|---|
| `seed/` | branches, products (tanpa harga modal), product_costs_OWNER_ONLY, customers, inventory_current, transactions_history, transaction_details_history, discount_rules_by_customer_type, discount_limit_by_category | Impor ke database sebagai data awal. Urutan impor: branches → products → customers → inventory_current → transactions → transaction_details |
| `dashboard_data/` | CSV hasil analisis + `dashboard_summary.json` | Backend membaca JSON/CSV lalu menyajikan lewat endpoint dasbor; Frontend menampilkannya |

## Aturan wajib
1. `product_costs_OWNER_ONLY.csv` (harga modal) **hanya boleh diakses peran pemilik**; jangan kirim ke peran kasir / jangan masukkan ke endpoint publik.
2. Kolom `data_source` jangan dibuang. Tampilkan penanda "Data demonstrasi (sintetis)" di dasbor selama data masih sintetis.
3. Jangan menaruh file ini (dan `.env`/API key) di repositori publik.
4. Harga akhir = `unit_price × (1 − diskon%)`; diskon% tidak boleh melebihi `products.discount_percentage`. Fee rekanan (`customers.partner_fee_pct`) adalah **biaya toko**, bukan diskon.

## Usulan endpoint (boleh disesuaikan)
| Endpoint | Sumber data | Peran |
|---|---|---|
| `GET /api/v1/dashboard/summary` | `dashboard_data/dashboard_summary.json` | pemilik |
| `GET /api/v1/restock-recommendations?branch_id=` | `dashboard_data/restock_recommendation.csv` | pemilik |
| `GET /api/v1/demand-forecast` | `dashboard_data/demand_forecast.csv` | pemilik |
| `GET /api/v1/products` | `seed/products.csv` | kasir, pemilik |
| `GET /api/v1/discount-rules` | `seed/discount_rules_by_customer_type.csv`, `seed/discount_limit_by_category.csv` | kasir, pemilik |

## Format
CSV UTF-8, pemisah koma, header di baris pertama; tanggal `YYYY-MM-DD`; uang dalam Rupiah (bilangan bulat, tanpa pemisah ribuan). Kamus kolom: `../DATA_DICTIONARY_ALL.csv`.

## Hal yang masih asumsi
Lead time pemasok 3 hari, perilaku diskon per jenis pelanggan, dan seluruh harga modal adalah asumsi simulasi; perlu konfirmasi pemilik.
"""
ai_md = f"""# Kontrak Data: Data Science → Tim Gen AI
**Status:** data SINTETIS (kalimat dibuat dari template × katalog). Tidak ada percakapan nyata pelanggan.

## Isi paket (`for_genai/`)
| File | Kegunaan |
|---|---|
| `intent_dataset.csv` | {len(ds)} kalimat berlabel 4 intent (`tanya_harga`, `tanya_diskon`, `cek_stok`, `lainnya`) + entitas + kolom `split` (train/val/test) |
| `intent_labels.csv` | definisi tiap intent |
| `product_alias_dictionary.csv` | {len(alias_df)} alias nama produk → `product_id` (normalisasi entitas) |
| `branch_aliases.csv`, `customer_type_aliases.csv` | alias cabang dan jenis pelanggan (sebagian alias adalah dugaan, perlu konfirmasi) |
| `knowledge_base_products.csv` | {len(kb)} dokumen produk untuk RAG (tanpa stok dan harga modal) |
| `discount_rules_by_customer_type.csv`, `discount_limit_by_category.csv` | aturan diskon untuk menjawab pertanyaan diskon |
| `inventory_current_for_answers.csv` | stok terkini (contoh; jawaban stok sebaiknya via API backend) |

## Catatan pemakaian
0. Jumlah contoh per intent tidak sama persis (`intent_labels.csv`); kelas `lainnya` lebih sedikit. Periksa keseimbangan kelas dan tangani bila perlu (mis. bobot kelas / augmentasi) lalu catat di README.
1. **Gunakan kolom `split` apa adanya.** Test berisi template yang tidak pernah muncul di train/val (uji generalisasi). Jangan mengacak ulang sebelum evaluasi.
2. Model intent harus **dilatih sendiri** (aturan Main Quest: bukan hanya memanggil API LLM / model siap pakai). Dataset ini hanya bahan latihan awal; sangat disarankan memperkaya dengan kalimat buatan tim agar tidak terlalu "bertemplate".
3. Intent `lainnya` mencakup pertanyaan di luar konteks (`domain = out_of_domain`) → dasar uji penolakan sopan chatbot.
4. Kolom `entity_*` boleh dipakai untuk ekstraksi entitas; jawaban harga/diskon/stok **diambil dari database lewat backend**, bukan dari teks RAG.
5. Metrik evaluasi yang disarankan: F1-score (macro) pada `split = test`, dilaporkan per intent.
6. Harga modal tidak disertakan dan **tidak boleh** dimasukkan ke prompt/LLM eksternal. Jangan kirim data pelanggan nyata ke API pihak ketiga.

## Contoh API (disepakati dengan Full-stack)
`POST /predict-intent` — request `{{"text": "stok ban irc 80/90-17 ada di paye?"}}` — response `{{"intent": "cek_stok", "confidence": 0.93}}`
"""
open(f"{FS}/KONTRAK_DATA_DS_KE_FULLSTACK.md", "w", encoding="utf-8").write(fs_md)
open(f"{AI}/KONTRAK_DATA_DS_KE_GENAI.md", "w", encoding="utf-8").write(ai_md)
print("kontrak data ditulis")
