// Membuat docs/Dokumentasi_Pipeline_DS_dan_Serah_Terima.docx dari docs/_docx_data.json
const fs = require("fs"); const path = require("path");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType, HeadingLevel,
        LevelFormat, BorderStyle, Header, Footer, PageNumber } = require("docx");
const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/_docx_data.json"), "utf8"));
const FONT = "Arial", W = 9638;                       // A4, margin 2 cm -> lebar isi 9638 DXA
const rp = n => "Rp " + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const fmt = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");

const t = (text, o = {}) => new TextRun({ text: String(text), font: FONT, size: o.size || 21, bold: o.bold, italics: o.italics, color: o.color });
const P = (text, o = {}) => new Paragraph({ children: Array.isArray(text) ? text : [t(text, o)], spacing: { after: o.after ?? 120, line: 300 }, alignment: o.align, keepNext: o.keepNext });
const H1 = s => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: s, font: FONT })], pageBreakBefore: false });
const H2 = s => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: s, font: FONT })] });
const bullet = (text, lvl = 0) => new Paragraph({ numbering: { reference: "bul", level: lvl }, children: Array.isArray(text) ? text : [t(text)], spacing: { after: 60, line: 288 } });
const code = s => new Paragraph({ children: [new TextRun({ text: s, font: "Consolas", size: 18 })], shading: { type: ShadingType.CLEAR, fill: "F2F2F2" }, spacing: { after: 40 }, indent: { left: 120 } });
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(text, w, o = {}) {
  return new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 50, bottom: 50, left: 80, right: 80 },
    shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text: String(text ?? ""), font: FONT, size: o.size || 17, bold: o.bold, color: o.color })], spacing: { after: 0 } })] });
}
function table(headers, rows, widths, o = {}) {
  const sum = widths.reduce((a, b) => a + b, 0); if (sum !== W) widths[widths.length - 1] += W - sum;
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: widths, rows: [
    new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], { fill: "1F4E78", bold: true, color: "FFFFFF", size: o.size })) }),
    ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], { fill: ri % 2 ? "F5F8FB" : undefined, size: o.size })) }))] });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 100 } });
const note = s => new Paragraph({ children: [t(s, { size: 20 })], shading: { type: ShadingType.CLEAR, fill: "FFF2CC" }, spacing: { after: 160, before: 60, line: 288 }, indent: { left: 100, right: 100 } });

const kpi = D.kpi, byCat = D.by_cat, mc = D.margin_cat;
const topCat = byCat[0], bestM = mc[0], worstM = mc[mc.length - 1];
const nVal = D.validation.length, nOk = D.validation.filter(v => v.lolos).length;
const fsRows = D.manifest.filter(m => m.penerima === "Full-stack"), aiRows = D.manifest.filter(m => m.penerima === "Gen AI");
const vt = D.verification_text || "";
const totalDiff = (vt.match(/TOTAL sel\/baris berbeda:\s*(\d+)/) || [0, "?"])[1];
const raw = D.raw_rows, cl = D.clean_rows;

const c = [];
c.push(new Paragraph({ children: [new TextRun({ text: "Pipeline Data Science & Serah Terima Data", font: FONT, size: 40, bold: true, color: "1F4E78" })], spacing: { after: 60 } }));
c.push(new Paragraph({ children: [new TextRun({ text: "Kios Sumber Urip · Asah 2026 Capstone", font: FONT, size: 26, color: "404040" })], spacing: { after: 60 } }));
c.push(P("Penjelasan apa yang dikerjakan Tim Data Science, dari data mentah sampai dashboard Streamlit, serta data apa yang diserahkan ke Tim Full-stack dan Tim Gen AI.", { color: "595959" }));
c.push(note("⚠ Seluruh data pada dokumen dan paket ini adalah SINTETIS (simulasi) untuk mengembangkan dan menguji pipeline. Bukan data operasional nyata Sumber Urip. Setelah data primer dari buku didigitalkan, jalankan pipeline yang sama pada data tersebut; kesimpulan bisnis hanya boleh diambil dari data primer."));

