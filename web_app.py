
# web_app_fixed.py – Canon EOS R Pro Tool (Fixed v9.0)
# ──────────────────────────────────────────────────────────────────
# BUGFIXES v9.0:
#  ① KRITISCH: st.set_page_config() als ERSTER Streamlit-Aufruf
#  ② KRITISCH: Session-State-Init VOR render_status_bar()
#  ③ KRITISCH: get_place_name() auf Modulebene (kein doppelter @cache)
#  ④ copy_button(): hash() kann negativ sein → abs() + str-Sanitize
#  ⑤ Gezeiten-Tool: st.stop()-Bug behoben, lat/lon in Session State
#  ⑥ "📸 Kamera-Vergleich" implementiert (fehlte komplett)
#  ⑦ Doppelter 'tool = st.session_state.tool'-Zugriff entfernt
#  ⑧ Doppelter 'if "tool" not in st.session_state'-Block entfernt
#  ⑨ set_tool()-Funktion entfernt (war definiert, aber nie genutzt)
#  ⑩ calculate_golden_hour() jetzt genutzt (Astro-Dashboard)
#  ⑪ 'import streamlit.components.v1' nur 1× am Anfang
#  ⑫ datetime-Namespace-Konflikt in PDF-Export behoben
#  ⑬ render_status_bar() HTML-Struktur bereinigt
#  ⑭ PWA-Injection an korrekte Stelle verschoben (nach set_page_config)
#  ⑮ Cache-Invalidierung an korrekte Stelle verschoben
# ──────────────────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════
#  IMPORTS (alle gebündelt, keine Duplikate)
# ════════════════════════════════════════════════════════════════
import math
import os
import io
import datetime as dt_module  # Klarer Name um Konflikte zu vermeiden
from datetime import datetime, timedelta, date

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components  # NUR EINMAL importieren

try:
    from astral import LocationInfo
    from astral.sun import sun
    import pytz
    ASTRAL_OK = True
except Exception as _e:
    ASTRAL_OK = False
    _ASTRAL_ERR = str(_e)

# ════════════════════════════════════════════════════════════════
#  KONSTANTEN
# ════════════════════════════════════════════════════════════════

SHUTTER_MAP: dict[str, float] = {
    "1/8000": 1/8000, "1/4000": 1/4000, "1/2000": 1/2000,
    "1/1000": 1/1000, "1/500":  1/500,  "1/250":  1/250,
    "1/125":  1/125,  "1/60":   1/60,   "1/30":   1/30,
    "1/15":   1/15,   "1/8":    1/8,    "1/4":    1/4,
    "1/2":    1/2,    "1":      1.0,     "2":      2.0,
    "4":      4.0,    "8":      8.0,    "15":     15.0,
    "30":     30.0,   "60":     60.0,
}

CITY_COORDS: dict[str, tuple[float, float]] = {
    "Berlin":     (52.520, 13.405),
    "München":    (48.135, 11.582),
    "Hamburg":    (53.551,  9.994),
    "Köln":       (50.938,  6.960),
    "Frankfurt":  (50.111,  8.682),
    "Wien":       (48.208, 16.374),
    "Zürich":     (47.377,  8.542),
    "Stuttgart":  (48.775,  9.182),
    "Düsseldorf": (51.227,  6.773),
    "Leipzig":    (51.340, 12.375),
}
CITY_LIST = sorted(CITY_COORDS.keys())

COC_MAP: dict[str, float] = {
    "Vollformat (36×24 mm)":   0.030,
    "APS-C Canon (1.6×)":      0.019,
    "APS-C Nikon/Sony (1.5×)": 0.020,
    "Micro 4/3 (2.0×)":        0.015,
}

CROP_MAP: dict[str, float] = {
    "Vollformat (1.0×)":       1.0,
    "APS-C Canon (1.6×)":      1.6,
    "APS-C Nikon/Sony (1.5×)": 1.5,
    "Micro 4/3 (2.0×)":        2.0,
    "1 Zoll (2.7×)":           2.7,
    "Smartphone (~6×)":        6.0,
}

SHUTTERS_ALL = [
    "1/8000","1/4000","1/2000","1/1000","1/500","1/250",
    "1/125","1/60","1/30","1/15","1/8","1/4","1/2",
    "1","2","4","8","15","30","60",
]

# ════════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN (pure Python – kein Streamlit-Aufruf!)
# ════════════════════════════════════════════════════════════════

def parse_shutter(s: str) -> float:
    return SHUTTER_MAP.get(s, 1/125)


@st.cache_data(ttl=3600)
def calculate_moon_phase(year: int, month: int, day: int) -> float:
    if month < 3:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day + b - 1524.5
    )
    days_since_new = (jd - 2451549.5) % 29.53058867
    return days_since_new / 29.53058867


def moon_phase_info(phase: float) -> tuple[str, float, str]:
    illum = abs(math.sin(phase * math.pi)) * 100
    if phase < 0.03 or phase > 0.97:
        return "🌑 Neumond",           illum, "Perfekt für Milchstraße & Deep-Sky!"
    if phase < 0.22:
        return "🌒 Zunehmende Sichel", illum, "Gut für frühe Abendfotos"
    if phase < 0.28:
        return "🌓 Erstes Viertel",    illum, "Interessante Schatten am Mond"
    if phase < 0.47:
        return "🌔 Zunehmender Mond",  illum, "Zu hell für Milchstraße"
    if phase < 0.53:
        return "🌕 Vollmond",          illum, "Perfekt für Mondlandschaften"
    if phase < 0.72:
        return "🌖 Abnehmender Mond",  illum, "Gut für späte Nacht"
    if phase < 0.78:
        return "🌗 Letztes Viertel",   illum, "Mond geht spät auf"
    return "🌘 Abnehmende Sichel",     illum, "Gut für Morgenaufnahmen"


def get_tide_photo_tip(tide_type: str) -> str:
    if tide_type == "High":
        return "🌊 Dramatische Wellen, Brandungsfotos, Langzeitbelichtung"
    return "🏖️ Spiegelungen, Gezeitenpfützen, Wattstrukturen, Makro"


def calculate_nd(base_sec: float, stops: int) -> float:
    return base_sec * (2 ** stops)


def evaluate_exposure(iso: int, aperture: float, shutter: float):
    ev   = math.log2((aperture ** 2) / shutter)
    ev_c = ev - math.log2(iso / 100)
    if ev_c < 6:  return ev_c, "⚫ Sehr dunkel"
    if ev_c < 10: return ev_c, "🔵 Dunkel"
    if ev_c < 13: return ev_c, "🟢 Optimal"
    if ev_c < 15: return ev_c, "🟡 Hell"
    return ev_c, "🔴 Überbelichtet"


def calculate_dof(focal_mm: float, aperture: float, distance_m: float, coc: float = 0.030):
    h  = (focal_mm ** 2) / (aperture * coc * 1000)
    fm = focal_mm / 1000
    dn = (h * distance_m) / (h + (distance_m - fm))
    df = (h * distance_m) / (h - (distance_m - fm)) if distance_m < h else float("inf")
    return dn, df, (df - dn if df != float("inf") else float("inf")), h


def calculate_golden_hour(sr: str, ss: str) -> dict:
    """Berechnet goldene & blaue Stunde aus Sonnenaufgang/-untergang."""
    fmt     = "%H:%M"
    sunrise = datetime.strptime(sr, fmt)
    sunset  = datetime.strptime(ss, fmt)
    return {
        "golden_morning": (sunrise.strftime(fmt),
                           (sunrise + timedelta(minutes=60)).strftime(fmt)),
        "golden_evening": ((sunset - timedelta(minutes=60)).strftime(fmt),
                           sunset.strftime(fmt)),
        "blue_morning":   ((sunrise - timedelta(minutes=30)).strftime(fmt),
                           sunrise.strftime(fmt)),
        "blue_evening":   (sunset.strftime(fmt),
                           (sunset + timedelta(minutes=30)).strftime(fmt)),
    }


def calculate_flash(gn: float, distance: float, iso: int = 100) -> float:
    return round((gn * math.sqrt(iso / 100)) / distance, 1)


def milky_way_score(phase: float, month: int) -> float:
    darkness = max(0.0, 1.0 - abs(math.sin(phase * math.pi)))
    if 0.45 < phase < 0.55:
        darkness = 0.0
    season = 1.0 - abs(month - 6.5) * 0.12 if 3 <= month <= 10 else 0.25
    return min(100, season * darkness * 100)


def astro_recommendation(score: float) -> str:
    if score >= 80: return "🟢 **Perfekt!** Pack die Kamera ein!"
    if score >= 60: return "🟡 **Gut!** Milchstraße sichtbar."
    if score >= 40: return "🟠 **Mäßig.** Auf dunklere Phase warten."
    return "🔴 **Schlecht.** Besseres Datum suchen."


def city_coords(name: str) -> tuple[float, float]:
    return CITY_COORDS.get(name.strip(), (51.0, 10.0))


def get_best_photo_times(sun_data: dict, moon_phase: float) -> str:
    sr = sun_data["sunrise"]
    ss = sun_data["sunset"]
    lines = [
        f"🌅 Goldene Stunde Morgen: {(sr - timedelta(minutes=15)).strftime('%H:%M')} – {(sr + timedelta(minutes=60)).strftime('%H:%M')}",
        f"🌆 Goldene Stunde Abend:  {(ss - timedelta(minutes=60)).strftime('%H:%M')} – {(ss + timedelta(minutes=15)).strftime('%H:%M')}",
        f"🌄 Blaue Stunde Morgen:   {(sr - timedelta(minutes=40)).strftime('%H:%M')} – {sr.strftime('%H:%M')}",
    ]
    if moon_phase < 0.15 or moon_phase > 0.85:
        lines.append("🌌 Milchstraße: 22:30 – 04:00 (dunkle Nacht!)")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# FIX ③: get_place_name auf MODULEBENE → Cache funktioniert korrekt
# ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_place_name(lat: float, lon: float) -> str | None:
    """Reverse Geocoding via OpenStreetMap Nominatim."""
    try:
        r = requests.get(
            f"https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1&accept-language=de",
            headers={"User-Agent": "CanonProTool/1.0"},
            timeout=3,
        )
        if r.status_code == 200:
            data = r.json()
            addr = data.get("address", {})
            city   = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
            county = addr.get("county") or addr.get("state_district")
            state  = addr.get("state")
            country_code = addr.get("country_code", "").upper()
            country = addr.get("country")
            if city and country_code:
                return f"{city}, {country_code}"
            if county and country_code:
                return f"{county}, {country_code}"
            if state and country:
                return f"{state}, {country}"
            if country:
                return country
    except Exception:
        pass
    return None


# ────────────────────────────────────────────────────────────────
# FIX ④: copy_button – hash() kann negativ sein → abs() + sicherer Name
# ────────────────────────────────────────────────────────────────
def copy_button(text_to_copy: str, label: str = "📋 Kopieren"):
    """Erstellt einen Button, der Text in die Zwischenablage kopiert."""
    # abs() verhindert negative Zahlen → ungültige JS-Funktionsnamen
    btn_id = f"btn_{abs(hash(text_to_copy))}"
    # Apostroph im Text escapen, damit JS nicht bricht
    safe_text = text_to_copy.replace("\\", "\\\\").replace("'", "\\'")

    components.html(f"""
    <style>
    .copy-btn {{
        background: #238636; color: white; border: none;
        padding: 8px 16px; border-radius: 6px; cursor: pointer;
        font-size: 14px; font-weight: bold; transition: background 0.2s;
    }}
    .copy-btn:hover {{ background: #2ea043; }}
    .copy-btn:active {{ transform: scale(0.98); }}
    </style>
    <button class="copy-btn" id="{btn_id}" onclick="copy_{btn_id}()">{label}</button>
    <script>
    function copy_{btn_id}() {{
        navigator.clipboard.writeText('{safe_text}').then(() => {{
            const btn = document.getElementById('{btn_id}');
            const orig = btn.innerText;
            btn.innerText = "✅ Kopiert!";
            btn.style.background = "#1F6FEB";
            setTimeout(() => {{ btn.innerText = orig; btn.style.background = "#238636"; }}, 2000);
        }});
    }}
    </script>
    """, height=50)


# ════════════════════════════════════════════════════════════════
#  FIX ①: st.set_page_config() als ERSTER Streamlit-Aufruf
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Canon EOS R – Pro Tool",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════
#  FIX ⑮ + ②: Cache-Invalidierung & Session-State VOR render_status_bar()
# ════════════════════════════════════════════════════════════════
if st.session_state.get("force_refresh_weather", False):
    st.cache_data.clear()
    st.session_state.force_refresh_weather = False

# Session-State-Initialisierung (EINMALIG, VOR jedem UI-Aufruf)
if "tool" not in st.session_state:
    st.session_state.tool = "🏠 Home"
if "logbook" not in st.session_state:
    st.session_state.logbook = []
if "spots" not in st.session_state:
    st.session_state.spots = []
if "gps_coords" not in st.session_state:
    st.session_state.gps_coords = ""
if "dash_city" not in st.session_state:
    st.session_state.dash_city = "Berlin"
if "gps_temp_coords" not in st.session_state:
    st.session_state.gps_temp_coords = None
# FIX ⑤: lat/lon für Gezeiten-Tool persistent machen
if "tide_lat" not in st.session_state:
    st.session_state.tide_lat = 54.32
if "tide_lon" not in st.session_state:
    st.session_state.tide_lon = 13.09

