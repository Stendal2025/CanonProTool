import json
import logging
import importlib
import streamlit as st
import streamlit.components.v1 as components
import requests

from config import SHUTTERS_ALL, CITY_COORDS
from utils import get_place_name
from i18n import _, render_language_selector, SUPPORTED_LANGUAGES
from database import init_db, get_setting, get_api_key, track_usage, get_top_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("canon_pro")
logger.info("App started")

init_db()


if st.session_state.get("force_refresh_weather", False):
    st.cache_data.clear()
    st.session_state.force_refresh_weather = False

SHORTCUT_MAP = {
    "1": "⚙️ Belichtung", "2": "🕶️ ND Rechner", "3": "📐 Schärfentiefe",
    "4": "🌍 Astro & Wetter Dashboard", "5": "🌙 Mond & Milchstraße",
    "6": "🌊 Gezeiten & Tide-Rechner", "7": "📍 GPS-Standort",
    "8": "📝 Planer", "9": "🎨 Filter-Sim",
}
shortcut = st.query_params.get("shortcut")
if shortcut:
    st.query_params.clear()
    if shortcut in SHORTCUT_MAP:
        st.session_state.tool = SHORTCUT_MAP[shortcut]
        st.rerun()

SW_CODE = r"""
const CACHE_NAME="canon-pro-tool-v1";const A=["/","https://cdn-icons-png.flaticon.com/512/2983/2983796.png","https://openweathermap.org/img/wn/01d@2x.png","https://openweathermap.org/img/wn/02d@2x.png","https://openweathermap.org/img/wn/03d@2x.png","https://openweathermap.org/img/wn/04d@2x.png","https://openweathermap.org/img/wn/10d@2x.png"];self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE_NAME).then(c=>c.addAll(A)));self.skipWaiting()});self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==CACHE_NAME).map(x=>caches.delete(x)))));self.clients.claim()});self.addEventListener("fetch",e=>{e.respondWith(caches.match(e.request).then(c=>fetch(e.request).then(r=>{let a=r.clone();caches.open(CACHE_NAME).then(ca=>ca.put(e.request,a));return r}).catch(()=>c)))});
"""

components.html(f"""
<meta name="theme-color" content="#1F6FEB">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Canon Pro">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2983/2983796.png">
<script>
if('serviceWorker'in navigator){{
navigator.serviceWorker.register(URL.createObjectURL(new Blob([{json.dumps(SW_CODE)}],{{type:'application/javascript'}})))
.then(()=>console.log('SW registered')).catch(()=>console.log('SW not supported'));
}}
const savedTheme=localStorage.getItem('canon_theme')||'dark';
document.documentElement.setAttribute('data-theme',savedTheme);
document.addEventListener('keydown',function(e){{
if(e.ctrlKey&&e.key>='1'&&e.key<='9'){{
const url=new URL(window.location.href);
url.searchParams.set('shortcut',e.key);
window.location.href=url.toString();
}}
}});
</script>
""", height=0)

st.set_page_config(page_title=_("app.title"), page_icon="📷", layout="wide", initial_sidebar_state="expanded")

OW_STATUS = "✅" if get_api_key("OPENWEATHER_API_KEY") else "❌"
WT_STATUS = "✅" if get_api_key("WORLD_TIDES_API_KEY") else "❌"
if not get_api_key("OPENWEATHER_API_KEY") or not get_api_key("WORLD_TIDES_API_KEY"):
    st.warning(f"🔑 **{_('env.keys_missing')}**\n\n🌤️ OpenWeatherMap: {OW_STATUS} · 🌊 WorldTides: {WT_STATUS}\n\n👉 Gehe zu **⚙️ Einstellungen** in der Seitenleiste, um Keys einzugeben.")


