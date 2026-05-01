# web_app_optimized.py – Canon EOS R Pro Tool (Optimierte Version v8.0)
# ──────────────────────────────────────────────────────────────────
# ÄNDERUNGEN v8.0:
#  • Sidebar-Navigation vollständig korrigiert (expander.button statt st.sidebar.button)
#  • Alle fehlenden elif-Blöcke ergänzt/korrigiert
#  • Einheitliche Key-Vergabe für alle Widgets
#  • GPS-Tool verbessert
#  • Fehlerbehandlung vereinheitlicht
#  • Imports bereinigt und gruppiert
# ──────────────────────────────────────────────────────────────────

import math
import os
import io
import pandas as pd
from datetime import datetime, timedelta

import streamlit as st
import requests
import streamlit.components.v1 as components


# ── Optionale Imports ────────────────────────────────────────────
try:
    from astral import LocationInfo
    from astral.sun import sun
    import pytz
    ASTRAL_OK = True
except Exception as _e:
    ASTRAL_OK = False
    _ASTRAL_ERR = str(_e)

# Cache-Invalidation für Status-Bar
if st.session_state.get("force_refresh_weather", False):
    st.cache_data.clear()
    st.session_state.force_refresh_weather = False

# ════════════════════════════════════════════════════════════════
#  KONSTANTEN
# ════════════════════════════════════════════════════════════════

SHUTTER_MAP: dict[str, float] = {
    "1/8000": 1 / 8000, "1/4000": 1 / 4000, "1/2000": 1 / 2000,
    "1/1000": 1 / 1000, "1/500":  1 / 500,  "1/250":  1 / 250,
    "1/125":  1 / 125,  "1/60":   1 / 60,   "1/30":   1 / 30,
    "1/15":   1 / 15,   "1/8":    1 / 8,    "1/4":    1 / 4,
    "1/2":    1 / 2,    "1":      1.0,       "2":      2.0,
    "4":      4.0,      "8":      8.0,       "15":     15.0,
    "30":     30.0,     "60":     60.0,
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
    "Vollformat (36×24 mm)":      0.030,
    "APS-C Canon (1.6×)":         0.019,
    "APS-C Nikon/Sony (1.5×)":    0.020,
    "Micro 4/3 (2.0×)":           0.015,
}

CROP_MAP: dict[str, float] = {
    "Vollformat (1.0×)":        1.0,
    "APS-C Canon (1.6×)":       1.6,
    "APS-C Nikon/Sony (1.5×)":  1.5,
    "Micro 4/3 (2.0×)":         2.0,
    "1 Zoll (2.7×)":            2.7,
    "Smartphone (~6×)":         6.0,
}

SHUTTERS_ALL = [
    "1/8000","1/4000","1/2000","1/1000","1/500","1/250",
    "1/125","1/60","1/30","1/15","1/8","1/4","1/2",
    "1","2","4","8","15","30","60",
]

# ════════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN
# ════════════════════════════════════════════════════════════════

import streamlit.components.v1 as components

def copy_button(text_to_copy: str, label: str = " Kopieren"):
    """Erstellt einen Button, der Text in die Zwischenablage kopiert."""
    # Eindeutige ID für den Button generieren
    btn_id = f"btn_{hash(text_to_copy)}"
    
    components.html(f"""
    <style>
    .copy-btn {{
        background: #238636; color: white; border: none;
        padding: 8px 16px; border-radius: 6px; cursor: pointer;
        font-size: 14px; font-weight: bold;
        transition: background 0.2s;
    }}
    .copy-btn:hover {{ background: #2ea043; }}
    .copy-btn:active {{ transform: scale(0.98); }}
    </style>
    <button class="copy-btn" onclick="copy_{btn_id}()">{label}</button>
    <script>
    function copy_{btn_id}() {{
        navigator.clipboard.writeText('{text_to_copy.replace("'", "\\'")}');
        const btn = document.querySelector('.copy-btn');
        const originalText = btn.innerText;
        btn.innerText = "✅ Kopiert!";
        btn.style.background = "#1F6FEB";
        setTimeout(() => {{
            btn.innerText = originalText;
            btn.style.background = "#238636";
        }}, 2000);
    }}
    </script>
    """, height=50)