c.push(H1("1. Ringkasan"));
c.push(P(`Paket ini berisi alur kerja Data Science yang lengkap dan dapat diulang: gathering → assessing → cleaning → analisis (EDA) → prediksi & restock → dashboard Streamlit → serah terima data. Seluruh langkah dijalankan dari data mentah dan menghasilkan data bersih, tabel analisis, grafik, dashboard, serta paket data untuk tim lain.`));
c.push(table(["Hal", "Hasil"], [
  ["Data mentah (kotor)", `6 tabel: transaksi ${fmt(raw.transactions)} baris, detail ${fmt(raw.transaction_details)}, produk ${raw.products}, pelanggan ${raw.customers}, stok ${fmt(raw.inventory)}, cabang ${raw.branches}`],
  ["Masalah data ditemukan (assessing)", `${D.assessing.length} jenis masalah, tercatat di data/analysis/assessing_report.csv`],
  ["Penanganan (cleaning)", `${D.cleaning.length} langkah, tiap langkah punya alasan (cleaning_log.csv)`],
  ["Data bersih", `transaksi ${fmt(cl.transactions)}, detail ${fmt(cl.transaction_details)}, produk ${cl.products}, pelanggan ${cl.customers}, stok ${fmt(cl.inventory)}; lolos ${nOk}/${nVal} pemeriksaan validasi`],
  ["Analisis", "6 pertanyaan bisnis dijawab; 14 KPI; 5 grafik"],
  ["Prediksi & restock", "4 model prediksi permintaan dibandingkan; rekomendasi restock per cabang-produk (aturan reorder point)"],
  ["Dashboard", "Streamlit 6 tab dengan filter, unggah CSV, dan unduh daftar restock"],
  ["Serah terima", `${fsRows.length} file untuk Tim Full-stack dan ${aiRows.length} file untuk Tim Gen AI, lengkap dengan kontrak data dan kamus data`],
], [2800, 6838], { size: 18 }));
c.push(gap());
c.push(P([t("Status pengujian. ", { bold: true }), t(`Seluruh notebook dijalankan penuh lewat run_pipeline.py (sel kode dieksekusi apa adanya) dan hasilnya lolos ${nOk}/${nVal} pemeriksaan validasi. Hasil cleaning dicocokkan dengan kunci jawaban: seluruh kunci dan angka identik; hanya ${totalDiff} sel nama (nama produk/pelanggan yang rusak oleh typo) yang belum identik. Logika dashboard diuji dengan uji asap (tanpa browser); tampilan Streamlit sebenarnya perlu dicoba sekali di komputer Anda dengan streamlit run dashboard/app.py.`)]));

c.push(H1("2. Isi paket dan cara menjalankan"));
c.push(table(["Folder / file", "Isi"], [
  ["data/raw/", "Data mentah (input pipeline)"],
  ["data/clean/", "6 tabel bersih hasil notebook 02"],
  ["data/analysis/", "Laporan assessing, log cleaning, tabel analisis, hasil prediksi & restock, serta figures/*.png"],
  ["notebooks/", "01_gathering_assessing · 02_cleaning · 03_eda_analisis · 04_prediksi_permintaan_restock · 05_serah_terima_fs_genai"],
  ["dashboard/app.py", "Dashboard Streamlit (+ README_DASHBOARD.md)"],
  ["handoff/for_fullstack/ · handoff/for_genai/", "Paket data untuk tim lain + kontrak data; DATA_DICTIONARY_ALL.csv dan HANDOFF_MANIFEST.csv"],
  ["src/validate_dataset.py", "27 pemeriksaan validasi data bersih"],
  ["verification/ · _kunci_jawaban/", "Verifikasi latihan; jangan dibuka sebelum selesai cleaning sendiri"],
  ["run_pipeline.py · requirements.txt · README.md", "Menjalankan semua notebook tanpa Jupyter; dependensi; panduan"],
], [3600, 6038], { size: 18 }));
c.push(gap());
c.push(P("Cara menjalankan (komputer sendiri):", { bold: true, keepNext: true }));
["pip install -r requirements.txt", "python run_pipeline.py                 # menjalankan notebook 01 s.d. 05 berurutan", "streamlit run dashboard/app.py         # membuka dashboard"].forEach(s => c.push(code(s)));
c.push(P("Di Jupyter atau Google Colab: buka folder notebooks/ lalu jalankan notebook 01 sampai 05 secara berurutan.", { after: 80 }));

