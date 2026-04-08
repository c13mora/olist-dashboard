"""
st_theme.py — Streamlit Dashboard Design Kit v2
================================================
Client-agnostic design system. Configure each client via brand.toml.

Usage (start of every page file):
    from st_theme import configure_page, sidebar_header, sidebar_nav, section_header, ...

    brand = configure_page("Page Title", "🎯")

    with st.sidebar:
        sidebar_header(brand)
        sidebar_nav()
        st.divider()
        # ... page-specific filters ...
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from contextlib import contextmanager

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib          # pip install tomli  (Python < 3.11)
    except ImportError:
        tomllib = None

# Project root — always the directory that contains this file.
_ROOT = Path(__file__).parent

# ── Navigation definition ─────────────────────────────────────────────────────
# Edit this list when adapting the kit to a different client / page structure.
# Tuple: (file_path_from_root, display_label, material_icon_name)
# Icon values are Streamlit Material icon names passed to st.Page(icon=...).
NAV_PAGES = [
    ("views/overview.py",   "Overview",         "dashboard"),
    ("views/revenue.py",    "Revenue & Orders", "trending_up"),
    ("views/customers.py",  "Customers",        "group"),
    ("views/operations.py", "Operations",       "local_shipping"),
]

# ── Default brand (fallback when brand.toml is absent) ───────────────────────
_DEFAULT_BRAND: dict = {
    "brand":  {"name": "Analytics", "tagline": "", "logo_path": "", "currency_symbol": "$"},
    "colors": {
        "primary":  "#6366F1",
        "accent":   "#818CF8",
        "positive": "#10B981",
        "negative": "#F43F5E",
        "warning":  "#F59E0B",
        "series":   ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#06B6D4", "#8B5CF6"],
    },
    "theme": {
        "bg_page":        "#111827",
        "bg_card":        "#1A2235",
        "bg_card_hover":  "#1F2940",
        "bg_sidebar":     "#0D1321",
        "border":         "#253350",
        "border_accent":  "#344568",
        "text_primary":   "#F0F4FF",
        "text_secondary": "#8B98B8",
        "text_muted":     "#4E5D7A",
    },
}

# Backward-compat aliases (used by the legacy dashboard.py)
COLORS = {
    "bg_page":       _DEFAULT_BRAND["theme"]["bg_page"],
    "bg_card":       _DEFAULT_BRAND["theme"]["bg_card"],
    "bg_card_hover": _DEFAULT_BRAND["theme"]["bg_card_hover"],
    "bg_sidebar":    _DEFAULT_BRAND["theme"]["bg_sidebar"],
    "border":        _DEFAULT_BRAND["theme"]["border"],
    "border_accent": _DEFAULT_BRAND["theme"]["border_accent"],
    "text_primary":  _DEFAULT_BRAND["theme"]["text_primary"],
    "text_secondary":_DEFAULT_BRAND["theme"]["text_secondary"],
    "text_muted":    _DEFAULT_BRAND["theme"]["text_muted"],
    "accent_indigo": "#6366F1",
    "accent_violet": "#818CF8",
    "accent_emerald":"#10B981",
    "accent_amber":  "#F59E0B",
    "accent_rose":   "#F43F5E",
    "accent_cyan":   "#06B6D4",
    "seq_low":       "#1A2235",
    "seq_high":      "#6366F1",
}
PALETTE = _DEFAULT_BRAND["colors"]["series"]


# ─────────────────────────────────────────────────────────────────────────────
# BRAND LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_brand(path: str = "brand.toml") -> dict:
    """
    Load brand config from a TOML file (relative to the project root).
    Falls back to _DEFAULT_BRAND if the file is missing or tomllib is unavailable.
    """
    brand_file = _ROOT / path
    if not brand_file.exists() or tomllib is None:
        return _DEFAULT_BRAND
    with open(brand_file, "rb") as f:
        data = tomllib.load(f)
    # Deep-merge with defaults so partial config files still work
    merged = _DEFAULT_BRAND.copy()
    for section in ("brand", "colors", "theme"):
        if section in data:
            merged[section] = {**_DEFAULT_BRAND.get(section, {}), **data[section]}
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# PAGE SETUP  (call once at the very top of each page)
# ─────────────────────────────────────────────────────────────────────────────

def configure_page(title: str, icon: str = "📊") -> dict:
    """
    Call once at the top of every page, before any other st.* call.
    Sets page config, loads brand, applies theme CSS and chrome hiding.
    Returns the brand dict — pass it to sidebar_header() and chart factories.
    """
    brand = load_brand()
    st.set_page_config(
        page_title=f"{title}  ·  {brand['brand']['name']}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme(brand)
    hide_chrome()
    return brand


# ─────────────────────────────────────────────────────────────────────────────
# THEME & CHROME
# ─────────────────────────────────────────────────────────────────────────────

def apply_theme(brand: dict) -> None:
    """
    Inject global CSS that applies the brand's dark theme and Inter typography
    consistently across all browsers. @import must be the very first CSS rule,
    so it is placed at the top of a dedicated style block before all other rules.
    """
    t = brand["theme"]
    c = brand["colors"]
    primary = c["primary"]

    # ── Block 1: font import (must be first rule) ──────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    /* Scope Inter to text-producing elements only.
       Deliberately excludes [class*="st-"] and bare span/div — those selectors
       match Streamlit's internal icon containers and override the Material
       Symbols font, causing icon glyphs to render as raw text. */
    html, body, .stApp, button, input, select, textarea,
    p, label, li, td, th, caption, blockquote {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Block 2: component theme + layout ─────────────────────────────────
    st.markdown(f"""
    <style>
    /* ── Page container ──────────────────────────────────────────────────── */
    .block-container {{
        padding-top: 0.25rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 100% !important;
    }}

    /* ── Card containers (st.container(border=True)) ─────────────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {t["bg_card"]} !important;
        border: 1px solid {t["border"]} !important;
        border-radius: 14px !important;
        overflow: hidden;
        transition: border-color 0.2s ease;
    }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        border-color: {t["border_accent"]} !important;
    }}

    /* ── Metric — inherits card background; no independent frame ─────────── */
    [data-testid="metric-container"] {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0.6rem 0.25rem 0.25rem 0.25rem;
        min-width: 0;
    }}

    /* Value — prevent clipping at any viewport width */
    [data-testid="metric-container"] [data-testid="stMetricValue"] > div {{
        font-size: clamp(1.1rem, 1.5vw, 1.65rem) !important;
        font-weight: 700 !important;
        white-space: nowrap;
        overflow: visible !important;
        text-overflow: unset !important;
        color: {t["text_primary"]} !important;
        line-height: 1.2;
    }}

    /* Label */
    [data-testid="metric-container"] label {{
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
        color: {t["text_secondary"]} !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
        margin-bottom: 0.25rem;
    }}

    /* Delta — base size/weight; colors set in Block 3 */
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {{
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        margin-top: 0.2rem;
        background: transparent !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {t["bg_sidebar"]} !important;
        border-right: 1px solid {t["border"]} !important;
    }}

    /* ── Dividers ────────────────────────────────────────────────────────── */
    hr {{
        border: none !important;
        border-top: 1px solid {t["border"]} !important;
        margin: 0.75rem 0 !important;
    }}

    /* ── Expander ────────────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        border: 1px solid {t["border"]} !important;
        border-radius: 14px !important;
        background: {t["bg_card"]} !important;
    }}

    /* ── Plotly: transparent background so card surface shows through ─────── */
    .js-plotly-plot .plotly .main-svg,
    .js-plotly-plot .plotly {{
        background: transparent !important;
    }}

    /* ── DataFrame ───────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {t["border"]} !important;
        border-radius: 14px !important;
        overflow: hidden;
    }}

    /* ── Column gaps — tighter to keep cards flush ───────────────────────── */
    [data-testid="stHorizontalBlock"] {{
        gap: 1rem !important;
    }}

    /* ── Multiselect tags ────────────────────────────────────────────────── */
    [data-testid="stMultiSelectTag"] {{
        background: {t["border_accent"]} !important;
        color: {t["text_primary"]} !important;
        border-radius: 4px !important;
    }}

    /* ── Section header utility classes ──────────────────────────────────── */
    .section-title {{
        font-size: 0.95rem;
        font-weight: 600;
        color: {t["text_primary"]};
        letter-spacing: -0.01em;
        line-height: 1.3;
    }}
    .section-subtitle {{
        font-size: 0.78rem;
        color: {t["text_secondary"]};
        margin-top: 0.2rem;
    }}
    .section-rule {{
        height: 1px;
        background: {t["border"]};
        margin-top: 0.6rem;
        margin-bottom: 1.1rem;
    }}

    /* ── Brand header in sidebar ─────────────────────────────────────────── */
    .brand-block {{
        padding: 1.5rem 1rem 1rem 1rem;
    }}
    .brand-name {{
        font-size: 1.05rem;
        font-weight: 600;
        color: {t["text_primary"]};
        letter-spacing: -0.02em;
        line-height: 1.2;
    }}
    .brand-tagline {{
        font-size: 0.7rem;
        color: {t["text_secondary"]};
        margin-top: 0.2rem;
        letter-spacing: 0.02em;
    }}
    .brand-accent-dot {{
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: {primary};
        margin-right: 0.4rem;
        vertical-align: middle;
        position: relative;
        top: -1px;
    }}

    /* ── Sidebar: collapse nav/brand gap ─────────────────────────────────── */
    [data-testid="stSidebarContent"] {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        padding-top: 0 !important;
    }}
    [data-testid="stSidebarNav"] {{
        flex: 0 0 auto !important;
        padding-top: 0.25rem !important;
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Block 3: delta colors + sidebar nav ───────────────────────────────
    st.markdown(f"""
    <style>
    /* ── Metric delta: brand positive/negative, no background shading ─────── */
    [data-testid="stMetricDelta"] > div {{
        background: transparent !important;
        padding: 0 !important;
        border-radius: 0 !important;
    }}
    /* Positive delta: up arrow + value text */
    [data-testid="stMetricDelta"]:has([data-testid="stMetricDeltaIcon-Up"]) {{
        color: {c["positive"]} !important;
    }}
    [data-testid="stMetricDelta"] [data-testid="stMetricDeltaIcon-Up"] {{
        color: {c["positive"]} !important;
        fill: {c["positive"]} !important;
    }}
    /* Negative delta: down arrow + value text */
    [data-testid="stMetricDelta"]:has([data-testid="stMetricDeltaIcon-Down"]) {{
        color: {c["negative"]} !important;
    }}
    [data-testid="stMetricDelta"] [data-testid="stMetricDeltaIcon-Down"] {{
        color: {c["negative"]} !important;
        fill: {c["negative"]} !important;
    }}

    /* ── Sidebar navigation links ─────────────────────────────────────────── */
    [data-testid="stSidebarNavLink"] {{
        border-radius: 8px !important;
        padding: 0.45rem 0.8rem !important;
        margin: 0.1rem 0.5rem !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.6rem !important;
        transition: background 0.15s ease;
    }}
    [data-testid="stSidebarNavLink"]:hover {{
        background: {t["border"]} !important;
    }}
    [data-testid="stSidebarNavLink"][aria-current="page"] {{
        background: {t["bg_card"]} !important;
        border-left: 2px solid {primary} !important;
    }}
    [data-testid="stSidebarNavLink"] p {{
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: {t["text_secondary"]} !important;
        margin: 0 !important;
        line-height: 1 !important;
    }}
    [data-testid="stSidebarNavLink"][aria-current="page"] p {{
        color: {t["text_primary"]} !important;
        font-weight: 600 !important;
    }}
    /* Icon area — target only the Material icon test-id to avoid touching
       the font-family of icon glyph containers (which would break rendering) */
    [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
        width: 18px !important;
        height: 18px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        color: {t["text_secondary"]} !important;
        flex-shrink: 0 !important;
    }}
    [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{
        color: {primary} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def hide_chrome() -> None:
    """
    Remove Streamlit default UI chrome for a clean, app-like appearance.
    We hide specific children of the header rather than zeroing its height —
    this preserves the sidebar expand/collapse toggle button.
    Works on Streamlit Community Cloud and local installs.
    """
    st.markdown("""
    <style>
    /* Hamburger menu */
    #MainMenu { visibility: hidden !important; }
    /* Footer */
    footer { visibility: hidden !important; }
    /* Minimal header — keeps the sidebar toggle clickable at the smallest
       height that still renders the button without clipping. */
    header[data-testid="stHeader"] {
        height: 2rem !important;
        min-height: 0 !important;
        background: transparent !important;
        border-bottom: none !important;
    }
    /* Toolbar, deploy button, decoration */
    [data-testid="stToolbarActions"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    .stDeployButton              { display: none !important; }
    /* Ensure sidebar collapse/expand toggle always renders correctly */
    [data-testid="collapsedControl"],
    button[kind="header"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    /* Logo size override — target every layer st.logo() could render into */
    [data-testid="stLogo"],
    [data-testid="stLogoSpacer"],
    [data-testid="stSidebarHeader"] img,
    [data-testid="stSidebarHeader"] > * {
        height: 90px !important;
        max-height: none !important;
        width: auto !important;
        max-width: 100% !important;
    }
    [data-testid="stSidebarHeader"] {
        height: auto !important;
        padding: 0.75rem 1rem 0.25rem 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CARD PRIMITIVE
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def card():
    """
    Context manager that wraps any Streamlit content in a branded card container.
    Uses st.container(border=True) so the card is styled globally via CSS
    targeting [data-testid="stVerticalBlockBorderWrapper"].

    Usage:
        with card():
            st.metric(...)

        with card():
            col_l, col_r = st.columns(2)
            with col_l: ...
            with col_r: ...
    """
    with st.container(border=True):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def sidebar_header(brand: dict) -> None:
    """No-op — logo is now handled by st.logo() in app.py. Kept for API compatibility."""
    pass


def sidebar_nav() -> None:
    """
    No-op — navigation is now handled by st.navigation() in app.py.
    Streamlit 1.44+ renders the nav automatically in the sidebar.
    Kept for API compatibility; safe to call but does nothing.
    """
    pass


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def render_header(
    title: str,
    subtitle: str,
    brand: dict,
    icon: str | None = None,
    context: str = "",
) -> None:
    """
    Render an inline page header (title + subtitle + active filter context).
    Sits at the top of the content area, scrolls naturally with the page.
    No sticky positioning — avoids Streamlit toolbar offset hacks entirely.
    The brand is shown in the sidebar via sidebar_header(); no badge here.
    """
    t     = brand.get("theme", {})
    txt_p = t.get("text_primary",   "#F8FAFC")
    txt_s = t.get("text_secondary", "#CBD5E1")
    txt_m = t.get("text_muted",     "#64748B")
    border = t.get("border",        "#334155")

    icon_html = (
        f'<span style="margin-right:0.5rem;display:inline-flex;align-items:center;'
        f'vertical-align:middle;">{svg_icon(icon, 22)}</span>'
        if icon else ""
    )
    context_html = (
        f'<div style="font-size:0.72rem;color:{txt_m};margin-top:0.35rem;line-height:1.4;">{context}</div>'
        if context else ""
    )

    st.markdown(
        f'<div style="padding:0.9rem 0 1rem 0;border-bottom:1px solid {border};margin-bottom:1.5rem;">'
        f'  <div style="display:flex;align-items:center;">'
        f'    {icon_html}'
        f'    <span style="font-size:1.85rem;font-weight:700;color:{txt_p};line-height:1.1;letter-spacing:-0.02em;">{title}</span>'
        f'  </div>'
        f'  <div style="font-size:0.875rem;color:{txt_s};margin-top:0.35rem;line-height:1.5;max-width:680px;">{subtitle}</div>'
        f'  {context_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "", brand_tag: dict | None = None) -> None:
    """
    Render a clean section header with an optional subtitle and a thin rule.
    Call this before each major content section instead of st.subheader().
    Pass brand_tag=brand to render a small brand line above the title.
    """
    brand = st.session_state.get("brand", _DEFAULT_BRAND)
    t = brand["theme"]

    brand_html = ""
    if brand_tag:
        name    = brand_tag.get("brand", {}).get("name", "")
        tagline = brand_tag.get("brand", {}).get("tagline", "")
        primary = brand_tag.get("colors", {}).get("primary", "#6366F1")
        brand_html = (
            f'<div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.35rem;">'
            f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
            f'background:{primary};flex-shrink:0;"></span>'
            f'<span style="font-size:0.72rem;font-weight:600;color:{t["text_primary"]};'
            f'letter-spacing:0.01em;">{name}</span>'
            + (f'<span style="font-size:0.72rem;color:{t["text_muted"]};margin-left:0.1rem;">· {tagline}</span>' if tagline else "")
            + f'</div>'
        )

    sub_html = f'<div class="section-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div>'
        f'{brand_html}'
        f'<div class="section-title">{title}</div>'
        f'{sub_html}'
        f'<div class="section-rule"></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def kpi_row(metrics: list[dict]) -> None:
    """
    Render a row of KPI metric cards.

    Each dict in metrics:
        label : str           — card label (supports emoji prefix)
        value : str           — pre-formatted display value
        delta : str | None    — period-over-period change, e.g. "+5.2%" or "-3.1%"
        help  : str | None    — tooltip text

    Example:
        kpi_row([
            {"label": "💰 Revenue",  "value": "R$ 13.6M", "delta": "+8.3%", "help": None},
            {"label": "🛒 Orders",   "value": "96.5K",    "delta": "-1.2%", "help": None},
        ])
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.metric(
                    label=m["label"],
                    value=m["value"],
                    delta=m.get("delta"),
                    help=m.get("help"),
                )


# ─────────────────────────────────────────────────────────────────────────────
# SVG ICON HELPERS  (Lucide-compatible, stroke-based, 24 × 24 viewBox)
# ─────────────────────────────────────────────────────────────────────────────

# Inner SVG content for each icon (no <svg> wrapper — added by svg_icon()).
# All shapes use stroke="currentColor" / fill="none" inherited from the wrapper.
_LUCIDE_ICONS: dict[str, str] = {
    "bar-chart-2": (
        '<line x1="18" y1="20" x2="18" y2="10"/>'
        '<line x1="12" y1="20" x2="12" y2="4"/>'
        '<line x1="6"  y1="20" x2="6"  y2="14"/>'
    ),
    "trending-up": (
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
        '<polyline points="17 6 23 6 23 12"/>'
    ),
    "users": (
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "truck": (
        '<rect x="1" y="3" width="15" height="13"/>'
        '<polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>'
        '<circle cx="5.5"  cy="18.5" r="2.5"/>'
        '<circle cx="18.5" cy="18.5" r="2.5"/>'
    ),
    "layout-dashboard": (
        '<rect x="3" y="3" width="7" height="7"/>'
        '<rect x="14" y="3" width="7" height="7"/>'
        '<rect x="14" y="14" width="7" height="7"/>'
        '<rect x="3"  y="14" width="7" height="7"/>'
    ),
    "dollar-sign": (
        '<line x1="12" y1="1" x2="12" y2="23"/>'
        '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
    ),
    "activity": (
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
    ),
    "package": (
        '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>'
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '<polyline points="3.27 6.96 12 12.01 20.73 6.96"/>'
        '<line x1="12" y1="22.08" x2="12" y2="12"/>'
    ),
}


def svg_icon(name: str, size: int = 16, color: str | None = None) -> str:
    """
    Return an inline SVG string for a Lucide-style monochrome icon.
    Embed inside st.markdown(unsafe_allow_html=True) blocks.

    name  : key from _LUCIDE_ICONS
    size  : pixel size applied to both width and height (default 16)
    color : hex string; defaults to text_secondary from the active brand
    """
    if color is None:
        brand = st.session_state.get("brand", _DEFAULT_BRAND)
        color = brand["theme"]["text_secondary"]
    content = _LUCIDE_ICONS.get(name, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:middle;flex-shrink:0;display:inline-block;">'
        f'{content}</svg>'
    )


def chart_card(title: str, fig: go.Figure, subtitle: str = "", key: str | None = None) -> None:
    """
    Render a chart inside a branded card.
    Title is rendered as styled HTML above the chart (not embedded in Plotly),
    giving consistent typography regardless of chart type.
    """
    brand = st.session_state.get("brand", _DEFAULT_BRAND)
    t = brand["theme"]

    with st.container(border=True):
        # Title and subtitle as a Plotly annotation — part of the figure, so
        # they survive fullscreen. Positioned in the top margin above the plot
        # area (paper y=1, yanchor="bottom"), giving full HTML styling control
        # independent of Plotly's built-in title system.
        annotation_text = f"<b>{title}</b>"
        if subtitle:
            annotation_text += (
                f"<br><span style='font-size:11px;font-weight:400;"
                f"color:{t['text_muted']};'>{subtitle}</span>"
            )

        fig.update_layout(
            title=dict(text=""),                    # clear any built-in title
            margin=dict(t=60 if subtitle else 44),  # headroom for annotation
        )
        fig.add_annotation(
            text=annotation_text,
            x=0, y=1,
            xref="paper", yref="paper",
            xanchor="left", yanchor="bottom",
            showarrow=False,
            font=dict(
                size=14,
                color=t["text_primary"],
                family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            ),
            align="left",
        )
        st.plotly_chart(fig, use_container_width=True, key=key)


# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY LAYOUT DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

def plotly_layout(
    brand: dict | None = None,
    height: int = 320,
    margin: dict | None = None,
    show_legend: bool = True,
    legend_top: bool = True,
    hovermode: str = "closest",
) -> dict:
    """
    Return a Plotly layout dict that matches the active brand's dark theme.
    Backgrounds are transparent so the card surface shows through.

    Pass directly to fig.update_layout(**plotly_layout(brand, ...)).
    """
    brand = brand or _DEFAULT_BRAND
    t = brand["theme"]

    _margin = margin or dict(l=12, r=12, t=36 if legend_top else 16, b=48)
    legend_cfg = (
        dict(
            orientation="h",
            y=1.12 if legend_top else -0.24,
            x=0.5,
            xanchor="center",
            font=dict(size=11, color=t["text_secondary"]),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        )
        if show_legend
        else dict(visible=False)
    )

    return dict(
        height=height,
        margin=_margin,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode=hovermode,
        xaxis=dict(
            tickfont=dict(size=10, color=t["text_secondary"]),
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.06)",
            tickangle=0,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=10, color=t["text_secondary"]),
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(0,0,0,0)",
            showgrid=True,
            zeroline=False,
        ),
        font=dict(
            color=t["text_primary"],
            family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            size=12,
        ),
        legend=legend_cfg,
        hoverlabel=dict(
            bgcolor=t["bg_card"],
            bordercolor=t["border_accent"],
            font=dict(color=t["text_primary"], size=12),
            namelength=-1,
        ),
    )


def apply_plotly_layout(fig: go.Figure, brand: dict | None = None, **kwargs) -> go.Figure:
    """Convenience wrapper: apply brand-aware dark theme to an existing figure."""
    fig.update_layout(**plotly_layout(brand=brand, **kwargs))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CHART FACTORY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def dual_axis_bar_line(
    df,
    x: str,
    bar_col: str,
    line_col: str,
    bar_label: str = "Bar",
    line_label: str = "Line",
    bar_color: str | None = None,
    line_color: str | None = None,
    height: int = 320,
    brand: dict | None = None,
) -> go.Figure:
    """
    Dual-axis chart: bars on primary Y, line on secondary Y.
    Ideal for Revenue + Orders over time.
    """
    brand = brand or _DEFAULT_BRAND
    c = brand["colors"]
    t = brand["theme"]
    bar_color  = bar_color  or c["primary"]
    line_color = line_color or c["warning"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x], y=df[bar_col], name=bar_label,
        marker_color=bar_color,
        marker_line_width=0,
        yaxis="y1",
        hovertemplate=f"<b>%{{x}}</b><br>{bar_label}: %{{y:,.0f}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df[x], y=df[line_col], name=line_label,
        mode="lines+markers",
        line=dict(color=line_color, width=2.5),
        marker=dict(size=5, color=line_color),
        yaxis="y2",
        hovertemplate=f"<b>%{{x}}</b><br>{line_label}: %{{y:,.0f}}<extra></extra>",
    ))

    layout = plotly_layout(brand=brand, height=height, hovermode="closest")
    layout["yaxis2"] = dict(
        overlaying="y", side="right", showgrid=False,
        tickfont=dict(size=10, color=t["text_secondary"]),
        linecolor="rgba(0,0,0,0)",
        zeroline=False,
    )
    fig.update_layout(**layout)
    return fig


def horizontal_bar(
    df,
    x: str,
    y: str,
    x_label: str = "",
    y_label: str = "",
    height: int = 320,
    brand: dict | None = None,
) -> go.Figure:
    """
    Horizontal bar chart with a sequential color scale (e.g. Top Categories).
    Bars are sorted ascending so the highest value appears at the top.
    x_label / y_label: human-readable axis titles (default "" suppresses coded column names).
    """
    brand = brand or _DEFAULT_BRAND
    c = brand["colors"]

    seq_low  = "#1A3A6B"   # dark end of sequential scale
    seq_high = c["primary"]

    fig = px.bar(
        df, x=x, y=y, orientation="h",
        color=x,
        color_continuous_scale=[[0, seq_low], [1, seq_high]],
        # Override px auto-labels so raw column names never appear on axes
        labels={x: x_label, y: y_label},
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>",
    )
    layout = plotly_layout(
        brand=brand, height=height,
        margin=dict(l=12, r=12, t=10, b=10),
        show_legend=False,
        hovermode="closest",
    )
    layout["yaxis"]["categoryorder"] = "total ascending"
    layout["xaxis"]["tickangle"] = 0
    fig.update_layout(coloraxis_showscale=False, **layout)
    return fig


def stacked_bar(
    df,
    x: str,
    series: list[tuple[str, str, str]],   # [(col, label, hex_color), …]
    height: int = 280,
    x_label: str = "",
    brand: dict | None = None,
) -> go.Figure:
    """
    Stacked bar chart.
    series = list of (column_name, display_label, hex_color)
    x_label: human-readable x-axis title (default "" suppresses coded column name).
    """
    brand = brand or _DEFAULT_BRAND
    fig = go.Figure()
    for col, label, color in series:
        fig.add_trace(go.Bar(
            x=df[x], y=df[col], name=label,
            marker_color=color,
            marker_line_width=0,
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:,.0f}}<extra></extra>",
        ))
    layout = plotly_layout(brand=brand, height=height, hovermode="x unified")
    if x_label:
        layout["xaxis"]["title"] = dict(text=x_label, font=dict(size=10))
    fig.update_layout(barmode="stack", **layout)
    return fig


def line_chart(
    df,
    x: str,
    y: str,
    color: str | None = None,
    height: int = 280,
    brand: dict | None = None,
    y_label: str = "",
    x_label: str = "",
) -> go.Figure:
    """Single-series line chart with markers and unified hover.
    y_label / x_label: human-readable axis titles shown on the chart axes.
    """
    brand = brand or _DEFAULT_BRAND
    color = color or brand["colors"]["accent"]
    y_fmt = y_label or y

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y],
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        hovertemplate=f"<b>%{{x}}</b><br>{y_fmt}: %{{y:,.2f}}<extra></extra>",
        showlegend=False,
    ))
    layout = plotly_layout(brand=brand, height=height, show_legend=False, hovermode="x unified")
    if y_label:
        layout["yaxis"]["title"] = dict(text=y_label, font=dict(size=10))
    if x_label:
        layout["xaxis"]["title"] = dict(text=x_label, font=dict(size=10))
    fig.update_layout(**layout)
    return fig


def multi_line_chart(
    df,
    x: str,
    lines: list[tuple[str, str, str, str]],  # [(col, label, color, dash), …]
    height: int = 280,
    brand: dict | None = None,
    y_title: str = "",
) -> go.Figure:
    """
    Multi-series line chart with unified hover.
    lines = [(col_name, display_label, hex_color, dash_style), …]
    dash_style: "solid" | "dash" | "dot" | "dashdot"
    """
    brand = brand or _DEFAULT_BRAND
    fig = go.Figure()
    for col, label, color, dash in lines:
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col],
            name=label,
            mode="lines+markers",
            line=dict(color=color, width=2.5, dash=dash),
            marker=dict(size=5 if dash == "solid" else 0, color=color),
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}<extra></extra>",
        ))
    layout = plotly_layout(brand=brand, height=height, hovermode="x unified")
    if y_title:
        layout["yaxis"]["title"] = dict(text=y_title, font=dict(size=11))
    fig.update_layout(**layout)
    return fig


def donut_chart(
    df,
    names: str,
    values: str,
    height: int = 280,
    brand: dict | None = None,
) -> go.Figure:
    """
    Donut chart with labels shown outside the segments.
    Legend hidden by default to avoid small-text clutter.
    """
    brand = brand or _DEFAULT_BRAND
    t = brand["theme"]
    palette = brand["colors"]["series"]

    fig = px.pie(
        df, names=names, values=values,
        color_discrete_sequence=palette,
        hole=0.48,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        textfont=dict(size=11, color=t["text_primary"]),
        outsidetextfont=dict(size=10, color=t["text_secondary"]),
        hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>%{percent}<extra></extra>",
    )
    fig.update_layout(
        showlegend=False,
        **plotly_layout(
            brand=brand, height=height, show_legend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            hovermode="closest",
        ),
    )
    return fig


def histogram(
    df,
    x: str,
    nbins: int = 40,
    color: str | None = None,
    height: int = 280,
    brand: dict | None = None,
    x_label: str = "",
) -> go.Figure:
    """Distribution histogram."""
    brand = brand or _DEFAULT_BRAND
    color = color or brand["colors"]["series"][4]   # purple by default
    x_fmt = x_label or x

    # Suppress px auto-label; we'll apply x_label explicitly if provided
    fig = px.histogram(df, x=x, nbins=nbins, color_discrete_sequence=[color],
                       labels={x: x_fmt})
    fig.update_traces(
        hovertemplate=f"{x_fmt}: %{{x:,.0f}}<br>Count: %{{y:,.0f}}<extra></extra>",
    )
    layout = plotly_layout(brand=brand, height=height, show_legend=False)
    if x_label:
        layout["xaxis"]["title"] = dict(text=x_label, font=dict(size=10))
    fig.update_layout(bargap=0.04, **layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# NUMBER FORMATTERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_currency(value: float, symbol: str = "R$", decimals: int = 0) -> str:
    """
    Format a monetary value so it always fits in a metric card.
    Auto-abbreviates large numbers (K / M).

    Examples:
        fmt_currency(13_591_644)        →  "R$ 13.6M"
        fmt_currency(159.75, decimals=2)→  "R$ 159.75"
        fmt_currency(1_230)             →  "R$ 1.2K"
    """
    if value >= 1_000_000:
        return f"{symbol} {value / 1_000_000:.1f}M"
    elif value >= 10_000:
        return f"{symbol} {value / 1_000:.1f}K"
    elif decimals:
        return f"{symbol} {value:,.{decimals}f}"
    else:
        return f"{symbol} {value:,.0f}"


def fmt_number(value: float) -> str:
    """Format an integer count with auto K/M abbreviation."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 10_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{int(value):,}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a percentage value."""
    return f"{value:.{decimals}f}%"


def pct_delta(current: float, prev: float | None) -> str | None:
    """
    Compute a period-over-period percentage delta string.
    Returns None when prev is zero or unavailable (avoids division by zero).

    Example: pct_delta(110, 100) → "+10.0%"
    """
    if prev is None or prev == 0:
        return None
    change = ((current - prev) / abs(prev)) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"