def parse_shutter(s: str) -> float:
    return SHUTTER_MAP.get(s, 1 / 125)


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
    """Gibt Fotografie-Tipps basierend auf Gezeitenzustand zurück."""
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
    fmt     = "%H:%M"
    sunrise = datetime.strptime(sr, fmt)
    sunset  = datetime.strptime(ss, fmt)
    return {
        "golden_morning": (sunrise.strftime(fmt),                              (sunrise + timedelta(minutes=60)).strftime(fmt)),
        "golden_evening": ((sunset - timedelta(minutes=60)).strftime(fmt),     sunset.strftime(fmt)),
        "blue_morning":   ((sunrise - timedelta(minutes=30)).strftime(fmt),    sunrise.strftime(fmt)),
        "blue_evening":   (sunset.strftime(fmt),                               (sunset + timedelta(minutes=30)).strftime(fmt)),
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

# ═══════════════════════════════════════════
#  📱 PWA & HOME-SCREEN (iOS-Optimiert)
# ══════════════════════════════════════════
import streamlit.components.v1 as components

components.html("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1F6FEB">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Canon Pro">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2983/2983796.png">
""", height=0)





# ════════════════════════════════════════════════════════════════
#  APP-KONFIGURATION & CSS
# ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Canon EOS R – Pro Tool",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ═══════════════════════════════════════════
#   LIVE STATUS BAR (Minimal-Fix)
# ══════════════════════════════════════════
def render_status_bar():
    import time
    
    # GPS-Daten holen
    gps = st.session_state.get("gps_coords")
    
    # Standort-Anzeige vorbereiten
    loc_display = "📍 Nicht gesetzt"
    place_name = None
    
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            
            # 🌍 Reverse Geocoding: Koordinaten → Ortsname (via OpenStreetMap Nominatim)
            @st.cache_data(ttl=3600)  # 1 Stunde cachen → spart API-Calls
            def get_place_name(lat, lon):
                try:
                    r = requests.get(
                        f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1&accept-language=de",
                        headers={"User-Agent": "CanonProTool/1.0"},
                        timeout=3
                    )
                    if r.status_code == 200:
                        data = r.json()
                        addr = data.get("address", {})
                        # Priorisierte Ortsnamen-Extraktion
                        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
                        county = addr.get("county") or addr.get("state_district")
                        state = addr.get("state")
                        country = addr.get("country")
                        country_code = addr.get("country_code", "").upper()
                        
                        if city and country_code:
                            return f"{city}, {country_code}"
                        elif county and country_code:
                            return f"{county}, {country_code}"
                        elif state and country:
                            return f"{state}, {country}"
                        elif country:
                            return country
                except:
                    pass
                return None
            
            place_name = get_place_name(lat, lon)
            
            # Anzeige: Ortsname bevorzugen, sonst Koordinaten
            if place_name:
                loc_display = f"📍 {place_name}"
            else:
                loc_display = f"📍 {lat:.2f}, {lon:.2f}"
                
        except:
            loc_display = str(gps) if gps else "📍 Nicht gesetzt"
    else:
        loc_display = str(gps) if gps else "📍 Nicht gesetzt"
    
    # Wetter laden (nur wenn GPS da)
    temp, desc = "--", "Warten auf GPS"
    if gps and "," in str(gps):
        try:
            lat, lon = map(float, str(gps).split(","))
            key = st.secrets.get("OPENWEATHER_API_KEY")
            if key:
                r = requests.get(
                    f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&lang=de", 
                    timeout=3
                )
                if r.status_code == 200:
                    d = r.json()
                    temp = f"{d['main']['temp']:.1f}°C"
                    desc = d['weather'][0]['description'].capitalize()
        except:
            temp, desc = "--", "Daten n/a"

    # Status-Bar UI rendern
    st.markdown("""
    <div style='background:#0D1117; padding:10px; margin-bottom:15px; border-radius:8px; border:1px solid #21262D;'>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns([3, 2.5, 2.5, 1])
    c1.markdown(f"{loc_display}<br><small style='color:#8B949E; font-size:11px;'>{gps if gps and ',' in str(gps) else ''}</small>", unsafe_allow_html=True)
    c2.markdown(f"☁️ **Wetter**<br><small style='color:#8B949E'>{temp} | {desc}</small>", unsafe_allow_html=True)
    c3.markdown(f"📷 **Status**<br><small style='color:#8B949E'>Live</small>", unsafe_allow_html=True)
    
    if c4.button("🔄", use_container_width=True, key="sb_refresh"):
        st.cache_data.clear()
        
    st.markdown("</div>", unsafe_allow_html=True)

# ⚠️ Diese Zeile MUSS nach der Definition und VOR der Sidebar stehen:
render_status_bar()

st.markdown("""
<style>
  /* Globale Einstellungen */
  .main { 
      background-color: #0A0E14; 
      color: #F0F6FC; 
  }
  h1, h2, h3 { 
      color: #58A6FF; 
  }
  
  /* Buttons */
  .stButton>button {
      background-color: #1F6FEB; 
      color: white;
      border-radius: 8px; 
      border: none;
      padding: 10px 24px; 
      font-weight: bold;
  }
  .stButton>button:hover { 
      background-color: #58A6FF; 
  }
  
  /* Mobile Optimierung (iPhone) */
  @media (max-width: 768px) {
    /* Mehr Padding für Touch */
    .main .block-container { 
        padding: 1rem !important; 
        padding-top: 2rem !important;
    }
    
    /* Größere Eingabefelder (verhindert Zoom auf iPhone) */
    .stTextInput input, 
    .stSelectbox div,
    .stNumberInput input { 
        font-size: 16px !important; 
        min-height: 48px !important; 
    }
    
    /* Größere Buttons für Daumenbedienung */
    .stButton>button { 
        min-height: 48px !important; 
        font-size: 16px !important;
        padding: 12px 24px !important;
    }
    
    /* Status-Bar kompakter auf Mobile */
    .status-bar-mobile {
        font-size: 12px !important;
        padding: 8px !important;
    }
    
    /* Dashboard-Kacheln größer auf Mobile */
    .dash-card > button {
        height: 90px !important;
        font-size: 15px !important;
    }
    
    /* Sidebar besser nutzbar */
    section[data-testid="stSidebar"] {
        width: 280px !important;
    }
  }
  
  /* Desktop: Sidebar schmaler */
  @media (min-width: 769px) {
    section[data-testid="stSidebar"] {
        width: 240px !important;
    }
  }
  
  /* Verhindert Zoom auf iPhone bei Fokus */
  input, select, textarea { 
      font-size: 16px !important; 
  }
  
  /* Bessere Lesbarkeit */
  .stMarkdown, .stText {
      font-size: 15px;
      line-height: 1.6;
  }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════

st.title("📷 CANON EOS R – PRO TOOL")
st.markdown("**Web Version** | 30 Photography Tools")
st.divider()

# ════════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════════

if "tool" not in st.session_state:
    st.session_state.tool = "🏠 Home"
if "logbook" not in st.session_state:
    st.session_state.logbook = []
if "spots" not in st.session_state:
    st.session_state.spots = []
if "gps_coords" not in st.session_state:
    st.session_state.gps_coords = "Berlin"


def set_tool(t: str):
    st.session_state.tool = t

# ═══════════════════════════════════════════
#  NAVIGATION STATE (MUSS VOR SIDEBAR STEHEN!)
# ══════════════════════════════════════════
if "tool" not in st.session_state:
    st.session_state.tool = "🏠 Home"  # Standard-Startseite

tool = st.session_state.tool  # ✅ Jetzt ist `tool` definiert!


# ════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION (Optimiert für iPhone)
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("📷 Canon Pro Tool")
    st.caption("30 Photography Tools")
    st.divider()

    #  Home-Button (immer sichtbar)
    if st.button("🏠 Home", use_container_width=True, type="primary" if tool == "🏠 Home" else "secondary"):
        st.session_state.tool = "🏠 Home"
        st.rerun()
    
    st.divider()

    #  Ordner 1: BELICHTUNG & FOKUS (geschlossen beim Start)
    with st.expander("⚙️ Belichtung & Fokus", expanded=False):
        if st.button("⚙️ Belichtung", use_container_width=True):
            st.session_state.tool = "⚙️ Belichtung"
            st.rerun()
        if st.button("🕶️ ND Rechner", use_container_width=True):
            st.session_state.tool = "🕶️ ND Rechner"
            st.rerun()
        if st.button("📐 Schärfentiefe", use_container_width=True):
            st.session_state.tool = "📐 Schärfentiefe"
            st.rerun()
        if st.button("🔬 Focus Stacking", use_container_width=True):
            st.session_state.tool = "🔬 Focus Stacking"
            st.rerun()
        if st.button("🎛️ ND Stacking", use_container_width=True):
            st.session_state.tool = "🎛️ ND Stacking"
            st.rerun()

    #  Ordner 2: PLANUNG & UMGEBUNG (geschlossen beim Start)
    with st.expander("🌍 Planung & Umgebung", expanded=False):
        if st.button("🌍 Astro & Wetter Dashboard", use_container_width=True):
            st.session_state.tool = "🌍 Astro & Wetter Dashboard"
            st.rerun()
        if st.button("🌙 Mond & Milchstraße", use_container_width=True):
            st.session_state.tool = "🌙 Mond & Milchstraße"
            st.rerun()
        if st.button("🌊 Gezeiten & Tide-Rechner", use_container_width=True):
            st.session_state.tool = "🌊 Gezeiten & Tide-Rechner"
            st.rerun()
        if st.button("📍 GPS-Standort", use_container_width=True):
            st.session_state.tool = "📍 GPS-Standort"
            st.rerun()
        if st.button("📝 Planer", use_container_width=True):
            st.session_state.tool = "📝 Planer"
            st.rerun()

    #  Ordner 3: SPEZIAL-MODI (geschlossen beim Start)
    with st.expander("🎨 Spezial-Modi", expanded=False):
        if st.button("🤿 Unterwasser-Modus", use_container_width=True):
            st.session_state.tool = "🤿 Unterwasser-Modus"
            st.rerun()
        if st.button("📸 Kamera-Vergleich", use_container_width=True):
            st.session_state.tool = "📸 Kamera-Vergleich"
            st.rerun()
        if st.button("📤 PDF Export", use_container_width=True):
            st.session_state.tool = "📤 PDF Export"
            st.rerun()
        # ... weitere Tools aus Ordner 3 ...

    st.divider()
    st.caption("💡 Tipp: Ordner aufklappen für alle Tools")

# ════════════════════════════════════════════════════════════════
#  TOOLS – HAUPTINHALT
# ════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════
#  📱 MOBILE DASHBOARD (Startseite)
# ══════════════════════════════════════════
if tool == "🏠 Home":
    st.markdown("""
    <style>
    .dash-card > button {
        height: 90px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        border-radius: 12px !important;
        background-color: #161B22 !important;
        color: #F0F6FC !important;
        border: 1px solid #30363D !important;
        white-space: pre-line !important;
        line-height: 1.3 !important;
        transition: all 0.2s ease !important;
        margin-bottom: 10px !important;
    }
    .dash-card > button:hover {
        background-color: #1F6FEB !important;
        border-color: #58A6FF !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(31, 111, 235, 0.3) !important;
    }
    .dash-card > button:active {
        transform: scale(0.98) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    st.header("📸 Canon Pro Tool")
    st.markdown("**Schnellzugriff** – Tippe auf eine Kachel")
    st.markdown("</div>", unsafe_allow_html=True)

    dash_tools = [
        ("⚙️ Belichtung", "EV-Werte & Dreieck"),
        ("🕶️ ND Rechner", "Filter & Stacking"),
        ("📐 Schärfentiefe", "DoF & Hyperfokal"),
        ("🌍 Astro & Wetter", "Planung & Live"),
        ("🌙 Mond & Milchstraße", "Phasen & Sichtbarkeit"),
        ("🌊 Gezeiten & Tide-Rechner"), "Ebbe & Flut"),
        ("📍 GPS-Standort", "Standort & Wetter"),
        ("🤿 Unterwasser-Modus", "Canon & Apexcam"),
    ]

    cols = st.columns(2)
    for i, (name, desc) in enumerate(dash_tools):
        with cols[i % 2]:
            with st.container():
                st.markdown('<div class="dash-card">', unsafe_allow_html=True)
                if st.button(f"{name}\n{desc}", use_container_width=True, type="secondary", key=f"home_{name}"):
                    st.session_state.tool = name
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #8B949E; font-size: 13px;'>
    💡 Nutze die Sidebar für alle 30 Tools<br>
    📱 GPS-Daten werden automatisch übernommen
    </div>
    """, unsafe_allow_html=True)
    
# ── ⚙️ BELICHTUNG ────────────────────────────────────────────────
elif tool == "⚙️ Belichtung":
    st.header("⚙️ Belichtung-Bewerter")
    col1, col2, col3 = st.columns(3)
    with col1:
        iso = st.selectbox("ISO", [100, 200, 400, 800, 1600, 3200, 6400, 12800], index=0)
    with col2:
        aperture = st.selectbox("Blende", [1.4, 1.8, 2.8, 4.0, 5.6, 8.0, 11, 16, 22], index=3)
    with col3:
        shutter_str = st.selectbox("Verschlusszeit", SHUTTERS_ALL, index=6)

    shutter = parse_shutter(shutter_str)
    if st.button("📊 Bewerten", type="primary"):
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

# ── 🕶️ ND RECHNER ───────────────────────────────────────────────
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
        
        # Formatierung
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

        # 📋 KOPPER-BUTTON (Streamlit Native - funktioniert garantiert!)
        st.markdown("**📋 Ergebnis für Notizen:**")
        copy_text = f"ND{nd_factor} | {base_str} → {result_str}"
        st.code(copy_text, language="text")
        st.caption("💡 Tippe auf das **Kopier-Icon** rechts im Code-Block!")

# ════════════════════════════════════════════════════════════════
#  🔬 FOCUS STACKING ASSISTANT
# ═══════════════════════════════════════════════════════════════

elif tool == "🔬 Focus Stacking":
    st.header("🔬 Focus Stacking Assistant")
    st.markdown("Berechne exakte Fokusschritte für maximale Schärfentiefe")
    
    col1, col2 = st.columns(2)
    with col1:
        focal = st.number_input(" Brennweite (mm)", min_value=10, max_value=600, value=100)
        aperture = st.number_input("🔘 Blende (f/)", min_value=1.0, max_value=32.0, value=5.6, step=0.1)
        
    with col2:
        sensor = st.selectbox("📐 Sensor", ["Vollformat (0.03mm)", "APS-C (0.02mm)", "Micro 4/3 (0.015mm)"])
        coc = 0.03 if "Voll" in sensor else (0.02 if "APS" in sensor else 0.015)
        
        # Start-Entfernung (nächster Punkt, der scharf sein soll)
        start_dist_m = st.number_input("📏 Start-Entfernung (m)", min_value=0.1, max_value=1000.0, value=0.5, step=0.1)
        overlap = st.slider("🔄 Überlappung (%)", 10, 90, 30)

    #  Berechnung
    if st.button("✅ Fokusschritte berechnen", type="primary"):
        try:
            # Hyperfokale Distanz berechnen (in mm)
            # H = (f^2) / (N * c) + f
            H = (focal**2) / (aperture * coc) + focal
            
            # Start-Entfernung in mm
            D_start = start_dist_m * 1000
            
            # Nahe und Ferne Schärfengrenze für den Startpunkt
            # S_near = (H * D) / (H + D)
            # S_far = (H * D) / (H - D)
            
            S_near = (H * D_start) / (H + D_start)
            
            # Wenn Startpunkt hinter der Hyperfokalen liegt, ist alles bis Unendlich scharf
            if D_start >= H:
                st.success(f"✅ **Alles scharf!** Dein Startpunkt ({start_dist_m}m) liegt hinter der hyperfokalen Distanz ({H/1000:.2f}m).")
                st.info("💡 Du brauchst kein Stacking! Stelle auf f/{aperture} und fokusiere auf {start_dist_m}m.")
            else:
                S_far = (H * D_start) / (H - D_start)
                dof = S_far - S_near
                
                # Optimale Schrittweite: 70% der DoF, um Lücken zu vermeiden (je nach Overlap)
                # Je höher der Overlap, desto kleiner der Schritt
                step_size_mm = dof * ((100 - overlap) / 100)
                step_size_cm = step_size_mm / 10
                
                # Geschätzte Anzahl der Schritte bis Unendlich
                # Formel approximiert die Verteilung der Schärfentiefe
                # Bei kleinen Entfernungen ist der Schritt klein, bei großen groß.
                # Wir machen eine simple Schätzung für die ersten Meter + Hinweis auf Unendlich
                
                estimated_shots = int((10.0 * 1000) / step_size_mm) if step_size_mm > 0 else 1
                if estimated_shots > 100: estimated_shots = "100+"
                
                st.success(f"""
                ### 📸 Fokus-Plan für Start: {start_dist_m}m
                
                | Parameter | Wert |
                |---|---|
                | **Hyperfokale Distanz** | {H/1000:.2f} m |
                | **Schärfentiefe am Start** | {dof/1000:.3f} m |
                | **Empfohlene Schrittweite** | **{step_size_cm:.1f} cm** |
                """)
                
                st.warning(f"⚠️ **Anleitung:**")
                st.markdown(f"""
                1. Fokusiere manuell auf **{start_dist_m}m**.
                2. Mache das erste Foto.
                3. Drehe den Fokusring um **{step_size_cm:.1f} cm** (weg von dir / Richtung Unendlich).
                4. Mache das nächste Foto.
                5. Wiederhole dies, bis der Hintergrund unscharf wird (ca. {estimated_shots} Bilder für die ersten 10m).
                """)
                
                if step_size_cm < 0.5:
                    st.error("🔴 **Achtung:** Sehr kleine Schrittweite! Benutze ein Makro-Schienensystem oder Focus-Rail.")
                elif focal > 100:
                    st.info("📏 **Tipp:** Bei Tele-Brennweiten wirkt sich bereits minimale Bewegung stark aus. Stativ ist Pflicht.")
                    
        except Exception as e:
            st.error(f"Fehler: {e}")

# ════════════════════════════════════════════════════════════════
#  ️ ND FILTER STACKING RECHNER
# ═══════════════════════════════════════════════════════════════

elif tool == "🎛️ ND Stacking":
    st.header("🎛️ ND Filter Stacking Rechner")
    st.markdown("Berechne Belichtungszeiten bei **kombinierten ND-Filtern**")

    ND_FILTERS = [
        ("Kein Filter", 0, 1), ("ND2 (1 Stop)", 1, 2), ("ND4 (2 Stops)", 2, 4),
        ("ND8 (3 Stops)", 3, 8), ("ND16 (4 Stops)", 4, 16), ("ND32 (5 Stops)", 5, 32),
        ("ND64 (6 Stops)", 6, 64), ("ND128 (7 Stops)", 7, 128), ("ND256 (8 Stops)", 8, 256),
        ("ND512 (9 Stops)", 9, 512), ("ND1000 (10 Stops)", 10, 1000), ("ND2000 (11 Stops)", 11, 2000),
        ("ND4000 (12 Stops)", 12, 4000),
    ]

    col1, col2, col3 = st.columns(3)
    with col1:
        base_str = st.selectbox("📸 Basiszeit (ohne Filter)",
            ["1/8000", "1/4000", "1/2000", "1/1000", "1/500", "1/250", "1/125", "1/60", "1/30", "1/15", "1/8", "1/4", "1/2", "1", "2", "4", "8", "15", "30", "60"],
            index=6)
    with col2:
        filter_a = st.selectbox("🔷 Filter A", [f[0] for f in ND_FILTERS], index=0)
    with col3:
        filter_b = st.selectbox("🔶 Filter B", [f[0] for f in ND_FILTERS], index=0)

    # Optionaler dritter Filter (sicher implementiert)
    with st.expander("➕ Dritten Filter hinzufügen (optional)"):
        filter_c = st.selectbox("🔺 Filter C", [f[0] for f in ND_FILTERS], index=0)
        use_c = st.checkbox("Filter C aktivieren", value=False)

    if st.button("✅ Stacking berechnen", type="primary"):
        # Basiszeit parsen
        if "/" in base_str:
            num, den = map(int, base_str.split("/"))
            base_sec = num / den
        else:
            base_sec = float(base_str)

        def get_filter_data(name):
            for n, stops, factor in ND_FILTERS:
                if n == name:
                    return stops, factor
            return 0, 1

        stops_a, factor_a = get_filter_data(filter_a)
        stops_b, factor_b = get_filter_data(filter_b)
        stops_c, factor_c = (0, 1)
        if use_c:
            stops_c, factor_c = get_filter_data(filter_c)

        total_stops = stops_a + stops_b + stops_c
        total_factor = factor_a * factor_b * factor_c
        result_sec = base_sec * total_factor

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
        - **Filter A:** {filter_a} ({stops_a} Stops)
        - **Filter B:** {filter_b} ({stops_b} Stops)
        - **Filter C:** {filter_c if use_c else "–"} {f"({stops_c} Stops)" if use_c else ""}
        - **Σ Gesamt-Stops:** {total_stops} Stops
        - ** ND-Faktor:** ND{total_factor}
        - **⏱️ Neue Belichtungszeit:** **{result_str}**
        """)

        if total_stops >= 6:
            st.warning("⚠️ **Ab 6 Stops:** Stativ + Fernauslöser zwingend empfohlen!")
        if total_stops >= 10:
            st.error("🔴 **Über 10 Stops:** Spiegel vorbelichten (Live View), Langzeitrauschreduktion erwägen!")
        if result_sec > 300:
            st.info("💡 **Tipp:** Bei >5 Min. Belichtung: Bulb-Modus + Intervalometer nutzen")

# ── 📐 SCHÄRFENTIEFE ─────────────────────────────────────────────
elif tool == "📐 Schärfentiefe":
    st.header("📐 Schärfentiefe-Rechner")
    col1, col2, col3 = st.columns(3)
    with col1:
        focal    = st.number_input("Brennweite (mm)", 14, 800, 50)
    with col2:
        aperture = st.selectbox("Blende (f/)", [1.2, 1.4, 1.8, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16, 22], index=4)
    with col3:
        distance = st.number_input("Entfernung (m)", 0.3, 500.0, 3.0, 0.1)

    sensor = st.selectbox("Sensor", list(COC_MAP.keys()))
    coc    = COC_MAP[sensor]

    if st.button("✅ Berechnen", type="primary"):
        near, far, total, hyper = calculate_dof(focal, aperture, distance, coc)
        far_str   = "∞"                  if far   == float("inf") else f"{far:.2f} m"
        total_str = "∞ (alles scharf)"   if total == float("inf") else f"{total:.2f} m"
        st.success(f"""
        ### 📊 Ergebnisse:
        - **Nahpunkt:** {near:.2f} m
        - **Fernpunkt:** {far_str}
        - **Schärfentiefe:** {total_str}
        - **Hyperfokale Distanz:** {hyper:.1f} m
        """)
        if distance >= hyper:
            st.info("💡 Fokus jenseits der hyperfokalen Distanz – alles bis ∞ ist scharf!")
        elif distance < 1.0:
            st.info("💡 Sehr kurze Distanz – Schärfentiefe sehr gering. Stativ empfohlen.")

# ── 🔦 BLITZ ─────────────────────────────────────────────────────
elif tool == "🔦 Blitz":
    st.header("🔦 Blitz-Rechner (Leitzahl)")
    col1, col2, col3 = st.columns(3)
    with col1:
        gn       = st.number_input("Leitzahl (GN)", 10, 100, 58)
    with col2:
        distance = st.number_input("Entfernung (m)", 0.5, 50.0, 5.0, 0.5)
    with col3:
        iso      = st.selectbox("ISO", [100, 200, 400, 800, 1600, 3200], index=0)

    if st.button("✅ Berechnen", type="primary"):
        ap = calculate_flash(gn, distance, iso)
        st.success(f"""
        ### Ergebnis:
        - **Empfohlene Blende:** f/{ap}
        - **GN {gn} | {distance} m | ISO {iso}**
        """)
        with st.expander("📋 Reichweiten-Tabelle"):
            rows = [
                {"Blende": f"f/{f}", "Max. Reichweite": f"{gn * math.sqrt(iso/100) / f:.1f} m"}
                for f in [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16]
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ── 📡 RAUSCHEN ──────────────────────────────────────────────────
elif tool == "📡 Rauschen":
    st.header("📡 Sensor-Rauschen & Dynamikumfang")
    iso = st.selectbox("ISO wählen:", [100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600])

    if st.button("📊 Analysieren", type="primary"):
        stops = math.log2(iso / 100)
        dr    = max(13.5 - stops * 0.8, 5.0)
        snr   = max(40   - stops * 5.5, 8.0)
        rating = (
            "🟢 Exzellent"    if snr >= 35 else
            "🟡 Gut"          if snr >= 25 else
            "🟠 Akzeptabel"   if snr >= 15 else
            "🔴 Stark verrauscht"
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("📉 SNR",            f"{snr:.1f} dB")
        c2.metric("🌈 Dynamikumfang",  f"{dr:.1f} EV")
        c3.metric("📊 Bewertung",      rating)

        with st.expander("📋 Alle ISO-Werte im Vergleich"):
            rows = []
            for i in [100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]:
                s = math.log2(i / 100)
                rows.append({
                    "ISO":            i,
                    "SNR (dB)":       f"{max(40-s*5.5,8):.1f}",
                    "Dynamik (EV)":   f"{max(13.5-s*0.8,5):.1f}",
                    "Empfehlung":     "✅" if max(40-s*5.5, 8) >= 25 else "⚠️",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ── 🌡️ WEIßABGLEICH ─────────────────────────────────────────────
elif tool == "🌡️ Weißabgleich":
    st.header("🌡️ Weißabgleich & Farbtemperatur")
    wb_data = [
        ("🕯️ Kerzenlicht",    "1800–2000 K", "#FF6B35"),
        ("💡 Glühlampe",      "2700–3200 K", "#FFA500"),
        ("🌅 Sonnenaufgang",  "3000–3500 K", "#FF8C42"),
        ("📸 Blitz",          "5000–5500 K", "#FFFEF0"),
        ("☀️ Tageslicht",     "5200–5800 K", "#FFFFF0"),
        ("⛅ Bewölkt",        "6000–6500 K", "#E8F0FF"),
        ("🏔️ Schatten",      "7000–8000 K", "#D0E0FF"),
        ("🌌 Blaue Stunde",   "9000–12000 K","#9090FF"),
    ]
    for name, kelvin, color in wb_data:
        c1, c2 = st.columns([2, 3])
        c1.markdown(f"<span style='color:{color};font-weight:bold'>{name}</span>", unsafe_allow_html=True)
        c2.code(kelvin)
    st.info("💡 **Tipp:** Immer manuellen WB in Kelvin setzen statt Auto – stabilere Farben im Timelapse!")

# ── 🔄 CROP-FAKTOR ───────────────────────────────────────────────
elif tool == "🔄 Crop-Faktor":
    st.header("🔄 Crop-Faktor Rechner")
    col1, col2 = st.columns(2)
    with col1:
        focal      = st.number_input("Brennweite (mm)", 10, 800, 50)
        aperture   = st.selectbox("Blende (f/)", [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16], index=4)
    with col2:
        sensor_from = st.selectbox("Von Sensor:", list(CROP_MAP.keys()), index=0)
        sensor_to   = st.selectbox("Nach Sensor:", list(CROP_MAP.keys()), index=1)

    if st.button("✅ Berechnen", type="primary"):
        cf_from        = CROP_MAP[sensor_from]
        cf_to          = CROP_MAP[sensor_to]
        focal_ff       = focal    * cf_from
        aperture_ff    = aperture * cf_from
        equiv_focal    = focal_ff    / cf_to
        equiv_aperture = aperture_ff / cf_to
        st.success(f"""
        ### 📊 Ergebnis:
        **Original ({sensor_from}):**
        - Brennweite: `{focal} mm` | Blende: `f/{aperture}`

        **Vollformat-Äquivalent:**
        - Brennweite: `{focal_ff:.0f} mm` | Blende: `f/{aperture_ff:.1f}`

        **Äquivalent auf {sensor_to}:**
        - Brennweite: `{equiv_focal:.0f} mm` | Blende: `f/{equiv_aperture:.1f}`
        """)
    with st.expander("📋 Crop-Faktor Referenz"):
        ref = [
            {"Sensor": k, "Crop-Faktor": v, "50 mm entspricht": f"{50*v:.0f} mm FF-Äquivalent"}
            for k, v in CROP_MAP.items()
        ]
        st.dataframe(pd.DataFrame(ref), use_container_width=True)

# ── 📈 HISTOGRAMM ────────────────────────────────────────────────
elif tool == "📈 Histogramm":
    st.header("📈 Belichtungs-Histogramm Simulator")
    ev       = st.slider("EV (Helligkeit)", 0, 20, 12)
    contrast = st.slider("Kontrast (Szene)", 10, 100, 50)
    channel  = st.selectbox("Kanal", ["Luminanz", "🔴 Rot", "🟢 Grün", "🔵 Blau"])

    if st.button("📊 Generieren", type="primary"):
        try:
            import numpy as np
            center    = int((ev / 20) * 255)
            x         = np.arange(256)
            y         = 1000 * np.exp(-((x - center) ** 2) / (2 * (contrast / 2) ** 2))
            color_map = {
                "Luminanz": "#E0E0E0",
                "🔴 Rot":   "#FF4444",
                "🟢 Grün":  "#44FF44",
                "🔵 Blau":  "#4444FF",
            }
            df_hist = pd.DataFrame({"Pixelwert": x, "Häufigkeit": y.astype(int)})
            st.bar_chart(df_hist.set_index("Pixelwert"), color=color_map[channel], use_container_width=True)
            if ev > 17:
                st.warning("🔴 Überbelichtet – Clipping!")
            elif ev < 4:
                st.warning("🔵 Unterbelichtet – Detailverlust in Schatten!")
            else:
                st.success("🟢 Gut belichtet! ETTR für weniger Rauschen.")
        except ImportError:
            st.error("numpy nicht verfügbar: pip install numpy")

# ── 🔭 OBJEKTIVE ─────────────────────────────────────────────────
elif tool == "🔭 Objektive":
    st.header("🔭 RF Objektiv-Datenbank")
    LENSES = [
        {"Name": "RF 14-35mm f/4L IS",      "Typ": "Weitwinkel Zoom",  "f/": 4.0,    "Gewicht": "540g",  "IS": "✅", "Preis": "~1.600€"},
        {"Name": "RF 15-35mm f/2.8L IS",    "Typ": "Weitwinkel Zoom",  "f/": 2.8,    "Gewicht": "840g",  "IS": "✅", "Preis": "~2.500€"},
        {"Name": "RF 24-70mm f/2.8L IS",    "Typ": "Standard Zoom",    "f/": 2.8,    "Gewicht": "900g",  "IS": "✅", "Preis": "~2.700€"},
        {"Name": "RF 24-105mm f/4L IS",     "Typ": "Standard Zoom",    "f/": 4.0,    "Gewicht": "700g",  "IS": "✅", "Preis": "~1.200€"},
        {"Name": "RF 50mm f/1.2L USM",      "Typ": "Standard Prime",   "f/": 1.2,    "Gewicht": "950g",  "IS": "❌", "Preis": "~2.400€"},
        {"Name": "RF 50mm f/1.8 STM",       "Typ": "Standard Prime",   "f/": 1.8,    "Gewicht": "160g",  "IS": "❌", "Preis": "~230€"},
        {"Name": "RF 85mm f/1.2L USM",      "Typ": "Portrait Prime",   "f/": 1.2,    "Gewicht": "1195g", "IS": "❌", "Preis": "~3.000€"},
        {"Name": "RF 85mm f/2 Macro IS",    "Typ": "Portrait Prime",   "f/": 2.0,    "Gewicht": "500g",  "IS": "✅", "Preis": "~700€"},
        {"Name": "RF 70-200mm f/2.8L IS",   "Typ": "Tele Zoom",        "f/": 2.8,    "Gewicht": "1070g", "IS": "✅", "Preis": "~2.900€"},
        {"Name": "RF 100-500mm f/4.5-7.1L", "Typ": "Supertele Zoom",   "f/": "4.5-7","Gewicht": "1370g", "IS": "✅", "Preis": "~3.000€"},
        {"Name": "RF 100mm f/2.8L Macro IS","Typ": "Makro Prime",      "f/": 2.8,    "Gewicht": "730g",  "IS": "✅", "Preis": "~1.500€"},
    ]
    typ_filter = st.multiselect("🏷️ Typ filtern:", sorted({l["Typ"] for l in LENSES}))
    filtered   = [l for l in LENSES if not typ_filter or l["Typ"] in typ_filter]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=450)
    st.info(f"📊 {len(filtered)} von {len(LENSES)} Objektiven angezeigt")

# ── ☁️ LIVE-WETTER ───────────────────────────────────────────────
elif tool == "☁️ Live-Wetter":
    st.header("☁️ Live-Wetter Analyse")
    st.markdown("Detaillierte Daten & Shooting-Empfehlungen")

    city_input = st.text_input(
        "📍 Stadt oder Koordinaten (z.B. Berlin oder 50.46,7.46)",
        value=st.session_state.gps_coords,
    )

    if st.button("🔄 Analyse starten", type="primary"):
        try:
            import requests
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]
            lat, lon = None, None

            if "," in city_input:
                try:
                    parts    = city_input.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                except Exception:
                    st.error("❌ Ungültiges Format. Bitte: 52.52,13.40")
                    st.stop()

            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )

            res  = requests.get(url, timeout=8)
            data = res.json()

            if data.get("cod") != 200:
                st.error(f"❌ {data.get('message','Unbekannter Fehler')}")
            else:
                temp        = data["main"]["temp"]
                feels_like  = data["main"]["feels_like"]
                humidity    = data["main"]["humidity"]
                pressure    = data["main"]["pressure"]
                visibility  = data.get("visibility", 10000) / 1000
                wind        = data["wind"]["speed"] * 3.6
                wind_gust   = data["wind"].get("gust", 0) * 3.6
                clouds      = data["clouds"]["all"]
                desc        = data["weather"][0]["description"]
                icon        = data["weather"][0]["icon"]
                sunrise     = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
                sunset      = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")

                st.subheader(f"📸 {desc.capitalize()} | {temp:.1f}°C (gefühlt {feels_like:.1f}°C)")
                st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png", width=100)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💨 Wind",            f"{wind:.1f} km/h",
                              delta=f"Böen: {wind_gust:.1f}" if wind_gust > 0 else None)
                    st.metric("☁️ Bewölkung",        f"{clouds}%")
                    st.metric("💧 Luftfeuchtigkeit", f"{humidity}%")
                with col2:
                    st.metric("👁️ Sichtweite",  f"{visibility:.1f} km")
                    st.metric("🌡️ Luftdruck",   f"{pressure} hPa")
                    st.caption("Hoher Druck = oft stabiles Licht")
                with col3:
                    st.metric("🌅 Aufgang",    sunrise)
                    st.metric("🌇 Untergang",  sunset)
                    day_len = datetime.strptime(sunset, "%H:%M") - datetime.strptime(sunrise, "%H:%M")
                    st.caption(f"Tageslänge: {str(day_len)[:5]} Std.")

                st.divider()
                st.subheader("📸 Fotografen-Check")
                score = 100
                notes = []

                if clouds < 20:
                    notes.append("🟢 Klarer Himmel – Top für Astro & Sunset")
                elif clouds < 60:
                    notes.append("🟡 Wolken – Gut für Dramatik/Landschaft")
                    score -= 20
                else:
                    notes.append("🟠 Stark bewölkt – Diffuses Licht (Portrait/Makro)")
                    score -= 40

                if wind > 40:
                    notes.append("⚠️ Starker Wind – Stativ beschweren!")
                    score -= 30
                elif wind > 20:
                    notes.append("🟡 Mäßiger Wind – Auf Verwacklung achten")
                    score -= 10

                if visibility < 5:
                    notes.append("🌫️ Schlechte Sicht (Nebel/Smog)")
                    score -= 20

                if   score >= 80: st.success(f"⭐⭐⭐ **PERFEKT (Score: {score})**\n\n" + "\n".join(notes))
                elif score >= 50: st.info(   f"⭐⭐ **GUT (Score: {score})**\n\n"     + "\n".join(notes))
                else:             st.warning(f"⭐ **SCHWIERIG (Score: {score})**\n\n" + "\n".join(notes))

        except Exception as e:
            st.error(f"Fehler: {e}")

# ── 📅 5-TAGE PROGNOSE ───────────────────────────────────────────
elif tool == "📅 5-Tage Prognose":
    st.header("📅 5-Tage-Wettervorhersage")
    city_input = st.text_input("📍 Stadt oder Koordinaten", value=st.session_state.gps_coords)

    if st.button("📊 Vorhersage laden", type="primary"):
        try:
            import requests
            API_KEY  = st.secrets["OPENWEATHER_API_KEY"]
            lat, lon = None, None

            if "," in city_input:
                try:
                    parts    = city_input.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                except Exception:
                    st.error("❌ Ungültiges Format. Bitte: 52.52,13.40")
                    st.stop()

            url = (
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/forecast"
                f"?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )

            data = requests.get(url, timeout=8).json()

            if data.get("cod") != "200":
                st.error(f"❌ {data.get('message','Unbekannter Fehler')}")
            else:
                times, temps, daily = [], [], {}
                for item in data["list"]:
                    dt  = datetime.fromtimestamp(item["dt"])
                    day = dt.strftime("%d.%m.")
                    times.append(dt.strftime("%d.%m. %H:%M"))
                    temps.append(item["main"]["temp"])
                    if day not in daily:
                        daily[day] = {
                            "min":  item["main"]["temp_min"],
                            "max":  item["main"]["temp_max"],
                            "desc": item["weather"][0]["description"],
                        }
                    else:
                        daily[day]["min"] = min(daily[day]["min"], item["main"]["temp_min"])
                        daily[day]["max"] = max(daily[day]["max"], item["main"]["temp_max"])

                st.subheader("🌡️ Temperaturverlauf")
                df_temp = pd.DataFrame({"Uhrzeit": times[:40], "Temperatur": temps[:40]})
                st.line_chart(df_temp.set_index("Uhrzeit"), use_container_width=True)

                st.subheader("📆 Tagesübersicht")
                cols = st.columns(len(daily))
                for i, (day, vals) in enumerate(daily.items()):
                    with cols[i]:
                        st.metric(day, f"{vals['min']:.0f}° / {vals['max']:.0f}°")
                        st.caption(vals["desc"].capitalize())

        except Exception as e:
            st.error(f"Fehler: {e}")

# ════════════════════════════════════════════════════════════════
#  🌍 ASTRO & WETTER DASHBOARD (Koordinaten-Fix)
# ════════════════════════════════════════════════════════════════

elif tool == "🌍 Astro & Wetter Dashboard":
    st.header("🌍 Astro & Wetter Dashboard")
    st.markdown("Alles für die Shooting-Planung an einem Ort")

    # Vorausgefüllte Stadt aus GPS-Tool übernehmen
    default_city = st.session_state.get("dash_city", "Berlin")
    city = st.text_input(
        "📍 Stadt oder Koordinaten (z.B. Berlin oder 52.52,13.40)",
        value=default_city,
        key="dash_input",
    )

    if st.button("🔄 Dashboard aktualisieren", type="primary"):
        try:
            import requests
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]

            # 🎯 Robuste Koordinaten-Erkennung
            lat, lon = None, None
            if "," in city:
                try:
                    # Leerzeichen entfernen, aufteilen, in Float umwandeln
                    parts = city.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                    
                    # Validierung: Koordinaten müssen im gültigen Bereich sein
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        st.error("❌ Ungültige Koordinaten. Breitengrad: -90 bis 90, Längengrad: -180 bis 180")
                        st.stop()
                except (ValueError, IndexError):
                    st.error("❌ Ungültiges Koordinaten-Format. Bitte: 52.52,13.40 (ohne Leerzeichen)")
                    st.stop()

            # API-URL bauen (mit Koordinaten oder Stadtnamen)
            if lat is not None:
                w_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
            else:
                w_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=de"

            w = requests.get(w_url, timeout=8).json()
            
            if w.get("cod") != 200:
                st.error(f"❌ {w.get('message', 'Unbekannter Fehler')}")
            else:
                # Wetter-Daten extrahieren
                temp = w["main"]["temp"]
                clouds = w["clouds"]["all"]
                wind = w["wind"]["speed"] * 3.6
                desc = w["weather"][0]["description"]
                icon = w["weather"][0]["icon"]
                sr_ts = datetime.fromtimestamp(w["sys"]["sunrise"]).strftime("%H:%M")
                ss_ts = datetime.fromtimestamp(w["sys"]["sunset"]).strftime("%H:%M")

                # Mond-Daten berechnen
                now = datetime.now()
                phase = calculate_moon_phase(now.year, now.month, now.day)
                m_name, m_illum, m_tip = moon_phase_info(phase)

                # Layout: 2 Spalten
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("☁️ Live-Wetter")
                    st.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=60)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🌡️", f"{temp:.1f}°C")
                    c2.metric("💨", f"{wind:.0f} km/h")
                    c3.metric("☁️", f"{clouds}%")
                    st.caption(f"{desc.capitalize()} | ☀️ {sr_ts} – {ss_ts}")
                    
                with col2:
                    st.subheader("🌙 Mondstatus")
                    st.metric("Phase", m_name)
                    st.metric("Beleuchtung", f"{m_illum:.0f}%")
                    st.caption(m_tip)

                # Astro-Score berechnen
                astro_sc = (100 - m_illum) * 0.6 + (100 - clouds) * 0.4
                mw_sc = milky_way_score(phase, now.month)

                st.info(f"""
                ### 📸 Shooting-Empfehlung
                {astro_recommendation(astro_sc)}

                **Milchstraße-Score:** {mw_sc:.0f}/100
                """)

                # Stunden-Übersicht (optional)
                with st.expander("📊 Stunden-Übersicht (heute)"):
                    if lat is not None:
                        f_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de&cnt=8"
                    else:
                        f_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=de&cnt=8"
                    
                    f_data = requests.get(f_url, timeout=8).json()
                    if f_data.get("cod") == "200":
                        items = f_data["list"]
                        df_h = pd.DataFrame({
                            "Zeit": [datetime.fromtimestamp(i["dt"]).strftime("%H:%M") for i in items],
                            "Temp °C": [i["main"]["temp"] for i in items],
                            "Wolken%": [i["clouds"]["all"] for i in items],
                        })
                        st.dataframe(df_h.set_index("Zeit"), use_container_width=True)
                        
        except Exception as e:
            st.error(f"Fehler: {type(e).__name__}: {e}")
            st.info("💡 Prüfe deinen API-Key in .streamlit/secrets.toml")

# ── 📍 GPS-STANDORT ──────────────────────────────────────────────
# ══════════════════════════════════════════
# 📍 GPS-STANDORT (Mit Ortsname via OpenStreetMap)
# ═══════════════════════════════════════════
elif tool == "📍 GPS-Standort":
    st.header("📍 Standort automatisch erkennen")
    import streamlit.components.v1 as components

    # Session State initialisieren
    if "gps_coords" not in st.session_state:
        st.session_state.gps_coords = None
    if "gps_temp_coords" not in st.session_state:
        st.session_state.gps_temp_coords = None  # Temporär für Auto-Fill

    # GPS-HTML
    gps_html = """
    <div style="padding:10px; box-sizing:border-box; font-family:sans-serif;">
        <button id="gps-btn" style="padding:12px; background:#1F6FEB; color:white; border:none; border-radius:8px; cursor:pointer; width:100%; margin-bottom:10px; font-size:16px;">
            📍 Standort abrufen
        </button>
        <div id="gps-res" style="display:none; background:#161B22; padding:12px; border-radius:8px; text-align:center; border:1px solid #30363D;">
            <p id="gps-txt" style="color:#58A6FF; font-family:monospace; margin:0 0 12px 0; font-size:14px;"></p>
            <a id="gps-link" href="#" style="display:inline-block; padding:12px; background:#238636; color:white; text-decoration:none; border-radius:6px; font-weight:bold; font-size:15px;">
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

        if(!navigator.geolocation) {
            txt.textContent = "❌ Geolocation nicht unterstützt";
            return;
        }

        navigator.geolocation.getCurrentPosition(pos => {
            const lat = pos.coords.latitude.toFixed(6);
            const lon = pos.coords.longitude.toFixed(6);
            txt.textContent = `✅ ${lat}, ${lon} (Ort wird gesucht...)`;

            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10&addressdetails=1`, {
                headers: { 'Accept-Language': 'de', 'User-Agent': 'CanonProTool/1.0' }
            })
            .then(r => r.json())
            .then(data => {
                let ort = "Unbekannter Ort";
                if(data && data.address) {
                    const a = data.address;
                    ort = a.city || a.town || a.village || a.municipality || a.county || a.state || a.country || "Unbekannter Ort";
                }
                txt.textContent = `✅ ${lat}, ${lon} (nahe ${ort})`;
                const baseUrl = window.location.href.split('?')[0];
                document.getElementById('gps-link').href = baseUrl + "?lat=" + lat + "&lon=" + lon;
            })
            .catch(() => {
                txt.textContent = `✅ ${lat}, ${lon}`;
                const baseUrl = window.location.href.split('?')[0];
                document.getElementById('gps-link').href = baseUrl + "?lat=" + lat + "&lon=" + lon;
            });

        }, err => {
            txt.textContent = `❌ Fehler: ${err.message}`;
        }, {enableHighAccuracy:true, timeout:10000});
    };
    </script>
    """
    components.html(gps_html, height=220)

    # Query-Params prüfen
    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")
    if lat_q and lon_q:
        st.session_state.gps_coords = f"{lat_q},{lon_q}"
        st.session_state.gps_temp_coords = f"{lat_q},{lon_q}"  # Auch für Auto-Fill speichern
        st.query_params.clear()
        st.success(f"✅ GPS übernommen: `{st.session_state.gps_coords}`")
        st.cache_data.clear()
        st.rerun()

    # Manuelle Eingabe mit Auto-Fill aus GPS-Result
    st.divider()
    st.markdown("### 📍 Koordinaten übernehmen")
    
    # Automatisch ausfüllen, wenn temporäre Koordinaten da sind
   # ✅ NEU (sicher):
    default_coords = st.session_state.get("gps_temp_coords")
    if default_coords and "," in default_coords:
        default_lat, default_lon = default_coords.split(",")
    else:
        default_lat, default_lon = "50.43", "7.47"
    
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Breitengrad", value=default_lat)
    with col2:
        manual_lon = st.text_input("Längengrad", value=default_lon)
    
    if st.button("✅ Übernehmen", use_container_width=True, type="primary"):
        st.session_state.gps_coords = f"{manual_lat},{manual_lon}"
        st.session_state.gps_temp_coords = f"{manual_lat},{manual_lon}"
        st.success(f" Standort gesetzt: `{st.session_state.gps_coords}`")
        st.cache_data.clear()
        st.rerun()

    # Aktueller Standort anzeigen
    if st.session_state.gps_coords:
        st.divider()
        st.success(f"### ✅ Aktueller Standort: `{st.session_state.gps_coords}`")
        if st.button("🗑️ Standort löschen"):
            st.session_state.gps_coords = None
            st.session_state.gps_temp_coords = None
            st.cache_data.clear()
            st.rerun()

# ════════════════════════════════════════════════════════════════
#  🌙 MOND & MILCHSTRAßE (Koordinaten-Fix)
# ════════════════════════════════════════════════════════════════

elif tool == "🌙 Mond & Milchstraße":
    st.header("🌙 Mondphasen & Milchstraße Sichtbarkeit")
    
    city_sel = st.selectbox("📍 Stadt", ["(manuell)"] + CITY_LIST)
    
    # 🎯 Koordinaten-Eingabe (mit GPS-Fallback)
    col1, col2 = st.columns(2)
    with col1:
        date_str = st.text_input(
            "📅 Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y")
        )
    with col2:
        if city_sel != "(manuell)":
            # Stadt aus Liste → Koordinaten aus CITY_COORDS
            latitude, longitude = CITY_COORDS[city_sel]
            st.number_input("🌍 Breitengrad", value=latitude, disabled=True, key="mw_lat")
            st.number_input("🌍 Längengrad", value=longitude, disabled=True, key="mw_lon")
        else:
            # Manuelle Eingabe oder GPS-Koordinaten
            default_coords = st.session_state.get("gps_coords", "51.34,12.38")
            coords_input = st.text_input(
                "📍 Koordinaten (Breitengrad, Längengrad)",
                value=default_coords,
                help="Beispiel: 50.466164, 7.469177"
            )
            # Robustes Parsing
            try:
                if "," in coords_input:
                    parts = coords_input.replace(" ", "").split(",")
                    latitude, longitude = float(parts[0]), float(parts[1])
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        st.error("❌ Ungültige Koordinaten")
                        st.stop()
                else:
                    latitude, longitude = 51.34, 12.38  # Fallback
            except:
                latitude, longitude = 51.34, 12.38  # Fallback bei Fehler

    option = st.selectbox(
        "🎯 Fokus", ["Milchstraße", "Mondfotografie", "Deep Sky", "Nordlichter"]
    )

    if st.button("🔍 Berechnen", type="primary"):
        try:
            # Datum parsen
            day, month, year = map(int, date_str.split("."))
            phase = calculate_moon_phase(year, month, day)
            p_name, p_illum, p_tip = moon_phase_info(phase)

            # Berechnung je nach Fokus
            if option == "Milchstraße":
                score = milky_way_score(phase, month)
                best_time = "22:30–04:00" if 4 <= month <= 9 else "03:00–06:00"
                rec = (
                    "🟢 Hervorragend!" if score >= 85 else
                    "🟡 Gut!" if score >= 65 else
                    "🟠 Mäßig." if score >= 40 else "🔴 Schlecht."
                )
            elif option == "Mondfotografie":
                score = p_illum
                best_time = "Abends nach Sonnenuntergang"
                rec = "🌕 Vollmond – perfekt!" if 0.45 < phase < 0.55 else "🌙 Interessante Phase"
            elif option == "Deep Sky":
                score = max(0, 100 - p_illum)
                best_time = "Mitternacht–Morgengrauen"
                rec = "🔭 Dunkler Himmel – ideal!" if score > 80 else "⚠️ Auf Neumond warten."
            else:  # Nordlichter
                if abs(latitude) > 58:
                    score = max(0, 100 - p_illum) * (
                        1.0 if month in range(10, 13) or month in range(1, 4) else 0.5
                    )
                    best_time = "21:00–02:00"
                    rec = "🌌 Aurora möglich bei klarem Himmel!"
                else:
                    score = 15
                    best_time = "–"
                    rec = "📍 Zu weit südlich – >58° Breite nötig (Skandinavien, Island)"

            st.success(f"""
            ### 📊 Ergebnis – {date_str} | 📍 {latitude:.4f}, {longitude:.4f}
            **🌙 Mondphase:** {p_name}  
            Beleuchtung: **{p_illum:.0f}%** | {p_tip}

            **⭐ Bewertung:** {score:.0f}/100  
            {rec}

            **⏰ Beste Zeit:** {best_time}
            """)
            st.info("""
            💡 **Tipps:** 🌑 Neumond = dunkelster Himmel  |  🌕 Vollmond = zu hell für Milchstraße  
            Milchstraße-Saison: März–Oktober (Peak: Juni–August)
            """)
        except ValueError:
            st.error("⚠️ Ungültiges Datum. Format: TT.MM.JJJJ (z.B. 15.08.2025)")
        except Exception as e:
            st.error(f"❌ Fehler: {type(e).__name__}: {e}")