# ════════════════════════════════════════════════════════════════
#  FIX ⑭: PWA-Injection NACH set_page_config()
# ════════════════════════════════════════════════════════════════
components.html("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1F6FEB">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Canon Pro">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2983/2983796.png">
""", height=0)

# ════════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  .main { background-color: #0A0E14; color: #F0F6FC; }
  h1, h2, h3 { color: #58A6FF; }
  .stButton>button {
      background-color: #1F6FEB; color: white;
      border-radius: 8px; border: none;
      padding: 10px 24px; font-weight: bold;
  }
  .stButton>button:hover { background-color: #58A6FF; }
  @media (max-width: 768px) {
    .main .block-container { padding: 1rem !important; padding-top: 2rem !important; }
    .stTextInput input, .stSelectbox div, .stNumberInput input {
        font-size: 16px !important; min-height: 48px !important;
    }
    .stButton>button { min-height: 48px !important; font-size: 16px !important; padding: 12px 24px !important; }
    .dash-card > button { height: 90px !important; font-size: 15px !important; }
    section[data-testid="stSidebar"] { width: 280px !important; }
  }
  @media (min-width: 769px) {
    section[data-testid="stSidebar"] { width: 240px !important; }
  }
  input, select, textarea { font-size: 16px !important; }
  .stMarkdown, .stText { font-size: 15px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  FIX ⑬: render_status_bar() – saubere HTML-Struktur
# ════════════════════════════════════════════════════════════════
def render_status_bar():
    gps = st.session_state.get("gps_coords", "")

    loc_display = "📍 Nicht gesetzt"
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            place_name = get_place_name(lat, lon)  # FIX ③: Modul-Level-Funktion
            loc_display = f"📍 {place_name}" if place_name else f"📍 {lat:.2f}°, {lon:.2f}°"
        except Exception:
            loc_display = f"📍 {gps}"

    temp, desc = "--", "Warten auf GPS"
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            key = st.secrets.get("OPENWEATHER_API_KEY", "")
            if key:
                r = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather"
                    f"?lat={lat}&lon={lon}&appid={key}&units=metric&lang=de",
                    timeout=3,
                )
                if r.status_code == 200:
                    d = r.json()
                    temp = f"{d['main']['temp']:.1f}°C"
                    desc = d["weather"][0]["description"].capitalize()
        except Exception:
            temp, desc = "--", "Daten n/a"

    # FIX ⑬: Columns direkt ohne HTML-div-Wrapper
    c1, c2, c3, c4 = st.columns([3, 2.5, 2.5, 1])
    c1.markdown(
        f"**{loc_display}**<br>"
        f"<small style='color:#8B949E'>{gps if gps and ',' in str(gps) else 'Kein GPS aktiv'}</small>",
        unsafe_allow_html=True,
    )
    c2.markdown(f"☁️ **Wetter**<br><small style='color:#8B949E'>{temp} | {desc}</small>", unsafe_allow_html=True)
    c3.markdown("📷 **Status**<br><small style='color:#8B949E'>Live</small>", unsafe_allow_html=True)
    if c4.button("🔄", use_container_width=True, key="sb_refresh"):
        st.cache_data.clear()
        st.rerun()
    st.divider()


render_status_bar()

# ════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════
st.title("📷 CANON EOS R – PRO TOOL")
st.markdown("**Web Version** | 32 Photography Tools")

# ════════════════════════════════════════════════════════════════
#  FIX ⑦+⑧: tool NUR EINMAL zuweisen, KEINE doppelten Checks
# ════════════════════════════════════════════════════════════════
tool = st.session_state.tool  # Einmalig, nach Session-State-Init

# ════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("📷 Canon Pro Tool")
    st.caption("32 Photography Tools")
    st.divider()

    if st.button("🏠 Home", use_container_width=True,
                 type="primary" if tool == "🏠 Home" else "secondary"):
        st.session_state.tool = "🏠 Home"
        st.rerun()

    st.divider()

    with st.expander("⚙️ Belichtung & Fokus", expanded=False):
        for t in ["️ Belichtung", "🕶️ ND Rechner", "📐 Schärfentiefe",
                  "🔬 Focus Stacking", "🎛️ ND Stacking", "📸 Bracketing",
                  "📊 Dynamikumfang & Kontrast"]:  # 👈 HIER EINGEFÜGT
            if st.button(t, use_container_width=True, key=f"sb_{t}"):
                st.session_state.tool = t
                st.rerun()

    with st.expander("🌍 Planung & Umgebung", expanded=False):
        for t in ["🌍 Astro & Wetter Dashboard", "🌙 Mond & Milchstraße",
                  "🌊 Gezeiten & Tide-Rechner", "📍 GPS-Standort", "📝 Planer"]:
            if st.button(t, use_container_width=True, key=f"sb_{t}"):
                st.session_state.tool = t
                st.rerun()

    with st.expander("🎨 Spezial-Modi", expanded=False):
        for t in ["🤿 Unterwasser-Modus", "📸 Kamera-Vergleich", "📤 PDF Export",
                  "🔦 Blitz", "📡 Rauschen", "🌡️ Weißabgleich", "🔄 Crop-Faktor",
                  "📈 Histogramm", "🔭 Objektive", "☁️ Live-Wetter",
                  "📅 5-Tage Prognose", "🌠 Sternspuren", "🌙 Aktuelle Mond-Daten",
                  "⏱️ Timelapse", "🖼️ EXIF", "🤖 KI", "📋 Cheat Sheets",
                  "⚖️ Vergleich", "🎨 Filter-Sim", "🎬 Video",
                  "🎨 Bearbeitung", "🔋 Akku", "🗺️ Spots", "📄 PDF-Planer","📱 AR-Brennweiten-Vorschau"]:
            if st.button(t, use_container_width=True, key=f"sb_{t}"):
                st.session_state.tool = t
                st.rerun()

    st.divider()
    st.caption("💡 Ordner aufklappen für alle Tools")

# ════════════════════════════════════════════════════════════════
#  TOOLS – HAUPTINHALT
# ════════════════════════════════════════════════════════════════

# ── 🏠 HOME DASHBOARD ──────────────────────────────────────────
if tool == "🏠 Home":
    st.markdown("""
    <style>
    .dash-card > button {
        height: 90px !important; font-size: 15px !important;
        font-weight: 500 !important; border-radius: 12px !important;
        background-color: #161B22 !important; color: #F0F6FC !important;
        border: 1px solid #30363D !important; white-space: pre-line !important;
        line-height: 1.3 !important; transition: all 0.2s ease !important;
        margin-bottom: 10px !important;
    }
    .dash-card > button:hover {
        background-color: #1F6FEB !important; border-color: #58A6FF !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(31, 111, 235, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.header("📸 Schnellzugriff")
    st.markdown("**Tippe auf eine Kachel**")

    dash_tools = [
        ("⚙️ Belichtung",              "EV-Werte & Dreieck"),
        ("🕶️ ND Rechner",              "Filter & Stacking"),
        ("📐 Schärfentiefe",            "DoF & Hyperfokal"),
        ("🌍 Astro & Wetter Dashboard", "Planung & Live-Daten"),
        ("🌙 Mond & Milchstraße",       "Phasen & Sichtbarkeit"),
        ("🌊 Gezeiten & Tide-Rechner",  "Ebbe & Flut"),
        ("📍 GPS-Standort",             "Standort & Wetter"),
        ("🤿 Unterwasser-Modus",        "Canon & Apexcam"),
        ("📸 Bracketing",               "AEB,Focus & WB Serien"),
        ("📱 AR-Vorschau",              "Live-Brennweiten-Overlay"),
        ("📊 Dynamikumfang",            "Bracketing-Bedarf berechnen"),
    ]
    cols = st.columns(2)
    for i, (name, desc) in enumerate(dash_tools):
        with cols[i % 2]:
            st.markdown('<div class="dash-card">', unsafe_allow_html=True)
            if st.button(f"{name}\n{desc}", use_container_width=True,
                         type="secondary", key=f"home_{name}"):
                st.session_state.tool = name
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#8B949E;font-size:13px;'>"
        "💡 Sidebar → alle 30 Tools<br>"
        "📱 GPS-Daten werden automatisch übernommen</div>",
        unsafe_allow_html=True,
    )

# ── ⚙️ BELICHTUNG ──────────────────────────────────────────────
elif tool == "⚙️ Belichtung":
    st.header("⚙️ Belichtung-Bewerter")
    col1, col2, col3 = st.columns(3)
    with col1:
        iso = st.selectbox("ISO", [100,200,400,800,1600,3200,6400,12800], index=0)
    with col2:
        aperture = st.selectbox("Blende", [1.4,1.8,2.8,4.0,5.6,8.0,11,16,22], index=3)
    with col3:
        shutter_str = st.selectbox("Verschlusszeit", SHUTTERS_ALL, index=6)

    if st.button("📊 Bewerten", type="primary"):
        shutter = parse_shutter(shutter_str)
        ev, rating = evaluate_exposure(iso, aperture, shutter)
        st.success(f"""
        ### Ergebnis:
        - **EV-Wert:** {ev:.2f}
        - **Bewertung:** {rating}
        - **ISO {iso} | f/{aperture} | {shutter_str}**
        """)
        if iso >= 3200:
            st.warning("💡 Hohes ISO – Rauschreduzierung in Post einplanen.")
        if aperture >= 16:
            st.info("💡 Kleine Blende – Beugungsunschärfe möglich (f/16+).")

# ── 🕶️ ND RECHNER ──────────────────────────────────────────────
elif tool == "🕶️ ND Rechner":
    st.header("🕶️ ND Filter Rechner")
    col1, col2 = st.columns(2)
    with col1:
        base_str = st.selectbox("Basiszeit (ohne ND)", SHUTTERS_ALL, index=6)
        base_sec = parse_shutter(base_str)
    with col2:
        nd_stops = st.slider("ND Stops", 1, 15, 3, help="ND8=3 | ND64=6 | ND1000=10")

    nd_factor = 2 ** nd_stops
    st.caption(f"Gewählter Filter: **ND{nd_factor}** ({nd_stops} Stops)")

    if st.button("✅ Berechnen", type="primary", key="calc_nd"):
        result_sec = calculate_nd(base_sec, nd_stops)

        if result_sec >= 3600:
            result_str = f"{result_sec/3600:.2f} Stunden"
        elif result_sec >= 60:
            result_str = f"{result_sec/60:.1f} Minuten"
        elif result_sec >= 1:
            result_str = f"{result_sec:.1f} Sekunden"
        else:
            result_str = f"1/{int(round(1/result_sec))}s"

        st.success(f"""
        ### 🎯 Ergebnis
        - **ND Filter:** ND{nd_factor} ({nd_stops} Stops)
        - **Alte Zeit:** {base_str}
        - **Neue Zeit:** **{result_str}**
        """)
        if result_sec > 300:
            st.warning("⚠️ Sehr lange Belichtung – Stativ + Fernauslöser empfohlen.")
        if result_sec > 900:
            st.warning("⚠️ Über 15 Minuten – Sensorrauschen möglich!")

        st.markdown("**📋 Ergebnis für Notizen:**")
        copy_text = f"ND{nd_factor} | {base_str} → {result_str}"
        st.code(copy_text, language="text")
        copy_button(copy_text)

# ── 🔬 FOCUS STACKING ──────────────────────────────────────────
elif tool == "🔬 Focus Stacking":
    st.header("🔬 Focus Stacking Assistant")
    st.markdown("Berechne exakte Fokusschritte für maximale Schärfentiefe")

    col1, col2 = st.columns(2)
    with col1:
        focal    = st.number_input("Brennweite (mm)", 10, 600, 100)
        aperture = st.number_input("Blende (f/)", 1.0, 32.0, 5.6, step=0.1)
    with col2:
        sensor = st.selectbox("Sensor", ["Vollformat (0.03mm)","APS-C (0.02mm)","Micro 4/3 (0.015mm)"])
        coc = 0.03 if "Voll" in sensor else (0.02 if "APS" in sensor else 0.015)
        start_dist_m = st.number_input("Start-Entfernung (m)", 0.1, 1000.0, 0.5, step=0.1)
        overlap = st.slider("Überlappung (%)", 10, 90, 30)

    if st.button("✅ Fokusschritte berechnen", type="primary"):
        H      = (focal**2) / (aperture * coc) + focal
        D_star = start_dist_m * 1000

        if D_star >= H:
            st.success(
                f"✅ **Alles scharf!** Startpunkt ({start_dist_m}m) liegt hinter "
                f"der hyperfokalen Distanz ({H/1000:.2f}m).\n\n"
                f"💡 Kein Stacking nötig!"
            )
        else:
            S_near = (H * D_star) / (H + D_star)
            S_far  = (H * D_star) / (H - D_star)
            dof    = S_far - S_near
            step_mm = dof * ((100 - overlap) / 100)
            step_cm = step_mm / 10
            est = int((10_000) / step_mm) if step_mm > 0 else 1
            est_str = "100+" if est > 100 else str(est)

            st.success(f"""
            ### 📸 Fokus-Plan: Start {start_dist_m}m
            | Parameter | Wert |
            |---|---|
            | Hyperfokale Distanz | {H/1000:.2f} m |
            | Schärfentiefe am Start | {dof/1000:.3f} m |
            | Empfohlene Schrittweite | **{step_cm:.1f} cm** |
            """)
            st.warning(f"""
            **Anleitung:**
            1. Fokussiere auf **{start_dist_m}m**
            2. Mache das erste Foto
            3. Drehe Fokusring um **{step_cm:.1f} cm** Richtung Unendlich
            4. Wiederhole (**~{est_str} Bilder** für die ersten 10m)
            """)
            if step_cm < 0.5:
                st.error("🔴 Sehr kleine Schrittweite! Makro-Schienensystem empfohlen.")
            elif focal > 100:
                st.info("📏 Tele-Brennweite: Minimale Bewegung wirkt stark. Stativ Pflicht.")

# ── 🎛️ ND STACKING ─────────────────────────────────────────────
elif tool == "🎛️ ND Stacking":
    st.header("🎛️ ND Filter Stacking Rechner")
    ND_FILTERS = [
        ("Kein Filter",0,1),("ND2 (1 Stop)",1,2),("ND4 (2 Stops)",2,4),
        ("ND8 (3 Stops)",3,8),("ND16 (4 Stops)",4,16),("ND32 (5 Stops)",5,32),
        ("ND64 (6 Stops)",6,64),("ND128 (7 Stops)",7,128),("ND256 (8 Stops)",8,256),
        ("ND512 (9 Stops)",9,512),("ND1000 (10 Stops)",10,1000),
        ("ND2000 (11 Stops)",11,2000),("ND4000 (12 Stops)",12,4000),
    ]

    col1, col2, col3 = st.columns(3)
    with col1:
        base_str = st.selectbox("Basiszeit (ohne Filter)", SHUTTERS_ALL, index=6)
    with col2:
        filter_a = st.selectbox("🔷 Filter A", [f[0] for f in ND_FILTERS], index=0)
    with col3:
        filter_b = st.selectbox("🔶 Filter B", [f[0] for f in ND_FILTERS], index=0)

    with st.expander("➕ Dritten Filter hinzufügen (optional)"):
        filter_c  = st.selectbox("🔺 Filter C", [f[0] for f in ND_FILTERS], index=0)
        use_c     = st.checkbox("Filter C aktivieren", value=False)

    if st.button("✅ Stacking berechnen", type="primary"):
        def get_filter_data(name):
            for n, stops, factor in ND_FILTERS:
                if n == name:
                    return stops, factor
            return 0, 1

        if "/" in base_str:
            n, d = map(int, base_str.split("/"))
            base_sec = n / d
        else:
            base_sec = float(base_str)

        sa, fa = get_filter_data(filter_a)
        sb, fb = get_filter_data(filter_b)
        sc, fc = get_filter_data(filter_c) if use_c else (0, 1)

        total_stops  = sa + sb + sc
        total_factor = fa * fb * fc
        result_sec   = base_sec * total_factor

        if result_sec >= 3600:
            result_str = f"{result_sec/3600:.2f} Stunden"
        elif result_sec >= 60:
            result_str = f"{result_sec/60:.1f} Minuten"
        elif result_sec >= 1:
            result_str = f"{result_sec:.1f} Sekunden"
        else:
            result_str = f"1/{int(round(1/result_sec))}s"

        st.success(f"""
        ### 🎯 Ergebnis:
        - **Filter A:** {filter_a} ({sa} Stops)
        - **Filter B:** {filter_b} ({sb} Stops)
        - **Filter C:** {filter_c if use_c else "–"} {f"({sc} Stops)" if use_c else ""}
        - **Σ Gesamt-Stops:** {total_stops} Stops | ND{total_factor}
        - **⏱️ Neue Belichtungszeit:** **{result_str}**
        """)
        if total_stops >= 6:
            st.warning("⚠️ Ab 6 Stops: Stativ + Fernauslöser zwingend!")
        if total_stops >= 10:
            st.error("🔴 Über 10 Stops: Langzeitrauschreduktion erwägen!")
        if result_sec > 300:
            st.info("💡 >5 Min.: Bulb-Modus + Intervalometer nutzen")

# ── 📐 SCHÄRFENTIEFE ───────────────────────────────────────────
elif tool == "📐 Schärfentiefe":
    st.header("📐 Schärfentiefe-Rechner")
    col1, col2, col3 = st.columns(3)
    with col1:
        focal    = st.number_input("Brennweite (mm)", 14, 800, 50)
    with col2:
        aperture = st.selectbox("Blende (f/)", [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16,22], index=4)
    with col3:
        distance = st.number_input("Entfernung (m)", 0.3, 500.0, 3.0, 0.1)

    sensor = st.selectbox("Sensor", list(COC_MAP.keys()))
    coc    = COC_MAP[sensor]

    if st.button("✅ Berechnen", type="primary"):
        near, far, total, hyper = calculate_dof(focal, aperture, distance, coc)
        far_str   = "∞" if far   == float("inf") else f"{far:.2f} m"
        total_str = "∞ (alles scharf)" if total == float("inf") else f"{total:.2f} m"
        st.success(f"""
        ### 📊 Ergebnisse:
        - **Nahpunkt:** {near:.2f} m
        - **Fernpunkt:** {far_str}
        - **Schärfentiefe:** {total_str}
        - **Hyperfokale Distanz:** {hyper:.1f} m
        """)
        if distance >= hyper:
            st.info("💡 Fokus jenseits der hyperfokalen Distanz – alles bis ∞ scharf!")
        elif distance < 1.0:
            st.info("💡 Sehr kurze Distanz – Schärfentiefe sehr gering. Stativ empfohlen.")

# ── 📍 GPS-STANDORT ────────────────────────────────────────────
elif tool == "📍 GPS-Standort":
    st.header("📍 Standort automatisch erkennen")

    gps_html = """
    <div style="padding:10px; box-sizing:border-box; font-family:sans-serif;">
        <button id="gps-btn" style="padding:12px; background:#1F6FEB; color:white; border:none;
            border-radius:8px; cursor:pointer; width:100%; margin-bottom:10px; font-size:16px;">
            📍 Standort abrufen
        </button>
        <div id="gps-res" style="display:none; background:#161B22; padding:12px;
            border-radius:8px; text-align:center; border:1px solid #30363D;">
            <p id="gps-txt" style="color:#58A6FF; font-family:monospace; margin:0 0 12px 0; font-size:14px;"></p>
            <a id="gps-link" href="#" style="display:inline-block; padding:12px; background:#238636;
                color:white; text-decoration:none; border-radius:6px; font-weight:bold; font-size:15px;">
                ✅ Koordinaten übernehmen
            </a>
        </div>
    </div>
    <script>
    document.getElementById('gps-btn').onclick = () => {
        const txt = document.getElementById('gps-txt');
        const res = document.getElementById('gps-res');
        txt.textContent = "⏳ Standort wird ermittelt...";
        res.style.display = "block";
        if (!navigator.geolocation) { txt.textContent = "❌ Geolocation nicht unterstützt"; return; }
        navigator.geolocation.getCurrentPosition(pos => {
            const lat = pos.coords.latitude.toFixed(6);
            const lon = pos.coords.longitude.toFixed(6);
            txt.textContent = `✅ ${lat}, ${lon} (Ort wird gesucht...)`;
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10`, {
                headers: { 'Accept-Language': 'de', 'User-Agent': 'CanonProTool/1.0' }
            }).then(r => r.json()).then(data => {
                let ort = "Unbekannt";
                if (data && data.address) {
                    const a = data.address;
                    ort = a.city || a.town || a.village || a.county || a.state || "Unbekannt";
                }
                txt.textContent = `✅ ${lat}, ${lon} (nahe ${ort})`;
                document.getElementById('gps-link').href =
                    window.location.href.split('?')[0] + "?lat=" + lat + "&lon=" + lon;
            }).catch(() => {
                txt.textContent = `✅ ${lat}, ${lon}`;
                document.getElementById('gps-link').href =
                    window.location.href.split('?')[0] + "?lat=" + lat + "&lon=" + lon;
            });
        }, err => { txt.textContent = `❌ Fehler: ${err.message}`; },
        { enableHighAccuracy: true, timeout: 10000 });
    };
    </script>
    """
    components.html(gps_html, height=220)

    # Query-Params verarbeiten
    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")
    if lat_q and lon_q:
        st.session_state.gps_coords     = f"{lat_q},{lon_q}"
        st.session_state.gps_temp_coords = f"{lat_q},{lon_q}"
        st.query_params.clear()
        st.success(f"✅ GPS übernommen: `{st.session_state.gps_coords}`")
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### 📍 Koordinaten manuell eingeben")

    default_coords = st.session_state.get("gps_temp_coords") or "50.43,7.47"
    if "," in default_coords:
        default_lat, default_lon = default_coords.split(",", 1)
    else:
        default_lat, default_lon = "50.43", "7.47"

    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Breitengrad", value=default_lat.strip())
    with col2:
        manual_lon = st.text_input("Längengrad", value=default_lon.strip())

    if st.button("✅ Übernehmen", use_container_width=True, type="primary"):
        try:
            lat_f = float(manual_lat)
            lon_f = float(manual_lon)
            if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
                st.error("❌ Ungültige Koordinaten!")
            else:
                coords = f"{lat_f},{lon_f}"
                st.session_state.gps_coords      = coords
                st.session_state.gps_temp_coords = coords
                st.success(f"✅ Standort gesetzt: `{coords}`")
                st.cache_data.clear()
                st.rerun()
        except ValueError:
            st.error("❌ Bitte nur Zahlen eingeben!")

    if st.session_state.gps_coords:
        st.divider()
        st.success(f"### ✅ Aktueller Standort: `{st.session_state.gps_coords}`")
        if st.button("🗑️ Standort löschen"):
            st.session_state.gps_coords      = ""
            st.session_state.gps_temp_coords = None
            st.cache_data.clear()
            st.rerun()

# ── 🌍 ASTRO & WETTER DASHBOARD ────────────────────────────────
elif tool == "🌍 Astro & Wetter Dashboard":
    st.header("🌍 Astro & Wetter Dashboard")

    city = st.text_input(
        "📍 Stadt oder Koordinaten (z.B. Berlin oder 52.52,13.40)",
        value=st.session_state.get("dash_city", "Berlin"),
        key="dash_input",
    )

    if st.button("🔄 Dashboard aktualisieren", type="primary"):
        try:
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]
            lat, lon = None, None
            if "," in city:
                parts = city.replace(" ", "").split(",")
                lat, lon = float(parts[0]), float(parts[1])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    st.error("❌ Ungültige Koordinaten")
                    st.stop()

            w_url = (
                f"http://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"http://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={API_KEY}&units=metric&lang=de"
            )
            w = requests.get(w_url, timeout=8).json()

            if w.get("cod") != 200:
                st.error(f"❌ {w.get('message','Fehler')}")
            else:
                temp   = w["main"]["temp"]
                clouds = w["clouds"]["all"]
                wind   = w["wind"]["speed"] * 3.6
                desc   = w["weather"][0]["description"]
                icon   = w["weather"][0]["icon"]
                sr_ts  = datetime.fromtimestamp(w["sys"]["sunrise"]).strftime("%H:%M")
                ss_ts  = datetime.fromtimestamp(w["sys"]["sunset"]).strftime("%H:%M")

                # FIX ⑩: calculate_golden_hour() wird jetzt genutzt!
                gh     = calculate_golden_hour(sr_ts, ss_ts)

                now    = datetime.now()
                phase  = calculate_moon_phase(now.year, now.month, now.day)
                m_name, m_illum, m_tip = moon_phase_info(phase)

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("☁️ Live-Wetter")
                    st.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=60)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🌡️", f"{temp:.1f}°C")
                    c2.metric("💨", f"{wind:.0f} km/h")
                    c3.metric("☁️", f"{clouds}%")
                    st.caption(f"{desc.capitalize()} | ☀️ {sr_ts} – {ss_ts}")
                    st.markdown(f"""
                    🌅 **Goldene Stunde Morgen:** {gh['golden_morning'][0]} – {gh['golden_morning'][1]}  
                    🌆 **Goldene Stunde Abend:** {gh['golden_evening'][0]} – {gh['golden_evening'][1]}  
                    🌄 **Blaue Stunde Morgen:** {gh['blue_morning'][0]} – {gh['blue_morning'][1]}
                    """)
                with col2:
                    st.subheader("🌙 Mondstatus")
                    st.metric("Phase", m_name)
                    st.metric("Beleuchtung", f"{m_illum:.0f}%")
                    st.caption(m_tip)

                astro_sc = (100 - m_illum) * 0.6 + (100 - clouds) * 0.4
                mw_sc    = milky_way_score(phase, now.month)
                st.info(f"""
                ### 📸 Shooting-Empfehlung
                {astro_recommendation(astro_sc)}

                **Milchstraße-Score:** {mw_sc:.0f}/100
                """)

                with st.expander("📊 Stunden-Übersicht (heute)"):
                    f_url = (
                        f"http://api.openweathermap.org/data/2.5/forecast"
                        f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de&cnt=8"
                        if lat else
                        f"http://api.openweathermap.org/data/2.5/forecast"
                        f"?q={city}&appid={API_KEY}&units=metric&lang=de&cnt=8"
                    )
                    f_data = requests.get(f_url, timeout=8).json()
                    if f_data.get("cod") == "200":
                        items = f_data["list"]
                        df_h  = pd.DataFrame({
                            "Zeit":     [datetime.fromtimestamp(i["dt"]).strftime("%H:%M") for i in items],
                            "Temp °C":  [i["main"]["temp"] for i in items],
                            "Wolken%":  [i["clouds"]["all"] for i in items],
                        })
                        st.dataframe(df_h.set_index("Zeit"), use_container_width=True)
        except Exception as e:
            st.error(f"Fehler: {type(e).__name__}: {e}")

