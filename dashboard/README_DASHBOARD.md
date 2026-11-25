# Dashboard Streamlit — Kios Sumber Urip

## Menjalankan lokal
```bash
pip install -r requirements-notebook.txt
python run_pipeline.py                # pastikan data/clean dan data/analysis sudah terisi
streamlit run app.py
```

## Fitur
- **Sumber data:** data bawaan (hasil pipeline) atau **unggah CSV** (transactions.csv + transaction_details.csv, skema sama dengan `data/clean`; divalidasi dan pesan kesalahan ditampilkan bila format salah).
- **Filter:** rentang tanggal, cabang, kategori, jenis pelanggan.
- **Tab:** Ringkasan (KPI, omzet mingguan, pola hari) · Produk & Kategori (omzet, produk teratas, fast/slow-moving) · Diskon & Margin (diskon efektif, margin, pelanggaran batas diskon) ·
  Stok & Restock (daftar rekomendasi + unduh CSV) · Prediksi (aktual vs prediksi + perbandingan model) · Tentang Data (assessing report, cleaning log, keterbatasan).
- Spanduk **"DATA SINTETIS"** muncul otomatis selama kolom `data_source = synthetic`.

## Deploy gratis (Streamlit Community Cloud)
1. Push folder proyek ke GitHub (**private**). Pastikan `data/clean/` dan `data/analysis/` ikut (tanpa `_kunci_jawaban/`).
2. Di share.streamlit.io pilih repositori, *main file path* = `app.py`, dan `requirements.txt` di root.
3. Salin URL aplikasi, mis. `https://nama-app.streamlit.app`.

## Menyematkan di aplikasi web tim Full-stack
Tambahkan `?embed=true` pada URL lalu sematkan dengan iframe, misalnya di halaman dasbor pemilik:
```html
<iframe src="https://nama-app.streamlit.app/?embed=true" style="width:100%;height:900px;border:0"></iframe>
```
Alternatif tanpa iframe: backend membaca `handoff/for_fullstack/dashboard_data/dashboard_summary.json` dan Frontend menggambar sendiri grafiknya.
Catatan: layanan gratis dapat "tidur" bila lama tidak dipakai (pembukaan pertama bisa lambat); siapkan pesan kesalahan/tunggu yang jelas di web.

## Keamanan
- Dashboard tidak menampilkan harga modal per produk. Margin yang tampil adalah **hasil agregat** (sintetis).
- Jangan menaruh kata sandi / API key di repositori. Dashboard ini tidak memerlukannya.
