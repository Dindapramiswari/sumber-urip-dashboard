# Kontrak Data: Data Science → Tim Gen AI
**Status:** data SINTETIS (kalimat dibuat dari template × katalog). Tidak ada percakapan nyata pelanggan.

## Isi paket (`for_genai/`)
| File | Kegunaan |
|---|---|
| `intent_dataset.csv` | 2519 kalimat berlabel 4 intent (`tanya_harga`, `tanya_diskon`, `cek_stok`, `lainnya`) + entitas + kolom `split` (train/val/test) |
| `intent_labels.csv` | definisi tiap intent |
| `product_alias_dictionary.csv` | 1577 alias nama produk → `product_id` (normalisasi entitas) |
| `branch_aliases.csv`, `customer_type_aliases.csv` | alias cabang dan jenis pelanggan (sebagian alias adalah dugaan, perlu konfirmasi) |
| `knowledge_base_products.csv` | 390 dokumen produk untuk RAG (tanpa stok dan harga modal) |
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
`POST /predict-intent` — request `{"text": "stok ban irc 80/90-17 ada di paye?"}` — response `{"intent": "cek_stok", "confidence": 0.93}`