# ── 🌙 MOND & MILCHSTRASSE ──────────────────────────────────────
elif tool == "🌙 Mond & Milchstraße":
    st.header("🌙 Mondphasen & Milchstraße Sichtbarkeit")

    city_sel = st.selectbox("📍 Stadt", ["(manuell)"] + CITY_LIST)
    col1, col2 = st.columns(2)
    with col1:
        date_str = st.text_input("📅 Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y"))
    with col2:
        if city_sel != "(manuell)":
            latitude, longitude = CITY_COORDS[city_sel]
            st.number_input("Breitengrad", value=latitude, disabled=True, key="mw_lat")
            st.number_input("Längengrad",  value=longitude, disabled=True, key="mw_lon")
        else:
            default_coords = st.session_state.get("gps_coords", "51.34,12.38")
            coords_input = st.text_input("Koordinaten (Br,Lg)", value=default_coords)
            try:
                parts = coords_input.replace(" ", "").split(",")
                latitude, longitude = float(parts[0]), float(parts[1])
            except Exception:
                latitude, longitude = 51.34, 12.38

    option = st.selectbox("🎯 Fokus", ["Milchstraße","Mondfotografie","Deep Sky","Nordlichter"])

    if st.button("🔍 Berechnen", type="primary"):
        try:
            day, month, year = map(int, date_str.split("."))
            phase = calculate_moon_phase(year, month, day)
            p_name, p_illum, p_tip = moon_phase_info(phase)

            if option == "Milchstraße":
                score     = milky_way_score(phase, month)
                best_time = "22:30–04:00" if 4 <= month <= 9 else "03:00–06:00"
                rec       = ("🟢 Hervorragend!" if score >= 85 else "🟡 Gut!" if score >= 65
                             else "🟠 Mäßig." if score >= 40 else "🔴 Schlecht.")
            elif option == "Mondfotografie":
                score     = p_illum
                best_time = "Abends nach Sonnenuntergang"
                rec       = "🌕 Vollmond – perfekt!" if 0.45 < phase < 0.55 else "🌙 Interessante Phase"
            elif option == "Deep Sky":
                score     = max(0, 100 - p_illum)
                best_time = "Mitternacht–Morgengrauen"
                rec       = "🔭 Dunkler Himmel – ideal!" if score > 80 else "⚠️ Auf Neumond warten."
            else:  # Nordlichter
                if abs(latitude) > 58:
                    score     = max(0, 100 - p_illum) * (1.0 if month in range(10,13) or month in range(1,4) else 0.5)
                    best_time = "21:00–02:00"
                    rec       = "🌌 Aurora möglich bei klarem Himmel!"
                else:
                    score     = 15
                    best_time = "–"
                    rec       = "📍 Zu weit südlich – >58° Breite nötig"

            st.success(f"""
            ### 📊 {date_str} | 📍 {latitude:.4f}, {longitude:.4f}
            **🌙 Phase:** {p_name} | Beleuchtung: **{p_illum:.0f}%** | {p_tip}

            **Score:** {score:.0f}/100 | {rec}

            **⏰ Beste Zeit:** {best_time}
            """)
        except ValueError:
            st.error("⚠️ Ungültiges Datum. Format: TT.MM.JJJJ")
        except Exception as e:
            st.error(f"❌ Fehler: {e}")

