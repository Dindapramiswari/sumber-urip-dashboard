# Kontrak Data: Data Science → Tim Full-stack
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