def render_status_bar():
    gps = st.session_state.get("gps_coords")
    loc_display = _("app.status.gps_not_set")
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            place_name = get_place_name(lat, lon)
            loc_display = f"📍 {place_name}" if place_name else f"📍 {lat:.2f}, {lon:.2f}"
        except (ValueError, TypeError, KeyError):
            loc_display = str(gps) if gps else _("app.status.gps_not_set")
    else:
        loc_display = str(gps) if gps else _("app.status.gps_not_set")
    temp, desc = "--", _("app.status.weather_waiting")
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            key = st.secrets.get("OPENWEATHER_API_KEY")
            if key:
                r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&lang=de", timeout=3)
                if r.status_code == 200:
                    d = r.json()
                    temp = f"{d['main']['temp']:.1f}°C"
                    desc = d['weather'][0]['description'].capitalize()
        except (requests.RequestException, KeyError, ValueError):
            temp, desc = "--", _("app.status.weather_na")
    st.markdown(f"<div style='background:{TC['bg2']};padding:10px;margin-bottom:15px;border-radius:8px;border:1px solid {TC['border']};'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([3, 2.5, 2.5, 1])
    c1.markdown(f"{loc_display}<br><small style='color:{TC['text2']};font-size:11px;'>{gps if gps and ',' in str(gps) else ''}</small>", unsafe_allow_html=True)
    c2.markdown(f"☁️ **{_('app.status.weather')}**<br><small style='color:{TC['text2']}'>{temp} | {desc}</small>", unsafe_allow_html=True)
    c3.markdown(f"📷 **{_('app.status.status')}**<br><small style='color:{TC['text2']}'>{_('app.status.live')}</small>", unsafe_allow_html=True)
    if c4.button("🔄", use_container_width=True, key="sb_refresh"):
        st.cache_data.clear()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"""
<style>
  :root {{
    --bg-primary: {TC["bg"]};
    --bg-secondary: {TC["bg2"]};
    --text-primary: {TC["text"]};
    --text-secondary: {TC["text2"]};
    --border-color: {TC["border"]};
    --card-bg: {TC["card"]};
    --accent: #1F6FEB;
    --accent-hover: #58A6FF;
  }}
  .main .block-container {{ background-color: var(--bg-primary); color: var(--text-primary); }}
  h1, h2, h3 {{ color: var(--accent-hover); }}
  .stButton>button {{ background-color: var(--accent); color: white; border-radius: 8px; border: none; padding: 10px 24px; font-weight: bold; min-height: 48px; }}
  .stButton>button:hover {{ background-color: var(--accent-hover); }}
  .stButton>button:focus-visible {{ outline: 3px solid var(--accent-hover); outline-offset: 2px; }}
  a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {{ outline: 3px solid var(--accent-hover); outline-offset: 2px; }}
  input, select, textarea {{ font-size: 16px !important; min-height: 48px !important; }}
  .stMarkdown, .stText {{ font-size: 15px; line-height: 1.6; }}
  section[data-testid="stSidebar"] {{ min-width: 240px; background-color: {TC['bg2']}; }}
  @media (max-width: 768px) {{
    .main .block-container {{ padding: 1rem !important; padding-top: 2rem !important; }}
    section[data-testid="stSidebar"] {{ width: 280px !important; }}
  }}
  @media (min-width: 769px) {{ section[data-testid="stSidebar"] {{ width: 240px !important; }} }}
  .dash-card > button {{ height: 90px !important; font-size: 15px !important; font-weight: 500 !important;
    border-radius: 12px !important; background-color: var(--card-bg) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important; white-space: pre-line !important; line-height: 1.3 !important;
    transition: all 0.2s ease !important; margin-bottom: 10px !important; }}
  .dash-card > button:hover {{ background-color: var(--accent) !important; border-color: var(--accent-hover) !important;
    transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(31, 111, 235, 0.3) !important; }}
  .dash-card > button:active {{ transform: scale(0.98) !important; }}
</style>
""", unsafe_allow_html=True)

if "theme" not in st.session_state: st.session_state.theme = "dark"
if "tool" not in st.session_state: st.session_state.tool = "🏠 Home"
if "logbook" not in st.session_state: st.session_state.logbook = []
if "spots" not in st.session_state: st.session_state.spots = []
if "gps_coords" not in st.session_state: st.session_state.gps_coords = "Berlin"
if "language" not in st.session_state: st.session_state.language = "de"
if "authenticated" not in st.session_state: st.session_state.authenticated = False

