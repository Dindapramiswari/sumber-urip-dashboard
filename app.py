# -*- coding: utf-8 -*-
"""Halaman utama: dashboard Analitik Penjualan Suku Cadang - Bengkel Sumber Urip.
Jalankan:  streamlit run app.py
Halaman 'Eksplorasi Interaktif' (menu kiri) membaca data/clean dan data/analysis secara langsung
dan punya filter serta unggah CSV. Angka pada tampilan utama ini adalah ringkasan hasil pipeline (data sintetis)."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Analitik Suku Cadang Sumber Urip", page_icon="🛞", layout="wide")
st.markdown(
    """<style>
    .block-container{padding:0.6rem 1rem 0 1rem !important; max-width:1320px}
    iframe{border:0; border-radius:12px}
    </style>""",
    unsafe_allow_html=True,
)

HTML = Path(__file__).parent / "assets" / "dashboard_sumber_urip.html"
if not HTML.exists():
    st.error("File assets/dashboard_sumber_urip.html tidak ditemukan. Pastikan folder assets/ ikut di-push ke GitHub.")
    st.stop()

st.page_link("pages/1_Eksplorasi_Interaktif.py", label="Buka eksplorasi interaktif (filter, unggah CSV, unduh rekomendasi restock)", icon="📊")
html = HTML.read_text(encoding="utf-8").replace('<html lang="id">', '<html lang="id" data-theme="dark">')
components.html(html, height=1150, scrolling=True)