# ── 🌠 STERNSPUREN ───────────────────────────────────────────────
elif tool == "🌠 Sternspuren":
    st.header("🌠 Sternspuren & Astrofotografie")
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Sternspuren", "⭐ Scharfe Sterne", "📐 Planung", "📚 Tipps"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            total_time = st.number_input("Gesamtzeit (Min)", 10, 480, 60)
            interval   = st.number_input("Intervall (Sek)", 1, 30, 5)
        with col2:
            shutter_s  = st.selectbox("Belichtung/Bild", ["10s","15s","20s","25s","30s"], index=2)
            iso_s      = st.selectbox("ISO", [400, 800, 1600, 3200], index=2)

        if st.button("✅ Berechnen", type="primary", key="star_calc"):
            sh_sec    = int(shutter_s.replace("s", ""))
            n_frames  = (total_time * 60) // (sh_sec + interval)
            trail_deg = (total_time / 4) * 15
            st.success(f"""
            ### Ergebnis:
            - Bilder: **{n_frames:,}** | Dauer: **{total_time} Min**
            - Sternspur: **{trail_deg:.0f}°** am Himmel
            - Speicher RAW: **~{n_frames*30/1024:.1f} GB**
            - Settings: {shutter_s} | ISO {iso_s} | f/2.8 | MF ∞
            """)
            st.info("📦 Stacking: StarStaX (Win) | Starry Landscape Stacker (Mac) | Sequator")

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            focal_sh  = st.number_input("Brennweite (mm)", 14, 400, 24)
            sensor_sh = st.selectbox("Sensor", ["Vollformat","APS-C Canon 1.6×","APS-C Nikon 1.5×","Micro 4/3 2×"])
        with col2:
            ap_sh = st.selectbox("Blende", [1.2, 1.4, 1.8, 2.0, 2.8, 4.0], index=3)

        crop_sh_map = {"Vollformat":1.0,"APS-C Canon 1.6×":1.6,"APS-C Nikon 1.5×":1.5,"Micro 4/3 2×":2.0}
        crop_sh  = crop_sh_map[sensor_sh]
        max_500  = 500 / (focal_sh * crop_sh)
        max_npf  = (35 * ap_sh + 30) / (focal_sh * crop_sh)
        st.success(f"""
        ### Maximale Belichtungszeit:
        - **500er-Regel:** {max_500:.1f}s
        - **NPF-Regel (präziser):** {max_npf:.1f}s
        Empfehlung: **{max_npf:.0f}s** für punktförmige Sterne
        """)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            date_plan = st.text_input("Datum", value=datetime.now().strftime("%d.%m.%Y"))
        with col2:
            lp = st.selectbox("Lichtverschmutzung", [
                "Bortle 1–2 (Sehr dunkel)", "Bortle 3–4 (Dunkel)",
                "Bortle 5–6 (Vorstadt)",    "Bortle 7–9 (Stadt)",
            ])

        if st.button("🔍 Prüfen", key="star_plan"):
            try:
                d, mo, yr = map(int, date_plan.split("."))
                phase      = calculate_moon_phase(yr, mo, d)
                _, illum, _ = moon_phase_info(phase)
                lp_score   = {"Bortle 1–2 (Sehr dunkel)":1.0,"Bortle 3–4 (Dunkel)":0.7,
                               "Bortle 5–6 (Vorstadt)":0.4,"Bortle 7–9 (Stadt)":0.1}[lp]
                season     = 1.0 if 3 <= mo <= 10 else 0.4
                total_sc   = ((100 - illum)/100 * 0.4 + season * 0.3 + lp_score * 0.3) * 100
                st.success(f"""
                ### Score: {total_sc:.0f}/100
                Mond: {illum:.0f}% | Saison: {"✅" if season==1.0 else "⚠️"} | LP: {lp}
                {astro_recommendation(total_sc)}
                """)
            except ValueError:
                st.error("Ungültiges Datum.")

    with tab4:
        st.markdown("""
        ### 📚 Guide: Sternspuren & Astrofotografie
        **Equipment:** Stativ | Intervalometer | Stirnlampe (Rotlicht) | Akkus | 64+ GB Karten

        **Kamera:** Manuell | RAW | WB manuell 3800 K | Rauschreduktion AUS | IS AUS

        **Fokus:** Manuell auf hellsten Stern im Live View 10× | ∞ nicht immer optimal!

        **Apps:** PhotoPills | Stellarium | Sky Guide | Dark Sky Finder

        **Stacking:** Sequator (Win) | Starry Landscape Stacker (Mac) | StarStaX
        """)

