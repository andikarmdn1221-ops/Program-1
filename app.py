import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

# =============================================================================
# 🎨 PERBAIKAN CSS: MENU TAMPIL KEREN & BERSIH
# =============================================================================
st.markdown("""
<style>
    /* Latar Belakang Utama */
    .stApp {
        background-color: #F4F7FE;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3 { color: #1A202C !important; font-weight: 800 !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    
    /* Styling Menu Radio Navigation */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 8px;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 10px 16px !important;
        margin: 0 !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #EDF2F7 !important;
        border-color: #CBD5E0 !important;
        transform: translateX(4px);
    }
    
    /* Teks Menu */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #2D3748 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    /* Metrik & Card */
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02) !important;
    }
    [data-testid="stMetricLabel"] p { color: #718096 !important; font-size: 13px !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] div { color: #1A202C !important; font-size: 32px !important; font-weight: 800 !important; }
    
    [data-testid="stForm"], [data-testid="stDataFrame"], [data-testid="stTable"] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02) !important;
        border: 1px solid #E2E8F0 !important;
    }

    .stButton button, .stDownloadButton button {
        background-color: #1A202C !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 10px 24px !important;
    }
</style>
""", unsafe_allow_html=True)