c.push(H1("3. Langkah-langkah yang dikerjakan"));
c.push(H2("Langkah 1 · Gathering dan Assessing (notebook 01)"));
c.push(P("Data mentah dibaca sebagai teks (dtype=str) supaya pandas tidak mengubah nilai diam-diam. Contoh jebakan: harga \"192.000\" (format Indonesia) akan terbaca 192,0 jika dibiarkan otomatis. Setelah itu data dinilai dari sisi tipe data, nilai kosong, duplikat, format campur, label tidak konsisten, outlier, relasi antar tabel (foreign key), dan kesesuaian rumus."));
c.push(table(["Tabel", "Kolom", "Masalah", "Baris", "Rencana penanganan"],
  D.assessing.map(a => [a.tabel, a.kolom, a.masalah, fmt(a.jumlah_baris), a.rencana_penanganan]), [1350, 1350, 2900, 650, 3388], { size: 15 }));
c.push(gap());

c.push(H2("Langkah 2 · Cleaning (notebook 02)"));
c.push(P("Prinsip: tidak ada data yang diubah atau dihapus tanpa alasan yang dapat dipertanggungjawabkan. Setiap penanganan dicatat di cleaning_log.csv beserta alasannya. Urutan kerja mengikuti ketergantungan antar tabel: produk → pelanggan → transaksi (dasar) → detail → produk (harga modal) → transaksi (hitung ulang) → stok → validasi."));
c.push(P("Beberapa teknik utama:", { bold: true, keepNext: true }));
[
  "Parser angka dan tanggal: \"Rp 1.234.000\", \"2 pcs\", \"12%\", \"-\" menjadi angka; DD/MM/YYYY dan DD-Mon-YYYY menjadi tanggal baku (ada bukti hari > 12 pada bagian pertama sehingga bukan MM/DD).",
  "Detail transaksi dijadikan sumber kebenaran: total transaksi yang kosong atau salah dihitung ulang dari detail.",
  "Quantity negatif diubah ke nilai mutlak karena subtotalnya positif dan cocok dengan |qty| × harga − diskon (salah tanda, bukan retur). Harga satuan 10× lipat diganti harga master.",
  "Product_id kosong dipulihkan lewat kemiripan nama + kecocokan harga satuan; metode diuji pada 300 baris berlabel (akurasi 100%).",
  "Relasi yatim direkonsiliasi: detail_id berurutan per transaksi, dan dugaan transaksi dibuktikan dengan sisa net_amount transaksi yang harus sama dengan subtotal baris (termasuk kasus salah ketik yang kebetulan menjadi id transaksi lain).",
  "Stok: stock_out dihitung ulang dari jumlah penjualan detail, ending_stock dari rumus initial + in − out.",
].forEach(s => c.push(bullet(s)));
c.push(table(["No", "Tabel", "Kolom", "Masalah", "Baris", "Penanganan"],
  D.cleaning.map(a => [a.no, a.tabel, a.kolom, a.masalah, fmt(a.jumlah_baris_terdampak), a.penanganan]), [450, 1250, 1350, 2400, 650, 3538], { size: 15 }));
c.push(gap());
c.push(P([t("Hasil. ", { bold: true }), t(`Data bersih lolos ${nOk} dari ${nVal} pemeriksaan otomatis (kunci unik, relasi antar tabel, kesesuaian rumus omzet/diskon/laba, stok, rentang tanggal, label sintetis). Keterbatasan: nama produk/pelanggan yang rusak oleh typo pada kata langka diperbaiki dengan aturan heuristik; kandidat yang perlu dicek manual disimpan di data/analysis/produk_perlu_cek_manual.csv.`)]));