# ════════════════════════════════════════════════════════════════
#  🌙 AKTUELLE MOND-DATEN (GPS & Koordinaten-Fix)
# ═══════════════════════════════════════════════════════════════

elif tool == "🌙 Aktuelle Mond-Daten":
    st.header("🌙 Live-Sonnen- & Mond-Daten")
    if not ASTRAL_OK:
        st.error(f"⚠️ astral/pytz nicht installiert: {_ASTRAL_ERR}")
        st.stop()

    st.subheader("📍 Standort festlegen")
    city_sel = st.selectbox("Stadt aus Liste", ["(manuell / GPS)"] + CITY_LIST, index=0)

    lat, lon = None, None
    if city_sel != "(manuell / GPS)":
        # Stadt aus Dropdown → Koordinaten aus Dictionary
        lat, lon = CITY_COORDS[city_sel]
        st.info(f"🏙️ Gewählt: **{city_sel}** ({lat:.4f}, {lon:.4f})")
    else:
        # Manuell oder GPS-Fallback
        default_coords = st.session_state.get("gps_coords", "51.34, 12.38")
        coords_input = st.text_input(
            "📍 Koordinaten eingeben",
            value=default_coords,
            help="GPS-Daten werden automatisch übernommen. Format: 50.46, 7.46"
        )
        # Robustes Parsing (gleiche Logik wie in den anderen Tools)
        try:
            if "," in coords_input:
                parts = coords_input.replace(" ", "").split(",")
                lat, lon = float(parts[0]), float(parts[1])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    st.error("❌ Ungültige Koordinaten. Bereich: Lat -90..90, Lon -180..180")
                    st.stop()
            else:
                lat, lon = 51.34, 12.38  # Fallback
        except Exception:
            lat, lon = 51.34, 12.38  # Fallback bei Parse-Fehler

    if st.button("🔄 Jetzt berechnen", type="primary"):
        try:
            tz = pytz.timezone("Europe/Berlin")
            # Dynamischer Standortname für die Anzeige
            display_name = city_sel if city_sel != "(manuell / GPS)" else f"{lat:.4f}, {lon:.4f}"
            
            city_info = LocationInfo(display_name, "DE", "Europe/Berlin", lat, lon)
            now = datetime.now(tz)
            s = sun(city_info.observer, date=now.date(), tzinfo=tz)
            phase = calculate_moon_phase(now.year, now.month, now.day)
            m_name, m_illum, m_tip = moon_phase_info(phase)

            st.success(f"""
            ### 📅 {now.strftime('%d.%m.%Y %H:%M')} | 📍 {display_name}

            **🌞 Sonne**
            • Aufgang:         `{s['sunrise'].strftime('%H:%M')}`
            • Untergang:       `{s['sunset'].strftime('%H:%M')}`
            • Goldene Stunde:  `{(s['sunrise']-timedelta(minutes=15)).strftime('%H:%M')} – {(s['sunrise']+timedelta(minutes=60)).strftime('%H:%M')}`

            **🌙 Mond**
            • Phase:           `{m_name}`
            • Beleuchtung:     `{m_illum:.0f}%`
            • Tipp:            {m_tip}

            **📸 Beste Foto-Zeiten**
            {get_best_photo_times(s, phase)}
            """)
        except Exception as e:
            st.error(f"❌ {type(e).__name__}: {e}")