# ── 🌊 GEZEITEN & TIDE-RECHNER ─────────────────────────────────
elif tool == "🌊 Gezeiten & Tide-Rechner":
    st.header("🌊 Gezeiten & Tide-Rechner")

    KUESTEN_ORTE = {
        "Rügen (DE)":          (54.32, 13.09),
        "Sylt (DE)":           (54.91,  8.31),
        "Norddeich (DE)":      (53.60,  7.15),
        "Cuxhaven (DE)":       (53.87,  8.70),
        "Norderney (DE)":      (53.71,  7.15),
        "Amrum (DE)":          (54.63,  8.33),
        "St. Peter-Ording (DE)":(54.31, 8.62),
        "Ostende (BE)":        (51.23,  2.93),
        "Brest (FR)":          (48.39, -4.49),
        "Liverpool (UK)":      (53.41, -3.00),
        "Brighton (UK)":       (50.82, -0.14),
    }

    methode = st.radio(
        "📍 Standort:",
        ["🏖️ Bekannter Küstenort", "📍 Eigene Koordinaten", "📱 GPS-Standort"],
        index=0,
    )

    # FIX ⑤: lat/lon in Session State speichern – kein st.stop()-Bug mehr
    if methode == "🏖️ Bekannter Küstenort":
        ort = st.selectbox("Ort:", list(KUESTEN_ORTE.keys()))
        st.session_state.tide_lat, st.session_state.tide_lon = KUESTEN_ORTE[ort]
        st.info(f"📍 {ort} ({st.session_state.tide_lat:.4f}, {st.session_state.tide_lon:.4f})")

    elif methode == "📍 Eigene Koordinaten":
        c1, c2 = st.columns(2)
        with c1:
            lat_in = st.number_input("Breitengrad",  value=st.session_state.tide_lat,
                                     min_value=-90.0, max_value=90.0, format="%.4f")
        with c2:
            lon_in = st.number_input("Längengrad",   value=st.session_state.tide_lon,
                                     min_value=-180.0, max_value=180.0, format="%.4f")
        st.session_state.tide_lat = lat_in
        st.session_state.tide_lon = lon_in
        st.info(f"📍 Koordinaten: {lat_in:.4f}, {lon_in:.4f}")

    else:  # GPS
        gps = st.session_state.get("gps_coords", "")
        if gps and "," in gps:
            try:
                lat_f, lon_f = map(float, gps.split(","))
                st.session_state.tide_lat = lat_f
                st.session_state.tide_lon = lon_f
                st.success(f"✅ GPS: {lat_f:.4f}, {lon_f:.4f}")
            except Exception:
                st.warning("⚠️ GPS-Daten fehlerhaft.")
        else:
            st.warning("⚠️ Kein GPS-Standort. Bitte zuerst 📍 GPS-Standort setzen.")

    tide_date = st.date_input("📅 Datum", value=date.today())

    if st.button("🌊 Gezeiten abrufen", type="primary"):
        lat_use = st.session_state.tide_lat
        lon_use = st.session_state.tide_lon
        try:
            API_KEY  = st.secrets["WORLD_TIDES_API_KEY"]
            start_ts = int(datetime.combine(tide_date, datetime.min.time()).timestamp())
            url      = (
                f"https://www.worldtides.info/api/v3"
                f"?lat={lat_use}&lon={lon_use}&key={API_KEY}"
                f"&start={start_ts}&length=86400&extremes"
            )
            res  = requests.get(url, timeout=10)
            data = res.json()

            if res.status_code != 200 or data.get("status") != 200:
                st.error(f"❌ API-Fehler: {data.get('error','Unbekannt')}")
            else:
                extremes = data.get("extremes", [])
                if not extremes:
                    st.info("ℹ️ Keine Gezeitendaten für diesen Standort.")
                else:
                    st.success(f"✅ Gezeiten für {tide_date.strftime('%d.%m.%Y')}")
                    df = pd.DataFrame([{
                        "Zeit":      datetime.fromtimestamp(e["dt"]).strftime("%H:%M"),
                        "Typ":       "🌊 Hochwasser" if e["type"]=="High" else "🏖️ Niedrigwasser",
                        "Höhe":      f"{e['height']:.2f} m",
                        "Foto-Tipp": get_tide_photo_tip(e["type"]),
                    } for e in extremes])
                    st.dataframe(df, use_container_width=True, hide_index=True)
        except KeyError:
            st.warning("⚠️ **API-Key fehlt!** Bitte `WORLD_TIDES_API_KEY` in Streamlit Secrets hinterlegen.")
            st.info("🔑 Kostenloser Key: [worldtides.info](https://www.worldtides.info/)")
        except Exception as e:
            st.error(f"❌ {type(e).__name__}: {e}")

# ── 📝 PLANER ──────────────────────────────────────────────────
elif tool == "📝 Planer":
    st.header("📝 Aufnahme-Planer & Logbuch")
    tab1, tab2 = st.tabs(["➕ Neuer Eintrag", "📖 Logbuch"])

    with tab1:
        c1, c2 = st.columns(2)
        loc     = c1.text_input("📍 Ort")
        sub     = c2.text_input("📸 Motiv")
        c3, c4 = st.columns(2)
        iso_log = c3.selectbox("ISO",    [100,200,400,800,1600,3200], key="log_iso")
        ap_log  = c4.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], key="log_ap")
        sh_log  = st.selectbox("Verschluss", ["1/1000","1/500","1/250","1/125","1/60","1/30","1s","2s","4s"], key="log_sh")
        notes   = st.text_area("📝 Notizen")
        rating  = st.slider("⭐ Bewertung", 1, 5, 3)

        if st.button("➕ Speichern", type="primary"):
            if loc or sub:
                st.session_state.logbook.append({
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "loc":      loc, "sub": sub,
                    "settings": f"ISO {iso_log} | f/{ap_log} | {sh_log}",
                    "notes":    notes,
                    "rating":   "⭐" * rating,
                })
                st.success("✅ Gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte Ort oder Motiv eingeben.")

    with tab2:
        if st.session_state.logbook:
            search  = st.text_input("🔍 Suchen…")
            entries = st.session_state.logbook
            if search:
                entries = [e for e in entries if search.lower() in str(e).lower()]
            for entry in reversed(entries):
                with st.expander(f"📸 {entry['date']} | {entry['loc']} – {entry['sub']} {entry['rating']}"):
                    st.markdown(
                        f"- **📍 Ort:** {entry['loc']}\n"
                        f"- **📸 Motiv:** {entry['sub']}\n"
                        f"- **⚙️ Settings:** `{entry['settings']}`\n"
                        f"- **📝 Notizen:** {entry['notes']}"
                    )
            if st.button("🗑️ Alle löschen"):
                st.session_state.logbook = []
                st.rerun()
        else:
            st.info("📭 Noch keine Einträge.")

# ── 🤿 UNTERWASSER-MODUS ───────────────────────────────────────
elif tool == "🤿 Unterwasser-Modus":
    st.header("🤿 Unterwasser-Fotografie Assistant")

    col1, col2 = st.columns(2)
    with col1:
        depth      = st.slider("Tiefe (m)", 0, 60, 5)
        visibility = st.slider("👁️ Sichtweite (m)", 1, 30, 10)
    with col2:
        water_type = st.selectbox("💧 Wasser-Typ", ["Tropisch/Klar","Gemäßigt","Trüb/Kalt"])
        use_flash  = st.checkbox("💡 Blitz/Licht nutzen", value=True)

    tab1, tab2 = st.tabs(["📷 Canon EOS R", "🏄 Apexcam"])

    with tab1:
        st.subheader("📷 Canon EOS R Settings")
        if use_flash:
            wb_val = "4800K – 5200K (Blitz)"
        else:
            base_wb = {"Tropisch/Klar": 5600, "Gemäßigt": 6000, "Trüb/Kalt": 6500}
            wb_val  = f"{min(base_wb[water_type] + depth * 25, 8000)}K"

        c1, c2 = st.columns(2)
        c1.metric("⚖️ Weißabgleich", wb_val)
        c1.metric("Bildformat", "RAW + JPEG (Fine)")
        c2.markdown("**Fokus:**\n✅ Focus Peaking (Rot)\n✅ MF Assist\n✅ Back-Button Focus")
        if use_flash:
            st.success("💡 Strobe-Arme auf 45° – vermeidet Backscatter.")
        else:
            st.warning("⚠️ Ohne Blitz: Roter Filter ab 5m dringend empfohlen!")

    with tab2:
        st.subheader("🏄 Apexcam ActionCam")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🎥 Video:** 4K/60fps\n**📷 Foto:** SuperPhoto (HDR)")
        with c2:
            st.markdown("**🌊 Anti-Shake:** EIS auf HOCH\n**Filter:** Roter Dome-Filter ab 3m")
        if visibility < 5:
            st.warning("⚠️ Trübes Wasser: Wet Lens (Weitwinkel-Makro) empfohlen!")

    st.divider()
    st.subheader("🌊 Umgebungs-Analyse")
    if depth <= 3:  lost = "Keine"
    elif depth <= 8: lost = "Rot"
    elif depth <= 15: lost = "Rot, Orange"
    else:            lost = "Rot, Orange, Gelb, Grün"
    st.metric("🎨 Verlorene Farben", lost)

    with st.expander("✅ Pre-Dive Checkliste"):
        for c in ["O-Ring reinigen & einfetten","Speicherkarte formatiert",
                  "Akku voll","Gehäuse-Vakuumtest","Objektiv trocken"]:
            st.checkbox(c, key=f"uw_{c}")

# ════════════════════════════════════════════════════════════════
#  FIX ⑥: 📸 KAMERA-VERGLEICH (komplett neu implementiert)
# ════════════════════════════════════════════════════════════════
elif tool == "📸 Kamera-Vergleich":
    st.header("📸 Kamera-Vergleich")
    st.markdown("Vergleiche Canon EOS R Modelle und Konkurrenz anhand der wichtigsten Specs.")

    CAMERAS = {
        "Canon EOS R":    {"MP":30.3,"ISO_max":40000,"AF_punkte":5655,"IBIS":False,"4K_crop":1.74,"Gewicht_g":660,"Preis_EUR":1400,"Akku_shots":370},
        "Canon EOS R5":   {"MP":45.0,"ISO_max":51200,"AF_punkte":5940,"IBIS":True, "4K_crop":1.0, "Gewicht_g":738,"Preis_EUR":3800,"Akku_shots":320},
        "Canon EOS R6 II":{"MP":24.2,"ISO_max":204800,"AF_punkte":6072,"IBIS":True,"4K_crop":1.0, "Gewicht_g":670,"Preis_EUR":2800,"Akku_shots":360},
        "Canon EOS R8":   {"MP":24.2,"ISO_max":102400,"AF_punkte":6072,"IBIS":False,"4K_crop":1.07,"Gewicht_g":461,"Preis_EUR":1600,"Akku_shots":220},
        "Canon EOS R50":  {"MP":24.2,"ISO_max":32000,"AF_punkte":651, "IBIS":False,"4K_crop":1.56,"Gewicht_g":375,"Preis_EUR":800, "Akku_shots":210},
        "Sony A7 IV":     {"MP":33.0,"ISO_max":51200,"AF_punkte":759, "IBIS":True, "4K_crop":1.0, "Gewicht_g":659,"Preis_EUR":2800,"Akku_shots":520},
        "Nikon Z8":       {"MP":45.7,"ISO_max":51200,"AF_punkte":493, "IBIS":True, "4K_crop":1.0, "Gewicht_g":910,"Preis_EUR":4500,"Akku_shots":340},
        "Nikon Z6 III":   {"MP":24.5,"ISO_max":64000,"AF_punkte":273, "IBIS":True, "4K_crop":1.0, "Gewicht_g":760,"Preis_EUR":2800,"Akku_shots":380},
    }

    cam_list = sorted(CAMERAS.keys())
    col1, col2 = st.columns(2)
    with col1:
        cam_a = st.selectbox("📷 Kamera A", cam_list, index=0)
    with col2:
        cam_b = st.selectbox("📷 Kamera B", cam_list, index=1)

    if cam_a == cam_b:
        st.warning("⚠️ Bitte zwei verschiedene Kameras wählen.")
    else:
        a, b = CAMERAS[cam_a], CAMERAS[cam_b]

        st.divider()
        st.subheader("📊 Direktvergleich")

        specs = [
            ("🖼️ Auflösung (MP)",    f"{a['MP']} MP",           f"{b['MP']} MP",
             cam_a if a["MP"] > b["MP"] else cam_b),
            ("📡 ISO max",            f"{a['ISO_max']:,}",        f"{b['ISO_max']:,}",
             cam_a if a["ISO_max"] > b["ISO_max"] else cam_b),
            ("🎯 AF-Punkte",          f"{a['AF_punkte']:,}",      f"{b['AF_punkte']:,}",
             cam_a if a["AF_punkte"] > b["AF_punkte"] else cam_b),
            ("🔄 IBIS",               "✅ Ja" if a["IBIS"] else "❌ Nein",
             "✅ Ja" if b["IBIS"] else "❌ Nein",
             cam_a if a["IBIS"] and not b["IBIS"] else (cam_b if b["IBIS"] and not a["IBIS"] else "Gleich")),
            ("🎬 4K Crop",            f"×{a['4K_crop']}",         f"×{b['4K_crop']}",
             cam_a if a["4K_crop"] <= b["4K_crop"] else cam_b),
            ("⚖️ Gewicht",            f"{a['Gewicht_g']}g",       f"{b['Gewicht_g']}g",
             cam_a if a["Gewicht_g"] < b["Gewicht_g"] else cam_b),
            ("🔋 Akku-Ausdauer",      f"{a['Akku_shots']} Fotos", f"{b['Akku_shots']} Fotos",
             cam_a if a["Akku_shots"] > b["Akku_shots"] else cam_b),
            ("💶 Preis (ca.)",        f"{a['Preis_EUR']}€",       f"{b['Preis_EUR']}€",
             cam_a if a["Preis_EUR"] < b["Preis_EUR"] else cam_b),
        ]

        header_cols = st.columns([3, 2, 2, 2])
        header_cols[0].markdown("**Eigenschaft**")
        header_cols[1].markdown(f"**{cam_a}**")
        header_cols[2].markdown(f"**{cam_b}**")
        header_cols[3].markdown("**Besser**")

        for spec, val_a, val_b, winner in specs:
            row = st.columns([3, 2, 2, 2])
            row[0].markdown(spec)
            row[1].markdown(val_a)
            row[2].markdown(val_b)
            row[3].markdown(f"🏆 {winner}" if winner not in ("Gleich", cam_a, cam_b) else
                            ("🤝 Gleich" if winner == "Gleich" else f"🏆 {winner}"))

        st.divider()
        # Preis-Leistungs-Übersicht
        score_a = (a["MP"] * 0.2 + math.log10(a["ISO_max"]) * 10 +
                   (10 if a["IBIS"] else 0) + a["Akku_shots"] * 0.05 -
                   a["4K_crop"] * 5 - a["Gewicht_g"] * 0.01)
        score_b = (b["MP"] * 0.2 + math.log10(b["ISO_max"]) * 10 +
                   (10 if b["IBIS"] else 0) + b["Akku_shots"] * 0.05 -
                   b["4K_crop"] * 5 - b["Gewicht_g"] * 0.01)

        c1, c2 = st.columns(2)
        c1.metric(f"⭐ Score {cam_a}", f"{score_a:.0f} Pkt.",
                  delta=f"{score_a - score_b:+.0f} vs. {cam_b}")
        c2.metric(f"⭐ Score {cam_b}", f"{score_b:.0f} Pkt.",
                  delta=f"{score_b - score_a:+.0f} vs. {cam_a}")

        winner = cam_a if score_a >= score_b else cam_b
        st.info(f"### 🏆 Empfehlung: **{winner}**\n"
                f"Basierend auf Auflösung, ISO, IBIS, Akku, Gewicht & 4K-Crop-Faktor.")

        # Alle Kameras im Überblick
        with st.expander("📋 Alle Kameras vergleichen"):
            df = pd.DataFrame(CAMERAS).T.reset_index()
            df.columns = ["Kamera","MP","ISO max","AF-Punkte","IBIS",
                          "4K Crop","Gewicht (g)","Preis (€)","Akku (Fotos)"]
            st.dataframe(df, use_container_width=True, hide_index=True)