c.push(H2("Langkah 3 · Analisis data / EDA (notebook 03)"));
c.push(P("Enam pertanyaan bisnis dijawab dari data bersih. Tabel hasil disimpan ke data/analysis dan dipakai dashboard serta tim lain."));
c.push(table(["Pertanyaan bisnis", "Output"], [
  ["1. Kategori dan produk apa yang omzetnya terbesar, per cabang?", "sales_by_category, sales_by_branch_month, sales_category_by_branch, top_products"],
  ["2. Produk mana yang fast-moving dan slow-moving (dan kelas ABC)?", "product_movement"],
  ["3. Berapa diskon per jenis pelanggan dan kategori, dan apakah dalam batas standar pemilik?", "discount_analysis (+ pemeriksaan pelanggaran batas)"],
  ["4. Bagaimana pola penjualan per hari dan per minggu di tiap cabang?", "sales_by_day, weekday_pattern, grafik omzet mingguan"],
  ["5. Kategori/pelanggan mana yang margin laba kotornya tertinggi dan terendah?", "margin_by_category, margin_by_customer_type"],
  ["6. Barang mana yang stoknya menipis di akhir periode?", "stock_status"],
], [5200, 4438], { size: 17 }));
c.push(gap());
c.push(P("Contoh temuan (dari data sintetis, hanya demonstrasi):", { bold: true, keepNext: true }));
c.push(bullet(`Omzet bersih ${rp(kpi.omzet_bersih)} dari ${fmt(kpi.jumlah_transaksi)} transaksi; margin laba kotor ${kpi.margin_laba_kotor_pct}%; diskon efektif ${kpi.diskon_efektif_pct}%.`));
c.push(bullet(`Kategori omzet terbesar: ${topCat.category} (${topCat.share_omzet_pct}% dari omzet bersih).`));
c.push(bullet(`Margin tertinggi: ${bestM.category} (${bestM.margin_pct}%); terendah: ${worstM.category} (${worstM.margin_pct}%).`));
c.push(bullet("Pemeriksaan ketepatan data dilakukan sebelum analisis: total transaksi = total detail, tidak ada detail tanpa produk/cabang, laba transaksi = laba detail − fee."));
c.push(note("Temuan di atas berasal dari data sintetis dan tidak boleh disajikan sebagai kondisi nyata Sumber Urip."));

c.push(H2("Langkah 4 · Prediksi permintaan dan rekomendasi restock (notebook 04, side quest)"));
c.push(P("Prediksi: unit terjual per minggu per cabang × kategori. Pembagian data berdasarkan waktu (3 minggu terakhir = data uji) dan fitur hanya memakai minggu sebelumnya (lag), sehingga tidak ada kebocoran data. Empat model dibandingkan dengan metrik yang sama:"));
c.push(table(["Model", "MAE", "RMSE", "WAPE (%)", "Terbaik"], D.model.map(m => [m.model, m.MAE, m.RMSE, m.WAPE_pct, m.terbaik ? "ya" : ""]), [4200, 1300, 1300, 1500, 1338], { size: 17 }));
c.push(gap());
c.push(P("Rekomendasi restock memakai aturan statistik yang transparan (bukan model): permintaan harian dari 28 hari terakhir, lead time pemasok diasumsikan 3 hari (asumsi simulasi), stok pengaman = 1,65 × simpangan baku × √lead time, titik pesan = permintaan × lead time + stok pengaman (minimal sama dengan stok minimum). Status: Habis → Restock segera → Waspada → Aman, dengan saran jumlah pesan."));
c.push(table(["Cabang", "Habis", "Restock segera", "Waspada", "Aman"], D.restock.map(r => [r.branch_name, r["Habis"] || 0, r["Restock segera"] || 0, r["Waspada"] || 0, r["Aman"] || 0]), [3000, 1500, 1900, 1500, 1738], { size: 17 }));
c.push(gap());
c.push(P("Catatan: data hanya ±12 minggu dan sintetis; hasil ini demonstrasi metode. Bila model sederhana menang, itu wajar untuk data pendek; pilih yang paling mudah dijelaskan."));