# ════════════════════════════════════════════════════════════════
#  🌊 GEZEITEN & TIDE-RECHNER (Verbesserte Koordinaten-Eingabe)
# ═══════════════════════════════════════════════════════════════

elif tool == "🌊 Gezeiten & Tide-Rechner":
    st.header("🌊 Gezeiten & Tide-Rechner")
    st.markdown("Ebbe & Flut für Küstenfotografie & Tauchplanung")

    # 📍 Standort-Auswahl (einfacher als manuelle Eingabe)
    KUESTEN_ORTE = {
        "Rügen (Deutschland)": "54.32, 13.09",
        "Sylt (Deutschland)": "54.91, 8.31",
        "Norddeich (Deutschland)": "53.60, 7.15",
        "Cuxhaven (Deutschland)": "53.87, 8.70",
        "Norderney (Deutschland)": "53.71, 7.15",
        "Amrum (Deutschland)": "54.63, 8.33",
        "St. Peter-Ording (Deutschland)": "54.31, 8.62",
        "Ostende (Belgien)": "51.23, 2.93",
        "Dünkirchen (Frankreich)": "51.03, 2.38",
        "Le Havre (Frankreich)": "49.49, 0.11",
        "Brest (Frankreich)": "48.39, -4.49",
        "Liverpool (UK)": "53.41, -3.00",
        "Brighton (UK)": "50.82, -0.14",
        "Amsterdam (Niederlande)": "52.37, 4.90",
    }

    eingabe_methode = st.radio(
        "📍 Standort wählen:",
        ["🏖️ Bekannter Küstenort", "📍 Eigene Koordinaten", "📍 GPS-Standort nutzen"],
        index=0
    )

    lat, lon = None, None

    if eingabe_methode == "🏖️ Bekannter Küstenort":
        ort_name = st.selectbox("Wähle einen Ort:", list(KUESTEN_ORTE.keys()))
        lat_str, lon_str = KUESTEN_ORTE[ort_name].split(",")
        lat, lon = float(lat_str.strip()), float(lon_str.strip())
        st.info(f"📍 Gewählt: **{ort_name}** ({lat:.4f}, {lon:.4f})")

    elif eingabe_methode == "📍 Eigene Koordinaten":
        default_coords = st.session_state.get("gps_coords", "54.32, 13.09")
        coords_input = st.text_input(
            "Koordinaten eingeben (Breitengrad, Längengrad)",
            value=default_coords,
            help="Beispiel: 54.32, 13.09 oder 54.32,13.09"
        )
        
        if st.button(" Koordinaten prüfen"):
            try:
                if not coords_input or "," not in coords_input:
                    st.error("❌ Bitte gib Koordinaten im Format ein: **54.32, 13.09**")
                    st.info("💡 Tipp: Verwende ein Komma (,) zwischen Breite und Länge")
                    st.stop()
                
                # Komma finden und aufteilen
                clean_input = coords_input.strip().replace(" ", "")
                parts = clean_input.split(",")
                
                if len(parts) != 2:
                    st.error("❌ Genau 2 Werte erwartet: Breitengrad, Längengrad")
                    st.stop()
                
                lat = float(parts[0])
                lon = float(parts[1])
                
                # Bereich prüfen
                if not (-90 <= lat <= 90):
                    st.error(f"❌ Breitengrad muss zwischen -90 und 90 liegen (dein Wert: {lat})")
                    st.stop()
                if not (-180 <= lon <= 180):
                    st.error(f"❌ Längengrad muss zwischen -180 und 180 liegen (dein Wert: {lon})")
                    st.stop()
                
                st.success(f"✅ Koordinaten gültig: {lat:.4f}, {lon:.4f}")
                
            except ValueError:
                st.error("❌ Bitte nur Zahlen eingeben! Beispiel: 54.32, 13.09")
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
            st.stop()

    else:  # GPS-Standort
        if "gps_coords" in st.session_state and st.session_state.gps_coords:
            try:
                lat, lon = map(float, st.session_state.gps_coords.split(","))
                st.success(f"✅ GPS-Standort übernommen: {lat:.4f}, {lon:.4f}")
            except:
                st.warning("⚠️ GPS-Daten nicht verfügbar. Bitte andere Methode wählen.")
                lat, lon = 54.32, 13.09  # Fallback
        else:
            st.warning("⚠️ Kein GPS-Standort gespeichert. Bitte zuerst 📍 GPS-Standort Tool nutzen.")
            lat, lon = 54.32, 13.09  # Fallback

    # 📅 Datum
    col1, col2 = st.columns(2)
    with col1:
        tide_date = st.date_input("📅 Datum", value=datetime.now().date())
    with col2:
        st.caption("🔑 API: WorldTides.info")

    if st.button("🌊 Gezeiten abrufen", type="primary"):
        if lat is None or lon is None:
            st.error("❌ Bitte zuerst gültige Koordinaten eingaben oder prüfen!")
            st.stop()

        try:
            # API-Key prüfen
            try:
                API_KEY = st.secrets["WORLD_TIDES_API_KEY"]
            except KeyError:
                st.warning("⚠️ **API-Key nicht hinterlegt!**")
                st.info("""
                🔑 **So bekommst du einen kostenlosen Key:**
                1. Gehe zu [worldtides.info](https://www.worldtides.info/)
                2. Registriere dich (kostenlos, E-Mail genügt)
                3. Erstelle einen API Key
                4. Trage ihn in Streamlit Cloud ein: 
                   `Settings → Secrets → WORLD_TIDES_API_KEY = "dein_key"`
                """)
                st.stop()

            # Daten abrufen
            start_ts = int(datetime.combine(tide_date, datetime.min.time()).timestamp())
            url = f"https://www.worldtides.info/api/v3?lat={lat}&lon={lon}&key={API_KEY}&start={start_ts}&length=86400&extremes"
            res = requests.get(url, timeout=10)
            data = res.json()

            if res.status_code != 200 or data.get("status") != 200:
                st.error(f"❌ API-Fehler: {data.get('error', 'Unbekannter Fehler')}")
                st.info(f"📍 Koordinaten: {lat:.4f}, {lon:.4f}")
            else:
                extremes = data.get("extremes", [])
                if not extremes:
                    st.info("ℹ️ Keine Gezeitendaten für diesen Standort verfügbar.")
                else:
                    st.success(f"✅ Gezeiten für {tide_date.strftime('%d.%m.%Y')}")
                    
                    # Tabelle erstellen
                    df = pd.DataFrame([
                        {
                            "Zeit": datetime.fromtimestamp(e["dt"]).strftime("%H:%M"),
                            "Typ": "🌊 Hochwasser" if e["type"] == "High" else "🏖️ Niedrigwasser",
                            "Höhe": f"{e['height']:.2f} m",
                            "Foto-Tipp": get_tide_photo_tip(e["type"])
                        } for e in extremes
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Zusammenfassung
                    low_tides = [e for e in extremes if e["type"] == "Low"]
                    high_tides = [e for e in extremes if e["type"] == "High"]
                    
                    if low_tides:
                        st.info(f"🏖️ **Niedrigwasser:** {low_tides[0]['height']:.2f}m um {datetime.fromtimestamp(low_tides[0]['dt']).strftime('%H:%M')} Uhr → Ideal für Watt & Spiegelungen")
                    if high_tides:
                        st.info(f"🌊 **Hochwasser:** {high_tides[0]['height']:.2f}m um {datetime.fromtimestamp(high_tides[0]['dt']).strftime('%H:%M')} Uhr → Dramatische Brandung & Wellen")
                        
        except Exception as e:
            st.error(f"❌ Fehler: {type(e).__name__}: {e}")
            st.info("💡 Prüfe deine Internetverbindung und API-Key")

# ── 📄 PDF-PLANER ────────────────────────────────────────────────
elif tool == "📄 PDF-Planer":
    st.header("📄 PDF-Shooting-Plan Generator")
    col1, col2 = st.columns(2)
    with col1:
        p_title  = st.text_input("📸 Projektname",       value="Canon EOS R Shooting")
        p_date   = st.date_input("📅 Datum",             datetime.now())
        p_loc    = st.text_input("📍 Ort",               value="Berlin")
    with col2:
        p_subj   = st.text_input("🎯 Motiv",             value="Landschaft / Portrait")
        p_client = st.text_input("👤 Auftraggeber",      value="Privat")

    equip = st.text_area("🎒 Equipment-Liste (je Zeile ein Item)", height=100,
        value="Kamera: Canon EOS R\nObjektiv: RF 24-70mm f/2.8\nStativ: Manfrotto\nFilter: ND 1000, Polfilter\nAkkus: 3x LP-E6NH")
    notes = st.text_area("📝 Notizen & Ablauf", height=100,
        value="08:00 Aufbau\n08:30 Golden Hour\n10:00 Backup\n")

    if st.button("📄 PDF Generieren & Herunterladen", type="primary"):
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(31, 111, 235)
            pdf.cell(0, 20, "SHOOTING PLAN", ln=True, align="C")
            pdf.line(10, 30, 200, 30)

            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, f"Projekt: {p_title}", ln=True)
            pdf.cell(0,  8, f"Datum: {p_date.strftime('%d.%m.%Y')} | Ort: {p_loc}", ln=True)
            pdf.cell(0,  8, f"Motiv: {p_subj} | Kunde: {p_client}", ln=True)
            pdf.ln(5)

            pdf.set_font("Helvetica", "B", 14)
            pdf.set_fill_color(240, 246, 252)
            pdf.cell(0, 10, "  Ausruestung & Settings", ln=True, fill=True)
            pdf.set_font("Helvetica", size=11)
            for line in equip.split("\n"):
                if line.strip():
                    pdf.cell(0, 7, f"- {line}", ln=True)
            pdf.ln(5)

            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "  Ablauf & Notizen", ln=True, fill=True)
            pdf.set_font("Helvetica", size=11)
            for line in notes.split("\n"):
                if line.strip():
                    pdf.multi_cell(0, 7, line)

            pdf.set_y(-20)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, "Erstellt mit Canon EOS R Pro Tool | Web Version", ln=True, align="C")

            pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
            st.download_button(
                label     = "⬇️ PDF Speichern",
                data      = pdf_bytes,
                file_name = f"Shooting_Plan_{p_date.strftime('%Y%m%d')}.pdf",
                mime      = "application/pdf",
            )
        except ImportError:
            st.error("fpdf2 fehlt: pip install fpdf2")
        except Exception as e:
            st.error(f"Fehler beim Erstellen: {e}")

