"""Visual theme for the Streamlit UI, matching the ProjectPilot web frontend."""

import streamlit as st

THEME_CSS = """
<style>
:root {
  --pp-bg: #080A0F; --pp-surface: #111722; --pp-border: #202938;
  --pp-blue: #5799F5; --pp-green: #51C995; --pp-purple: #B18AFF;
  --pp-text: #E8ECF4; --pp-muted: #A3AEC2;
}
.stApp {
  background:
    radial-gradient(900px 520px at 8% -8%, rgba(87,153,245,.13), transparent 70%),
    radial-gradient(700px 480px at 96% 6%, rgba(177,138,255,.09), transparent 70%),
    radial-gradient(900px 500px at 50% 112%, rgba(81,201,149,.08), transparent 70%),
    var(--pp-bg);
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 1180px; }

h1, h2, h3 { letter-spacing: -0.03em; font-weight: 600; }
.pp-hero h1 {
  font-size: clamp(2.2rem, 4vw, 3.4rem); line-height: 1.05; margin: 0 0 .6rem;
}
.pp-grad {
  background: linear-gradient(100deg, #5799F5, #51C995);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.pp-hero p { color: var(--pp-muted); max-width: 60ch; font-size: 1.05rem; }

/* Sidebar as a glass panel */
section[data-testid="stSidebar"] {
  background: rgba(17,23,34,.85);
  border-right: 1px solid var(--pp-border);
}

/* Bordered containers become glass cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 18px;
  border: 1px solid rgba(120,140,175,.16);
  background: linear-gradient(180deg, rgba(23,31,46,.72), rgba(14,19,29,.62));
  transition: border-color .25s ease, transform .25s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: rgba(87,153,245,.4);
}

/* Primary button */
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
  color: #06080C; font-weight: 600; border: 0; border-radius: 999px;
  background: linear-gradient(100deg, #5799F5, #51C995);
  box-shadow: 0 10px 30px -10px rgba(87,153,245,.65);
  transition: transform .25s ease, box-shadow .25s ease;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
  transform: translateY(-2px); color: #06080C;
  box-shadow: 0 16px 38px -10px rgba(81,201,149,.55);
}

/* Inputs */
div[data-baseweb="select"] > div, .stTextInput input {
  background: rgba(8,10,15,.6) !important; border-color: var(--pp-border) !important;
  border-radius: 10px !important;
}
.stTextInput input:focus { border-color: var(--pp-blue) !important; box-shadow: 0 0 0 3px rgba(87,153,245,.2) !important; }

div[data-testid="stExpander"] { border-radius: 12px; border-color: var(--pp-border); }
div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--pp-border); }
div[data-testid="stAlert"] { border-radius: 14px; border: 1px solid rgba(87,153,245,.25); background: rgba(87,153,245,.08); }
footer { visibility: hidden; }
</style>
"""

HERO_HTML = """
<div class="pp-hero">
  <h1>Find the project that <span class="pp-grad">fits your skills</span>,<br>goals and timeline.</h1>
  <p>Find project ideas that match your domain, skill level, interests,
  available time, and preferred programming language.</p>
</div>
"""


def apply_theme() -> None:
    """Inject the shared dark theme styles into the Streamlit page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def show_hero() -> None:
    """Render the page header."""
    st.markdown(HERO_HTML, unsafe_allow_html=True)