c.push(H2("Langkah 5 · Dashboard Streamlit (dashboard/app.py)"));
[
  "Sumber data: data bawaan (hasil pipeline) atau unggah CSV (transactions.csv + transaction_details.csv). File divalidasi dan pesan kesalahan jelas ditampilkan bila format salah.",
  "Filter: rentang tanggal, cabang, kategori, jenis pelanggan.",
  "Tab: Ringkasan · Produk & Kategori · Diskon & Margin · Stok & Restock (unduh CSV) · Prediksi · Tentang Data (assessing report dan cleaning log).",
  "Spanduk \"DATA SINTETIS\" tampil otomatis selama kolom data_source = synthetic.",
  "Deploy gratis lewat Streamlit Community Cloud; disematkan di web tim Full-stack dengan iframe (tambahkan ?embed=true) atau diganti grafik sendiri dari dashboard_summary.json. Langkah rinci ada di dashboard/README_DASHBOARD.md.",
].forEach(s => c.push(bullet(s)));

c.push(H2("Langkah 6 · Serah terima (notebook 05)"));
c.push(P("Notebook 05 mengemas hasil menjadi dua paket terpisah, membuat kontrak data (format, aturan pakai, batasan), kamus data seluruh file, dan manifest. Rinciannya pada bagian 4 dan 5."));

c.push(H1("4. Data yang dikirim ke Tim Full-stack"));
c.push(P("Folder handoff/for_fullstack/ beserta KONTRAK_DATA_DS_KE_FULLSTACK.md. Tujuan: data awal database, aturan harga/diskon untuk backend, dan hasil analisis untuk dashboard di web."));
const fsGroups = [
  ["seed/branches.csv", "3 cabang", "Master cabang"],
  ["seed/products.csv", `${cl.products} produk (tanpa harga modal)`, "Katalog untuk kasir dan pemilik"],
  ["seed/product_costs_OWNER_ONLY.csv", "harga modal per produk", "Hanya peran pemilik; jangan masuk endpoint publik"],
  ["seed/customers.csv", "23 pelanggan/bengkel rekanan fiktif + partner_fee_pct", "Master pelanggan; fee rekanan = biaya toko"],
  ["seed/inventory_current.csv", "stok terkini per cabang-produk", "Stok awal aplikasi"],
  ["seed/transactions_history.csv · transaction_details_history.csv", `${fmt(cl.transactions)} transaksi · ${fmt(cl.transaction_details)} detail`, "Riwayat demo (opsional)"],
  ["seed/discount_rules_by_customer_type.csv · discount_limit_by_category.csv", "perilaku & batas diskon", "Mesin harga/diskon di backend (asumsi, perlu konfirmasi pemilik)"],
  ["dashboard_data/*.csv (16 file)", "hasil analisis, prediksi, restock", "Data dasbor"],
  ["dashboard_data/dashboard_summary.json", "ringkasan seluruh hasil", "Satu endpoint untuk dasbor"],
  ["KONTRAK_DATA_DS_KE_FULLSTACK.md", "kontrak data dan usulan endpoint", "Dibaca sebelum integrasi"],
];
c.push(table(["File", "Isi", "Dipakai untuk"], fsGroups, [3700, 2900, 3038], { size: 16 }));
c.push(gap());
c.push(P("Aturan penting untuk Tim Full-stack:", { bold: true, keepNext: true }));
["Harga modal hanya untuk peran pemilik; kasir tidak boleh melihatnya.", "Pertahankan kolom data_source dan tampilkan penanda \"data demonstrasi (sintetis)\" selama data masih sintetis.",
 "Harga akhir = harga satuan × (1 − diskon%), diskon tidak boleh melebihi batas produk; fee rekanan adalah biaya toko, bukan diskon.", "Jangan menaruh file ini, .env, atau API key di repositori publik.",
 "Urutan impor seed: branches → products → customers → inventory_current → transactions → transaction_details."].forEach(s => c.push(bullet(s)));
c.push(P("Usulan endpoint: GET /api/v1/dashboard/summary · /restock-recommendations · /demand-forecast · /products · /discount-rules.", { size: 20 }));