# ── 📝 PLANER ────────────────────────────────────────────────────
elif tool == "📝 Planer":
    st.header("📝 Aufnahme-Planer & Logbuch")
    tab1, tab2 = st.tabs(["➕ Neuer Eintrag", "📖 Logbuch"])

    SHUTTERS_LOG = ["1/1000","1/500","1/250","1/125","1/60","1/30","1/15","1s","2s","4s"]

    with tab1:
        c1, c2   = st.columns(2)
        loc      = c1.text_input("📍 Ort")
        sub      = c2.text_input("📸 Motiv")
        c3, c4   = st.columns(2)
        iso_log  = c3.selectbox("ISO",    [100,200,400,800,1600,3200], key="log_iso")
        ap_log   = c4.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], key="log_ap")
        sh_log   = st.selectbox("Verschluss", SHUTTERS_LOG, key="log_sh")
        notes    = st.text_area("📝 Notizen")
        rating   = st.slider("⭐ Bewertung", 1, 5, 3)

        if st.button("➕ Speichern", type="primary"):
            if loc or sub:
                st.session_state.logbook.append({
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "loc":      loc,
                    "sub":      sub,
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

# ── 🗺️ SPOTS ─────────────────────────────────────────────────────
elif tool == "🗺️ Spots":
    st.header("🗺️ Foto-Spot Manager")
    tab1, tab2 = st.tabs(["➕ Spot hinzufügen", "📌 Meine Spots"])

    with tab1:
        c1, c2 = st.columns(2)
        name   = c1.text_input("📍 Name des Spots")
        typ    = c2.selectbox("🏷️ Typ", ["Landschaft","Portrait","Street","Architektur","Astro","Sonstiges"])
        c3, c4 = st.columns(2)
        lat    = c3.number_input("🌐 Breitengrad",  value=51.34, format="%.4f")
        lon    = c4.number_input("🌐 Längengrad",   value=12.38, format="%.4f")
        beste  = st.text_input("⏰ Beste Zeit")
        notes  = st.text_area("📝 Notizen")

        if st.button("➕ Spot speichern", type="primary"):
            if name:
                st.session_state.spots.append({
                    "Name": name, "Typ": typ, "Lat": lat,
                    "Lon":  lon,  "Beste Zeit": beste, "Notizen": notes,
                })
                st.success(f"✅ '{name}' gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte einen Namen eingeben.")

    with tab2:
        if st.session_state.spots:
            st.dataframe(pd.DataFrame(st.session_state.spots), use_container_width=True)
            last = st.session_state.spots[-1]
            st.markdown(f"🔗 [Letzten Spot auf Google Maps öffnen](https://maps.google.com/?q={last['Lat']},{last['Lon']})")
            if st.button("🗑️ Alle Spots löschen"):
                st.session_state.spots = []
                st.rerun()
        else:
            st.info("📭 Noch keine Spots gespeichert.")

# ── ⏱️ TIMELAPSE ─────────────────────────────────────────────────
elif tool == "⏱️ Timelapse":
    st.header("⏱️ Timelapse-Rechner")
    tab1, tab2 = st.tabs(["📊 Berechnung", "💡 Tipps"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            duration = st.number_input("🎬 Video-Länge (Sek)", min_value=5, value=30)
        with col2:
            fps = st.selectbox("📊 FPS", [24, 25, 30, 60], index=0)
        with col3:
            interval = st.number_input("⏱️ Intervall (Sek)", min_value=1, value=5)

        file_format = st.selectbox("💾 Format", ["RAW (~30 MB)","JPEG Fine (~10 MB)","JPEG Normal (~5 MB)"])

        if st.button("✅ Berechnen", type="primary"):
            frames    = duration * fps
            total_sec = frames * interval
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            s = int(total_sec % 60)
            size_map  = {"RAW (~30 MB)": 30, "JPEG Fine (~10 MB)": 10, "JPEG Normal (~5 MB)": 5}
            size_gb   = frames * size_map[file_format] / 1024

            st.success(f"""
            ### 📊 Ergebnis:
            | Parameter | Wert |
            |---|---|
            | 📸 Anzahl Bilder | {frames:,} |
            | ⏱️ Aufnahmedauer | {h}h {m}m {s}s |
            | 💾 Speicherbedarf | {size_gb:.1f} GB |
            """)
            if size_gb > 64:
                st.warning("⚠️ Mehr als 64 GB!")
            if total_sec > 14400:
                st.warning("⚠️ Über 4 Stunden – mehrere Akkus einplanen!")

    with tab2:
        st.markdown("""
        ### 💡 Intervall-Empfehlungen
        | Motiv            | Intervall |
        |------------------|-----------|
        | Wolken (schnell) | 1–3s      |
        | Sonnenuntergang  | 3–5s      |
        | Sternenhimmel    | 20–30s    |
        | Baustelle        | 5–15 min  |
        | Pflanzenwachstum | 15–30 min |
        """)

# ── 🖼️ EXIF ──────────────────────────────────────────────────────
elif tool == "🖼️ EXIF":
    st.header("🖼️ EXIF-Daten auslesen")
    uploaded = st.file_uploader("📤 Foto hochladen", type=["jpg","jpeg","png","webp"])

    if uploaded:
        try:
            from PIL import Image, ExifTags
            img = Image.open(uploaded)
            col1, col2 = st.columns(2)
            with col1:
                st.image(img, caption="Vorschau", use_container_width=True)
            with col2:
                exif_data = img.getexif()
                if not exif_data:
                    st.warning("⚠️ Keine EXIF-Daten gefunden.")
                else:
                    tags = {
                        ExifTags.TAGS[k]: str(v)
                        for k, v in exif_data.items()
                        if k in ExifTags.TAGS and not isinstance(v, bytes)
                    }
                    IMPORTANT = ["Make","Model","ExposureTime","FNumber",
                                 "ISOSpeedRatings","FocalLength","DateTimeOriginal","LensModel"]
                    st.subheader("📸 Kamera-Einstellungen")
                    for key in IMPORTANT:
                        if key in tags:
                            st.markdown(f"**{key}:** `{tags[key]}`")
                    with st.expander("📋 Alle EXIF-Daten"):
                        st.dataframe(
                            pd.DataFrame(list(tags.items()), columns=["Tag","Wert"]),
                            use_container_width=True, height=400,
                        )
        except ImportError:
            st.error("Pillow fehlt: pip install Pillow")
        except Exception as e:
            st.error(f"Fehler beim Lesen der EXIF-Daten: {e}")
    else:
        st.info("👆 Lade ein Foto hoch, um EXIF-Daten anzuzeigen.")

# ── 🤖 KI ─────────────────────────────────────────────────────────
elif tool == "🤖 KI":
    st.header("🤖 KI Fotografie-Assistent")
    scene = st.text_area("📝 Szene beschreiben", placeholder="z.B. 'Sonnenuntergang am See'", height=80)

    st.markdown("**Quick-Presets:**")
    cols    = st.columns(4)
    presets = ["sunset","portrait","night","landscape","street","macro","sport","astro"]
    for i, p in enumerate(presets):
        if cols[i % 4].button(f"📸 {p.capitalize()}", use_container_width=True, key=f"ki_{p}"):
            scene = p

    KI_DB = {
        "sunset":    ("🌅 SUNSET",    "ISO 100 | f/8 | 1/125s",    "GND-Filter | Stativ | Bracketing"),
        "portrait":  ("👤 PORTRAIT",  "ISO 100 | f/1.8 | 1/200s",  "Eye-AF | 85 mm | Offener Schatten"),
        "night":     ("🌙 NACHT",     "ISO 1600 | f/2.8 | 10s",    "Stativ | Fernauslöser | RAW"),
        "landscape": ("🏔️ LANDSCHAFT","ISO 100 | f/11 | 1/60s",    "Stativ | Polfilter | Golden Hour"),
        "street":    ("🏙️ STREET",    "ISO 400 | f/5.6 | 1/250s",  "35 mm | Zone Focus | Burst"),
        "macro":     ("🔬 MAKRO",     "ISO 200 | f/8 | 1/160s",    "Focus Stack | Stativ | Diffusor"),
        "sport":     ("⚡ SPORT",     "ISO 800 | f/4 | 1/1000s",   "AI Servo | Burst | 70–200 mm"),
        "astro":     ("🌌 ASTRO",     "ISO 3200 | f/1.8 | 20s",    "500er-Regel | Neumond | MF ∞"),
    }

    if st.button("🤖 KI Vorschlag", type="primary"):
        if not scene.strip():
            st.warning("Bitte Szene beschreiben oder Preset wählen.")
        else:
            found = False
            for key, (title, settings, tips) in KI_DB.items():
                if key in scene.lower():
                    st.success(f"### {title}\n**Settings:** `{settings}`\n**Tipps:** {tips}")
                    found = True
                    break
            if not found:
                st.info("### 📸 Allgemein\n**Settings:** `ISO 200 | f/5.6 | 1/125s`\nBeschreibe deine Szene genauer.")

# ── 📋 CHEAT SHEETS ──────────────────────────────────────────────
elif tool == "📋 Cheat Sheets":
    st.header("📋 Schnellreferenz-Karten")
    sheet  = st.selectbox("📑 Kategorie:", ["Portrait","Landschaft","Nacht/Astro","Street","Makro","Sport","Hochzeit"])
    GUIDES = {
        "Portrait": """
👤 PORTRAIT
══════════════════════════════
Brennweite:  85–135 mm
Blende:      f/1.4 – f/2.8
ISO:         100–400
Verschluss:  1/200s+
FOKUS:   Eye-AF | Single Point
LICHT:   Offener Schatten | Golden Hour
TIPPS:   Augen im oberen Drittel | Burst
""",
        "Landschaft": """
🏔️ LANDSCHAFT
══════════════════════════════
Brennweite:  16–35 mm
Blende:      f/8 – f/16
ISO:         100
Verschluss:  Stativ!
FOKUS:   1/3 der Szene | Hyperfokus
FILTER:  Polfilter + GND
ZEIT:    Golden Hour | Blaue Stunde
""",
        "Nacht/Astro": """
🌙 NACHT & ASTRO
══════════════════════════════
Brennweite:  14–24 mm
Blende:      f/1.4 – f/2.8
ISO:         1600–6400
Verschluss:  500 ÷ Brennweite (max)
FOKUS:   MF auf hellen Stern
SETUP:   Neumond | Stativ | RAW
STACK:   Sequator / Starry Landscape
""",
        "Street": """
🏙️ STREET
══════════════════════════════
Brennweite:  28–50 mm (35 mm klassisch)
Blende:      f/5.6 – f/8
ISO:         Auto (max 3200)
Verschluss:  1/250s+
TECHNIK:  Zone Focus @ 3 m
TIPPS:    Unauffällig | Burst | Hüfte
""",
        "Makro": """
🔬 MAKRO
══════════════════════════════
Brennweite:  90–105 mm Makro
Blende:      f/5.6 – f/11
ISO:         200–800
Verschluss:  1/160s+
FOKUS:   MF | Focus Stacking
LICHT:   Diffuses Licht | Ringblitz
STATIV:  Makroschlitten empfohlen
""",
        "Sport": """
⚡ SPORT
══════════════════════════════
Brennweite:  70–400 mm
Blende:      f/2.8 – f/4
ISO:         800–3200
Verschluss:  1/1000s minimum!
AF:      AI Servo | Zone AF
BURST:   High-Speed Continuous
TIPP:    Action voraussehen
""",
        "Hochzeit": """
💍 HOCHZEIT
══════════════════════════════
ISO:         400–1600 (Kirche: 3200)
Blende:      f/2.8 – f/4
Verschluss:  1/250s+
EQUIPMENT: 2 Bodies! | 24–70 + 70–200
BACKUP:    Dual Card | 4+ Akkus
SHOT LIST: Getting Ready → Tanz
""",
    }
    st.code(GUIDES[sheet], language="text")

# ── ⚖️ VERGLEICH ─────────────────────────────────────────────────
elif tool == "⚖️ Vergleich":
    st.header("⚖️ Einstellungs-Vergleich")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🅰️ Setup A")
        a_iso    = st.selectbox("ISO",    [100,200,400,800,1600,3200,6400], index=0, key="a_iso")
        a_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16],    index=3, key="a_ap")
        a_sh_str = st.selectbox("Verschluss", SHUTTERS_ALL, index=6, key="a_sh")
    with col2:
        st.subheader("🅱️ Setup B")
        b_iso    = st.selectbox("ISO",    [100,200,400,800,1600,3200,6400], index=0, key="b_iso")
        b_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16],    index=3, key="b_ap")
        b_sh_str = st.selectbox("Verschluss", SHUTTERS_ALL, index=6, key="b_sh")

    if st.button("⚖️ Vergleichen", type="primary"):
        a_sh  = parse_shutter(a_sh_str)
        b_sh  = parse_shutter(b_sh_str)
        ev_a  = math.log2((a_ap ** 2) / a_sh) - math.log2(a_iso / 100)
        ev_b  = math.log2((b_ap ** 2) / b_sh) - math.log2(b_iso / 100)
        diff  = ev_a - ev_b
        c1, c2, c3 = st.columns(3)
        c1.metric("🅰️ Setup A", f"EV {ev_a:.2f}")
        c2.metric("🅱️ Setup B", f"EV {ev_b:.2f}")
        c3.metric("Δ Differenz", f"{abs(diff):.2f} Stops")
        if abs(diff) < 0.05:
            st.success("✅ Gleiche Belichtung!")
        elif diff > 0:
            st.info(f"☀️ Setup A ist {abs(diff):.2f} Stops heller")
        else:
            st.info(f"🌙 Setup B ist {abs(diff):.2f} Stops heller")

