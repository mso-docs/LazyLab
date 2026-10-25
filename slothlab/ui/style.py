"""Local styles shared by every appearance preference; no external assets."""
BASE_CSS = r'''
.stApp, [data-testid="stHeader"] { background:var(--lab-bg); color:var(--lab-ink); }
[data-testid="stMainBlockContainer"] { max-width:1480px; padding-top:2.1rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:var(--lab-panel); border-right:1px solid var(--lab-line); }
h1,h2,h3 { color:var(--lab-ink); letter-spacing:-.035em; }
h1 { font-weight:750; }
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], [data-testid="stMetricValue"], [data-testid="stSidebar"] label { color:var(--lab-ink); }
[data-testid="stCaptionContainer"], [data-testid="stMetricLabel"] { color:var(--lab-muted); }
[data-testid="stMetric"], [data-testid="stForm"] { background:var(--lab-panel); border:1px solid var(--lab-line); border-radius:14px; padding:1rem 1.1rem; }
[data-testid="stMetricValue"] { font-size:1.9rem; font-weight:650; }
[data-testid="stForm"] { padding:1.5rem; }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"]>div, [data-baseweb="textarea"], [data-baseweb="popover"] [role="listbox"] { background:var(--lab-field); color:var(--lab-ink); }
input, textarea, [data-baseweb="select"] input { color:var(--lab-ink)!important; caret-color:var(--lab-ink); }
[data-baseweb="menu"], [role="option"] { background:var(--lab-panel); color:var(--lab-ink); }
[data-testid="stCode"], [data-testid="stCode"] pre, [data-testid="stTable"] { background:var(--lab-panel); color:var(--lab-ink); }
[data-testid="stTable"] th, [data-testid="stTable"] td { color:var(--lab-ink); border-color:var(--lab-line); }
.stTabs [data-baseweb="tab-list"] { gap:1.6rem; border-bottom:1px solid var(--lab-line); }
.stTabs [data-baseweb="tab"] { font-weight:600; color:var(--lab-muted); padding-bottom:1rem; }
.stTabs [aria-selected="true"] { color:var(--lab-accent); }
.stTabs [data-baseweb="tab-highlight"] { background:var(--lab-accent); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button { border-radius:9px; background:var(--lab-panel); color:var(--lab-ink); border-color:var(--lab-line); }
.stButton>button[kind="primary"], .stFormSubmitButton>button[kind="primary"] { background:#16765e; border-color:#16765e; color:#fff; }
a { color:var(--lab-accent); }
.lab-brand { font-size:1.45rem; font-weight:750; color:var(--lab-ink); letter-spacing:-.04em; margin-bottom:0; }
.lab-brand span { color:var(--lab-accent); }
.lab-brand-sub { color:var(--lab-muted); font-size:.76rem; margin:0 0 2rem; }
.lab-eyebrow { color:var(--lab-accent); font-size:.73rem; font-weight:750; letter-spacing:.15em; margin-bottom:.55rem; }
.lab-hero { background:#18343e; border-radius:18px; padding:1.7rem 2rem; color:#d3e3e6; margin-bottom:1.6rem; }
.lab-hero h2 { color:#f0f8f5; font-size:1.75rem; margin:0 0 .6rem; font-weight:650; }
.lab-hero p { color:#d0e0e3; font-size:.94rem; margin:0; max-width:760px; }
.lab-pill { display:inline-block; border:1px solid #65818a; border-radius:30px; padding:.23rem .6rem; color:#bce9ce; font-size:.7rem; margin-bottom:.7rem; }
.lab-empty { text-align:center; background:var(--lab-panel); border:1px dashed var(--lab-line); border-radius:16px; padding:3rem 1.5rem; margin:1rem 0; }
.lab-empty h3 { color:var(--lab-ink); font-size:1.35rem; }
.lab-empty p { color:var(--lab-muted); }
.lab-footer { color:var(--lab-muted); font-size:.74rem; margin-top:2rem; padding-top:1rem; border-top:1px solid var(--lab-line); }
.lab-lesson { background:var(--lab-soft); border:1px solid var(--lab-line); border-radius:16px; padding:1.25rem 1.5rem; margin-bottom:1rem; }
.lab-lesson p { color:var(--lab-muted); }
@media (max-width:760px) { [data-testid="stMainBlockContainer"] { padding-top:1rem; } .lab-hero { padding:1.3rem; } }
'''
# Compatibility for consumers importing the former light-only constant.
from slothlab.ui.themes import theme_css
STYLE = theme_css('Light')