# ── 📤 PDF EXPORT ──────────────────────────────────────────────
elif tool == "📤 PDF Export":
    st.header("📄 Shooting-Plan erstellen")

    try:
        from fpdf import FPDF
    except ImportError:
        st.error("❌ 'fpdf2' fehlt – bitte in requirements.txt ergänzen!")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        pdf_client = st.text_input("Kunde / Projekt", placeholder="z.B. Hochzeit Müller")
        default_loc = ""
        gps = st.session_state.get("gps_coords", "")
        if gps and "," in gps:
            default_loc = gps
        pdf_loc = st.text_input("Ort / Location", value=default_loc)
    with col2:
        # FIX ⑫: date statt datetime.date – kein Namespace-Konflikt
        pdf_date    = st.date_input("Datum", value=date.today())
        pdf_weather = st.text_input("Wetter / Bedingungen", placeholder="Sonne, 22°C")

    pdf_notes = st.text_area("Notizen & Settings", height=150,
                              placeholder="• 16:00 Golden Hour\n• Objektiv: 50mm 1.2")

    if st.button("📄 PDF generieren", type="primary"):
        if not pdf_client or not pdf_loc:
            st.warning("⚠️ Bitte mindestens Kunde und Ort angeben.")
        else:
            try:
                class ShootingPDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica","B",15)
                        self.set_text_color(41,98,255)
                        self.cell(0,10,"Canon EOS R – Shooting Plan",0,1,"C")
                        self.set_draw_color(200,200,200)
                        self.line(10,22,200,22)
                        self.ln(8)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica","I",8)
                        self.set_text_color(128,128,128)
                        # FIX ⑫: datetime.now() korrekt aufgerufen
                        self.cell(0,10,f"Canon EOS R Pro Tool | {datetime.now().strftime('%d.%m.%Y')}",0,0,"C")

                pdf = ShootingPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_font("Helvetica","B",12)
                pdf.set_text_color(0,0,0)
                pdf.cell(0,8,f"Projekt: {pdf_client}",0,1)
                pdf.set_font("Helvetica",size=11)
                pdf.cell(0,8,f"Datum: {pdf_date.strftime('%d.%m.%Y')}",0,1)
                pdf.cell(0,8,f"Ort: {pdf_loc}",0,1)
                if pdf_weather:
                    pdf.cell(0,8,f"Wetter: {pdf_weather}",0,1)
                pdf.ln(8)
                pdf.set_font("Helvetica","B",12)
                pdf.cell(0,8,"Notizen & Settings:",0,1)
                pdf.set_font("Helvetica",size=10)
                pdf.multi_cell(0,6,pdf_notes or "Keine Notizen vorhanden.")

                filename = f"ShootingPlan_{pdf_date.strftime('%Y%m%d')}.pdf"
                pdf_bytes = pdf.output(dest="S")
                if isinstance(pdf_bytes, str):
                    pdf_bytes = pdf_bytes.encode("latin-1","replace")

                st.success("✅ PDF erstellt!")
                st.download_button("📥 PDF Herunterladen", pdf_bytes, filename, "application/pdf")
            except Exception as e:
                st.error(f"Fehler: {e}")

# ── 🔦 BLITZ ───────────────────────────────────────────────────
elif tool == "🔦 Blitz":
    st.header("🔦 Blitz-Rechner (Leitzahl)")
    col1, col2, col3 = st.columns(3)
    with col1: gn       = st.number_input("Leitzahl (GN)", 10, 100, 58)
    with col2: distance = st.number_input("Entfernung (m)", 0.5, 50.0, 5.0, 0.5)
    with col3: iso      = st.selectbox("ISO", [100,200,400,800,1600,3200], index=0)

    if st.button("✅ Berechnen", type="primary"):
        ap = calculate_flash(gn, distance, iso)
        st.success(f"### Empfohlene Blende: f/{ap}\n**GN {gn} | {distance}m | ISO {iso}**")
        with st.expander("📋 Reichweiten-Tabelle"):
            rows = [{"Blende": f"f/{f}", "Max. Reichweite": f"{gn * math.sqrt(iso/100) / f:.1f} m"}
                    for f in [1.4,2.0,2.8,4.0,5.6,8.0,11,16]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ── 📡 RAUSCHEN ────────────────────────────────────────────────
elif tool == "📡 Rauschen":
    st.header("📡 Sensor-Rauschen & Dynamikumfang")
    iso = st.selectbox("ISO:", [100,200,400,800,1600,3200,6400,12800,25600])

    if st.button("📊 Analysieren", type="primary"):
        stops  = math.log2(iso / 100)
        dr     = max(13.5 - stops * 0.8, 5.0)
        snr    = max(40   - stops * 5.5, 8.0)
        rating = ("🟢 Exzellent" if snr >= 35 else "🟡 Gut" if snr >= 25
                  else "🟠 Akzeptabel" if snr >= 15 else "🔴 Stark verrauscht")
        c1,c2,c3 = st.columns(3)
        c1.metric("📉 SNR",           f"{snr:.1f} dB")
        c2.metric("🌈 Dynamikumfang", f"{dr:.1f} EV")
        c3.metric("📊 Bewertung",     rating)

        with st.expander("📋 ISO-Vergleich"):
            rows = [{"ISO": i, "SNR (dB)": f"{max(40-math.log2(i/100)*5.5,8):.1f}",
                     "Dynamik (EV)": f"{max(13.5-math.log2(i/100)*0.8,5):.1f}",
                     "OK": "✅" if max(40-math.log2(i/100)*5.5,8) >= 25 else "⚠️"}
                    for i in [100,200,400,800,1600,3200,6400,12800,25600]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ── 🌡️ WEIßABGLEICH ───────────────────────────────────────────
elif tool == "🌡️ Weißabgleich":
    st.header("🌡️ Weißabgleich & Farbtemperatur")
    for name, kelvin, color in [
        ("🕯️ Kerzenlicht","1800–2000 K","#FF6B35"),
        ("💡 Glühlampe","2700–3200 K","#FFA500"),
        ("🌅 Sonnenaufgang","3000–3500 K","#FF8C42"),
        ("📸 Blitz","5000–5500 K","#FFFEF0"),
        ("☀️ Tageslicht","5200–5800 K","#FFFFF0"),
        ("⛅ Bewölkt","6000–6500 K","#E8F0FF"),
        ("🏔️ Schatten","7000–8000 K","#D0E0FF"),
        ("🌌 Blaue Stunde","9000–12000 K","#9090FF"),
    ]:
        c1,c2 = st.columns([2,3])
        c1.markdown(f"<span style='color:{color};font-weight:bold'>{name}</span>", unsafe_allow_html=True)
        c2.code(kelvin)
    st.info("💡 Manuellen WB in Kelvin setzen – stabilere Farben im Timelapse!")

# ── 🔄 CROP-FAKTOR ─────────────────────────────────────────────
elif tool == "🔄 Crop-Faktor":
    st.header("🔄 Crop-Faktor Rechner")
    col1, col2 = st.columns(2)
    with col1:
        focal       = st.number_input("Brennweite (mm)", 10, 800, 50)
        aperture    = st.selectbox("Blende", [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16], index=4)
    with col2:
        sensor_from = st.selectbox("Von:", list(CROP_MAP.keys()), index=0)
        sensor_to   = st.selectbox("Nach:", list(CROP_MAP.keys()), index=1)

    if st.button("✅ Berechnen", type="primary"):
        cf_from = CROP_MAP[sensor_from]
        cf_to   = CROP_MAP[sensor_to]
        st.success(f"""
        **Original ({sensor_from}):** {focal}mm | f/{aperture}  
        **Vollformat-Äq.:** {focal*cf_from:.0f}mm | f/{aperture*cf_from:.1f}  
        **Äq. auf {sensor_to}:** {focal*cf_from/cf_to:.0f}mm | f/{aperture*cf_from/cf_to:.1f}
        """)

# ── 🔭 OBJEKTIVE ───────────────────────────────────────────────
elif tool == "🔭 Objektive":
    st.header("🔭 RF Objektiv-Datenbank")
    LENSES = [
        {"Name":"RF 14-35mm f/4L IS",   "Typ":"Weitwinkel Zoom","f/":4.0,"Gewicht":"540g","IS":"✅","Preis":"~1.600€"},
        {"Name":"RF 15-35mm f/2.8L IS",  "Typ":"Weitwinkel Zoom","f/":2.8,"Gewicht":"840g","IS":"✅","Preis":"~2.500€"},
        {"Name":"RF 24-70mm f/2.8L IS",  "Typ":"Standard Zoom",  "f/":2.8,"Gewicht":"900g","IS":"✅","Preis":"~2.700€"},
        {"Name":"RF 24-105mm f/4L IS",   "Typ":"Standard Zoom",  "f/":4.0,"Gewicht":"700g","IS":"✅","Preis":"~1.200€"},
        {"Name":"RF 50mm f/1.2L USM",    "Typ":"Standard Prime", "f/":1.2,"Gewicht":"950g","IS":"❌","Preis":"~2.400€"},
        {"Name":"RF 50mm f/1.8 STM",     "Typ":"Standard Prime", "f/":1.8,"Gewicht":"160g","IS":"❌","Preis":"~230€"},
        {"Name":"RF 85mm f/1.2L USM",    "Typ":"Portrait Prime", "f/":1.2,"Gewicht":"1195g","IS":"❌","Preis":"~3.000€"},
        {"Name":"RF 85mm f/2 Macro IS",  "Typ":"Portrait Prime", "f/":2.0,"Gewicht":"500g","IS":"✅","Preis":"~700€"},
        {"Name":"RF 70-200mm f/2.8L IS", "Typ":"Tele Zoom",      "f/":2.8,"Gewicht":"1070g","IS":"✅","Preis":"~2.900€"},
        {"Name":"RF 100-500mm f/4.5-7.1L","Typ":"Supertele Zoom","f/":"4.5-7","Gewicht":"1370g","IS":"✅","Preis":"~3.000€"},
        {"Name":"RF 100mm f/2.8L Macro IS","Typ":"Makro Prime",  "f/":2.8,"Gewicht":"730g","IS":"✅","Preis":"~1.500€"},
    ]
    typ_filter = st.multiselect("🏷️ Typ:", sorted({l["Typ"] for l in LENSES}))
    filtered   = [l for l in LENSES if not typ_filter or l["Typ"] in typ_filter]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=450)
    st.info(f"📊 {len(filtered)} von {len(LENSES)} Objektiven")

# ── ☁️ LIVE-WETTER ─────────────────────────────────────────────
elif tool == "☁️ Live-Wetter":
    st.header("☁️ Live-Wetter Analyse")
    city_input = st.text_input("📍 Stadt oder Koordinaten",
                                value=st.session_state.gps_coords or "Berlin")

    if st.button("🔄 Analyse starten", type="primary"):
        try:
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]
            lat, lon = None, None
            if "," in city_input:
                parts    = city_input.replace(" ","").split(",")
                lat, lon = float(parts[0]), float(parts[1])

            url = (
                f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/weather?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )
            res  = requests.get(url, timeout=8)
            data = res.json()

            if data.get("cod") != 200:
                st.error(f"❌ {data.get('message','Fehler')}")
            else:
                temp       = data["main"]["temp"]
                humidity   = data["main"]["humidity"]
                clouds     = data["clouds"]["all"]
                wind       = data["wind"]["speed"] * 3.6
                desc       = data["weather"][0]["description"]
                icon       = data["weather"][0]["icon"]
                sunrise    = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
                sunset     = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")

                st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png", width=80)
                st.subheader(f"{desc.capitalize()} | {temp:.1f}°C")
                c1,c2,c3 = st.columns(3)
                c1.metric("💨 Wind",     f"{wind:.1f} km/h")
                c1.metric("☁️ Wolken",   f"{clouds}%")
                c2.metric("💧 Luftfeuchte", f"{humidity}%")
                c3.metric("🌅 Aufgang",  sunrise)
                c3.metric("🌇 Untergang",sunset)

                score = 100
                notes = []
                if clouds < 20: notes.append("🟢 Klarer Himmel – Top für Astro!")
                elif clouds < 60: score -= 20; notes.append("🟡 Wolken – dramatisch")
                else: score -= 40; notes.append("🟠 Bewölkt – diffuses Licht")
                if wind > 40: score -= 30; notes.append("⚠️ Starker Wind!")
                elif wind > 20: score -= 10; notes.append("🟡 Mäßiger Wind")

                if   score >= 80: st.success(f"⭐⭐⭐ **PERFEKT (Score: {score})**\n\n" + "\n".join(notes))
                elif score >= 50: st.info(   f"⭐⭐ **GUT (Score: {score})**\n\n"       + "\n".join(notes))
                else:             st.warning(f"⭐ **SCHWIERIG (Score: {score})**\n\n"   + "\n".join(notes))
        except Exception as e:
            st.error(f"Fehler: {e}")

# ── 📅 5-TAGE PROGNOSE ─────────────────────────────────────────
elif tool == "📅 5-Tage Prognose":
    st.header("📅 5-Tage-Wettervorhersage")
    city_input = st.text_input("📍 Stadt oder Koordinaten",
                                value=st.session_state.gps_coords or "Berlin")

    if st.button("📊 Vorhersage laden", type="primary"):
        try:
            API_KEY  = st.secrets["OPENWEATHER_API_KEY"]
            lat, lon = None, None
            if "," in city_input:
                parts    = city_input.replace(" ","").split(",")
                lat, lon = float(parts[0]), float(parts[1])

            url = (
                f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/forecast?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )
            data = requests.get(url, timeout=8).json()

            if data.get("cod") != "200":
                st.error(f"❌ {data.get('message','Fehler')}")
            else:
                times, temps, daily = [], [], {}
                for item in data["list"]:
                    d   = datetime.fromtimestamp(item["dt"])
                    day = d.strftime("%d.%m.")
                    times.append(d.strftime("%d.%m. %H:%M"))
                    temps.append(item["main"]["temp"])
                    if day not in daily:
                        daily[day] = {"min": item["main"]["temp_min"],
                                      "max": item["main"]["temp_max"],
                                      "desc": item["weather"][0]["description"]}
                    else:
                        daily[day]["min"] = min(daily[day]["min"], item["main"]["temp_min"])
                        daily[day]["max"] = max(daily[day]["max"], item["main"]["temp_max"])

                st.line_chart(pd.DataFrame({"Temperatur":temps[:40]}, index=times[:40]),
                              use_container_width=True)
                cols = st.columns(len(daily))
                for i,(day,vals) in enumerate(daily.items()):
                    with cols[i]:
                        st.metric(day, f"{vals['min']:.0f}°/{vals['max']:.0f}°")
                        st.caption(vals["desc"].capitalize())
        except Exception as e:
            st.error(f"Fehler: {e}")