c.push(H1("5. Data yang dikirim ke Tim Gen AI"));
c.push(P("Folder handoff/for_genai/ beserta KONTRAK_DATA_DS_KE_GENAI.md. Tujuan: bahan latihan model intent, normalisasi entitas, dan basis pengetahuan RAG."));
c.push(table(["File", "Isi", "Kegunaan"], [
  ["intent_dataset.csv", `${fmt(D.intent_total)} kalimat berlabel 4 intent + entitas + kolom split`, "Melatih dan menguji klasifikasi intent"],
  ["intent_labels.csv", "definisi dan contoh tiap intent", "Acuan label"],
  ["product_alias_dictionary.csv", "alias nama produk → product_id", "Normalisasi entitas produk"],
  ["branch_aliases.csv · customer_type_aliases.csv", "alias cabang dan jenis pelanggan", "Ekstraksi entitas (sebagian alias dugaan)"],
  ["knowledge_base_products.csv", `${cl.products} dokumen produk`, "RAG (tanpa stok dan harga modal)"],
  ["discount_rules_by_customer_type.csv · discount_limit_by_category.csv", "aturan diskon", "Menjawab pertanyaan diskon"],
  ["inventory_current_for_answers.csv", "stok terkini", "Contoh; jawaban stok sebaiknya via API backend"],
  ["KONTRAK_DATA_DS_KE_GENAI.md", "kontrak data", "Dibaca sebelum melatih model"],
], [3500, 3100, 3038], { size: 16 }));
c.push(gap());
c.push(P("Komposisi dataset intent (jumlah kalimat per intent dan split):", { bold: true, keepNext: true }));
c.push(table(["Intent", "train", "val", "test"], D.intent_split.map(r => [r.intent, r.train, r.val, r.test]), [3600, 2000, 2000, 2038], { size: 17 }));
c.push(gap());
c.push(P("Aturan penting untuk Tim Gen AI:", { bold: true, keepNext: true }));
["Gunakan kolom split apa adanya. Dua template per intent hanya ada di test (template yang tidak pernah dilihat saat latihan) untuk menguji generalisasi.",
 "Kalimat dibuat dari template × katalog (sintetis), bukan percakapan nyata; perkaya dengan kalimat buatan tim agar tidak terlalu bertemplate. Kelas lainnya lebih sedikit: periksa keseimbangan kelas dan catat penanganannya.",
 "Model intent harus dilatih sendiri (aturan Main Quest), bukan hanya memanggil API LLM atau model siap pakai.",
 "Jawaban harga, diskon, dan stok diambil dari database lewat backend, bukan dari teks RAG. Metrik yang disarankan: F1-score (macro) pada split test, dilaporkan per intent.",
 "Harga modal tidak disertakan dan tidak boleh dikirim ke LLM eksternal; jangan mengirim data pelanggan nyata ke API pihak ketiga."].forEach(s => c.push(bullet(s)));
c.push(P("Contoh API yang disepakati: POST /predict-intent dengan {\"text\": \"stok ban irc 80/90-17 ada di paye?\"} menghasilkan {\"intent\": \"cek_stok\", \"confidence\": 0.93}.", { size: 20 }));

