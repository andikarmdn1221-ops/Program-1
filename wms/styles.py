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

        /* =====================================================
           MIRAI LOGIN
           Hanya aktif saat marker login hadir di halaman.
           ===================================================== */
        body:has(#mirai-login-marker) [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 12% 10%, rgba(59, 130, 246, 0.13), transparent 28rem),
                radial-gradient(circle at 88% 88%, rgba(99, 102, 241, 0.10), transparent 30rem),
                linear-gradient(145deg, #f8fbff 0%, #f4f7fb 52%, #f8fafc 100%);
        }
        body:has(#mirai-login-marker) [data-testid="stHeader"] {
            background: transparent !important;
        }
        body:has(#mirai-login-marker) .block-container {
            width: min(100%, 580px) !important;
            max-width: 580px !important;
            padding-top: clamp(2.8rem, 8vh, 6rem) !important;
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            padding-bottom: 3rem !important;
        }
        .mirai-login-hero {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.65rem;
        }
        .mirai-brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 3.5rem;
            width: 3.5rem;
            height: 3.5rem;
            border-radius: 1.05rem;
            background: linear-gradient(145deg, #2563eb 0%, #4f46e5 100%);
            color: #ffffff;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.24);
            font-size: 1.55rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: -0.04em;
        }
        .mirai-login-title {
            color: #0f172a;
            font-size: 2.15rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: -0.045em;
        }
        .mirai-login-kicker {
            margin-top: 0.42rem;
            color: #2563eb;
            font-size: 0.68rem;
            font-weight: 750;
            line-height: 1.2;
            letter-spacing: 0.13em;
        }
        .mirai-login-subtitle {
            margin: 0 0 1.35rem 0;
            color: #64748b;
            font-size: 0.93rem;
            line-height: 1.55;
        }
        body:has(#mirai-login-marker) [data-baseweb="tab-list"] {
            gap: 0.35rem;
            padding: 0.3rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.85rem;
            background: rgba(255, 255, 255, 0.78);
        }
        body:has(#mirai-login-marker) [data-baseweb="tab"] {
            flex: 1 1 0;
            justify-content: center;
            min-height: 2.55rem;
            border-radius: 0.62rem;
            color: #64748b;
            font-weight: 650;
        }
        body:has(#mirai-login-marker) [aria-selected="true"] {
            background: #eff6ff !important;
            color: #1d4ed8 !important;
        }
        body:has(#mirai-login-marker) [data-baseweb="tab-highlight"] {
            display: none !important;
        }
        body:has(#mirai-login-marker) [data-testid="stForm"] {
            margin-top: 0.8rem;
            padding: 1.35rem 1.35rem 1.2rem;
            border: 1px solid rgba(203, 213, 225, 0.88);
            border-radius: 1.1rem;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.09);
            backdrop-filter: blur(12px);
        }
        body:has(#mirai-login-marker) [data-baseweb="input"] {
            border-color: #dbe3ef !important;
            border-radius: 0.75rem !important;
            background: #f8fafc !important;
        }
        body:has(#mirai-login-marker) [data-baseweb="input"]:focus-within {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12) !important;
        }
        body:has(#mirai-login-marker) [data-testid="stFormSubmitButton"] > button {
            min-height: 2.85rem;
            border: 0 !important;
            border-radius: 0.75rem !important;
            background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            font-weight: 750 !important;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.20);
            transition: transform 150ms ease, box-shadow 150ms ease, filter 150ms ease;
        }
        body:has(#mirai-login-marker) [data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.04);
            box-shadow: 0 11px 24px rgba(37, 99, 235, 0.27);
        }
        body:has(#mirai-login-marker) [data-testid="stAlert"] {
            border-radius: 0.85rem;
        }

        @media (max-width: 768px) {
            body:has(#mirai-login-marker) .block-container {
                width: min(100%, 560px) !important;
                max-width: 560px !important;
                padding-top: max(4.25rem, calc(3.8rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.9rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.9rem, env(safe-area-inset-right)) !important;
            }
        }
        @media (max-width: 430px) {
            body:has(#mirai-login-marker) .block-container {
                padding-top: max(3.9rem, calc(3.45rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.72rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.72rem, env(safe-area-inset-right)) !important;
            }
            .mirai-login-hero { gap: 0.78rem; }
            .mirai-brand-mark {
                flex-basis: 3rem;
                width: 3rem;
                height: 3rem;
                border-radius: 0.88rem;
                font-size: 1.3rem;
            }
            .mirai-login-title { font-size: 1.75rem; }
            .mirai-login-kicker { font-size: 0.58rem; letter-spacing: 0.1em; }
            .mirai-login-subtitle { margin-bottom: 1rem; font-size: 0.86rem; }
            body:has(#mirai-login-marker) [data-testid="stForm"] {
                padding: 1rem 0.9rem 0.9rem;
                border-radius: 0.95rem;
            }
        }


        /* =====================================================
           MIRAI APPLICATION SHELL + DASHBOARD
           ===================================================== */
        section[data-testid="stSidebar"] {
            border-right: 1px solid #e2e8f0;
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 1.1rem;
        }
        .mirai-sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            margin: 0.2rem 0 1rem;
        }
        .mirai-sidebar-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 2.55rem;
            width: 2.55rem;
            height: 2.55rem;
            border-radius: 0.78rem;
            background: linear-gradient(145deg, #2563eb 0%, #4f46e5 100%);
            color: #ffffff;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22);
            font-size: 1.05rem;
            font-weight: 800;
        }
        .mirai-sidebar-name {
            color: #0f172a;
            font-size: 1.12rem;
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: -0.025em;
        }
        .mirai-sidebar-tagline {
            margin-top: 0.24rem;
            color: #64748b;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .mirai-user-card {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 0.25rem;
            padding: 0.7rem;
            border: 1px solid #e2e8f0;
            border-radius: 0.85rem;
            background: rgba(255, 255, 255, 0.8);
        }
        .mirai-user-avatar {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 2rem;
            width: 2rem;
            height: 2rem;
            border-radius: 0.65rem;
            background: #dbeafe;
            color: #1d4ed8;
            font-size: 0.82rem;
            font-weight: 800;
        }
        .mirai-user-name {
            max-width: 11rem;
            overflow: hidden;
            color: #1e293b;
            font-size: 0.8rem;
            font-weight: 750;
            line-height: 1.2;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .mirai-user-role {
            margin-top: 0.16rem;
            color: #64748b;
            font-size: 0.67rem;
            line-height: 1.2;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0.18rem;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label {
            min-height: 2.2rem;
            padding: 0.34rem 0.55rem;
            border: 1px solid transparent;
            border-radius: 0.68rem;
            color: #475569;
            transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
            border-color: #dbeafe;
            background: #eff6ff;
            color: #1d4ed8;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            border-color: #bfdbfe;
            background: #dbeafe;
            color: #1d4ed8;
            font-weight: 700;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
            display: none;
        }
        section[data-testid="stSidebar"] [data-testid="stAlert"] {
            padding: 0.65rem 0.7rem;
            border-radius: 0.78rem;
            font-size: 0.75rem;
        }

        .mirai-page-header {
            position: relative;
            display: flex;
            align-items: center;
            gap: 1rem;
            overflow: hidden;
            min-height: 7.4rem;
            padding: 1.25rem 1.35rem;
            border: 1px solid #dbeafe;
            border-radius: 1.15rem;
            background:
                radial-gradient(circle at 88% 10%, rgba(99, 102, 241, 0.13), transparent 12rem),
                linear-gradient(135deg, #f8fbff 0%, #eff6ff 100%);
            box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
        }
        .mirai-page-header::after {
            content: "";
            position: absolute;
            right: -2.2rem;
            bottom: -3.5rem;
            width: 11rem;
            height: 11rem;
            border: 1.6rem solid rgba(37, 99, 235, 0.055);
            border-radius: 50%;
            pointer-events: none;
        }
        .mirai-page-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 3.5rem;
            width: 3.5rem;
            height: 3.5rem;
            border-radius: 1rem;
            background: linear-gradient(145deg, #2563eb 0%, #4f46e5 100%);
            color: #ffffff;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.23);
            font-size: 1.4rem;
            font-weight: 850;
        }
        .mirai-page-copy {
            position: relative;
            z-index: 1;
            min-width: 0;
        }
        .mirai-page-eyebrow {
            margin-bottom: 0.3rem;
            color: #2563eb;
            font-size: 0.64rem;
            font-weight: 800;
            letter-spacing: 0.11em;
        }
        .mirai-page-copy h1 {
            margin: 0 !important;
            color: #0f172a;
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: -0.04em;
        }
        .mirai-page-copy p {
            margin: 0.42rem 0 0;
            color: #64748b;
            font-size: 0.86rem;
            line-height: 1.4;
        }
        .mirai-page-meta {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: flex-end;
            flex-direction: column;
            gap: 0.42rem;
            margin-left: auto;
        }
        .mirai-page-meta span {
            padding: 0.34rem 0.58rem;
            border: 1px solid rgba(191, 219, 254, 0.9);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.72);
            color: #475569;
            font-size: 0.66rem;
            line-height: 1;
            white-space: nowrap;
        }
        .st-key-main_refresh {
            width: 9.7rem !important;
            max-width: 9.7rem !important;
            margin: 0.7rem 0 0.25rem auto !important;
        }
        .st-key-main_refresh .stButton > button {
            width: 9.7rem !important;
            min-height: 2.45rem !important;
            height: 2.45rem !important;
            padding: 0.4rem 0.75rem !important;
            border: 1px solid #bfdbfe !important;
            border-radius: 0.72rem !important;
            background: #ffffff !important;
            color: #1d4ed8 !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.045);
        }
        .mirai-header-divider,
        .mirai-section-divider {
            width: 100%;
            height: 1px;
            margin: 1rem 0;
            background: linear-gradient(90deg, transparent 0%, #e2e8f0 8%, #e2e8f0 92%, transparent 100%);
        }

        .wms-sync-pill {
            border-color: #bfdbfe;
            background: #eff6ff;
            color: #1e40af;
            font-weight: 650;
        }
        .wms-alert-strip {
            box-shadow: 0 5px 16px rgba(245, 158, 11, 0.08);
        }
        .wms-kpi-grid {
            gap: 0.9rem;
            margin-top: 1rem;
        }
        .wms-kpi-card {
            min-height: 7.4rem;
            border-color: #e2e8f0;
            border-top-width: 1px;
            padding: 1.05rem 1.1rem;
            box-shadow: 0 7px 22px rgba(15, 23, 42, 0.055);
            transition: transform 150ms ease, box-shadow 150ms ease;
        }
        .wms-kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.085);
        }
        .wms-kpi-card::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 3px;
            background: var(--kpi-color);
        }
        .wms-kpi-value {
            font-size: 2rem;
        }

        .mirai-health-card {
            min-height: 19rem;
            padding: 1.1rem 1.15rem;
            border: 1px solid #e2e8f0;
            border-radius: 1rem;
            background: #ffffff;
            box-shadow: 0 7px 22px rgba(15, 23, 42, 0.05);
        }
        .mirai-health-heading {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.7rem;
            margin-bottom: 1.2rem;
        }
        .mirai-health-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 780;
        }
        .mirai-health-badge {
            padding: 0.3rem 0.52rem;
            border-radius: 999px;
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 0.65rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .mirai-health-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: clamp(1rem, 3vw, 2.5rem);
            min-height: 13.5rem;
        }
        .mirai-donut {
            position: relative;
            display: grid;
            flex: 0 0 9.5rem;
            width: 9.5rem;
            height: 9.5rem;
            place-items: center;
            border-radius: 50%;
            background: conic-gradient(
                #22c55e 0 var(--safe-end),
                #f59e0b var(--safe-end) var(--critical-end),
                #ef4444 var(--critical-end) 100%
            );
            box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.03);
        }
        .mirai-donut::after {
            content: "";
            position: absolute;
            inset: 1.22rem;
            border-radius: 50%;
            background: #ffffff;
            box-shadow: 0 3px 15px rgba(15, 23, 42, 0.08);
        }
        .mirai-donut-center {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            flex-direction: column;
        }
        .mirai-donut-center strong {
            color: #0f172a;
            font-size: 1.75rem;
            line-height: 1;
        }
        .mirai-donut-center span {
            margin-top: 0.28rem;
            color: #64748b;
            font-size: 0.62rem;
            font-weight: 650;
        }
        .mirai-health-legend {
            min-width: 8.5rem;
        }
        .mirai-health-legend > div {
            display: grid;
            grid-template-columns: 0.62rem 1fr auto;
            align-items: center;
            gap: 0.48rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f1f5f9;
            color: #475569;
            font-size: 0.75rem;
        }
        .mirai-health-legend > div:last-child {
            border-bottom: 0;
        }
        .mirai-health-legend strong {
            color: #0f172a;
            font-size: 0.82rem;
        }
        .mirai-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 50%;
        }
        .mirai-dot-safe { background: #22c55e; }
        .mirai-dot-critical { background: #f59e0b; }
        .mirai-dot-empty { background: #ef4444; }

        .mirai-section-heading {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            margin: 0.15rem 0 0.75rem;
            padding: 0.3rem 0.15rem;
        }
        .mirai-section-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 2rem;
            width: 2rem;
            height: 2rem;
            border-radius: 0.62rem;
            background: #dbeafe;
            color: #1d4ed8;
            font-size: 0.88rem;
            font-weight: 800;
        }
        .mirai-section-icon-red {
            background: #fee2e2;
            color: #dc2626;
        }
        .mirai-section-heading strong {
            display: block;
            color: #0f172a;
            font-size: 1rem;
            line-height: 1.2;
        }
        .mirai-section-heading small {
            display: block;
            margin-top: 0.18rem;
            color: #64748b;
            font-size: 0.68rem;
            line-height: 1.25;
        }
        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid #e2e8f0;
            border-radius: 0.9rem;
            background: #ffffff;
            box-shadow: 0 5px 18px rgba(15, 23, 42, 0.045);
        }

        @media (max-width: 900px) {
            .mirai-page-meta {
                display: none;
            }
            .mirai-health-content {
                gap: 1rem;
            }
            .mirai-donut {
                flex-basis: 8rem;
                width: 8rem;
                height: 8rem;
            }
        }
        @media (max-width: 768px) {
            .mirai-page-header {
                align-items: flex-start;
                min-height: 0;
                padding: 1rem;
                border-radius: 1rem;
            }
            .mirai-page-mark {
                flex-basis: 2.8rem;
                width: 2.8rem;
                height: 2.8rem;
                border-radius: 0.82rem;
                font-size: 1.1rem;
            }
            .mirai-page-eyebrow {
                font-size: 0.55rem;
                letter-spacing: 0.08em;
            }
            .mirai-page-copy h1 {
                font-size: 1.55rem !important;
            }
            .mirai-page-copy p {
                font-size: 0.78rem;
            }
            .st-key-main_refresh {
                width: 100% !important;
                max-width: 100% !important;
                margin: 0.6rem 0 0.2rem !important;
            }
            .st-key-main_refresh .stButton > button {
                width: 100% !important;
                min-height: 2.75rem !important;
                height: 2.75rem !important;
            }
            .mirai-health-card {
                min-height: 0;
            }
        }
        @media (max-width: 430px) {
            .mirai-page-header {
                gap: 0.72rem;
                padding: 0.85rem;
            }
            .mirai-page-mark {
                flex-basis: 2.55rem;
                width: 2.55rem;
                height: 2.55rem;
            }
            .mirai-page-copy p {
                display: none;
            }
            .mirai-health-content {
                align-items: stretch;
                flex-direction: column;
            }
            .mirai-donut {
                margin: 0.25rem auto;
            }
            .mirai-health-legend {
                width: 100%;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