# ── 🌠 STERNSPUREN ─────────────────────────────────────────────
elif tool == "🌠 Sternspuren":
    st.header("🌠 Sternspuren & Astrofotografie")
    tab1,tab2,tab3,tab4 = st.tabs(["🎯 Sternspuren","⭐ Scharfe Sterne","📐 Planung","📚 Tipps"])

    with tab1:
        c1,c2 = st.columns(2)
        total_time = c1.number_input("Gesamtzeit (Min)", 10, 480, 60)
        interval   = c1.number_input("Intervall (Sek)",  1,  30,  5)
        shutter_s  = c2.selectbox("Belichtung/Bild", ["10s","15s","20s","25s","30s"], index=2)
        iso_s      = c2.selectbox("ISO", [400,800,1600,3200], index=2)

        if st.button("✅ Berechnen", type="primary", key="star_calc"):
            sh_sec   = int(shutter_s.replace("s",""))
            n_frames = (total_time * 60) // (sh_sec + interval)
            trail    = (total_time / 4) * 15
            st.success(f"""
            - Bilder: **{n_frames:,}** | Dauer: **{total_time} Min**
            - Sternspur: **{trail:.0f}°** | Speicher: **~{n_frames*30/1024:.1f} GB**
            """)

    with tab2:
        c1,c2 = st.columns(2)
        focal_sh  = c1.number_input("Brennweite (mm)", 14, 400, 24)
        sensor_sh = c1.selectbox("Sensor", ["Vollformat","APS-C Canon 1.6×","APS-C Nikon 1.5×","Micro 4/3 2×"])
        ap_sh     = c2.selectbox("Blende", [1.2,1.4,1.8,2.0,2.8,4.0], index=3)
        crop_sh   = {"Vollformat":1.0,"APS-C Canon 1.6×":1.6,"APS-C Nikon 1.5×":1.5,"Micro 4/3 2×":2.0}[sensor_sh]
        max_500   = 500  / (focal_sh * crop_sh)
        max_npf   = (35 * ap_sh + 30) / (focal_sh * crop_sh)
        st.success(f"**500er-Regel:** {max_500:.1f}s | **NPF (präziser):** {max_npf:.1f}s")

    with tab3:
        c1,c2 = st.columns(2)
        date_plan = c1.text_input("Datum", value=datetime.now().strftime("%d.%m.%Y"))
        lp        = c2.selectbox("Lichtverschmutzung",
                                  ["Bortle 1–2 (Sehr dunkel)","Bortle 3–4","Bortle 5–6","Bortle 7–9"])
        if st.button("🔍 Prüfen", key="star_plan"):
            try:
                d,mo,yr = map(int, date_plan.split("."))
                phase   = calculate_moon_phase(yr,mo,d)
                _,illum,_ = moon_phase_info(phase)
                lp_s    = {"Bortle 1–2 (Sehr dunkel)":1.0,"Bortle 3–4":0.7,"Bortle 5–6":0.4,"Bortle 7–9":0.1}[lp]
                season  = 1.0 if 3 <= mo <= 10 else 0.4
                sc      = ((100-illum)/100*0.4 + season*0.3 + lp_s*0.3)*100
                st.success(f"Score: {sc:.0f}/100\n\n{astro_recommendation(sc)}")
            except ValueError:
                st.error("Ungültiges Datum.")

    with tab4:
        st.markdown("""
        **Equipment:** Stativ | Intervalometer | Stirnlampe (Rotlicht) | 64+ GB Karten  
        **Kamera:** Manuell | RAW | WB 3800K | Rauschreduktion AUS | IS AUS  
        **Stacking:** Sequator (Win) | Starry Landscape Stacker (Mac)
        """)

# ── 🌙 AKTUELLE MOND-DATEN ─────────────────────────────────────
elif tool == "🌙 Aktuelle Mond-Daten":
    st.header("🌙 Live-Sonnen- & Mond-Daten")
    if not ASTRAL_OK:
        st.error(f"⚠️ astral/pytz nicht installiert: {_ASTRAL_ERR}")
        st.stop()

    city_sel = st.selectbox("Stadt", ["(manuell / GPS)"] + CITY_LIST)
    if city_sel != "(manuell / GPS)":
        lat, lon = CITY_COORDS[city_sel]
    else:
        default = st.session_state.get("gps_coords", "51.34,12.38")
        inp = st.text_input("Koordinaten", value=default)
        try:
            parts = inp.replace(" ","").split(",")
            lat, lon = float(parts[0]), float(parts[1])
        except Exception:
            lat, lon = 51.34, 12.38

    if st.button("🔄 Berechnen", type="primary"):
        try:
            tz        = pytz.timezone("Europe/Berlin")
            name      = city_sel if city_sel != "(manuell / GPS)" else f"{lat:.4f},{lon:.4f}"
            city_info = LocationInfo(name,"DE","Europe/Berlin",lat,lon)
            now       = datetime.now(tz)
            s         = sun(city_info.observer, date=now.date(), tzinfo=tz)
            phase     = calculate_moon_phase(now.year, now.month, now.day)
            m_name, m_illum, m_tip = moon_phase_info(phase)

            st.success(f"""
            ### 📅 {now.strftime('%d.%m.%Y %H:%M')} | 📍 {name}

            **🌞 Sonne:**  
            Aufgang: `{s['sunrise'].strftime('%H:%M')}` | Untergang: `{s['sunset'].strftime('%H:%M')}`

            **🌙 Mond:**  
            Phase: `{m_name}` | Beleuchtung: `{m_illum:.0f}%` | {m_tip}

            **📸 Beste Foto-Zeiten**  
            {get_best_photo_times(s, phase)}
            """)
        except Exception as e:
            st.error(f"❌ {type(e).__name__}: {e}")

# ── ⏱️ TIMELAPSE ───────────────────────────────────────────────
elif tool == "⏱️ Timelapse":
    st.header("⏱️ Timelapse-Rechner")
    tab1,tab2 = st.tabs(["📊 Berechnung","💡 Tipps"])

    with tab1:
        c1,c2,c3 = st.columns(3)
        duration = c1.number_input("Video-Länge (Sek)", 5, 600, 30)
        fps      = c2.selectbox("FPS", [24,25,30,60])
        interval = c3.number_input("Intervall (Sek)", 1, 3600, 5)
        fmt      = st.selectbox("Format", ["RAW (~30 MB)","JPEG Fine (~10 MB)","JPEG Normal (~5 MB)"])

        if st.button("✅ Berechnen", type="primary"):
            frames    = duration * fps
            total_sec = frames * interval
            h = int(total_sec//3600); m = int((total_sec%3600)//60); s = int(total_sec%60)
            size_gb   = frames * {"RAW (~30 MB)":30,"JPEG Fine (~10 MB)":10,"JPEG Normal (~5 MB)":5}[fmt] / 1024
            st.success(f"**Bilder:** {frames:,} | **Dauer:** {h}h {m}m {s}s | **Speicher:** {size_gb:.1f} GB")
            if size_gb > 64: st.warning("⚠️ >64 GB!")

    with tab2:
        st.markdown("""
        | Motiv | Intervall |
        |---|---|
        | Wolken | 1–3s |
        | Sonnenuntergang | 3–5s |
        | Sternenhimmel | 20–30s |
        | Baustelle | 5–15 min |
        """)

# ── 🖼️ EXIF ────────────────────────────────────────────────────
elif tool == "🖼️ EXIF":
    st.header("🖼️ EXIF-Daten auslesen")
    uploaded = st.file_uploader("📤 Foto hochladen", type=["jpg","jpeg","png","webp"])

    if uploaded:
        try:
            from PIL import Image, ExifTags
            img = Image.open(uploaded)
            c1,c2 = st.columns(2)
            with c1:
                st.image(img, caption="Vorschau", use_container_width=True)
            with c2:
                exif_data = img.getexif()
                if not exif_data:
                    st.warning("⚠️ Keine EXIF-Daten gefunden.")
                else:
                    tags = {ExifTags.TAGS[k]: str(v) for k,v in exif_data.items()
                            if k in ExifTags.TAGS and not isinstance(v,bytes)}
                    for key in ["Make","Model","ExposureTime","FNumber",
                                "ISOSpeedRatings","FocalLength","DateTimeOriginal","LensModel"]:
                        if key in tags:
                            st.markdown(f"**{key}:** `{tags[key]}`")
                    with st.expander("📋 Alle EXIF-Daten"):
                        st.dataframe(pd.DataFrame(list(tags.items()), columns=["Tag","Wert"]),
                                     use_container_width=True, height=400)
        except ImportError:
            st.error("Pillow fehlt: pip install Pillow")
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Foto hoch.")

# ── 🤖 KI ──────────────────────────────────────────────────────
elif tool == "🤖 KI":
    st.header("🤖 KI Fotografie-Assistent")
    scene = st.text_area("📝 Szene beschreiben", height=80)

    KI_DB = {
        "sunset":    ("🌅 SUNSET",    "ISO 100 | f/8 | 1/125s",    "GND-Filter | Stativ"),
        "portrait":  ("👤 PORTRAIT",  "ISO 100 | f/1.8 | 1/200s",  "Eye-AF | 85mm"),
        "night":     ("🌙 NACHT",     "ISO 1600 | f/2.8 | 10s",    "Stativ | RAW"),
        "landscape": ("🏔️ LANDSCHAFT","ISO 100 | f/11 | 1/60s",    "Polfilter | Stativ"),
        "street":    ("🏙️ STREET",    "ISO 400 | f/5.6 | 1/250s",  "35mm | Burst"),
        "macro":     ("🔬 MAKRO",     "ISO 200 | f/8 | 1/160s",    "Stativ | Diffusor"),
        "sport":     ("⚡ SPORT",     "ISO 800 | f/4 | 1/1000s",   "AI Servo | Burst"),
        "astro":     ("🌌 ASTRO",     "ISO 3200 | f/1.8 | 20s",    "500er-Regel | MF ∞"),
    }

    cols = st.columns(4)
    for i, key in enumerate(KI_DB):
        if cols[i%4].button(f"📸 {key.capitalize()}", key=f"ki_{key}"):
            scene = key

    if st.button("🤖 KI Vorschlag", type="primary"):
        if not scene.strip():
            st.warning("Bitte Szene eingeben oder Preset wählen.")
        else:
            found = False
            for key,(title,settings,tips) in KI_DB.items():
                if key in scene.lower():
                    st.success(f"### {title}\n**Settings:** `{settings}`\n**Tipps:** {tips}")
                    found = True
                    break
            if not found:
                st.info("### 📸 Allgemein\n**Settings:** `ISO 200 | f/5.6 | 1/125s`")

# ── 📋 CHEAT SHEETS ────────────────────────────────────────────
elif tool == "📋 Cheat Sheets":
    st.header("📋 Schnellreferenz-Karten")
    GUIDES = {
        "Portrait":    "👤 PORTRAIT\nBrennweite: 85–135mm | Blende: f/1.4–f/2.8\nISO: 100–400 | Eye-AF",
        "Landschaft":  "🏔️ LANDSCHAFT\nBrennweite: 16–35mm | Blende: f/8–f/16\nISO: 100 | Stativ | Golden Hour",
        "Nacht/Astro": "🌙 NACHT\nBrennweite: 14–24mm | Blende: f/1.4–f/2.8\nISO: 1600–6400 | 500er-Regel",
        "Street":      "🏙️ STREET\nBrennweite: 28–50mm | Blende: f/5.6–f/8\nISO: Auto (max 3200) | 1/250s+",
        "Makro":       "🔬 MAKRO\nBrennweite: 90–105mm | Blende: f/5.6–f/11\nISO: 200–800 | Focus Stacking",
        "Sport":       "⚡ SPORT\nBrennweite: 70–400mm | Blende: f/2.8–f/4\nISO: 800–3200 | 1/1000s min",
        "Hochzeit":    "💍 HOCHZEIT\nISO: 400–3200 | Blende: f/2.8–f/4\n2 Bodies! | 4+ Akkus",
    }
    sheet = st.selectbox("Kategorie:", list(GUIDES.keys()))
    st.code(GUIDES[sheet], language="text")

# ── ⚖️ VERGLEICH ───────────────────────────────────────────────
elif tool == "⚖️ Vergleich":
    st.header("⚖️ Einstellungs-Vergleich")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("🅰️ Setup A")
        a_iso    = st.selectbox("ISO",    [100,200,400,800,1600,3200,6400], index=0, key="a_iso")
        a_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16],    index=3, key="a_ap")
        a_sh_str = st.selectbox("Verschluss", SHUTTERS_ALL, index=6, key="a_sh")
    with c2:
        st.subheader("🅱️ Setup B")
        b_iso    = st.selectbox("ISO",    [100,200,400,800,1600,3200,6400], index=0, key="b_iso")
        b_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16],    index=3, key="b_ap")
        b_sh_str = st.selectbox("Verschluss", SHUTTERS_ALL, index=6, key="b_sh")

    if st.button("⚖️ Vergleichen", type="primary"):
        ev_a = math.log2((a_ap**2) / parse_shutter(a_sh_str)) - math.log2(a_iso/100)
        ev_b = math.log2((b_ap**2) / parse_shutter(b_sh_str)) - math.log2(b_iso/100)
        diff = ev_a - ev_b
        c1,c2,c3 = st.columns(3)
        c1.metric("🅰️ Setup A", f"EV {ev_a:.2f}")
        c2.metric("🅱️ Setup B", f"EV {ev_b:.2f}")
        c3.metric("Δ Differenz", f"{abs(diff):.2f} Stops")
        if abs(diff) < 0.05: st.success("✅ Gleiche Belichtung!")
        elif diff > 0:        st.info(f"☀️ Setup A ist {abs(diff):.2f} Stops heller")
        else:                 st.info(f"🌙 Setup B ist {abs(diff):.2f} Stops heller")