# ── 🎨 FILTER-SIM ────────────────────────────────────────────────
elif tool == "🎨 Filter-Sim":
    st.header("🎨 Filter-Simulator")
    uploaded = st.file_uploader("🖼️ Foto hochladen", type=["jpg","png","jpeg","webp"])

    if uploaded:
        try:
            import numpy as np
            from PIL import Image, ImageEnhance, ImageFilter

            img = Image.open(uploaded).convert("RGB")
            col1, col2 = st.columns(2)
            with col1:
                st.image(img, caption="Original", use_container_width=True)

            filt = st.selectbox("🎨 Filter wählen", [
                "Kein Filter",         "ND2  (1 Stop dunkler)",
                "ND8  (3 Stops dunkler)",  "ND64 (6 Stops dunkler)",
                "ND1000 (10 Stops dunkler)", "Schwarzweiß (S/W)",
                "Warmton (Sunset-Look)", "Kaltton (Blaustich)",
                "Kontrast erhöhen",    "Soft-Focus / Glow", "Vignette",
            ])
            intensity = st.slider("Intensität", 0.0, 1.0, 0.8, 0.05)
            img_f     = img.copy()

            if   "ND2"        in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.50  * intensity))
            elif "ND8"        in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.875 * intensity))
            elif "ND64"       in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.02, 1.0 - 0.984 * intensity))
            elif "ND1000"     in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.01, 0.001 + (1 - intensity) * 0.1))
            elif "Schwarzweiß" in filt:
                img_f = img_f.convert("L").convert("RGB")
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 0.5)
            elif "Warmton"    in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: min(255, int(p * (1.0 + 0.25 * intensity))))
                b = b.point(lambda p: max(0,   int(p * (1.0 - 0.25 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kaltton"    in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: max(0,   int(p * (1.0 - 0.20 * intensity))))
                b = b.point(lambda p: min(255, int(p * (1.0 + 0.30 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kontrast"   in filt:
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 1.5)
            elif "Soft-Focus" in filt:
                blurred = img_f.filter(ImageFilter.GaussianBlur(radius=int(intensity * 8)))
                img_f   = Image.blend(img_f, blurred, alpha=intensity * 0.6)
            elif "Vignette"   in filt:
                w_px, h_px = img_f.size
                arr        = np.array(img_f, dtype=float)
                cx, cy     = w_px / 2, h_px / 2
                Y, X       = np.ogrid[:h_px, :w_px]
                dist       = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
                mask       = np.clip(1 - intensity * np.clip(dist - 0.5, 0, 1) * 1.5, 0, 1)
                arr        = (arr * mask[:, :, np.newaxis]).clip(0, 255).astype("uint8")
                img_f      = Image.fromarray(arr)

            with col2:
                st.image(img_f, caption=f"Filter: {filt}", use_container_width=True)

            buf = io.BytesIO()
            img_f.save(buf, format="JPEG", quality=92)
            st.download_button("⬇️ Gefiltertes Bild herunterladen",
                               buf.getvalue(), "filtered_photo.jpg", "image/jpeg")
        except ImportError:
            st.error("Pillow / numpy fehlen: pip install Pillow numpy")
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Bild hoch, um Filter zu simulieren.")

# ── 🎬 VIDEO ─────────────────────────────────────────────────────
elif tool == "🎬 Video":
    st.header("🎬 Video-Modus Guide")
    tab1, tab2, tab3 = st.tabs(["📊 Specs", "⚙️ Settings", "🎞️ 180°-Regel"])

    with tab1:
        st.markdown("""
        ### 📹 Canon EOS R Video-Spezifikationen
        | Modus   | Auflösung   | FPS  | Crop   |
        |---------|-------------|------|--------|
        | 4K UHD  | 3840×2160   | 24p  | 1.74×  |
        | 4K UHD  | 3840×2160   | 30p  | 1.74×  |
        | Full HD | 1920×1080   | 60p  | 1.0×   |
        | Full HD | 1920×1080   | 120p | 1.0×   |
        """)
    with tab2:
        st.markdown("""
        ### ⚙️ Empfohlene Settings
        **🎬 Cinematic:** 24fps | 1/50s | C-Log | ND-Filter\n
        **📺 YouTube:**   30fps | 1/60s | Standard | Dual Pixel AF\n
        **⚡ Slow-Mo:**   120fps | 1/250s | Viel Licht erforderlich
        """)
    with tab3:
        fps_v        = st.selectbox("FPS wählen:", [24, 25, 30, 50, 60, 120])
        shutter_180  = fps_v * 2
        st.success(f"**{fps_v} fps → 1/{shutter_180}s Verschlusszeit** (180°-Regel)")

# ── 🎨 BEARBEITUNG ───────────────────────────────────────────────
elif tool == "🎨 Bearbeitung":
    st.header("🎨 Fotobearbeitung & Post-Processing")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Grundbearbeitung", "🌈 Farben", "✨ Effekte", "🌙 Astro", "📚 Workflows"]
    )
    with tab1:
        st.markdown("#### Basis-Korrektur (Lightroom)")
        col1, col2 = st.columns(2)
        with col1:
            exp_val    = st.slider("Belichtung", -2.0, 2.0, 0.0, 0.1)
            contrast_v = st.slider("Kontrast",   -50, 100, 20)
            highlights = st.slider("Lichter",    -100, 100, -40)
        with col2:
            shadows    = st.slider("Tiefen",     -100, 100, 40)
            whites     = st.slider("Weiß",       -100, 100, 10)
            blacks     = st.slider("Schwarz",    -100, 100, -10)
        st.success(
            f"Belichtung: {exp_val:+.1f} | Kontrast: {contrast_v:+d}\n"
            f"Lichter: {highlights:+d} | Tiefen: {shadows:+d} | Weiß: {whites:+d} | Schwarz: {blacks:+d}"
        )
    with tab2:
        st.markdown("#### HSL / Farbkorrektur")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("🔵 Blau (Himmel)")
            st.slider("Sättigung", -100, 100, 20, key="bl_s")
            st.slider("Helligkeit", -100, 100, -20, key="bl_l")
        with col2:
            st.caption("🟠 Orange (Haut)")
            st.slider("Sättigung", -100, 100, 10, key="or_s")
            st.slider("Helligkeit", -100, 100, 5,  key="or_l")
    with tab3:
        clarity  = st.slider("Klarheit",          -50, 100, 20)
        dehaze   = st.slider("Dunst entfernen",    -50, 100, 15)
        vignette = st.slider("Vignette",          -100, 100, -20)
        grain    = st.slider("Körnigkeit",           0, 100,  10)
        st.info(f"Klarheit: {clarity:+d} | Dunst: {dehaze:+d} | Vignette: {vignette:+d} | Körnung: {grain}")
    with tab4:
        st.markdown("""
        #### 🌙 Astro-Workflow (Schritt für Schritt)
        1. **Stacking:** Sequator → 16-bit TIFF
        2. **WB:** 3800 K
        3. **Belichtung** +0.7 | Tiefen +50 | Lichter −30
        4. **HSL:** Blau Sättigung +40 | Lila +50
        5. **Schärfen:** 70 | Rauschreduktion: 25
        6. **Klarheit:** +50 | Dunst: +40 | Vignette: −20
        """)
    with tab5:
        st.markdown("""
        #### Export-Einstellungen
        | Zweck      | Format | Qualität | Größe  | Farbraum  |
        |------------|--------|----------|--------|-----------|
        | Web/Social | JPEG   | 80–85%   | 2048px | sRGB      |
        | Druck      | TIFF   | 100%     | 300DPI | AdobeRGB  |
        | Archiv     | DNG    | –        | Orig.  | –         |
        """)

# ── 🔋 AKKU ──────────────────────────────────────────────────────
elif tool == "🔋 Akku":
    st.header("🔋 Akku-Kalkulator")
    BATTERY_MAP = {
        "LP-E6NH (2130 mAh) – ~370 Shots": 370,
        "LP-E6N  (1865 mAh) – ~350 Shots": 350,
        "LP-E6   (1800 mAh) – ~300 Shots": 300,
    }
    battery = st.selectbox("🔋 Akku-Typ", list(BATTERY_MAP.keys()))
    cap     = BATTERY_MAP[battery]
    spm     = st.number_input("⏱️ Shots/Minute", 0.5, 10.0, 2.0, 0.5)

    col1, col2, col3 = st.columns(3)
    lcd   = col1.slider("📱 LCD-Nutzung (%)",  0, 100, 50)
    flash = col2.slider("💡 Blitz-Nutzung (%)", 0, 100, 20)
    wifi  = col3.slider("📡 WiFi/BT (%)",       0, 100, 30)
    ibis  = st.checkbox("📷 IBIS aktiv", value=True)

    if st.button("✅ Berechnen", type="primary"):
        factor = max(0.3,
            1.0
            - (lcd   / 100) * 0.15
            - (flash / 100) * 0.20
            - (wifi  / 100) * 0.10
            - (0.05 if ibis else 0)
        )
        shots  = int(cap * factor)
        mins   = shots / spm if spm > 0 else 0
        h, m   = int(mins // 60), int(mins % 60)

        c1, c2, c3 = st.columns(3)
        c1.metric("📸 Shots",    f"{shots:,}")
        c2.metric("⏱️ Laufzeit", f"{h}h {m}min")
        c3.metric("⚡ Effizienz", f"{factor*100:.0f}%")

        if factor < 0.6:
            st.warning("⚠️ Hoher Verbrauch – Ersatzakku einpacken!")
        akkus = math.ceil((8 * 60 * spm) / max(shots, 1))
        st.info(f"💡 Für 8h Shooting: ca. **{akkus} Akkus** empfohlen")

# ════════════════════════════════════════════════════════════════
#  🤿 UNTERWASSER-FOTOGRAFIE ASSISTANT (Canon + Apexcam)
# ═══════════════════════════════════════════════════════════════

elif tool == "🤿 Unterwasser-Modus":
    st.header("🤿 Unterwasser-Fotografie Assistant")
    st.markdown("Settings & Tipps für Canon EOS R & Apexcam ActionCam")

    # 📍 Basis-Daten (für beide Kameras relevant)
    col1, col2 = st.columns(2)
    with col1:
        depth = st.slider(" Tiefe (m)", 0, 60, 5)
        visibility = st.slider("👁️ Sichtweite (m)", 1, 30, 10)
    with col2:
        water_type = st.selectbox("💧 Wasser-Typ", ["Tropisch/Klar", "Gemäßigt", "Trüb/Kalt"])
        use_flash = st.checkbox("💡 Blitz/Licht nutzen", value=True)

    # ────────────────────────────────────────────────────────────
    #  TAB-ANSICHT FÜR KAMERA-SPEZIFISCHE TIPPS
    # ────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["📷 Canon EOS R (Pro)", "🏄 Apexcam (Action)"])

    # >>> CANON EOS R TAB <<<
    with tab1:
        st.subheader("📷 Canon EOS R Settings")
        c1, c2 = st.columns(2)
        
        # 1. Weißabgleich Logik
        if use_flash:
            wb_val = "4800K – 5200K (Blitz)"
        else:
            base_wb = {"Tropisch/Klar": 5600, "Gemäßigt": 6000, "Trüb/Kalt": 6500}
            wb_val = f"{min(base_wb[water_type] + (depth * 25), 8000)}K"
            
        c1.metric("⚖️ Weißabgleich", wb_val)
        c1.metric(" Bildformat", "RAW + JPEG (Fine)")
        
        # 2. Fokus-Tipps
        c2.markdown("""
        **Fokus-Strategie:**
        ✅ **Focus Peaking (Rot)** aktivieren
        ✅ **MF Assist** (Lupe) nutzen
        ✅ **Back-Button Focus** für schnellen Wechsel
        """)

        if use_flash:
             st.success("💡 **Blitz-Tipp:** Strobe-Arme auf 45° stellen, um Rückstreuung (Backscatter) zu vermeiden.")
        else:
            st.warning(" **Ohne Blitz:** Roter Filter ab 5m Tiefe dringend empfohlen!")

    # >>> APEXCAM TAB <<<
    with tab2:
        st.subheader("🏄 Apexcam ActionCam Settings")
        st.info("🔹 Klein, wendig, perfekt für B-Roll & enge Höhlen.")
        
        col_v, col_w = st.columns(2)
        with col_v:
            st.markdown("**🎥 Video Einstellungen**")
            st.write("🎞️ **Auflösung:** 4K / 60fps")
            st.caption("(60fps macht Bewegungen flüssiger & leichtes Zeitlupen-Potenzial)")
            st.write("📷 **Foto:** SuperPhoto (HDR)")
            
        with col_w:
            st.markdown("** Stabilisierung & Licht**")
            st.write("🌊 **Anti-Shake:** EIS auf 'HOCH' stellen!")
            st.caption("(Wasserströmung wackelt stark, EIS ist Pflicht)")
            st.write(" **Filter:** Roter Dome-Filter ab 3m")

        # Apexcam Spezifika
        with st.expander("🐙 Apexcam Profi-Tipps"):
            st.markdown("""
            1. **Get Close or Go Home:** ActionCams haben kleine Sensoren. Geh nah ran (<1m), sonst wird alles grau/blau.
            2. **Housing prüfen:** Die Apexcam M80 Air ist 40m wasserdicht *nackt*, aber für Fotos immer das Gehäuse nutzen!
            3. **Touchscreen nass:** Deaktiviere "Touch Lock" oder nutze den "Mode"-Knopf am Gehäuse, da der Screen nass oft "spinnt".
            4. **Akku:** Kälteschutz (Neopren-Hülle) hilft bei kaltem Wasser.
            """)
            
        if visibility < 5:
            st.warning("⚠️ Trübes Wasser: Apexcam leidet hier mehr als die Canon. Nutze Weitwinkel-Makro-Linse (Wet Lens)!")

    # ────────────────────────────────────────────────────────────
    #  GLOBALE UNTERWASSER-DATEN (Für beide Kameras)
    # ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🌊 Umgebungs-Analyse")
    
    # Farbverlust (Physik)
    if depth <= 3: lost_colors = "Keine"
    elif depth <= 8: lost_colors = "Rot"
    elif depth <= 15: lost_colors = "Rot, Orange"
    else: lost_colors = "Rot, Orange, Gelb, Grün"
    
    st.metric("🎨 Verlorene Farben ab dieser Tiefe", lost_colors)
    
    # Checkliste
    with st.expander("✅ Pre-Dive Checkliste"):
        checks = [
            "O-Ring reinigen & einfetten",
            "Speicherkarte formatiert?",
            "Akku voll (Kälte-Reserve einkalkulieren)",
            "Gehäuse-Vakuumtest gemacht?",
            "Objektiv trocken? (Keine Fingerabdrücke)"
        ]
        for c in checks:
            st.checkbox(c, key=f"uw_{c}")

elif tool == "📤 PDF Export":
    st.header("📄 Shooting-Plan erstellen")
    st.markdown("Erstelle einen professionellen PDF-Bericht für Kunden oder als Checkliste.")

    # Import prüfen
    try:
        from fpdf import FPDF
        import datetime
    except ImportError:
        st.error("❌ Fehler: 'fpdf2' ist nicht installiert. Bitte zu requirements.txt hinzufügen!")
        st.stop()

    #  Formular
    st.subheader("📝 Planungsdetails")
    
    col1, col2 = st.columns(2)
    with col1:
        pdf_client = st.text_input("Kunde / Projekt", placeholder="z. B. Hochzeit Müller")
        # Auto-Fill Location wenn verfügbar
        default_loc = ""
        if st.session_state.get("gps_coords"):
            gps = st.session_state.gps_coords
            if "," in str(gps):
                default_loc = f"{gps.split(',')[0].strip()}, {gps.split(',')[1].strip()}"
            else:
                default_loc = str(gps)
        pdf_loc = st.text_input("Ort / Location", value=default_loc)
        
    with col2:
        pdf_date = st.date_input("Datum", value=datetime.date.today())
        pdf_weather = st.text_input("Wetter / Bedingungen", placeholder="z. B. Sonne, 22°C")

    pdf_notes = st.text_area("Notizen & Settings (Kamera, Objektive, Ablauf...)", height=150, 
                             placeholder="• 16:00 Uhr: Golden Hour Start\n• Objektiv: 50mm 1.2\n• ND1000 für Wasser...")

    #  PDF Generierung
    if st.button("📄 PDF generieren & Download", type="primary"):
        if not pdf_client or not pdf_loc:
            st.warning("⚠️ Bitte mindestens Kunde und Ort angeben.")
        else:
            try:
                # PDF Klasse
                class ShootingPDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica", 'B', 15)
                        self.set_text_color(41, 98, 255) # Blau
                        self.cell(0, 10, 'Canon EOS R - Shooting Plan', 0, 1, 'C')
                        self.ln(5)
                        self.set_draw_color(200, 200, 200)
                        self.line(10, 25, 200, 25)
                        self.ln(10)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica", 'I', 8)
                        self.set_text_color(128, 128, 128)
                        self.cell(0, 10, f'Erstellt mit Canon EOS R Pro Tool | {datetime.datetime.now().strftime("%d.%m.%Y")}', 0, 0, 'C')

                pdf = ShootingPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # Inhalt
                pdf.set_font("Helvetica", 'B', 12)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 8, f'Projekt: {pdf_client}', 0, 1)
                pdf.set_font("Helvetica", size=11)
                pdf.cell(0, 8, f'Datum: {pdf_date.strftime("%d.%m.%Y")}', 0, 1)
                pdf.cell(0, 8, f'Ort: {pdf_loc}', 0, 1)
                if pdf_weather:
                    pdf.cell(0, 8, f'Wetter: {pdf_weather}', 0, 1)
                
                pdf.ln(10)
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 8, 'Notizen & Settings:', 0, 1)
                pdf.set_font("Helvetica", size=10)
                pdf.multi_cell(0, 6, pdf_notes if pdf_notes else "Keine Notizen vorhanden.")
                
                # Speichern
                filename = f"ShootingPlan_{pdf_date.strftime('%Y%m%d')}.pdf"
                pdf.output(filename)
                
                # Download Button
                with open(filename, "rb") as f:
                    st.success("✅ PDF erfolgreich erstellt!")
                    st.download_button(
                        label="📥 PDF Herunterladen",
                        data=f,
                        file_name=filename,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Fehler bei der Erstellung: {e}")

    st.divider()
    st.caption("💡 Tipp: Die PDF ist optimiert für den Druck und den Versand per E-Mail.")

# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════

st.divider()
st.markdown("""
<div style='text-align:center;color:#8B949E;font-size:0.85em;'>
    📷 Canon EOS R – Pro Tool v8.0 | 30 Tools<br>
    Mondphase: Jean-Meeus-Algorithmus | GPS: Query-Params-Methode<br>
    Alle Berechnungen sind Richtwerte – Praxistests empfohlen.
</div>
""", unsafe_allow_html=True)