TC = {
    "dark":  {"bg":"#0A0E14","bg2":"#161B22","text":"#F0F6FC","text2":"#8B949E","border":"#30363D","card":"#161B22"},
    "light": {"bg":"#FFFFFF","bg2":"#F6F8FA","text":"#1F2328","text2":"#656D76","border":"#D0D7DE","card":"#F6F8FA"},
}[st.session_state.theme]

render_status_bar()

st.title(_("app.title"))
st.markdown(f"**Web Version** | {_('app.subtitle')}")
st.divider()

TOOLS_CANONICAL: dict[str, str] = {
    "🏠 Home": "",
    "⚙️ Belichtung": "tools.belichtung.render_belichtung",
    "🕶️ ND Rechner": "tools.belichtung.render_nd_rechner",
    "📐 Schärfentiefe": "tools.belichtung.render_schaerfentiefe",
    "🔬 Focus Stacking": "tools.belichtung.render_focus_stacking",
    "🎛️ ND Stacking": "tools.belichtung.render_nd_stacking",
    "🔦 Blitz": "tools.belichtung.render_blitz",
    "📡 Rauschen": "tools.belichtung.render_rauschen",
    "📈 Histogramm": "tools.belichtung.render_histogramm",
    "⚖️ Vergleich": "tools.belichtung.render_vergleich",
    "🔄 Crop-Faktor": "tools.belichtung.render_crop_faktor",
    "🌙 Mond & Milchstraße": "tools.mond.render_mond_milchstrasse",
    "🌙 Aktuelle Mond-Daten": "tools.mond.render_aktuelle_mond_daten",
    "🌠 Sternspuren": "tools.mond.render_sternspuren",
    "🌍 Astro & Wetter Dashboard": "tools.mond.render_astro_wetter_dashboard",
    "📍 GPS-Standort": "tools.gps.render_gps",
    "☁️ Live-Wetter": "tools.wetter.render_live_wetter",
    "📅 5-Tage Prognose": "tools.wetter.render_5tage_prognose",
    "🌡️ Weißabgleich": "tools.sonstige.render_weissabgleich",
    "🔭 Objektive": "tools.sonstige.render_objektive",
    "🌊 Gezeiten & Tide-Rechner": "tools.sonstige.render_gezeiten",
    "📄 PDF-Planer": "tools.sonstige.render_pdf_planer",
    "📝 Planer": "tools.sonstige.render_planer",
    "🗺️ Spots": "tools.sonstige.render_spots",
    "⏱️ Timelapse": "tools.sonstige.render_timelapse",
    "🖼️ EXIF": "tools.sonstige.render_exif",
    "🤖 KI": "tools.sonstige.render_ki",
    "📋 Cheat Sheets": "tools.sonstige.render_cheat_sheets",
    "🎨 Filter-Sim": "tools.sonstige.render_filter_sim",
    "🎬 Video": "tools.sonstige.render_video",
    "🎨 Bearbeitung": "tools.sonstige.render_bearbeitung",
    "🔋 Akku": "tools.sonstige.render_akku",
    "🤿 Unterwasser-Modus": "tools.sonstige.render_unterwasser",
    "📤 PDF Export": "tools.sonstige.render_pdf_export",
    "⚙️ Einstellungen": "tools.sonstige.render_einstellungen",
}


def lazy_call(route_str: str):
    if not route_str:
        return
    parts = route_str.rsplit(".", 1)
    module = importlib.import_module(parts[0])
    getattr(module, parts[1])()


tool = st.session_state.tool