c.push(H1("6. Pemenuhan checklist Data Science"));
c.push(table(["Checklist (Asah)", "Bukti dalam paket"], [
  ["Main Quest · mengidentifikasi masalah dan peran data", "Notebook 03 (pertanyaan bisnis) dan dokumen ini"],
  ["Main Quest · merumuskan pertanyaan bisnis", "Notebook 03: 6 pertanyaan bisnis"],
  ["Main Quest · data wrangling: gathering, assessing, cleaning", "Notebook 01 dan 02; assessing_report.csv; cleaning_log.csv"],
  ["Main Quest · mengolah dan menganalisis data + penjelasan proses", "Notebook 03 dan tabel di data/analysis"],
  ["Main Quest · temuan dan rekomendasi yang mudah dipahami", "Notebook 03 (temuan otomatis dan rekomendasi), dashboard"],
  ["Main Quest · data/hasil analisis untuk anggota lain + cara pakai", "handoff/ (dua paket, kontrak data, kamus data)"],
  ["Main Quest · memeriksa ketepatan data", "Notebook 02 (validasi 27 cek) dan notebook 03 bagian 0"],
  ["Side Quest · dasbor interaktif (Streamlit), indikator, filter, unggah file, integrasi", "dashboard/app.py; README_DASHBOARD.md; dashboard_summary.json"],
  ["Side Quest · data untuk model AI, kamus data, split train/test", "handoff/for_genai/ (intent_dataset dengan split), DATA_DICTIONARY_ALL.csv"],
  ["Side Quest · model prediksi dan perbandingan model", "Notebook 04; model_comparison.csv; demand_forecast.csv"],
  ["Larangan · data dummy disajikan seolah nyata", "Label \"sintetis\" di semua file, dashboard, dan dokumen; kolom data_source dipertahankan"],
  ["Larangan · mengubah/menghilangkan data tanpa alasan", "cleaning_log.csv mencatat alasan setiap penanganan"],
], [4800, 4838], { size: 17 }));

c.push(H1("7. Asumsi, keterbatasan, dan langkah berikutnya"));
c.push(P("Yang masih asumsi:", { bold: true, keepNext: true }));
["Seluruh transaksi, stok, pelanggan, dan harga modal adalah simulasi; harga ban IRC berasal dari transkripsi foto pricelist HET 15 Juni 2026 dan perlu diverifikasi ulang.",
 "Aturan diskon pemilik (oli 12%, ban mobil 10%, ban motor 12%, spare part 20–25%, fee bengkel rekanan kecil 5%) masih informasi lisan dan belum dikonfirmasi; kapan spare part dapat 20% atau 25% belum diketahui.",
 "Lead time pemasok 3 hari dan perilaku diskon per jenis pelanggan adalah asumsi simulasi.",
 "Data hanya 3 bulan tanpa musiman nyata, retur, atau servis; model prediksi hanya demonstrasi."].forEach(s => c.push(bullet(s)));
c.push(P("Langkah berikutnya:", { bold: true, keepNext: true }));
["Digitalkan buku Sumber Urip sebagai data primer (anonimkan nama pelanggan; minta izin penggunaan data), lalu jalankan ulang pipeline dari notebook 01.",
 "Konfirmasi aturan diskon dan lead time ke pemilik; perbarui tabel aturan dan notebook 04.",
 "Kirim paket handoff ke tiap tim bersama DATA_DICTIONARY_ALL.csv; sepakati kontrak API sebelum pengembangan.",
 "Coba dashboard di browser (streamlit run dashboard/app.py) dan deploy ke Streamlit Community Cloud.",
 "Sebelum pengumpulan: pastikan label sintetis tampil di video demo, README, dan dashboard; jangan mengunggah kata sandi/API key atau data pribadi."].forEach(s => c.push(bullet(s)));

c.push(H1("Lampiran · Daftar lengkap file yang diserahkan"));
c.push(table(["Penerima", "File", "Baris", "Kolom", "Tujuan"], D.manifest.map(m => [m.penerima, m.file.replace(/^for_(fullstack|genai)\//, ""), fmt(m.baris), m.kolom || "-", m.tujuan]), [1100, 3300, 700, 700, 3838], { size: 15 }));

const doc = new Document({
  creator: "Tim Data Science", title: "Pipeline Data Science & Serah Terima Data - Kios Sumber Urip",
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 30, bold: true, color: "1F4E78" }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true, color: "2E75B6" }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({ children: [new TextRun({ text: "Kios Sumber Urip · Pipeline Data Science · DATA SINTETIS", font: FONT, size: 16, color: "7F7F7F" })], alignment: AlignmentType.RIGHT })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Halaman ", font: FONT, size: 16, color: "7F7F7F" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "7F7F7F" })] })] }) },
    children: c }]
});
Packer.toBuffer(doc).then(b => { const out = path.join(ROOT, "docs/Dokumentasi_Pipeline_DS_dan_Serah_Terima.docx"); fs.writeFileSync(out, b); console.log("ditulis", out, b.length); });