# ── 🎨 FILTER-SIM ──────────────────────────────────────────────
elif tool == "🎨 Filter-Sim":
    st.header("🎨 Filter-Simulator")
    uploaded = st.file_uploader("🖼️ Foto hochladen", type=["jpg","png","jpeg","webp"])

    if uploaded:
        try:
            import numpy as np
            from PIL import Image, ImageEnhance, ImageFilter

            img  = Image.open(uploaded).convert("RGB")
            c1,c2 = st.columns(2)
            with c1:
                st.image(img, caption="Original", use_container_width=True)

            filt      = st.selectbox("Filter:", ["Kein Filter","ND2","ND8","ND64","ND1000",
                                                  "Schwarzweiß","Warmton","Kaltton",
                                                  "Kontrast","Soft-Focus","Vignette"])
            intensity = st.slider("Intensität", 0.0, 1.0, 0.8, 0.05)
            img_f     = img.copy()

            if   "ND2"        in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1-0.50*intensity))
            elif "ND8"        in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1-0.875*intensity))
            elif "ND64"       in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.02, 1-0.984*intensity))
            elif "ND1000"     in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.01, 0.001+(1-intensity)*0.1))
            elif "Schwarzweiß" in filt:
                img_f = ImageEnhance.Contrast(img_f.convert("L").convert("RGB")).enhance(1+intensity*0.5)
            elif "Warmton"    in filt:
                r,g,b = img_f.split()
                r = r.point(lambda p: min(255,int(p*(1+0.25*intensity))))
                b = b.point(lambda p: max(0,  int(p*(1-0.25*intensity))))
                img_f = Image.merge("RGB",(r,g,b))
            elif "Kaltton"    in filt:
                r,g,b = img_f.split()
                r = r.point(lambda p: max(0,  int(p*(1-0.20*intensity))))
                b = b.point(lambda p: min(255,int(p*(1+0.30*intensity))))
                img_f = Image.merge("RGB",(r,g,b))
            elif "Kontrast"   in filt:
                img_f = ImageEnhance.Contrast(img_f).enhance(1+intensity*1.5)
            elif "Soft-Focus" in filt:
                blurred = img_f.filter(ImageFilter.GaussianBlur(int(intensity*8)))
                img_f   = Image.blend(img_f, blurred, intensity*0.6)
            elif "Vignette"   in filt:
                w_px,h_px = img_f.size
                arr       = np.array(img_f, dtype=float)
                cx,cy     = w_px/2, h_px/2
                Y,X       = np.ogrid[:h_px,:w_px]
                dist      = np.sqrt(((X-cx)/cx)**2 + ((Y-cy)/cy)**2)
                mask      = np.clip(1-intensity*np.clip(dist-0.5,0,1)*1.5, 0, 1)
                img_f     = Image.fromarray((arr*mask[:,:,np.newaxis]).clip(0,255).astype("uint8"))

            with c2:
                st.image(img_f, caption=f"Filter: {filt}", use_container_width=True)
            buf = io.BytesIO()
            img_f.save(buf, format="JPEG", quality=92)
            st.download_button("⬇️ Herunterladen", buf.getvalue(), "filtered.jpg", "image/jpeg")
        except ImportError:
            st.error("Pillow / numpy fehlen: pip install Pillow numpy")
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Bild hoch.")

# ── 🎬 VIDEO ───────────────────────────────────────────────────
elif tool == "🎬 Video":
    st.header("🎬 Video-Modus Guide")
    tab1,tab2,tab3 = st.tabs(["📊 Specs","⚙️ Settings","🎞️ 180°-Regel"])

    with tab1:
        st.markdown("""
        | Modus  | Auflösung  | FPS | Crop |
        |---|---|---|---|
        | 4K UHD | 3840×2160 | 24p | 1.74× |
        | 4K UHD | 3840×2160 | 30p | 1.74× |
        | Full HD | 1920×1080 | 60p | 1.0× |
        | Full HD | 1920×1080 | 120p | 1.0× |
        """)
    with tab2:
        st.markdown("**Cinematic:** 24fps | 1/50s | C-Log | ND-Filter  \n**YouTube:** 30fps | 1/60s | Dual Pixel AF")
    with tab3:
        fps_v = st.selectbox("FPS:", [24,25,30,50,60,120])
        st.success(f"**{fps_v} fps → 1/{fps_v*2}s Verschlusszeit** (180°-Regel)")

# ── 🎨 BEARBEITUNG ─────────────────────────────────────────────
elif tool == "🎨 Bearbeitung":
    st.header("🎨 Post-Processing Guide")
    tab1,tab2,tab3 = st.tabs(["📊 Grundbearbeitung","🌈 Farben","📚 Workflows"])

    with tab1:
        c1,c2 = st.columns(2)
        with c1:
            exp_val    = c1.slider("Belichtung", -2.0, 2.0, 0.0, 0.1)
            contrast_v = c1.slider("Kontrast", -50, 100, 20)
            highlights = c1.slider("Lichter", -100, 100, -40)
        with c2:
            shadows    = c2.slider("Tiefen", -100, 100, 40)
            whites     = c2.slider("Weiß", -100, 100, 10)
            blacks     = c2.slider("Schwarz", -100, 100, -10)
        st.code(f"Belichtung:{exp_val:+.1f} | Kontrast:{contrast_v:+d} | Lichter:{highlights:+d} | Tiefen:{shadows:+d}")

    with tab2:
        st.markdown("**Blau (Himmel):**")
        st.slider("Sättigung", -100, 100, 20, key="bl_s")
        st.markdown("**Orange (Haut):**")
        st.slider("Sättigung", -100, 100, 10, key="or_s")

    with tab3:
        st.markdown("""
        **Astro-Workflow:** Sequator → 16-bit TIFF → WB 3800K → Belichtung +0.7 → HSL Blau +40  
        **Export Web:** JPEG 80–85% | 2048px | sRGB  
        **Export Druck:** TIFF 100% | 300 DPI | AdobeRGB
        """)

