# Pipeline Data Science — Kios Sumber Urip (Asah 2026 Capstone)

Paket ini berisi **seluruh langkah Data Science dari data mentah sampai siap diserahkan ke tim Full-stack dan Gen AI**:
`gathering → assessing → cleaning → analisis (EDA) → prediksi & restock → dashboard Streamlit → serah terima data`.

> ⚠️ **Semua data di paket ini adalah SINTETIS (simulasi)** — bukan data operasional nyata Sumber Urip. Tujuannya mengembangkan dan menguji pipeline.
> Saat data primer dari buku Sumber Urip sudah didigitalkan, taruh di `data/raw/` dengan skema yang sama lalu jalankan ulang. Kesimpulan bisnis hanya boleh diambil dari data primer.

## Deploy: GitHub + Streamlit Community Cloud
1. Buat repositori di GitHub (disarankan **private**), lalu upload seluruh isi folder ini (`app.py`, `pages/`, `assets/`, `data/`, `.streamlit/`, `requirements.txt` harus ikut).
2. Buka https://share.streamlit.io → **New app** → pilih repositori dan branch, **Main file path = `app.py`** → Deploy.
3. Selesai: halaman utama = tampilan dashboard, menu kiri **Eksplorasi Interaktif** = versi dengan filter dan unggah CSV.

> Data di repositori ini sintetis. Folder `_kunci_jawaban/` sengaja tidak disertakan. File `handoff/.../product_costs_OWNER_ONLY.csv` memuat harga modal, jadi tetap gunakan repositori private untuk data nyata.

## Struktur
```
README.md · requirements.txt · run_pipeline.py
data/raw/            data mentah (kotor)               ← INPUT
data/clean/          data bersih hasil notebook 02     ← OUTPUT
data/analysis/       tabel hasil analisis, log, grafik ← OUTPUT (dibaca dashboard)
data/reference/      pricelist ban IRC (transkripsi foto)
notebooks/           01 … 05 (.ipynb, jalankan berurutan)
nb_src/              sumber notebook (format percent/jupytext)
app.py · pages/       dashboard Streamlit (halaman utama + eksplorasi interaktif)
assets/              tampilan dashboard utama (HTML)
handoff/for_fullstack/   PAKET untuk Tim Full-stack     ← DIKIRIM
handoff/for_genai/       PAKET untuk Tim Gen AI         ← DIKIRIM
handoff/DATA_DICTIONARY_ALL.csv · HANDOFF_MANIFEST.csv
src/validate_dataset.py  27 pemeriksaan validasi data bersih
verification/ · _kunci_jawaban/   verifikasi latihan (JANGAN dibuka sebelum selesai cleaning)
docs/                dokumen penjelasan (docx)
```

## Cara menjalankan
**Opsi A – Jupyter / Google Colab (disarankan untuk belajar):** buka `notebooks/` dan jalankan berurutan:

| No | Notebook | Isi | Output utama |
|---|---|---|---|
| 01 | `01_gathering_assessing` | memuat data mentah & menilai kualitas | `data/analysis/assessing_report.csv` |
| 02 | `02_cleaning` | membersihkan, mencatat alasan tiap penanganan, validasi 27 cek | `data/clean/*.csv`, `cleaning_log.csv` |
| 03 | `03_eda_analisis` | menjawab 6 pertanyaan bisnis, KPI, grafik | tabel & `figures/*.png` di `data/analysis/` |
| 04 | `04_prediksi_permintaan_restock` | prediksi permintaan mingguan (bandingkan 4 model) + rekomendasi restock | `demand_forecast.csv`, `restock_recommendation.csv` |
| 05 | `05_serah_terima_fs_genai` | membuat paket data untuk Full-stack & Gen AI + kontrak data | folder `handoff/` |

**Opsi B – tanpa Jupyter (cukup Python):**
```bash
pip install -r requirements-notebook.txt
python run_pipeline.py          # menjalankan notebook 01–05 berurutan
python verification/verify_against_ground_truth.py   # (latihan) cocokkan hasil dengan kunci jawaban
python tools/smoke_test_dashboard.py                 # uji logika dashboard tanpa membuka browser
```
**Dashboard:**
```bash
streamlit run app.py
```
Detail deploy & penyematan di aplikasi web: `dashboard/README_DASHBOARD.md`.

## Mengganti ke data primer (buku Sumber Urip)
1. Ketik/digitalkan buku ke 6 tabel dengan nama kolom seperti `data/raw/*_raw.csv`. Minimal: `transactions`, `transaction_details`, `products`, `branches`, `customers`, `inventory`.
2. Hapus kolom/label sintetis (`data_source = synthetic`) dan **jangan** menyisipkan nama pelanggan asli tanpa izin (anonimkan).
3. Sesuaikan aturan pada notebook 02 bila format buku berbeda (mis. pemetaan nama cabang, format tanggal), lalu jalankan notebook 01 → 05.
4. Jalankan `python src/validate_dataset.py data/clean` — semua pemeriksaan harus lolos.
5. Perbarui asumsi di notebook 04 (lead time pemasok, dsb.) setelah dikonfirmasi pemilik.

## Yang dikirim ke tim lain
Lihat `handoff/for_fullstack/KONTRAK_DATA_DS_KE_FULLSTACK.md` dan `handoff/for_genai/KONTRAK_DATA_DS_KE_GENAI.md`.
Kirim **satu folder per tim** (zip-kan `for_fullstack/` untuk Full-stack, `for_genai/` untuk Gen AI) beserta `DATA_DICTIONARY_ALL.csv`.
**Harga modal (`product_costs_OWNER_ONLY.csv`) hanya untuk peran pemilik** — jangan dipublikasikan.
