"""Tampilan responsif desktop, tablet, dan ponsel."""

import streamlit as st

def inject_responsive_css():
    st.markdown(
        r"""
        <style>
        /* =====================================================
           v8.0 PRODUCTION + MOBILE
           Desktop tetap lebar; iPhone/Android dibuat touch-safe.
           ===================================================== */
        html, body, [class*="css"] {
            -webkit-text-size-adjust: 100%;
        }

        /* Tampilan lebih bersih tanpa mengubah komponen bawaan Streamlit. */
        .block-container {
            padding-top: 2rem;
            max-width: 1440px;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 0.85rem;
            padding: 0.75rem 0.9rem;
            background: rgba(128, 128, 128, 0.035);
        }

        /* Kartu KPI khusus dashboard: stabil di desktop dan ringkas di HP. */
        .wms-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.75rem 0 1.15rem 0;
        }
        .wms-kpi-card {
            position: relative;
            overflow: hidden;
            min-width: 0;
            min-height: 7rem;
            padding: 1rem 1.05rem;
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 1rem;
            background: #ffffff;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.055);
        }
        .wms-kpi-card::after {
            display: none;
        }
        .wms-kpi-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.55rem;
        }
        .wms-kpi-label {
            min-width: 0;
            color: #64748b;
            font-size: 0.82rem;
            font-weight: 650;
            line-height: 1.25;
        }
        .wms-kpi-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 2rem;
            width: 2rem;
            height: 2rem;
            border-radius: 0.65rem;
            background: var(--kpi-soft);
            color: var(--kpi-color);
            font-size: 1rem;
            overflow: visible;
        }
        .wms-kpi-icon svg {
            display: block;
            width: 1.12rem;
            height: 1.12rem;
            overflow: visible;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .wms-kpi-value {
            position: relative;
            z-index: 1;
            color: #0f172a;
            font-size: 1.9rem;
            font-weight: 750;
            line-height: 1.08;
            letter-spacing: -0.035em;
            white-space: nowrap;
        }
        .wms-kpi-blue { --kpi-color: #2563eb; --kpi-soft: #dbeafe; border-top: 3px solid #3b82f6; }
        .wms-kpi-indigo { --kpi-color: #4f46e5; --kpi-soft: #e0e7ff; border-top: 3px solid #6366f1; }
        .wms-kpi-amber { --kpi-color: #b45309; --kpi-soft: #fef3c7; border-top: 3px solid #f59e0b; }
        .wms-kpi-red { --kpi-color: #dc2626; --kpi-soft: #fee2e2; border-top: 3px solid #ef4444; }

        .wms-sync-pill {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            margin: 0.1rem 0 0.65rem 0;
            padding: 0.36rem 0.65rem;
            border: 1px solid #dbeafe;
            border-radius: 999px;
            background: #eff6ff;
            color: #475569;
            font-size: 0.78rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .wms-alert-strip {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            margin: 0.15rem 0 0.75rem 0;
            padding: 0.78rem 0.9rem;
            border: 1px solid #fde68a;
            border-left: 4px solid #f59e0b;
            border-radius: 0.85rem;
            background: #fffbeb;
            color: #92400e;
            font-weight: 650;
            line-height: 1.3;
        }
        .st-key-main_refresh {
            width: 2.75rem;
            max-width: 2.75rem;
        }
        .st-key-main_refresh .stButton > button {
            width: 2.75rem !important;
            min-height: 2.55rem !important;
            height: 2.55rem !important;
            padding: 0 !important;
            border: 1px solid #bfdbfe !important;
            border-radius: 0.75rem !important;
            background: #eff6ff !important;
            color: #1d4ed8 !important;
            font-size: 1rem !important;
            font-weight: 650 !important;
        }
        .st-key-main_refresh .stButton > button:hover {
            border-color: #60a5fa !important;
            background: #dbeafe !important;
        }
        [data-testid="stAlert"] {
            border-radius: 0.8rem;
        }

        /* Tombol/link tidak memotong label panjang. */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="stLinkButton"] a {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        @media (max-width: 768px) {
            /* Tombol pembuka menu wajib tetap terlihat di layar kecil. */
            [data-testid="stSidebarCollapsedControl"] {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                z-index: 1000000 !important;
            }

            /* Safe-area penting untuk iPhone dengan notch / Dynamic Island. */
            .block-container {
                padding-top: max(4rem, calc(3.55rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.72rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.72rem, env(safe-area-inset-right)) !important;
                padding-bottom: max(1.4rem, env(safe-area-inset-bottom)) !important;
                max-width: 100% !important;
                overflow-x: clip !important;
            }
            [data-testid="stAppViewContainer"] > .main {
                max-width: 100vw !important;
                overflow-x: hidden !important;
            }

            /* Sidebar menjadi panel yang muat di iPhone/Android kecil. */
            section[data-testid="stSidebar"] {
                width: min(88vw, 320px) !important;
                min-width: min(88vw, 320px) !important;
            }
            section[data-testid="stSidebar"] > div {
                width: min(88vw, 320px) !important;
            }

            /* Kolom ditumpuk supaya form tidak terpotong. */
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.55rem !important;
            }
            [data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }

            /* Metric bawaan pada halaman lain menjadi grid 2 kolom. */
            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
                display: grid !important;
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                gap: 0.55rem !important;
            }
            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="column"] {
                width: auto !important;
                min-width: 0 !important;
                flex: none !important;
            }

            h1 {
                font-size: 1.52rem !important;
                line-height: 1.18 !important;
                overflow-wrap: anywhere !important;
                margin-top: 0 !important;
            }
            h2 { font-size: 1.28rem !important; line-height: 1.2 !important; }
            h3 { font-size: 1.08rem !important; }
            hr {
                margin-top: 0.6rem !important;
                margin-bottom: 0.65rem !important;
            }

            /* 16px mencegah Safari iOS melakukan zoom otomatis saat input fokus. */
            input, textarea, select,
            [data-baseweb="select"] input {
                font-size: 16px !important;
            }

            /* Target sentuh minimal ~48px. */
            .stButton > button,
            .stDownloadButton > button,
            [data-testid="stFormSubmitButton"] > button,
            [data-testid="stLinkButton"] a {
                width: 100% !important;
                min-height: 3rem !important;
                font-size: 0.95rem !important;
                padding: 0.55rem 0.75rem !important;
            }

            [data-testid="stMetric"] {
                min-height: 5.6rem !important;
                padding: 0.7rem 0.75rem !important;
                border-radius: 0.85rem !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.4rem !important;
                line-height: 1.12 !important;
            }

            .wms-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.55rem;
                margin: 0.55rem 0 0.8rem 0;
            }
            .wms-kpi-card {
                min-height: 6.05rem;
                padding: 0.72rem 0.75rem;
                border-radius: 0.85rem;
                box-shadow: 0 3px 11px rgba(15, 23, 42, 0.045);
            }
            .wms-kpi-top { margin-bottom: 0.4rem; }
            .wms-kpi-label { font-size: 0.74rem; }
            .wms-kpi-icon {
                flex-basis: 1.75rem;
                width: 1.75rem;
                height: 1.75rem;
                border-radius: 0.55rem;
                font-size: 0.88rem;
            }
            .wms-kpi-value { font-size: 1.52rem; }
            .wms-sync-pill {
                display: flex;
                width: fit-content;
                margin-bottom: 0.55rem;
                padding: 0.32rem 0.55rem;
                border-radius: 0.65rem;
                font-size: 0.72rem;
            }
            .wms-alert-strip {
                gap: 0.55rem;
                margin-bottom: 0.65rem;
                padding: 0.66rem 0.72rem;
                border-radius: 0.72rem;
                font-size: 0.86rem;
            }
            .st-key-main_refresh {
                width: 2.75rem !important;
                max-width: 2.75rem !important;
                margin: 0.15rem 0 0.15rem auto !important;
            }
            .st-key-main_refresh .stButton > button {
                width: 2.75rem !important;
                min-height: 2.55rem !important;
                height: 2.55rem !important;
                padding: 0 !important;
                font-size: 1rem !important;
            }

            /* Tabs dapat digeser horizontal, tidak memaksa layar melebar. */
            [data-baseweb="tab-list"] {
                overflow-x: auto !important;
                scrollbar-width: thin;
                white-space: nowrap !important;
            }

            /* Dataframe & chart tidak membuat horizontal page overflow. */
            [data-testid="stDataFrame"],
            [data-testid="stPlotlyChart"],
            [data-testid="stPlotlyChart"] > div {
                width: 100% !important;
                max-width: 100% !important;
            }
            [data-testid="stDataFrame"] {
                overflow-x: auto !important;
            }

            /* Uploader tetap berada di viewport HP. */
            [data-testid="stFileUploader"],
            [data-testid="stFileUploaderDropzone"] {
                max-width: 100% !important;
                min-width: 0 !important;
            }
            [data-testid="stFileUploaderDropzone"] {
                padding: 0.75rem !important;
            }

            [data-testid="stAlert"],
            [data-testid="stCaptionContainer"] {
                line-height: 1.35 !important;
                overflow-wrap: anywhere !important;
            }

            /* Navigasi sidebar lebih enak disentuh. */
            section[data-testid="stSidebar"] [role="radiogroup"] label {
                min-height: 2.2rem !important;
                padding-top: 0.15rem !important;
                padding-bottom: 0.15rem !important;
            }
        }

        @media (max-width: 430px) {
            .block-container {
                padding-top: max(3.85rem, calc(3.4rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.52rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.52rem, env(safe-area-inset-right)) !important;
            }
            h1 { font-size: 1.36rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.30rem !important; }
            .wms-kpi-card { min-height: 5.8rem; padding: 0.66rem 0.68rem; }
            .wms-kpi-label { font-size: 0.7rem; }
            .wms-kpi-value { font-size: 1.4rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