with st.sidebar:
    st.title("📷 Canon Pro Tool")
    st.caption(_("app.subtitle"))
    render_language_selector()
    st.divider()
    st.markdown(f"**{_('auth.login_title')}**")
    if is_auth := st.session_state.get("authenticated", False):
        st.success(_("auth.greeting"))
        if st.button(_("auth.logout"), use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
    else:
        pwd = st.text_input(_("auth.password"), type="password", placeholder=_("auth.password_placeholder"), key="login_pwd")
        if st.button(_("auth.login"), use_container_width=True, type="primary"):
            if pwd == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error(_("auth.wrong_password"))
    st.divider()
    HOME_KEY = "🏠 Home"
    if st.button(_("app.home"), use_container_width=True, type="primary" if tool == HOME_KEY else "secondary"):
        st.session_state.tool = HOME_KEY; st.rerun()
    st.divider()
    with st.expander(_("nav.exposure_focus"), expanded=False):
        if st.button(_("tool.exposure"), use_container_width=True): st.session_state.tool = "⚙️ Belichtung"; st.rerun()
        if st.button(_("tool.nd_calc"), use_container_width=True): st.session_state.tool = "🕶️ ND Rechner"; st.rerun()
        if st.button(_("tool.dof"), use_container_width=True): st.session_state.tool = "📐 Schärfentiefe"; st.rerun()
        if st.button(_("tool.focus_stacking"), use_container_width=True): st.session_state.tool = "🔬 Focus Stacking"; st.rerun()
        if st.button(_("tool.nd_stacking"), use_container_width=True): st.session_state.tool = "🎛️ ND Stacking"; st.rerun()
    with st.expander(_("nav.planning_env"), expanded=False):
        if st.button(_("tool.astro_dashboard"), use_container_width=True): st.session_state.tool = "🌍 Astro & Wetter Dashboard"; st.rerun()
        if st.button(_("tool.moon_milkyway"), use_container_width=True): st.session_state.tool = "🌙 Mond & Milchstraße"; st.rerun()
        if st.button(_("tool.tides"), use_container_width=True): st.session_state.tool = "🌊 Gezeiten & Tide-Rechner"; st.rerun()
        if st.button(_("tool.gps"), use_container_width=True): st.session_state.tool = "📍 GPS-Standort"; st.rerun()
        if st.button(_("tool.planner"), use_container_width=True): st.session_state.tool = "📝 Planer"; st.rerun()
    with st.expander(_("nav.special_modes"), expanded=False):
        if st.button(_("tool.underwater"), use_container_width=True): st.session_state.tool = "🤿 Unterwasser-Modus"; st.rerun()
        if st.button(_("tool.compare"), use_container_width=True): st.session_state.tool = "⚖️ Vergleich"; st.rerun()
        if st.button(_("tool.pdf_export"), use_container_width=True): st.session_state.tool = "📤 PDF Export"; st.rerun()
    with st.expander(_("nav.settings"), expanded=False):
        if st.button(_("tool.settings"), use_container_width=True): st.session_state.tool = "⚙️ Einstellungen"; st.rerun()
    st.divider()
    current_theme = st.session_state.get("theme", "dark")
    theme_label = "☀️ " + _("tool.light_mode") if current_theme == "dark" else "🌙 " + _("tool.dark_mode")
    if st.button(theme_label, use_container_width=True):
        st.session_state.theme = "light" if current_theme == "dark" else "dark"
        components.html(f"""<script>localStorage.setItem('canon_theme','{st.session_state.theme}');</script>""", height=0)
        st.rerun()
    if st.button("⌨️ " + _("tool.shortcuts"), use_container_width=True):
        st.info("""**⌨️ Tastaturkürzel**\n\n""" + "\n".join(f"**Ctrl+{k}:** {v.split(' ')[1] if ' ' in v else v}" for k, v in SHORTCUT_MAP.items()) + """\n\n*Funktionieren nach einmaligem Klick ins Fenster*""")
    st.divider()
    st.caption(_("app.sidebar.tip"))

if tool == "🏠 Home":
    st.markdown("""
    <style>
    .dash-card > button { height: 90px !important; font-size: 15px !important; font-weight: 500 !important;
        border-radius: 12px !important; background-color: #161B22 !important; color: #F0F6FC !important;
        border: 1px solid #30363D !important; white-space: pre-line !important; line-height: 1.3 !important;
        transition: all 0.2s ease !important; margin-bottom: 10px !important; }
    .dash-card > button:hover { background-color: #1F6FEB !important; border-color: #58A6FF !important;
        transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(31, 111, 235, 0.3) !important; }
    .dash-card > button:active { transform: scale(0.98) !important; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    st.header(_("app.dashboard.title"))
    st.markdown(_("app.dashboard.subtitle"))
    st.markdown("</div>", unsafe_allow_html=True)
    DASHBOARD_DESC = {
        "⚙️ Belichtung": "EV-Werte & Dreieck", "🕶️ ND Rechner": "Filter & Stacking",
        "📐 Schärfentiefe": "DoF & Hyperfokal", "🔬 Focus Stacking": "Z-Stapel",
        "🎛️ ND Stacking": "Kombinierte ND", "🔦 Blitz": "Leitzahl",
        "📡 Rauschen": "SNR & Dynamik", "📈 Histogramm": "Pixel-Verteilung",
        "⚖️ Vergleich": "Zwei Setups", "🔄 Crop-Faktor": "Sensor-Äquivalent",
        "🌙 Mond & Milchstraße": "Phasen & Sichtbarkeit", "🌙 Aktuelle Mond-Daten": "Live-Daten",
        "🌠 Sternspuren": "Astro-Guide", "🌍 Astro & Wetter Dashboard": "Planung & Live-Daten",
        "📍 GPS-Standort": "Standort & Wetter", "☁️ Live-Wetter": "Aktuelle Bedingungen",
        "📅 5-Tage Prognose": "Vorhersage", "🌡️ Weißabgleich": "Farbtemperatur",
        "🔭 Objektive": "RF Datenbank", "🌊 Gezeiten & Tide-Rechner": "Ebbe & Flut",
        "📄 PDF-Planer": "Shooting-Plan", "📝 Planer": "Logbuch",
        "🗺️ Spots": "Orte verwalten", "⏱️ Timelapse": "Intervall-Rechner",
        "🖼️ EXIF": "Metadaten", "🤖 KI": "Szenen-Assistent",
        "📋 Cheat Sheets": "Schnellreferenz", "🎨 Filter-Sim": "Bild-Filter",
        "🎬 Video": "Modus-Guide", "🎨 Bearbeitung": "Post-Processing",
        "🔋 Akku": "Laufzeit", "🤿 Unterwasser-Modus": "Tauch-Settings",
        "📤 PDF Export": "Kunden-Bericht",
    }
    top_tools = get_top_tools(12)
    if len(top_tools) >= 4:
        dash_tools = [(name, DASHBOARD_DESC.get(name, "Tool")) for name, _ in top_tools if name in DASHBOARD_DESC or name in TOOLS_CANONICAL]
    else:
        defaults = ["⚙️ Belichtung", "🕶️ ND Rechner", "📐 Schärfentiefe", "🌍 Astro & Wetter Dashboard",
                    "🌙 Mond & Milchstraße", "🌊 Gezeiten & Tide-Rechner", "📍 GPS-Standort", "🤿 Unterwasser-Modus"]
        dash_tools = [(name, DASHBOARD_DESC.get(name, "")) for name in defaults]
    st.caption(f"📊 {len(dash_tools)} meistgenutzte Tools")
    cols = st.columns(2)
    for i, (name, desc) in enumerate(dash_tools):
        with cols[i % 2]:
            with st.container():
                st.markdown('<div class="dash-card">', unsafe_allow_html=True)
                if st.button(f"{name}\n{desc}", use_container_width=True, type="secondary", key=f"home_{name}"):
                    track_usage(name)
                    st.session_state.tool = name; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown(f"<div style='text-align:center;color:var(--text-secondary);font-size:13px;'>{_('app.dashboard.hint')}<br>{_('app.dashboard.gps_hint')}</div>", unsafe_allow_html=True)
elif tool in TOOLS_CANONICAL:
    route_str = TOOLS_CANONICAL[tool]
    if not route_str:
        pass
    else:
        track_usage(tool)
        authed = st.session_state.get("authenticated", False)
        auth_needed = tool in ("📝 Planer", "🗺️ Spots", "📍 GPS-Standort", "⚙️ Einstellungen")
        if auth_needed and not authed:
            st.markdown(f"<div class='auth-box'><h3>{_('auth.protected')}</h3><p>{_('auth.login_prompt')}</p></div>", unsafe_allow_html=True)
        else:
            logger.info("Tool: %s", tool)
            lazy_call(route_str)

st.divider()
st.markdown(f"""
<div style='text-align:center;color:var(--text-secondary);font-size:0.85em;'>
    📷 {_('app.title')} {_('app.version')} | {_('app.subtitle')}<br>
    {_('offline.cached')} | {_('app.footer')}
</div>
""", unsafe_allow_html=True)