# ── 🔋 AKKU ────────────────────────────────────────────────────
elif tool == "🔋 Akku":
    st.header("🔋 Akku-Kalkulator")
    BATTERY_MAP = {
        "LP-E6NH (2130 mAh) – ~370 Shots": 370,
        "LP-E6N  (1865 mAh) – ~350 Shots": 350,
        "LP-E6   (1800 mAh) – ~300 Shots": 300,
    }
    battery = st.selectbox("Akku-Typ", list(BATTERY_MAP.keys()))
    cap     = BATTERY_MAP[battery]
    spm     = st.number_input("Shots/Minute", 0.5, 10.0, 2.0, 0.5)
    c1,c2,c3 = st.columns(3)
    lcd   = c1.slider("LCD-Nutzung (%)",  0, 100, 50)
    flash = c2.slider("Blitz-Nutzung (%)", 0, 100, 20)
    wifi  = c3.slider("WiFi/BT (%)",       0, 100, 30)
    ibis  = st.checkbox("IBIS aktiv", value=True)

    if st.button("✅ Berechnen", type="primary"):
        factor = max(0.3, 1.0 - (lcd/100)*0.15 - (flash/100)*0.20 - (wifi/100)*0.10 - (0.05 if ibis else 0))
        shots  = int(cap * factor)
        mins   = shots / spm
        h,m    = int(mins//60), int(mins%60)
        c1,c2,c3 = st.columns(3)
        c1.metric("📸 Shots",    f"{shots:,}")
        c2.metric("⏱️ Laufzeit", f"{h}h {m}min")
        c3.metric("⚡ Effizienz", f"{factor*100:.0f}%")
        if factor < 0.6:
            st.warning("⚠️ Hoher Verbrauch – Ersatzakku einpacken!")
        st.info(f"💡 Für 8h: ca. **{math.ceil((8*60*spm)/max(shots,1))} Akkus** empfohlen")

# ── 🗺️ SPOTS ───────────────────────────────────────────────────
elif tool == "🗺️ Spots":
    st.header("🗺️ Foto-Spot Manager")
    tab1,tab2 = st.tabs(["➕ Spot hinzufügen","📌 Meine Spots"])

    with tab1:
        c1,c2 = st.columns(2)
        name  = c1.text_input("📍 Name")
        typ   = c2.selectbox("🏷️ Typ", ["Landschaft","Portrait","Street","Architektur","Astro","Sonstiges"])
        c3,c4 = st.columns(2)
        lat   = c3.number_input("Breitengrad",  value=51.34, format="%.4f")
        lon   = c4.number_input("Längengrad",   value=12.38, format="%.4f")
        beste = st.text_input("⏰ Beste Zeit")
        notes = st.text_area("📝 Notizen")

        if st.button("➕ Speichern", type="primary"):
            if name:
                st.session_state.spots.append({
                    "Name":name,"Typ":typ,"Lat":lat,"Lon":lon,
                    "Beste Zeit":beste,"Notizen":notes,
                })
                st.success(f"✅ '{name}' gespeichert!")
                st.rerun()

    with tab2:
        if st.session_state.spots:
            st.dataframe(pd.DataFrame(st.session_state.spots), use_container_width=True)
            last = st.session_state.spots[-1]
            st.markdown(f"🔗 [Letzten Spot auf Google Maps](https://maps.google.com/?q={last['Lat']},{last['Lon']})")
            if st.button("🗑️ Alle löschen"):
                st.session_state.spots = []
                st.rerun()
        else:
            st.info("📭 Noch keine Spots.")

# ── 📄 PDF-PLANER (alter Name) ─────────────────────────────────
elif tool == "📄 PDF-Planer":
    # Redirect zum neuen PDF Export Tool
    st.session_state.tool = "📤 PDF Export"
    st.rerun()

# ── 📈 HISTOGRAMM ──────────────────────────────────────────────
elif tool == "📈 Histogramm":
    st.header("📈 Belichtungs-Histogramm Simulator")
    ev       = st.slider("EV (Helligkeit)", 0, 20, 12)
    contrast = st.slider("Kontrast", 10, 100, 50)

    if st.button("📊 Generieren", type="primary"):
        try:
            import numpy as np
            center = int((ev/20)*255)
            x = np.arange(256)
            y = 1000 * np.exp(-((x-center)**2) / (2*(contrast/2)**2))
            df_hist = pd.DataFrame({"Pixelwert":x,"Häufigkeit":y.astype(int)})
            st.bar_chart(df_hist.set_index("Pixelwert"), use_container_width=True)
            if ev > 17: st.warning("🔴 Überbelichtet!")
            elif ev < 4: st.warning("🔵 Unterbelichtet!")
            else: st.success("🟢 Gut belichtet!")
        except ImportError:
            st.error("numpy fehlt: pip install numpy")

# ── 📸 BRACKETING ASSISTANT ──────────────────────────────────────
elif tool == "📸 Bracketing":
    st.header("📸 Bracketing-Assistant")
    st.markdown("Automatische Serien für HDR, Focus Stacking & kreative Experimente")

    # Tab-Navigation
    tab_exp, tab_foc, tab_wb = st.tabs(["🔆 Exposure (AEB)", "🎯 Focus", "🎨 WB"])

    # ═══════════════════════════════════════════════════════════
    #  🔆 EXPOSURE BRACKETING (AEB)
    # ═══════════════════════════════════════════════════════════
    with tab_exp:
        st.subheader("🔆 Exposure Bracketing für HDR")
        
        col1, col2 = st.columns(2)
        with col1:
            base_ev = st.slider("Basis-Belichtung (EV)", -3.0, 3.0, 0.0, 0.5)
            step_ev = st.selectbox("Schrittweite (Stops)", [0.3, 0.5, 0.7, 1.0, 1.5, 2.0], index=1)
            shots = st.selectbox("Anzahl Bilder", [3, 5, 7, 9], index=0)
        with col2:
            iso = st.number_input("ISO (fest)", 100, 12800, 400, step=100)
            aperture = st.selectbox("Blende (fest)", [1.4,1.8,2.8,4,5.6,8,11,16,22], index=4)
            shutter_base = st.selectbox("Basis-Verschlusszeit", SHUTTERS_ALL, index=6)

        if st.button("✅ AEB-Serie berechnen", type="primary", key="bracket_aeb"):
            base_sec = parse_shutter(shutter_base)
            ev_steps = [(i - shots//2) * step_ev for i in range(shots)]
            
            st.success(f"### 📋 AEB-Serie: {shots} Bilder | Schritt: {step_ev} Stops")
            
            rows = []
            for i, ev in enumerate(ev_steps, 1):
                # Belichtungsanpassung: shutter_sec = base_sec * 2^(-ev)
                shutter_sec = base_sec * (2 ** (-ev))
                # Formatierung
                if shutter_sec >= 1:
                    shutter_str = f"{shutter_sec:.1f}s"
                elif shutter_sec >= 1/30:
                    shutter_str = f"1/{int(round(1/shutter_sec))}s"
                else:
                    shutter_str = f"{shutter_sec:.3f}s"
                
                rows.append({
                    "Bild": f"#{i}",
                    "EV-Korrektur": f"{ev:+.1f}",
                    "Verschlusszeit": shutter_str,
                    "ISO": iso,
                    "Blende": f"f/{aperture}",
                    "Hinweis": "🟢 Normal" if ev == 0 else ("🔵 Unterbelichtet" if ev < 0 else "🟡 Überbelichtet")
                })
            
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            
            # Copy-Button für die Serie
            copy_text = f"AEB {shots}x {step_ev}EV: " + " | ".join([f"{r['EV-Korrektur']}={r['Verschlusszeit']}" for r in rows])
            st.code(copy_text, language="text")
            copy_button(copy_text, label="📋 Serie kopieren")
            
            # Tipps
            with st.expander("💡 AEB-Tipps"):
                st.markdown("""
                - **Stativ verwenden** für perfekte Ausrichtung der HDR-Bilder
                - **Fernauslöser** oder 2s-Selbstauslöser gegen Verwacklung
                - **RAW-Format** für maximale Nachbearbeitungs-Flexibilität
                - **Reihenfolge**: -EV → 0EV → +EV (so sortieren viele HDR-Softwares automatisch)
                - **Belichtungsreihe testen**: Erst 3 Bilder mit 1 Stop, dann bei Bedarf erweitern
                """)

    # ═══════════════════════════════════════════════════════════
    #  🎯 FOCUS BRACKETING
    # ═══════════════════════════════════════════════════════════
    with tab_foc:
        st.subheader("🎯 Focus Bracketing für Stacking")
        
        col1, col2 = st.columns(2)
        with col1:
            focal = st.number_input("Brennweite (mm)", 14, 600, 100)
            aperture = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], index=4)
            sensor = st.selectbox("Sensor", ["Vollformat","APS-C Canon","APS-C Nikon","Micro 4/3"])
            coc = {"Vollformat":0.030,"APS-C Canon":0.019,"APS-C Nikon":0.020,"Micro 4/3":0.015}[sensor]
        with col2:
            start_dist = st.number_input("Start-Entfernung (m)", 0.1, 100.0, 1.0, 0.1)
            end_dist = st.number_input("End-Entfernung (m)", 0.2, 500.0, 10.0, 0.5)
            overlap = st.slider("Überlappung der Schärfenzone (%)", 10, 90, 30)

        if st.button("✅ Fokus-Schritte berechnen", type="primary", key="bracket_focus"):
            # Hyperfokale Distanz: H = f² / (N * c) + f
            f_mm = focal
            H = (f_mm**2) / (aperture * coc) + f_mm  # in mm
            
            # Näherung für Fokus-Schritte (in mm)
            # Schrittweite ≈ (DoF am Startpunkt) * (1 - overlap/100)
            D1 = start_dist * 1000  # in mm
            D2 = end_dist * 1000
            
            # Schärfentiefe am Startpunkt
            near = (H * D1) / (H + D1 - focal)
            far = (H * D1) / (H - D1 + focal) if D1 < H else float("inf")
            dof_start = (far - near) / 1000 if far != float("inf") else 10  # in Meter
            
            # Schrittweite in Meter
            step_m = dof_start * (1 - overlap/100)
            if step_m < 0.01: step_m = 0.01  # Minimum 1 cm
            
            # Anzahl Bilder
            total_dist = end_dist - start_dist
            num_shots = max(2, int(total_dist / step_m) + 1)
            
            st.success(f"### 📋 Fokus-Serie: {num_shots} Bilder")
            st.info(f"**Schrittweite:** {step_m*100:.1f} cm | **Gesamtstrecke:** {total_dist:.1f} m")
            
            # Tabelle mit Fokus-Positionen
            focus_positions = []
            current = start_dist
            for i in range(num_shots):
                focus_positions.append({
                    "Bild": f"#{i+1}",
                    "Fokus auf": f"{current:.2f} m",
                    "Schärfenzone ca.": f"{max(0,current-dof_start/2):.2f} – {min(end_dist,current+dof_start/2):.2f} m"
                })
                current += step_m
            
            st.dataframe(pd.DataFrame(focus_positions), use_container_width=True, hide_index=True)
            
            # Copy-Button
            copy_text = f"Focus Bracketing: {num_shots}x {step_m*100:.1f}cm Schritt | {start_dist}–{end_dist}m"
            st.code(copy_text, language="text")
            copy_button(copy_text, label="📋 Fokus-Plan kopieren")
            
            with st.expander("💡 Focus-Bracketing-Tipps"):
                st.markdown("""
                - **Manueller Fokus** + Focus Peaking verwenden
                - **Stativ** ist Pflicht – keine Bewegung zwischen den Bildern
                - **Belichtung konstant halten** (Manuell-Modus)
                - **Reihenfolge**: Nah → Fern (oder umgekehrt, aber konsistent)
                - **Stacking-Software**: Helicon Focus, Zerene Stacker, Photoshop
                - **Bei Makro**: Schrittweite kann <1mm sein – Fokussierschiene empfohlen!
                """)

    # ═══════════════════════════════════════════════════════════
    #  🎨 WHITE BALANCE BRACKETING
    # ═══════════════════════════════════════════════════════════
    with tab_wb:
        st.subheader("🎨 White Balance Bracketing")
        
        col1, col2 = st.columns(2)
        with col1:
            base_wb = st.selectbox("Basis-WB", [
                "🕯️ Glühlampe (3200K)", "🌅 Sonnenaufgang (4000K)", 
                "☀️ Tageslicht (5200K)", "⛅ Bewölkt (6000K)", 
                "🏔️ Schatten (7500K)", "🌌 Blaue Stunde (9000K)"
            ])
            step_kelvin = st.selectbox("Schrittweite (Kelvin)", [200, 300, 500, 800, 1000], index=1)
            wb_shots = st.selectbox("Anzahl WB-Varianten", [3, 5, 7], index=0)
        with col2:
            st.markdown("**🎨 Farbton-Verschiebung (optional)**")
            tint_step = st.slider("Grün↔Magenta Schritt", -3, 3, 0)
            use_tint = st.checkbox("Farbton-Bracketing aktivieren", value=False)

        if st.button("✅ WB-Serie berechnen", type="primary", key="bracket_wb"):
            # Kelvin-Werte extrahieren
            kelvin_map = {
                "🕯️ Glühlampe (3200K)": 3200, "🌅 Sonnenaufgang (4000K)": 4000,
                "☀️ Tageslicht (5200K)": 5200, "⛅ Bewölkt (6000K)": 6000,
                "🏔️ Schatten (7500K)": 7500, "🌌 Blaue Stunde (9000K)": 9000
            }
            base_k = kelvin_map[base_wb]
            
            # Serie berechnen
            wb_series = []
            offset_range = range(-(wb_shots//2), wb_shots//2 + 1)
            for i, offset in enumerate(offset_range, 1):
                k_val = base_k + offset * step_kelvin
                k_val = max(2000, min(10000, k_val))  # Clamp auf sinnvollen Bereich
                wb_series.append({
                    "Bild": f"#{i}",
                    "Kelvin": f"{k_val}K",
                    "Beschreibung": "🟡 Wärmer" if offset > 0 else ("🔵 Kälter" if offset < 0 else "⚪ Neutral"),
                    "Farbton": f"{tint_step*offset:+d}" if use_tint else "–"
                })
            
            st.success(f"### 📋 WB-Serie: {wb_shots} Varianten | Schritt: {step_kelvin}K")
            st.dataframe(pd.DataFrame(wb_series), use_container_width=True, hide_index=True)
            
            # Copy-Button
            copy_text = f"WB Bracketing: {base_wb} ±{step_kelvin}K x{wb_shots}"
            st.code(copy_text, language="text")
            copy_button(copy_text, label="📋 WB-Plan kopieren")
            
            with st.expander("💡 WB-Bracketing-Tipps"):
                st.markdown("""
                - **RAW fotografieren** – WB kann später beliebig angepasst werden
                - **Bracketing lohnt sich bei**: Gemischtem Licht (Fenster + Lampe), Events, Produktfotos
                - **Farbton-Bracketing**: Hilft bei grünem Kunstlicht oder Magenta-Stich
                - **Alternativ**: Einmal neutral fotografieren, später in Lightroom variieren
                - **Kreativ-Tipp**: Extreme WB-Werte (2000K / 10000K) für künstlerische Effekte
                """)

    # ═══════════════════════════════════════════════════════════
    #  🎁 BONUS: ALL-IN-ONE BRACKETING PLANER
    # ═══════════════════════════════════════════════════════════
    st.divider()
    with st.expander("🎁 Bonus: Kompletten Bracketing-Plan erstellen"):
        st.markdown("Kombiniere mehrere Bracketing-Typen für maximale Flexibilität")
        
        c1, c2 = st.columns(2)
        with c1:
            use_aeb = st.checkbox("🔆 Exposure Bracketing", value=True)
            use_focus = st.checkbox("🎯 Focus Bracketing", value=False)
        with c2:
            use_wb = st.checkbox("🎨 WB Bracketing", value=False)
            total_shots = 1
            if use_aeb: total_shots *= shots
            if use_focus: total_shots *= num_shots if 'num_shots' in locals() else 5
            if use_wb: total_shots *= wb_shots
            st.metric("📸 Geschätzte Gesamtzahl Bilder", f"{total_shots}")
        
        if st.button("📄 Bracketing-Plan als PDF"):
            st.info("💡 Kombiniertes Bracketing erzeugt viele Bilder – nur bei Stativ + ausreichend Speicher nutzen!")
            st.warning(f"⚠️ {total_shots} Bilder können schnell 2-5 GB Speicher belegen (RAW)")

    st.caption("💡 Bracketing ist eine Profi-Technik – übe zuerst mit 3-Bild-Serien!")

elif tool == "📱 AR-Brennweiten-Vorschau":
    st.header("📱 AR-Brennweiten-Vorschau")
    st.markdown("Halte dein Handy hoch und sieh live, wie viel Motiv verschiedene Objektive erfassen.")

    ar_html = """
    <style>
      body { margin:0; background:#0A0E14; font-family:system-ui; color:#F0F6FC; overflow:hidden; }
      #cam-container { position:relative; width:100vw; height:100vh; display:flex; align-items:center; justify-content:center; }
      video { width:100%; height:100%; object-fit:cover; transform:scaleX(-1); }
      #fov-overlay { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); border:2px solid #58A6FF; box-shadow:0 0 0 9999px rgba(0,0,0,0.6); transition:all 0.3s ease; }
      .controls { position:absolute; bottom:20px; left:0; width:100%; display:flex; flex-wrap:wrap; justify-content:center; gap:8px; padding:0 10px; }
      .btn { padding:10px 16px; background:#1F6FEB; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; }
      .btn.active { background:#58A6FF; }
      .info { position:absolute; top:15px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.7); padding:6px 12px; border-radius:6px; font-size:14px; text-align:center; }
      .ratio-btn { background:#21262D; }
    </style>
    <div id="cam-container">
      <video id="cam" autoplay playsinline muted></video>
      <div id="fov-overlay"></div>
      <div class="info" id="fov-info">24mm | 3:2</div>
      <div class="controls">
        <button class="btn" onclick="setFocal(14)">14mm</button>
        <button class="btn active" onclick="setFocal(24)">24mm</button>
        <button class="btn" onclick="setFocal(35)">35mm</button>
        <button class="btn" onclick="setFocal(50)">50mm</button>
        <button class="btn" onclick="setFocal(85)">85mm</button>
        <button class="btn" onclick="setFocal(135)">135mm</button>
        <button class="btn ratio-btn" onclick="toggleRatio()">3:2 ⇄ 16:9</button>
      </div>
    </div>
    <script>
      let currentFocal = 24;
      let ratio = "3:2";
      const video = document.getElementById('cam');
      const overlay = document.getElementById('fov-overlay');
      const info = document.getElementById('fov-info');

      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => video.srcObject = stream)
        .catch(() => {
          document.body.innerHTML = "<div style='padding:40px;text-align:center;'>📷 Kamera-Zugriff verweigert.<br>Nutze manuelle Planung im Rechner.</div>";
        });

      function setFocal(f) {
        currentFocal = f;
        document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
        updateOverlay();
      }

      function toggleRatio() {
        ratio = ratio === "3:2" ? "16:9" : "3:2";
        updateOverlay();
      }

      function updateOverlay() {
        // FOV-Skalierung: 24mm = 100%, 50mm = 48%, 85mm = 28% etc.
        const scale = 24 / currentFocal;
        const [w, h] = ratio === "3:2" ? [300 * scale, 200 * scale] : [320 * scale, 180 * scale];
        overlay.style.width = w + 'px';
        overlay.style.height = h + 'px';
        info.textContent = `${currentFocal}mm | ${ratio}`;
      }
      updateOverlay();
    </script>
    """
    st.components.v1.html(ar_html, height=600, scrolling=False)

    st.divider()
    st.markdown("""
    💡 **Profi-Tipp:** 
    - Nutze **24mm** als Referenz für Weitwinkel-Landschaften
    - **50mm** entspricht ungefähr dem natürlichen menschlichen Blickfeld
    - **85mm+** komprimiert Perspektive – ideal für Portraits & Details
    """)

# ──  DYNAMIKUMFANG & KONTRAST ───────────────────────────────────
elif tool == "📊 Dynamikumfang & Kontrast":
    st.header("📊 Dynamikumfang & Bracketing-Rechner")
    st.markdown("Berechne exakt, wie viele Aufnahmen du für HDR/TONEMAPPING benötigst.")

    # 1. Sauberes Dictionary: Der Text (Key) muss exakt so im SelectBox stehen
    DR_OPTIONS = {
        "🌫️ Bewölkt / Nebel (8–10 Stops)": 9.0,
        "🌳 Wald / Schatten (10–12 Stops)": 11.0,
        "🏔️ Landschaft / Sonne (12–14 Stops)": 13.0,
        "🌅 Sonnenuntergang / Silhouette (16–18 Stops)": 17.0,
        "🪟 Innenraum + Fenster (18–20 Stops)": 19.0,
        "🌃 Nachtaufnahme / Stadt (14–16 Stops)": 15.0,
    }

    col1, col2 = st.columns(2)
    with col1:
        # Auswahl NUR der Keys aus dem Dictionary + Manuelle Option
        available_keys = list(DR_OPTIONS.keys()) + ["⚙️ Manuell eingeben..."]
        scene_label = st.selectbox("🌍 Szenen-Typ", available_keys)
        
        # Value holen
        if scene_label == "️ Manuell eingeben...":
            scene_dr = st.number_input("Szenen-Dynamikumfang (Stops)", 6.0, 24.0, 14.0, 0.5)
        else:
            scene_dr = DR_OPTIONS[scene_label]

    with col2:
        iso = st.selectbox("📷 Aufnahme-ISO", [100, 200, 400, 800, 1600, 3200, 6400], index=0)
        # Canon EOS R Sensor-Daten (ca.)
        cam_dr_map = {100:13.6, 200:13.1, 400:12.4, 800:11.7, 1600:11.0, 3200:10.2, 6400:9.4}
        cam_dr = cam_dr_map[iso]
        st.metric(" Sensor-Dynamikumfang (ca.)", f"{cam_dr:.1f} Stops")
        step_ev = st.selectbox("🔢 Bracketing-Schrittweite", [0.5, 1.0, 1.5, 2.0], index=1)

    if st.button("✅ Bracketing-Bedarf berechnen", type="primary", key="calc_dr"):
        # Berechnung: (Szenen-Kontrast minus Sensor-DR) durch Schrittweite
        diff = max(0, scene_dr - cam_dr)
        shots = max(1, math.ceil(diff / step_ev) + 1)
        
        ev_offsets = [(i - shots//2) * step_ev for i in range(shots)]
        
        st.success(f"### 📸 Empfehlung: {shots} Bilder für {scene_dr:.1f} Stops Szene")
        
        rows = []
        for i, ev in enumerate(ev_offsets, 1):
            rows.append({
                "Bild": f"#{i}",
                "EV-Korrektur": f"{ev:+.1f}",
                "Abdeckung": f"{max(0, cam_dr - abs(ev)):.1f}–{cam_dr + abs(ev):.1f} Stops",
                "Hinweis": "🟢 Basis" if ev == 0 else ("🔵 Schatten" if ev < 0 else "🟡 Lichter")
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        
        copy_text = f"HDR-Bracketing: {shots}x {step_ev}EV | ISO {iso} | Szene: {scene_dr:.0f} Stops"
        st.code(copy_text, language="text")
        copy_button(copy_text, label="📋 Plan kopieren")
        
        with st.expander("💡 Profi-Empfehlungen"):
            st.markdown(f"""
            - **Sensor-Grenze:** Bei ISO {iso} deckt deine Canon EOS R ~{cam_dr:.1f} Stops ab.
            - **Überlappung:** Automatisch ~1 Stop für nahtloses Tonemapping.
            - **RAW ist Pflicht:** JPEG verliert bereits in der Kamera Dynamikumfang.
            - **Stativ & Fernauslöser:** Ab 3 Bildern kritisch für Pixel-genaue Ausrichtung.
            - **Software:** Lightroom HDR Merge, Photomatix, oder Aurora HDR.
            """)

            

# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════
st.divider()
st.markdown(
    "<div style='text-align:center;color:#8B949E;font-size:0.85em;'>"
    "📷 Canon EOS R – Pro Tool v9.0 | "
    "Mondphase: Jean-Meeus-Algorithmus | GPS: Query-Params-Methode<br>"
    "Alle Berechnungen sind Richtwerte – Praxistests empfohlen."
    "</div>",
    unsafe_allow_html=True,
)

