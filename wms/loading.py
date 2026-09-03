"""Loading overlay ringan untuk startup dan proses autentikasi Mirai."""

import html

import streamlit as st


def show_loading_screen(
    title: str = "Menyiapkan Mirai",
    message: str = "Menghubungkan database dan menyiapkan ruang kerja.",
):
    """Tampilkan overlay loading dan kembalikan placeholder untuk ditutup pemanggil."""
    safe_title = html.escape(str(title))
    safe_message = html.escape(str(message))
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <style>
        .mirai-loading-screen {{
            position: fixed;
            inset: 0;
            z-index: 2147483000;
            display: grid;
            min-height: 100vh;
            min-height: 100dvh;
            padding:
                max(1.25rem, env(safe-area-inset-top))
                max(1.25rem, env(safe-area-inset-right))
                max(1.25rem, env(safe-area-inset-bottom))
                max(1.25rem, env(safe-area-inset-left));
            overflow: hidden;
            place-items: center;
            background:
                radial-gradient(circle at 18% 16%, rgba(96, 165, 250, 0.22), transparent 18rem),
                radial-gradient(circle at 86% 82%, rgba(129, 140, 248, 0.22), transparent 20rem),
                linear-gradient(145deg, #f8fbff 0%, #eef4ff 52%, #f2f0ff 100%);
            color: #0f172a;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            isolation: isolate;
        }}
        .mirai-loading-screen::before,
        .mirai-loading-screen::after {{
            content: "";
            position: absolute;
            z-index: -1;
            width: clamp(15rem, 52vw, 32rem);
            height: clamp(15rem, 52vw, 32rem);
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 50%;
            opacity: 0.68;
        }}
        .mirai-loading-screen::before {{
            top: -17rem;
            right: -10rem;
            box-shadow: 0 0 0 3.8rem rgba(255, 255, 255, 0.12);
        }}
        .mirai-loading-screen::after {{
            bottom: -19rem;
            left: -8rem;
            box-shadow: 0 0 0 4.8rem rgba(255, 255, 255, 0.10);
        }}
        .mirai-loading-card {{
            display: flex;
            width: min(100%, 24rem);
            align-items: center;
            flex-direction: column;
            padding: clamp(1.65rem, 6vw, 2.35rem);
            border: 1px solid rgba(255, 255, 255, 0.84);
            border-radius: 1.65rem;
            background: rgba(255, 255, 255, 0.74);
            box-shadow:
                0 1.5rem 4rem rgba(30, 64, 175, 0.13),
                inset 0 1px 0 rgba(255, 255, 255, 0.9);
            text-align: center;
        }}
        .mirai-loading-emblem {{
            position: relative;
            display: grid;
            width: 6.4rem;
            height: 6.4rem;
            margin-bottom: 1.25rem;
            place-items: center;
        }}
        .mirai-loading-orbit {{
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: conic-gradient(
                from 15deg,
                transparent 0 16%,
                rgba(59, 130, 246, 0.28) 28%,
                #4f46e5 49%,
                transparent 61% 100%
            );
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 0);
            animation: mirai-orbit 1.4s linear infinite;
        }}
        .mirai-loading-logo {{
            position: relative;
            display: grid;
            width: 4.55rem;
            height: 4.55rem;
            border: 1px solid rgba(255, 255, 255, 0.54);
            border-radius: 1.35rem;
            place-items: center;
            background: linear-gradient(145deg, #3b82f6 0%, #4f46e5 58%, #7c3aed 100%);
            box-shadow:
                0 0.9rem 2.2rem rgba(79, 70, 229, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.32);
            color: #ffffff;
            font-size: 2rem;
            font-weight: 850;
            letter-spacing: -0.07em;
            animation: mirai-logo-breathe 1.8s ease-in-out infinite;
        }}
        .mirai-loading-brand {{
            color: #1e3a8a;
            font-size: 0.67rem;
            font-weight: 850;
            letter-spacing: 0.26em;
            text-transform: uppercase;
        }}
        .mirai-loading-title {{
            margin-top: 0.55rem;
            color: #0f172a;
            font-size: clamp(1.25rem, 5vw, 1.55rem);
            font-weight: 800;
            line-height: 1.2;
            letter-spacing: -0.035em;
        }}
        .mirai-loading-message {{
            max-width: 18.5rem;
            min-height: 2.4em;
            margin-top: 0.55rem;
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.5;
        }}
        .mirai-loading-track {{
            position: relative;
            width: 100%;
            height: 0.28rem;
            margin-top: 1.45rem;
            overflow: hidden;
            border-radius: 999px;
            background: #dbeafe;
        }}
        .mirai-loading-bar {{
            position: absolute;
            inset: 0 auto 0 0;
            width: 44%;
            border-radius: inherit;
            background: linear-gradient(90deg, #60a5fa 0%, #4f46e5 62%, #8b5cf6 100%);
            box-shadow: 0 0 0.8rem rgba(79, 70, 229, 0.38);
            animation: mirai-progress 1.35s cubic-bezier(0.65, 0, 0.35, 1) infinite;
        }}
        .mirai-loading-status {{
            display: flex;
            min-height: 1.2rem;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.8rem;
            color: #64748b;
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.02em;
        }}
        .mirai-loading-dot {{
            width: 0.42rem;
            height: 0.42rem;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.34);
            animation: mirai-status-pulse 1.55s ease-out infinite;
        }}
        @keyframes mirai-orbit {{
            to {{ transform: rotate(360deg); }}
        }}
        @keyframes mirai-logo-breathe {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.035); }}
        }}
        @keyframes mirai-progress {{
            0% {{ transform: translateX(-115%); }}
            100% {{ transform: translateX(330%); }}
        }}
        @keyframes mirai-status-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.36); }}
            72%, 100% {{ box-shadow: 0 0 0 0.48rem rgba(34, 197, 94, 0); }}
        }}
        @media (max-width: 430px) {{
            .mirai-loading-card {{
                width: min(100%, 20.5rem);
                border-radius: 1.35rem;
            }}
            .mirai-loading-emblem {{
                width: 5.75rem;
                height: 5.75rem;
            }}
            .mirai-loading-logo {{
                width: 4.05rem;
                height: 4.05rem;
                border-radius: 1.16rem;
                font-size: 1.75rem;
            }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .mirai-loading-orbit {{ animation-duration: 3.2s; }}
            .mirai-loading-logo,
            .mirai-loading-dot {{ animation: none; }}
            .mirai-loading-bar {{ animation-duration: 2.6s; }}
        }}
        </style>
        <div
            class="mirai-loading-screen"
            role="status"
            aria-live="polite"
            aria-label="{safe_title}"
        >
            <div class="mirai-loading-card">
                <div class="mirai-loading-emblem" aria-hidden="true">
                    <div class="mirai-loading-orbit"></div>
                    <div class="mirai-loading-logo">M</div>
                </div>
                <div class="mirai-loading-brand">Mirai · Warehouse</div>
                <div class="mirai-loading-title">{safe_title}</div>
                <div class="mirai-loading-message">{safe_message}</div>
                <div class="mirai-loading-track" aria-hidden="true">
                    <div class="mirai-loading-bar"></div>
                </div>
                <div class="mirai-loading-status">
                    <span class="mirai-loading-dot" aria-hidden="true"></span>
                    Proses aman sedang berjalan
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return placeholder


def hide_loading_screen(placeholder):
    """Hapus overlay dengan aman; menerima ``None`` agar mudah dipakai di finally."""
    if placeholder is not None:
        placeholder.empty()
