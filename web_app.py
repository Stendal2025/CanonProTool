# web_app_optimized.py – Canon EOS R Pro Tool (Optimierte Version)
# ──────────────────────────────────────────────────────────────────
# ÄNDERUNGEN:
#  • eval() entfernt → sicheres SHUTTER_MAP dict
#  • GPS: query_params + JS-Redirect (zuverlässige Methode)
#  • @st.cache_data für teure Berechnungen
#  • Koordinaten-Dict zentralisiert (kein Duplikat mehr)
#  • Mondphasen-Algorithmus verbessert (Jean Meeus)
#  • numpy __import__()-Hack entfernt
#  • Debug-Checkbox entfernt (nur per ENV-Var aktivierbar)
#  • Fehlerbehandlung vereinheitlicht
#  • Codestruktur: Konstanten oben, Funktionen gruppiert
# ──────────────────────────────────────────────────────────────────

import math
import os
import pandas as pd
from datetime import datetime, timedelta

import streamlit as st

# ── Optionale Imports ────────────────────────────────────────────
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

# Sicheres Shutter-Speed-Mapping (ersetzt eval())
SHUTTER_MAP: dict[str, float] = {
    "1/8000": 1/8000, "1/4000": 1/4000, "1/2000": 1/2000,
    "1/1000": 1/1000, "1/500":  1/500,  "1/250":  1/250,
    "1/125":  1/125,  "1/60":   1/60,   "1/30":   1/30,
    "1/15":   1/15,   "1/8":    1/8,    "1/4":    1/4,
    "1/2":    1/2,    "1":      1.0,    "2":      2.0,
    "4":      4.0,    "8":      8.0,    "15":     15.0,
    "30":     30.0,   "60":     60.0,
}

# Stadtkoordinaten (einmalig definiert, überall nutzbar)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "Berlin":    (52.520,  13.405),
    "München":   (48.135,  11.582),
    "Hamburg":   (53.551,   9.994),
    "Köln":      (50.938,   6.960),
    "Frankfurt": (50.111,   8.682),
    "Wien":      (48.208,  16.374),
    "Zürich":    (47.377,   8.542),
    "Stuttgart": (48.775,   9.182),
    "Düsseldorf":(51.227,   6.773),
    "Leipzig":   (51.340,  12.375),
}
CITY_LIST = sorted(CITY_COORDS.keys())

# CoC (Circle of Confusion) je Sensortyp
COC_MAP: dict[str, float] = {
    "Vollformat (36×24 mm)":   0.030,
    "APS-C Canon (1.6×)":      0.019,
    "APS-C Nikon/Sony (1.5×)": 0.020,
    "Micro 4/3 (2.0×)":        0.015,
}

CROP_MAP: dict[str, float] = {
    "Vollformat (1.0×)":          1.0,
    "APS-C Canon (1.6×)":         1.6,
    "APS-C Nikon/Sony (1.5×)":    1.5,
    "Micro 4/3 (2.0×)":           2.0,
    "1 Zoll (2.7×)":              2.7,
    "Smartphone (~6×)":           6.0,
}

# ════════════════════════════════════════════════════════════════
#  HILFSFUNKTIONEN
# ════════════════════════════════════════════════════════════════

def parse_shutter(s: str) -> float:
    """Sichere Shutter-Speed-Konvertierung (kein eval)."""
    return SHUTTER_MAP.get(s, 1/125)


@st.cache_data(ttl=3600)
def calculate_moon_phase(year: int, month: int, day: int) -> float:
    """
    Verbesserte Mondphasen-Berechnung nach Jean Meeus 'Astronomical Algorithms'.
    Gibt Wert 0..1 zurück (0 = Neumond, 0.5 = Vollmond).
    """
    if month < 3:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = (math.floor(365.25 * (year + 4716))
          + math.floor(30.6001 * (month + 1))
          + day + b - 1524.5)
    # Bekannter Neumond: 6. Jan 2000 (JD 2451549.5)
    days_since_new = (jd - 2451549.5) % 29.53058867
    return days_since_new / 29.53058867


def moon_phase_info(phase: float) -> tuple[str, float, str]:
    """Gibt (Name, Beleuchtung%, Tipp) für eine Phase 0..1 zurück."""
    illum = abs(math.sin(phase * math.pi)) * 100
    if phase < 0.03 or phase > 0.97:
        return "🌑 Neumond",            illum, "Perfekt für Milchstraße & Deep-Sky!"
    if phase < 0.22:
        return "🌒 Zunehmende Sichel",  illum, "Gut für frühe Abendfotos"
    if phase < 0.28:
        return "🌓 Erstes Viertel",     illum, "Interessante Schatten am Mond"
    if phase < 0.47:
        return "🌔 Zunehmender Mond",   illum, "Zu hell für Milchstraße"
    if phase < 0.53:
        return "🌕 Vollmond",           illum, "Perfekt für Mondlandschaften"
    if phase < 0.72:
        return "🌖 Abnehmender Mond",   illum, "Gut für späte Nacht"
    if phase < 0.78:
        return "🌗 Letztes Viertel",    illum, "Mond geht spät auf"
    return "🌘 Abnehmende Sichel",      illum, "Gut für Morgenaufnahmen"


def calculate_nd(base_sec: float, stops: int) -> float:
    return base_sec * (2 ** stops)


def evaluate_exposure(iso: int, aperture: float, shutter: float):
    ev = math.log2((aperture ** 2) / shutter)
    ev_c = ev - math.log2(iso / 100)
    if ev_c < 6:    return ev_c, "⚫ Sehr dunkel"
    if ev_c < 10:   return ev_c, "🔵 Dunkel"
    if ev_c < 13:   return ev_c, "🟢 Optimal"
    if ev_c < 15:   return ev_c, "🟡 Hell"
    return ev_c, "🔴 Überbelichtet"


def calculate_dof(focal_mm: float, aperture: float, distance_m: float, coc: float = 0.030):
    h = (focal_mm ** 2) / (aperture * coc * 1000)
    fm = focal_mm / 1000
    dn = (h * distance_m) / (h + (distance_m - fm))
    df = ((h * distance_m) / (h - (distance_m - fm))
          if distance_m < h else float("inf"))
    return dn, df, (df - dn if df != float("inf") else float("inf")), h


def calculate_golden_hour(sr: str, ss: str) -> dict:
    fmt = "%H:%M"
    sunrise = datetime.strptime(sr, fmt)
    sunset  = datetime.strptime(ss, fmt)
    return {
        "golden_morning": (sunrise.strftime(fmt),
                           (sunrise + timedelta(minutes=60)).strftime(fmt)),
        "golden_evening": ((sunset  - timedelta(minutes=60)).strftime(fmt),
                           sunset.strftime(fmt)),
        "blue_morning":   ((sunrise - timedelta(minutes=30)).strftime(fmt),
                           sunrise.strftime(fmt)),
        "blue_evening":   (sunset.strftime(fmt),
                           (sunset  + timedelta(minutes=30)).strftime(fmt)),
    }


def calculate_flash(gn: float, distance: float, iso: int = 100) -> float:
    return round((gn * math.sqrt(iso / 100)) / distance, 1)


def milky_way_score(phase: float, month: int) -> float:
    """Gibt Score 0-100 für Milchstraßen-Sichtbarkeit zurück."""
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
    """Gibt Koordinaten zurück, Fallback auf Deutschlands Mitte."""
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


# ════════════════════════════════════════════════════════════════
#  GPS – QUERY-PARAM-METHODE
#  Funktioniert zuverlässig ohne iframe-Tricks:
#  JS liest GPS → setzt ?lat=XX&lon=YY → Streamlit liest st.query_params
# ════════════════════════════════════════════════════════════════

def gps_js_widget() -> tuple[float | None, float | None]:
    """
    Zeigt den GPS-Button an und liest Koordinaten aus Query-Params.
    Gibt (lat, lon) zurück oder (None, None) wenn noch nicht abgerufen.
    """
    params = st.query_params
    lat = params.get("lat")
    lon = params.get("lon")

    js_html = """
    <style>
      #gps-btn {
        padding: 12px 26px;
        background: #1F6FEB;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        cursor: pointer;
        transition: background 0.2s;
      }
      #gps-btn:hover { background: #58A6FF; }
      #gps-status { margin-top: 10px; color: #8B949E; font-size: 14px; }
    </style>
    <button id="gps-btn">📍 GPS-Standort automatisch abrufen</button>
    <p id="gps-status">Klicke den Button – Browser fragt nach Erlaubnis.</p>

    <script>
      document.getElementById('gps-btn').onclick = function() {
        const status = document.getElementById('gps-status');
        if (!navigator.geolocation) {
          status.textContent = '❌ Browser unterstützt Geolocation nicht.';
          return;
        }
        status.textContent = '⏳ Standort wird abgerufen…';
        navigator.geolocation.getCurrentPosition(
          function(pos) {
            const lat = pos.coords.latitude.toFixed(5);
            const lon = pos.coords.longitude.toFixed(5);
            status.textContent = '✅ Standort erkannt! Seite wird neu geladen…';
            // Füge lat/lon als Query-Params an die aktuelle URL an
            const url = new URL(window.parent.location.href);
            url.searchParams.set('lat', lat);
            url.searchParams.set('lon', lon);
            window.parent.location.href = url.toString();
          },
          function(err) {
            const msgs = {1: 'Zugriff verweigert.', 2: 'Position nicht verfügbar.', 3: 'Timeout.'};
            status.textContent = '❌ ' + (msgs[err.code] || err.message);
          },
          { enableHighAccuracy: true, timeout: 12000 }
        );
      };
    </script>
    """
    st.components.v1.html(js_html, height=110)

    if lat and lon:
        try:
            return float(lat), float(lon)
        except ValueError:
            pass
    return None, None


# ════════════════════════════════════════════════════════════════
#  APP-KONFIGURATION & CSS
# ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Canon EOS R – Pro Tool",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
  /* Mobile */
  @media (max-width: 768px) {
    .main .block-container { padding: 1rem !important; }
    .stTextInput input, .stSelectbox div { font-size: 16px !important; min-height: 44px !important; }
    .stButton>button { min-height: 44px !important; }
  }
  input, select, textarea { font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

# Debug-Modus nur wenn ENV-Var gesetzt (kein UI-Checkbox in Produktion)
if os.getenv("DEBUG_MODE") == "1":
    st.sidebar.warning("🔍 Debug-Modus aktiv")
    st.sidebar.json(dict(st.session_state))
    st.sidebar.json(dict(st.query_params))

# ════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════

st.title("📷 CANON EOS R – PRO TOOL")
st.markdown("**Web Version** | 28 Photography Tools")
st.divider()

# ════════════════════════════════════════════════════════════════
#  SIDEBAR-NAVIGATION
# ════════════════════════════════════════════════════════════════

TOOLS = [
    "🏠 Home",
    "🕶️ ND Rechner",
    "📐 Schärfentiefe",
    "📊 Belichtung",
    "🌅 Golden Hour",
    "🔦 Blitz",
    "🤖 KI",
    "🌡️ Weißabgleich",
    "📋 Cheat Sheets",
    "🔄 Crop-Faktor",
    "🖼️ EXIF",
    "⏱️ Timelapse",
    "📝 Planer",
    "⚖️ Vergleich",
    "🔭 Objektive",
    "🎬 Video",
    "🔋 Akku",
    "📡 Rauschen",
    "🗺️ Spots",
    "☁️ Wetter",
    "📈 Histogramm",
    "🎨 Filter-Sim",
    "🌙 Mond & Milchstraße",
    "🌠 Sternspuren",
    "🎨 Bearbeitung",
    "🌙 Aktuelle Mond-Daten",
    "☁️ Live-Wetter",
    "📅 5-Tage Prognose",
    "🌍 Astro & Wetter Dashboard",
    "📍 GPS-Standort",
    "📄 PDF-Planer"
]

st.sidebar.title("🔧 Tools")
tool = st.sidebar.radio("Wähle ein Werkzeug:", TOOLS, index=0)

# ════════════════════════════════════════════════════════════════
#  🏠 HOME
# ════════════════════════════════════════════════════════════════

if tool == "🏠 Home":
    st.header("Willkommen beim Canon EOS R Pro Tool!")
    st.markdown("""
    ### 📸 Was kann diese App?
    - **28 professionelle Rechner** für Fotografie
    - **Belichtungsdreieck** optimieren
    - **Schärfentiefe** berechnen
    - **Goldene Stunde** planen
    - **ND-Filter** kalkulieren
    - **Live-Wetter & Astrodaten** abrufen
    ### 🚀 Schnellstart
    Wähle links ein Tool aus der Sidebar!
    """)
    col1, col2, col3 = st.columns(3)
    with col1: st.info("📊 **Belichtung**\n\nEV-Werte berechnen")
    with col2: st.success("📐 **Schärfentiefe**\n\nDoF kalkulieren")
    with col3: st.warning("🌅 **Planung**\n\nGolden Hour Times")

# ════════════════════════════════════════════════════════════════
#  🕶️ ND RECHNER
# ════════════════════════════════════════════════════════════════

elif tool == "🕶️ ND Rechner":
    st.header("🕶️ ND Filter Rechner")
    SHUTTERS_ND = [
        "1/8000","1/4000","1/2000","1/1000","1/500","1/250",
        "1/125","1/60","1/30","1/15","1/8","1/4","1/2",
        "1","2","4","8","15","30","60",
    ]
    col1, col2 = st.columns(2)
    with col1:
        base_str = st.selectbox("Basiszeit (ohne ND)", SHUTTERS_ND, index=6)
        base_sec = parse_shutter(base_str)
    with col2:
        nd_stops = st.slider("ND Stops", 1, 15, 3,
                             help="ND8=3 | ND64=6 | ND1000=10 | ND32768=15")

    nd_factor = 2 ** nd_stops
    st.caption(f"Gewählter Filter: **ND{nd_factor}** ({nd_stops} Stops)")

    if st.button("✅ Berechnen", type="primary"):
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
        ### Ergebnis:
        - **ND Filter:** ND{nd_factor} ({nd_stops} Stops)
        - **Neue Belichtungszeit:** {result_str}
        - **Von:** {base_str} → **Zu:** {result_str}
        """)
        if result_sec > 300:
            st.warning("⚠️ Sehr lange Belichtung – Stativ + Fernauslöser empfohlen.")
        if result_sec > 900:
            st.warning("⚠️ Über 15 Minuten – Sensorrauschen durch Wärme möglich!")

# ════════════════════════════════════════════════════════════════
#  📐 SCHÄRFENTIEFE
# ════════════════════════════════════════════════════════════════

elif tool == "📐 Schärfentiefe":
    st.header("📐 Schärfentiefe-Rechner")
    col1, col2, col3 = st.columns(3)
    with col1: focal    = st.number_input("Brennweite (mm)", 14, 800, 50)
    with col2: aperture = st.selectbox("Blende (f/)",
                            [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16,22], index=4)
    with col3: distance = st.number_input("Entfernung (m)", 0.3, 500.0, 3.0, 0.1)

    sensor = st.selectbox("Sensor", list(COC_MAP.keys()))
    coc = COC_MAP[sensor]

    if st.button("✅ Berechnen", type="primary"):
        near, far, total, hyper = calculate_dof(focal, aperture, distance, coc)
        far_str   = "∞"           if far   == float("inf") else f"{far:.2f} m"
        total_str = "∞ (alles scharf)" if total == float("inf") else f"{total:.2f} m"
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

# ════════════════════════════════════════════════════════════════
#  📊 BELICHTUNG
# ════════════════════════════════════════════════════════════════

elif tool == "📊 Belichtung":
    st.header("📊 Belichtungs-Bewerter")
    SHUTTERS_BASIC = [
        "1/8000","1/4000","1/2000","1/1000","1/500",
        "1/250","1/125","1/60","1/30","1/15",
        "1/8","1/4","1/2","1","2","4","8","15","30",
    ]
    col1, col2, col3 = st.columns(3)
    with col1: iso         = st.selectbox("ISO", [100,200,400,800,1600,3200,6400,12800], index=0)
    with col2: aperture    = st.selectbox("Blende", [1.4,1.8,2.8,4.0,5.6,8.0,11,16,22], index=3)
    with col3: shutter_str = st.selectbox("Verschlusszeit", SHUTTERS_BASIC)

    shutter = parse_shutter(shutter_str)

    if st.button("📊 Bewerten", type="primary"):
        ev, rating = evaluate_exposure(iso, aperture, shutter)
        st.success(f"""
        ### Ergebnis:
        - **EV-Wert:** {ev:.2f}
        - **Bewertung:** {rating}
        - **ISO {iso} | f/{aperture} | {shutter_str}**
        """)
        # Belichtungsdreieck-Tipps
        if iso >= 3200:
            st.warning("💡 Hohes ISO – Rauschreduzierung in Post einplanen.")
        if aperture >= 16:
            st.info("💡 Kleine Blende – Beugungsunschärfe möglich (f/16+).")

# ════════════════════════════════════════════════════════════════
#  🌅 GOLDEN HOUR
# ════════════════════════════════════════════════════════════════

elif tool == "🌅 Golden Hour":
    st.header("🌅 Golden & Blue Hour")
    col1, col2 = st.columns(2)
    with col1: sunrise = st.text_input("Sonnenaufgang (HH:MM)", value="06:30")
    with col2: sunset  = st.text_input("Sonnenuntergang (HH:MM)", value="20:15")

    if st.button("🔍 Berechnen", type="primary"):
        try:
            r = calculate_golden_hour(sunrise, sunset)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🌄 Morgen")
                st.info(f"🔵 **Blaue Stunde:** {r['blue_morning'][0]} – {r['blue_morning'][1]}")
                st.warning(f"🟠 **Goldene Stunde:** {r['golden_morning'][0]} – {r['golden_morning'][1]}")
            with col2:
                st.markdown("### 🌆 Abend")
                st.warning(f"🟠 **Goldene Stunde:** {r['golden_evening'][0]} – {r['golden_evening'][1]}")
                st.info(f"🔵 **Blaue Stunde:** {r['blue_evening'][0]} – {r['blue_evening'][1]}")
        except ValueError:
            st.error("⚠️ Bitte gültiges Format HH:MM eingeben (z.B. 06:30)")

# ════════════════════════════════════════════════════════════════
#  🔦 BLITZ
# ════════════════════════════════════════════════════════════════

elif tool == "🔦 Blitz":
    st.header("🔦 Blitz-Rechner (Leitzahl)")
    col1, col2, col3 = st.columns(3)
    with col1: gn       = st.number_input("Leitzahl (GN)", 10, 100, 58)
    with col2: distance = st.number_input("Entfernung (m)", 0.5, 50.0, 5.0, 0.5)
    with col3: iso      = st.selectbox("ISO", [100,200,400,800,1600,3200], index=0)

    if st.button("✅ Berechnen", type="primary"):
        ap = calculate_flash(gn, distance, iso)
        st.success(f"""
        ### Ergebnis:
        - **Empfohlene Blende:** f/{ap}
        - **GN {gn} | {distance} m | ISO {iso}**
        """)
        with st.expander("📋 Reichweiten-Tabelle"):
            rows = [
                {"Blende": f"f/{f}",
                 "Max. Reichweite": f"{gn * math.sqrt(iso/100) / f:.1f} m"}
                for f in [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16]
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ════════════════════════════════════════════════════════════════
#  🤖 KI
# ════════════════════════════════════════════════════════════════

elif tool == "🤖 KI":
    st.header("🤖 KI Fotografie-Assistent")
    scene = st.text_area("📝 Szene beschreiben",
                         placeholder="z.B. 'Sonnenuntergang am See'", height=80)
    st.markdown("**Quick-Presets:**")
    cols = st.columns(4)
    presets = ["sunset","portrait","night","landscape","street","macro","sport","astro"]
    for i, p in enumerate(presets):
        if cols[i % 4].button(f"📸 {p.capitalize()}", use_container_width=True, key=f"ki_{p}"):
            scene = p

    KI_DB = {
        "sunset":    ("🌅 SUNSET",     "ISO 100 | f/8 | 1/125s",   "GND-Filter | Stativ | Bracketing"),
        "portrait":  ("👤 PORTRAIT",   "ISO 100 | f/1.8 | 1/200s", "Eye-AF | 85 mm | Offener Schatten"),
        "night":     ("🌙 NACHT",      "ISO 1600 | f/2.8 | 10s",   "Stativ | Fernauslöser | RAW"),
        "landscape": ("🏔️ LANDSCHAFT", "ISO 100 | f/11 | 1/60s",   "Stativ | Polfilter | Golden Hour"),
        "street":    ("🏙️ STREET",     "ISO 400 | f/5.6 | 1/250s", "35 mm | Zone Focus | Burst"),
        "macro":     ("🔬 MAKRO",      "ISO 200 | f/8 | 1/160s",   "Focus Stack | Stativ | Diffusor"),
        "sport":     ("⚡ SPORT",      "ISO 800 | f/4 | 1/1000s",  "AI Servo | Burst | 70–200 mm"),
        "astro":     ("🌌 ASTRO",      "ISO 3200 | f/1.8 | 20s",   "500er-Regel | Neumond | MF ∞"),
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
                st.info("### 📸 Allgemein\n**Settings:** `ISO 200 | f/5.6 | 1/125s`\n"
                        "Beschreibe deine Szene genauer für spezifischere Empfehlungen.")

# ════════════════════════════════════════════════════════════════
#  🌡️ WEISSABGLEICH
# ════════════════════════════════════════════════════════════════

elif tool == "🌡️ Weißabgleich":
    st.header("🌡️ Weißabgleich & Farbtemperatur")
    wb_data = [
        ("🕯️ Kerzenlicht",    "1800–2000 K",  "#FF6B35"),
        ("💡 Glühlampe",      "2700–3200 K",  "#FFA500"),
        ("🌅 Sonnenaufgang",  "3000–3500 K",  "#FF8C42"),
        ("📸 Blitz",          "5000–5500 K",  "#FFFEF0"),
        ("☀️ Tageslicht",     "5200–5800 K",  "#FFFFF0"),
        ("⛅ Bewölkt",        "6000–6500 K",  "#E8F0FF"),
        ("🏔️ Schatten",       "7000–8000 K",  "#D0E0FF"),
        ("🌌 Blaue Stunde",   "9000–12000 K", "#9090FF"),
    ]
    for name, kelvin, color in wb_data:
        c1, c2 = st.columns([2, 3])
        c1.markdown(f"<span style='color:{color};font-weight:bold'>{name}</span>",
                    unsafe_allow_html=True)
        c2.code(kelvin)
    st.info("💡 **Tipp:** Immer manuellen WB in Kelvin setzen statt Auto – stabilere Farben im Timelapse!")

# ════════════════════════════════════════════════════════════════
#  📋 CHEAT SHEETS
# ════════════════════════════════════════════════════════════════

elif tool == "📋 Cheat Sheets":
    st.header("📋 Schnellreferenz-Karten")
    sheet = st.selectbox("📑 Kategorie:",
        ["Portrait","Landschaft","Nacht/Astro","Street","Makro","Sport","Hochzeit"])
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

# ════════════════════════════════════════════════════════════════
#  🔄 CROP-FAKTOR
# ════════════════════════════════════════════════════════════════

elif tool == "🔄 Crop-Faktor":
    st.header("🔄 Crop-Faktor Rechner")
    col1, col2 = st.columns(2)
    with col1:
        focal    = st.number_input("Brennweite (mm)", 10, 800, 50)
        aperture = st.selectbox("Blende (f/)", [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16], index=4)
    with col2:
        sensor_from = st.selectbox("Von Sensor:", list(CROP_MAP.keys()), index=0)
        sensor_to   = st.selectbox("Nach Sensor:", list(CROP_MAP.keys()), index=1)

    if st.button("✅ Berechnen", type="primary"):
        cf_from = CROP_MAP[sensor_from]
        cf_to   = CROP_MAP[sensor_to]
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
        ref = [{"Sensor": k, "Crop-Faktor": v,
                "50 mm entspricht": f"{50*v:.0f} mm FF-Äquivalent"}
               for k, v in CROP_MAP.items()]
        st.dataframe(pd.DataFrame(ref), use_container_width=True)

# ════════════════════════════════════════════════════════════════
#  🖼️ EXIF
# ════════════════════════════════════════════════════════════════

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
                    tags = {ExifTags.TAGS[k]: str(v)
                            for k, v in exif_data.items()
                            if k in ExifTags.TAGS and not isinstance(v, bytes)}
                    IMPORTANT = ["Make","Model","ExposureTime","FNumber",
                                 "ISOSpeedRatings","FocalLength","DateTimeOriginal","LensModel"]
                    st.subheader("📸 Kamera-Einstellungen")
                    for key in IMPORTANT:
                        if key in tags:
                            st.markdown(f"**{key}:** `{tags[key]}`")
                    with st.expander("📋 Alle EXIF-Daten"):
                        st.dataframe(pd.DataFrame(list(tags.items()),
                                     columns=["Tag","Wert"]),
                                     use_container_width=True, height=400)
        except Exception as e:
            st.error(f"Fehler beim Lesen der EXIF-Daten: {e}")
    else:
        st.info("👆 Lade ein Foto hoch, um EXIF-Daten anzuzeigen.")

# ════════════════════════════════════════════════════════════════
#  ⏱️ TIMELAPSE
# ════════════════════════════════════════════════════════════════

elif tool == "⏱️ Timelapse":
    st.header("⏱️ Timelapse-Rechner")
    tab1, tab2 = st.tabs(["📊 Berechnung","💡 Tipps"])
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1: duration = st.number_input("🎬 Video-Länge (Sek)", min_value=5, value=30)
        with col2: fps      = st.selectbox("📊 FPS", [24,25,30,60], index=0)
        with col3: interval = st.number_input("⏱️ Intervall (Sek)", min_value=1, value=5)
        file_format = st.selectbox("💾 Format",
            ["RAW (~30 MB)","JPEG Fine (~10 MB)","JPEG Normal (~5 MB)"])
        if st.button("✅ Berechnen", type="primary"):
            frames    = duration * fps
            total_sec = frames * interval
            h, m, s   = int(total_sec//3600), int((total_sec%3600)//60), int(total_sec%60)
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
            if size_gb > 64:  st.warning("⚠️ Mehr als 64 GB!")
            if total_sec > 14400: st.warning("⚠️ Über 4 Stunden – mehrere Akkus einplanen!")
    with tab2:
        st.markdown("""
        ### 💡 Intervall-Empfehlungen
        | Motiv              | Intervall |
        |--------------------|-----------|
        | Wolken (schnell)   | 1–3s      |
        | Sonnenuntergang    | 3–5s      |
        | Sternenhimmel      | 20–30s    |
        | Baustelle          | 5–15 min  |
        | Pflanzenwachstum   | 15–30 min |
        """)

# ════════════════════════════════════════════════════════════════
#  📝 PLANER
# ════════════════════════════════════════════════════════════════

elif tool == "📝 Planer":
    st.header("📝 Aufnahme-Planer & Logbuch")
    if "logbook" not in st.session_state:
        st.session_state.logbook = []
    tab1, tab2 = st.tabs(["➕ Neuer Eintrag","📖 Logbuch"])
    SHUTTERS_LOG = ["1/1000","1/500","1/250","1/125","1/60","1/30","1/15","1s","2s","4s"]
    with tab1:
        c1, c2 = st.columns(2)
        loc = c1.text_input("📍 Ort");  sub = c2.text_input("📸 Motiv")
        c3, c4 = st.columns(2)
        iso_log = c3.selectbox("ISO", [100,200,400,800,1600,3200], key="log_iso")
        ap_log  = c4.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], key="log_ap")
        sh_log  = st.selectbox("Verschluss", SHUTTERS_LOG, key="log_sh")
        notes   = st.text_area("📝 Notizen")
        rating  = st.slider("⭐ Bewertung", 1, 5, 3)
        if st.button("➕ Speichern", type="primary"):
            if loc or sub:
                st.session_state.logbook.append({
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "loc": loc, "sub": sub,
                    "settings": f"ISO {iso_log} | f/{ap_log} | {sh_log}",
                    "notes": notes, "rating": "⭐" * rating,
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
                    st.markdown(f"- **📍 Ort:** {entry['loc']}\n"
                                f"- **📸 Motiv:** {entry['sub']}\n"
                                f"- **⚙️ Settings:** `{entry['settings']}`\n"
                                f"- **📝 Notizen:** {entry['notes']}")
            if st.button("🗑️ Alle löschen"):
                st.session_state.logbook = []
                st.rerun()
        else:
            st.info("📭 Noch keine Einträge.")

# ════════════════════════════════════════════════════════════════
#  ⚖️ VERGLEICH
# ════════════════════════════════════════════════════════════════

elif tool == "⚖️ Vergleich":
    st.header("⚖️ Einstellungs-Vergleich")
    SHUTTERS_CMP = ["1/8000","1/4000","1/2000","1/1000","1/500","1/250",
                    "1/125","1/60","1/30","1/15","1/8","1/4","1/2","1","2","4"]
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🅰️ Setup A")
        a_iso    = st.selectbox("ISO", [100,200,400,800,1600,3200,6400], index=0, key="a_iso")
        a_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], index=3, key="a_ap")
        a_sh_str = st.selectbox("Verschluss", SHUTTERS_CMP, index=6, key="a_sh")
    with col2:
        st.subheader("🅱️ Setup B")
        b_iso    = st.selectbox("ISO", [100,200,400,800,1600,3200,6400], index=0, key="b_iso")
        b_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], index=3, key="b_ap")
        b_sh_str = st.selectbox("Verschluss", SHUTTERS_CMP, index=6, key="b_sh")
    if st.button("⚖️ Vergleichen", type="primary"):
        a_sh = parse_shutter(a_sh_str)
        b_sh = parse_shutter(b_sh_str)
        ev_a = math.log2((a_ap**2) / a_sh) - math.log2(a_iso / 100)
        ev_b = math.log2((b_ap**2) / b_sh) - math.log2(b_iso / 100)
        diff = ev_a - ev_b
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

# ════════════════════════════════════════════════════════════════
#  🔭 OBJEKTIVE
# ════════════════════════════════════════════════════════════════

elif tool == "🔭 Objektive":
    st.header("🔭 RF Objektiv-Datenbank")
    LENSES = [
        {"Name":"RF 14-35mm f/4L IS",       "Typ":"Weitwinkel Zoom",  "f/":4.0,     "Gewicht":"540g",   "IS":"✅","Preis":"~1.600€"},
        {"Name":"RF 15-35mm f/2.8L IS",      "Typ":"Weitwinkel Zoom",  "f/":2.8,     "Gewicht":"840g",   "IS":"✅","Preis":"~2.500€"},
        {"Name":"RF 24-70mm f/2.8L IS",      "Typ":"Standard Zoom",    "f/":2.8,     "Gewicht":"900g",   "IS":"✅","Preis":"~2.700€"},
        {"Name":"RF 24-105mm f/4L IS",       "Typ":"Standard Zoom",    "f/":4.0,     "Gewicht":"700g",   "IS":"✅","Preis":"~1.200€"},
        {"Name":"RF 50mm f/1.2L USM",        "Typ":"Standard Prime",   "f/":1.2,     "Gewicht":"950g",   "IS":"❌","Preis":"~2.400€"},
        {"Name":"RF 50mm f/1.8 STM",         "Typ":"Standard Prime",   "f/":1.8,     "Gewicht":"160g",   "IS":"❌","Preis":"~230€"},
        {"Name":"RF 85mm f/1.2L USM",        "Typ":"Portrait Prime",   "f/":1.2,     "Gewicht":"1195g",  "IS":"❌","Preis":"~3.000€"},
        {"Name":"RF 85mm f/2 Macro IS",      "Typ":"Portrait Prime",   "f/":2.0,     "Gewicht":"500g",   "IS":"✅","Preis":"~700€"},
        {"Name":"RF 70-200mm f/2.8L IS",     "Typ":"Tele Zoom",        "f/":2.8,     "Gewicht":"1070g",  "IS":"✅","Preis":"~2.900€"},
        {"Name":"RF 100-500mm f/4.5-7.1L",   "Typ":"Supertele Zoom",   "f/":"4.5-7", "Gewicht":"1370g",  "IS":"✅","Preis":"~3.000€"},
        {"Name":"RF 100mm f/2.8L Macro IS",  "Typ":"Makro Prime",      "f/":2.8,     "Gewicht":"730g",   "IS":"✅","Preis":"~1.500€"},
    ]
    typ_filter = st.multiselect("🏷️ Typ filtern:", sorted({l["Typ"] for l in LENSES}))
    filtered = [l for l in LENSES if not typ_filter or l["Typ"] in typ_filter]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=450)
    st.info(f"📊 {len(filtered)} von {len(LENSES)} Objektiven angezeigt")

# ════════════════════════════════════════════════════════════════
#  🎬 VIDEO
# ════════════════════════════════════════════════════════════════

elif tool == "🎬 Video":
    st.header("🎬 Video-Modus Guide")
    tab1, tab2, tab3 = st.tabs(["📊 Specs","⚙️ Settings","🎞️ 180°-Regel"])
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
        **📺 YouTube:** 30fps | 1/60s | Standard | Dual Pixel AF\n
        **⚡ Slow-Mo:** 120fps | 1/250s | Viel Licht erforderlich
        """)
    with tab3:
        fps_v = st.selectbox("FPS wählen:", [24,25,30,50,60,120])
        shutter_180 = fps_v * 2
        st.success(f"**{fps_v} fps → 1/{shutter_180}s Verschlusszeit** (180°-Regel)")

# ════════════════════════════════════════════════════════════════
#  🔋 AKKU
# ════════════════════════════════════════════════════════════════

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
    lcd   = col1.slider("📱 LCD-Nutzung (%)",   0, 100, 50)
    flash = col2.slider("💡 Blitz-Nutzung (%)", 0, 100, 20)
    wifi  = col3.slider("📡 WiFi/BT (%)",        0, 100, 30)
    ibis  = st.checkbox("📷 IBIS aktiv", value=True)
    if st.button("✅ Berechnen", type="primary"):
        factor = max(0.3, 1.0 - (lcd/100)*0.15 - (flash/100)*0.20
                     - (wifi/100)*0.10 - (0.05 if ibis else 0))
        shots = int(cap * factor)
        mins  = shots / spm if spm > 0 else 0
        h, m  = int(mins//60), int(mins%60)
        c1, c2, c3 = st.columns(3)
        c1.metric("📸 Shots",    f"{shots:,}")
        c2.metric("⏱️ Laufzeit", f"{h}h {m}min")
        c3.metric("⚡ Effizienz",f"{factor*100:.0f}%")
        if factor < 0.6:
            st.warning("⚠️ Hoher Verbrauch – Ersatzakku einpacken!")
        akkus_needed = math.ceil((8 * 60 * spm) / max(shots, 1))
        st.info(f"💡 Für 8h Shooting: ca. **{akkus_needed} Akkus** empfohlen")

# ════════════════════════════════════════════════════════════════
#  📡 RAUSCHEN
# ════════════════════════════════════════════════════════════════

elif tool == "📡 Rauschen":
    st.header("📡 Sensor-Rauschen & Dynamikumfang")
    iso = st.selectbox("ISO wählen:", [100,200,400,800,1600,3200,6400,12800,25600])
    if st.button("📊 Analysieren", type="primary"):
        stops = math.log2(iso / 100)
        dr    = max(13.5 - stops * 0.8, 5.0)
        snr   = max(40   - stops * 5.5, 8.0)
        rating = ("🟢 Exzellent" if snr >= 35 else
                  "🟡 Gut"       if snr >= 25 else
                  "🟠 Akzeptabel"if snr >= 15 else "🔴 Stark verrauscht")
        c1, c2, c3 = st.columns(3)
        c1.metric("📉 SNR",           f"{snr:.1f} dB")
        c2.metric("🌈 Dynamikumfang", f"{dr:.1f} EV")
        c3.metric("📊 Bewertung",     rating)
        with st.expander("📋 Alle ISO-Werte im Vergleich"):
            rows = []
            for i in [100,200,400,800,1600,3200,6400,12800,25600]:
                s = math.log2(i / 100)
                rows.append({"ISO": i,
                              "SNR (dB)":     f"{max(40-s*5.5,8):.1f}",
                              "Dynamik (EV)": f"{max(13.5-s*0.8,5):.1f}",
                              "Empfehlung":   "✅" if max(40-s*5.5,8) >= 25 else "⚠️"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ════════════════════════════════════════════════════════════════
#  🗺️ SPOTS
# ════════════════════════════════════════════════════════════════

elif tool == "🗺️ Spots":
    st.header("🗺️ Foto-Spot Manager")
    if "spots" not in st.session_state:
        st.session_state.spots = []
    tab1, tab2 = st.tabs(["➕ Spot hinzufügen","📌 Meine Spots"])
    with tab1:
        c1, c2 = st.columns(2)
        name  = c1.text_input("📍 Name des Spots")
        typ   = c2.selectbox("🏷️ Typ", ["Landschaft","Portrait","Street","Architektur","Astro","Sonstiges"])
        c3, c4 = st.columns(2)
        lat   = c3.number_input("🌐 Breitengrad",  value=51.34, format="%.4f")
        lon   = c4.number_input("🌐 Längengrad",   value=12.38, format="%.4f")
        beste = st.text_input("⏰ Beste Zeit")
        notes = st.text_area("📝 Notizen")
        if st.button("➕ Spot speichern", type="primary"):
            if name:
                st.session_state.spots.append({
                    "Name": name, "Typ": typ,
                    "Lat": lat, "Lon": lon,
                    "Beste Zeit": beste, "Notizen": notes
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

# ════════════════════════════════════════════════════════════════
#  ☁️ WETTER (statischer Assistent)
# ════════════════════════════════════════════════════════════════

elif tool == "☁️ Wetter":
    st.header("☁️ Wetter-Assistent für Fotografen")
    col1, col2 = st.columns(2)
    temp   = col1.number_input("🌡️ Temperatur (°C)", value=15)
    wind   = col2.number_input("💨 Wind (km/h)", value=10)
    clouds = st.slider("☁️ Bewölkung (%)", 0, 100, 40)
    cond   = st.selectbox("Bedingung",
        ["☀️ Klar","⛅ Teilweise","☁️ Bedeckt","🌧️ Regen","🌫️ Nebel","❄️ Schnee"])
    if st.button("📊 Foto-Bedingungen prüfen", type="primary"):
        recs = []
        if clouds < 30:   recs.append("🌅 Klarer Horizont – ideal für Sunset & Astro!")
        elif clouds < 60: recs.append("⛅ Wolkenstruktur – gut für dramatische Landschaften")
        else:             recs.append("☁️ Weiches Diffuslicht – ideal für Portrait & Makro")
        if wind > 40:     recs.append("💨 Starker Wind! Stativ beschweren, 1/500s+, Tele meiden")
        elif wind > 20:   recs.append("💨 Mäßiger Wind – Verwacklungsgefahr, Stativ stabilisieren")
        if temp < 0:      recs.append("❄️ Kalt! Akku warm halten, Fingerhandschuhe")
        elif temp > 35:   recs.append("☀️ Heiß! Kamera vor Sonne schützen")
        if "Nebel" in cond: recs.append("🌫️ Nebel = mystische Stimmung! Kontrast & Klarheit erhöhen")
        if "Regen" in cond: recs.append("🌧️ Regenhülle! Nach dem Regen = tolle Reflexionen")
        if "Schnee" in cond: recs.append("❄️ Belichtung +1 EV | Weißabgleich manuell")
        st.info("✅ **Analyse:**\n\n" + "\n\n".join(recs))

# ════════════════════════════════════════════════════════════════
#  📈 HISTOGRAMM
# ════════════════════════════════════════════════════════════════

elif tool == "📈 Histogramm":
    st.header("📈 Belichtungs-Histogramm Simulator")
    ev       = st.slider("EV (Helligkeit)", 0, 20, 12)
    contrast = st.slider("Kontrast (Szene)", 10, 100, 50)
    channel  = st.selectbox("Kanal", ["Luminanz","🔴 Rot","🟢 Grün","🔵 Blau"])
    if st.button("📊 Generieren", type="primary"):
        try:
            import numpy as np
            center = int((ev / 20) * 255)
            x      = np.arange(256)
            y      = 1000 * np.exp(-((x - center)**2) / (2 * (contrast/2)**2))
            color_map = {"Luminanz":"#E0E0E0","🔴 Rot":"#FF4444",
                         "🟢 Grün":"#44FF44","🔵 Blau":"#4444FF"}
            df_hist = pd.DataFrame({"Pixelwert": x, "Häufigkeit": y.astype(int)})
            st.bar_chart(df_hist.set_index("Pixelwert"),
                         color=color_map[channel], use_container_width=True)
            if ev > 17:   st.warning("🔴 Überbelichtet – Clipping!")
            elif ev < 4:  st.warning("🔵 Unterbelichtet – Detailverlust in Schatten!")
            else:         st.success("🟢 Gut belichtet! ETTR für weniger Rauschen.")
        except ImportError:
            st.error("numpy nicht verfügbar: pip install numpy")

# ════════════════════════════════════════════════════════════════
#  🎨 FILTER-SIM
# ════════════════════════════════════════════════════════════════

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
                "Kein Filter",
                "ND2  (1 Stop dunkler)","ND8  (3 Stops dunkler)",
                "ND64 (6 Stops dunkler)","ND1000 (10 Stops dunkler)",
                "Schwarzweiß (S/W)","Warmton (Sunset-Look)",
                "Kaltton (Blaustich)","Kontrast erhöhen",
                "Soft-Focus / Glow","Vignette",
            ])
            intensity = st.slider("Intensität", 0.0, 1.0, 0.8, 0.05)
            img_f = img.copy()
            if "ND2"    in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.50 * intensity))
            elif "ND8"  in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.875 * intensity))
            elif "ND64" in filt: img_f = ImageEnhance.Brightness(img_f).enhance(max(0.02, 1.0 - 0.984 * intensity))
            elif "ND1000"in filt:img_f = ImageEnhance.Brightness(img_f).enhance(max(0.01, 0.001 + (1-intensity)*0.1))
            elif "Schwarzweiß" in filt:
                img_f = img_f.convert("L").convert("RGB")
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 0.5)
            elif "Warmton" in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: min(255, int(p * (1.0 + 0.25 * intensity))))
                b = b.point(lambda p: max(0,   int(p * (1.0 - 0.25 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kaltton" in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: max(0,   int(p * (1.0 - 0.20 * intensity))))
                b = b.point(lambda p: min(255, int(p * (1.0 + 0.30 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kontrast" in filt:
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 1.5)
            elif "Soft-Focus" in filt:
                blurred = img_f.filter(ImageFilter.GaussianBlur(radius=int(intensity * 8)))
                img_f = Image.blend(img_f, blurred, alpha=intensity * 0.6)
            elif "Vignette" in filt:
                # Numpy-Import ist bereits oben erfolgt
                w, h_px = img_f.size
                arr = np.array(img_f, dtype=float)
                cx, cy = w / 2, h_px / 2
                Y, X   = np.ogrid[:h_px, :w]
                dist   = np.sqrt(((X - cx)/cx)**2 + ((Y - cy)/cy)**2)
                mask   = np.clip(1 - intensity * np.clip(dist - 0.5, 0, 1) * 1.5, 0, 1)
                arr    = (arr * mask[:, :, np.newaxis]).clip(0, 255).astype("uint8")
                img_f  = Image.fromarray(arr)
            with col2:
                st.image(img_f, caption=f"Filter: {filt}", use_container_width=True)
            from io import BytesIO
            buf = BytesIO()
            img_f.save(buf, format="JPEG", quality=92)
            st.download_button("⬇️ Gefiltertes Bild herunterladen",
                               buf.getvalue(), "filtered_photo.jpg", "image/jpeg")
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Bild hoch, um Filter zu simulieren.")

# ════════════════════════════════════════════════════════════════
#  🌙 MOND & MILCHSTRAßE
# ════════════════════════════════════════════════════════════════

elif tool == "🌙 Mond & Milchstraße":
    st.header("🌙 Mondphasen & Milchstraße Sichtbarkeit")
    city_sel = st.selectbox("📍 Stadt", ["(manuell)"] + CITY_LIST)
    col1, col2 = st.columns(2)
    with col1:
        date_str = st.text_input("📅 Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y"))
    with col2:
        if city_sel != "(manuell)":
            latitude = CITY_COORDS[city_sel][0]
            st.number_input("🌍 Breitengrad", value=latitude, disabled=True)
        else:
            latitude = st.number_input("🌍 Breitengrad", min_value=-90.0, max_value=90.0, value=51.34)
    option = st.selectbox("🎯 Fokus", ["Milchstraße","Mondfotografie","Deep Sky","Nordlichter"])

    if st.button("🔍 Berechnen", type="primary"):
        try:
            day, month, year = map(int, date_str.split("."))
            phase = calculate_moon_phase(year, month, day)
            p_name, p_illum, p_tip = moon_phase_info(phase)

            if option == "Milchstraße":
                score       = milky_way_score(phase, month)
                best_time   = "22:30–04:00" if 4 <= month <= 9 else "03:00–06:00"
                rec = ("🟢 Hervorragend!" if score >= 85 else
                       "🟡 Gut!"          if score >= 65 else
                       "🟠 Mäßig."        if score >= 40 else
                       "🔴 Schlecht.")
            elif option == "Mondfotografie":
                score     = p_illum
                best_time = "Abends nach Sonnenuntergang"
                rec = "🌕 Vollmond – perfekt!" if 0.45 < phase < 0.55 else "🌙 Interessante Phase"
            elif option == "Deep Sky":
                score     = max(0, 100 - p_illum)
                best_time = "Mitternacht–Morgengrauen"
                rec = "🔭 Dunkler Himmel – ideal!" if score > 80 else "⚠️ Auf Neumond warten."
            else:  # Nordlichter
                if abs(latitude) > 58:
                    score     = max(0, 100 - p_illum) * (1.0 if month in range(10,13) or month in range(1,4) else 0.5)
                    best_time = "21:00–02:00"
                    rec = "🌌 Aurora möglich bei klarem Himmel!"
                else:
                    score = 15; best_time = "–"
                    rec = "📍 Zu weit südlich – >58° Breite nötig (Skandinavien, Island)"

            st.success(f"""
            ### 📊 Ergebnis – {date_str}
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
        except (ValueError, TypeError):
            st.error("⚠️ Ungültiges Datum. Format: TT.MM.JJJJ (z.B. 15.08.2025)")

# ════════════════════════════════════════════════════════════════
#  🌠 STERNSPUREN
# ════════════════════════════════════════════════════════════════

elif tool == "🌠 Sternspuren":
    st.header("🌠 Sternspuren & Astrofotografie")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🎯 Sternspuren","⭐ Scharfe Sterne","📐 Planung","📚 Tipps"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            total_time = st.number_input("Gesamtzeit (Min)", 10, 480, 60)
            interval   = st.number_input("Intervall (Sek)", 1, 30, 5)
        with col2:
            shutter_s = st.selectbox("Belichtung/Bild", ["10s","15s","20s","25s","30s"], index=2)
            iso_s     = st.selectbox("ISO", [400,800,1600,3200], index=2)
        if st.button("✅ Berechnen", type="primary", key="star_calc"):
            sh_sec    = int(shutter_s.replace("s",""))
            n_frames  = (total_time * 60) // (sh_sec + interval)
            trail_deg = (total_time / 4) * 15
            st.success(f"""
            ### Ergebnis:
            - Bilder: **{n_frames:,}**  |  Dauer: **{total_time} Min**
            - Sternspur: **{trail_deg:.0f}°** am Himmel
            - Speicher RAW: **~{n_frames*30/1024:.1f} GB**
            - Settings: {shutter_s} | ISO {iso_s} | f/2.8 | MF ∞
            """)
            st.info("📦 Stacking: StarStaX (Win) | Starry Landscape Stacker (Mac) | Sequator (online)")
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            focal_sh  = st.number_input("Brennweite (mm)", 14, 400, 24)
            sensor_sh = st.selectbox("Sensor",
                ["Vollformat","APS-C Canon 1.6×","APS-C Nikon 1.5×","Micro 4/3 2×"])
        with col2:
            ap_sh = st.selectbox("Blende", [1.2,1.4,1.8,2.0,2.8,4.0], index=3)
        crop_sh_map = {"Vollformat":1.0,"APS-C Canon 1.6×":1.6,
                       "APS-C Nikon 1.5×":1.5,"Micro 4/3 2×":2.0}
        crop_sh = crop_sh_map[sensor_sh]
        max_500 = 500 / (focal_sh * crop_sh)
        max_npf = (35 * ap_sh + 30) / (focal_sh * crop_sh)
        st.success(f"""
        ### Maximale Belichtungszeit:
        - **500er-Regel:** {max_500:.1f}s
        - **NPF-Regel (präziser):** {max_npf:.1f}s
        
        Empfehlung: **{max_npf:.0f}s** für punktförmige Sterne
        """)
    with tab3:
        col1, col2 = st.columns(2)
        with col1: date_plan = st.text_input("Datum", value=datetime.now().strftime("%d.%m.%Y"))
        with col2:
            lp = st.selectbox("Lichtverschmutzung",
                ["Bortle 1–2 (Sehr dunkel)","Bortle 3–4 (Dunkel)",
                 "Bortle 5–6 (Vorstadt)","Bortle 7–9 (Stadt)"])
        if st.button("🔍 Prüfen"):
            try:
                d, mo, yr = map(int, date_plan.split("."))
                phase = calculate_moon_phase(yr, mo, d)
                _, illum, _ = moon_phase_info(phase)
                lp_score = {"Bortle 1–2 (Sehr dunkel)":1.0,"Bortle 3–4 (Dunkel)":0.7,
                            "Bortle 5–6 (Vorstadt)":0.4,"Bortle 7–9 (Stadt)":0.1}[lp]
                season = 1.0 if 3 <= mo <= 10 else 0.4
                total  = ((100-illum)/100*0.4 + season*0.3 + lp_score*0.3) * 100
                st.success(f"""
                ### Score: {total:.0f}/100
                Mond: {illum:.0f}% | Saison: {"✅" if season==1.0 else "⚠️"} | LP: {lp}
                {astro_recommendation(total)}
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
        
        **Stacking-Software:** Sequator (Win) | Starry Landscape Stacker (Mac) | StarStaX
        """)

# ════════════════════════════════════════════════════════════════
#  🎨 BEARBEITUNG
# ════════════════════════════════════════════════════════════════

elif tool == "🎨 Bearbeitung":
    st.header("🎨 Fotobearbeitung & Post-Processing")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Grundbearbeitung","🌈 Farben","✨ Effekte","🌙 Astro","📚 Workflows"])
    with tab1:
        st.markdown("#### Basis-Korrektur (Lightroom)")
        col1, col2 = st.columns(2)
        with col1:
            exp_val    = st.slider("Belichtung",  -2.0, 2.0,  0.0, 0.1)
            contrast   = st.slider("Kontrast",    -50,  100,   20)
            highlights = st.slider("Lichter",     -100, 100,  -40)
        with col2:
            shadows    = st.slider("Tiefen",      -100, 100,   40)
            whites     = st.slider("Weiß",        -100, 100,   10)
            blacks     = st.slider("Schwarz",     -100, 100,  -10)
        st.success(f"""Belichtung: {exp_val:+.1f} | Kontrast: {contrast:+d}
Lichter: {highlights:+d} | Tiefen: {shadows:+d} | Weiß: {whites:+d} | Schwarz: {blacks:+d}""")
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
            st.slider("Helligkeit", -100, 100, 5, key="or_l")
    with tab3:
        st.markdown("#### Kreative Effekte")
        clarity  = st.slider("Klarheit",           -50, 100, 20)
        dehaze   = st.slider("Dunst entfernen",     -50, 100, 15)
        vignette = st.slider("Vignette",           -100, 100, -20)
        grain    = st.slider("Körnigkeit",            0, 100,  10)
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
        | Zweck       | Format | Qualität | Größe      | Farbraum  |
        |-------------|--------|----------|------------|-----------|
        | Web/Social  | JPEG   | 80–85%   | 2048px     | sRGB      |
        | Druck       | TIFF   | 100%     | 300 DPI    | AdobeRGB  |
        | Archiv      | DNG    | –        | Original   | –         |
        """)

# ════════════════════════════════════════════════════════════════
#  🌙 AKTUELLE MOND-DATEN (Live via astral)
# ════════════════════════════════════════════════════════════════

elif tool == "🌙 Aktuelle Mond-Daten":
    st.header("🌙 Live-Sonnen- & Mond-Daten")
    if not ASTRAL_OK:
        st.error(f"⚠️ astral/pytz nicht installiert: {_ASTRAL_ERR}")
        st.stop()

    city_sel = st.selectbox("📍 Standort", CITY_LIST)
    if st.button("🔄 Jetzt berechnen", type="primary"):
        try:
            lat, lon = CITY_COORDS[city_sel]
            tz = pytz.timezone("Europe/Berlin")
            city_info = LocationInfo(city_sel, "DE", "Europe/Berlin", lat, lon)
            now       = datetime.now(tz)
            s         = sun(city_info.observer, date=now.date(), tzinfo=tz)
            phase     = calculate_moon_phase(now.year, now.month, now.day)
            m_name, m_illum, m_tip = moon_phase_info(phase)
            st.success(f"""
            ### 📅 {now.strftime('%d.%m.%Y %H:%M')} | {city_sel}

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
#  ☁️ LIVE-WETTER
# ════════════════════════════════════════════════════════════════

elif tool == "☁️ Live-Wetter":
    st.header("☁️ Live-Wetter für Fotografen")
    city = st.text_input("📍 Stadt", value="Leipzig")
    if st.button("🌤️ Wetter laden", type="primary"):
        try:
            import requests
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]
            url  = (f"http://api.openweathermap.org/data/2.5/weather"
                    f"?q={city}&appid={API_KEY}&units=metric&lang=de")
            data = requests.get(url, timeout=8).json()
            if data.get("cod") != 200:
                st.error(f"❌ {data.get('message','Unbekannter Fehler')}")
            else:
                temp       = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                humidity   = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"] * 3.6
                clouds     = data["clouds"]["all"]
                desc       = data["weather"][0]["description"]
                icon       = data["weather"][0]["icon"]
                sunrise    = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
                sunset     = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
                foto_tip   = ("🌅 Klarer Himmel – Perfekt für Sunset & Astro!" if clouds < 20 else
                              "⛅ Teilweise bewölkt – Ideal für Landschaften"   if clouds < 50 else
                              "☁️ Stark bewölkt – Weiches Licht für Portrait")
                if wind_speed > 40:
                    foto_tip += "\n💨 Starker Wind! Stativ beschweren."
                col1, col2, col3 = st.columns(3)
                col1.metric("🌡️ Temperatur", f"{temp:.1f}°C", f"{feels_like:.1f}°C gefühlt")
                col2.metric("💨 Wind",       f"{wind_speed:.1f} km/h")
                col3.metric("💧 Luftfeucht.", f"{humidity}%")
                st.success(f"""
                ### 📸 {desc.capitalize()} | Bewölkung: {clouds}%
                - Sonnenaufgang: {sunrise} | Untergang: {sunset}
                
                💡 {foto_tip}
                """)
                st.image(f"http://openweathermap.org/img/wn/{icon}@2x.png", width=80)
        except Exception as e:
            st.error(f"❌ {e}")
            st.info("💡 Prüfe OPENWEATHER_API_KEY in .streamlit/secrets.toml")

# ════════════════════════════════════════════════════════════════
#  📅 5-TAGE PROGNOSE
# ════════════════════════════════════════════════════════════════

elif tool == "📅 5-Tage Prognose":
    st.header("📅 5-Tage-Wettervorhersage")
    city = st.text_input("📍 Stadt", value="Leipzig", key="forecast_city")
    if st.button("📊 Vorhersage laden", type="primary"):
        try:
            import requests
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]
            url  = (f"http://api.openweathermap.org/data/2.5/forecast"
                    f"?q={city}&appid={API_KEY}&units=metric&lang=de")
            data = requests.get(url, timeout=8).json()
            if data.get("cod") != "200":
                st.error(f"❌ {data.get('message')}")
            else:
                times, temps = [], []
                daily: dict[str, dict] = {}
                for item in data["list"]:
                    dt  = datetime.fromtimestamp(item["dt"])
                    times.append(dt.strftime("%d.%m. %H:%M"))
                    temps.append(item["main"]["temp"])
                    day = dt.strftime("%d.%m.")
                    if day not in daily:
                        daily[day] = {"min": item["main"]["temp_min"],
                                      "max": item["main"]["temp_max"],
                                      "desc": item["weather"][0]["description"]}
                    else:
                        daily[day]["min"] = min(daily[day]["min"], item["main"]["temp_min"])
                        daily[day]["max"] = max(daily[day]["max"], item["main"]["temp_max"])
                st.subheader("🌡️ Temperaturverlauf")
                df_t = pd.DataFrame({"Zeit": times[:40], "Temperatur (°C)": temps[:40]})
                st.line_chart(df_t.set_index("Zeit"), use_container_width=True)
                st.subheader("📆 Tagesübersicht")
                cols = st.columns(len(daily))
                for i, (day, v) in enumerate(daily.items()):
                    with cols[i]:
                        st.metric(day, f"{v['min']:.0f}° / {v['max']:.0f}°")
                        st.caption(v["desc"].capitalize())
        except Exception as e:
            st.error(f"Fehler: {e}")

# ════════════════════════════════════════════════════════════════
#  📍 GPS-STANDORT  (NEU: Query-Params-Methode)
# ════════════════════════════════════════════════════════════════

elif tool == "📍 GPS-Standort":
    st.header("📍 Automatische Standort-Erkennung")
    st.markdown("""
    Der Button ruft den GPS-Standort deines Geräts ab und überträgt ihn
    sicher per URL-Parameter an die App – **kein iframe-Trick, kein Reload-Loop**.
    """)

    lat_gps, lon_gps = gps_js_widget()

    if lat_gps and lon_gps:
        st.success(f"✅ Standort erkannt: **{lat_gps:.5f}°N, {lon_gps:.5f}°O**")
        st.session_state["gps_lat"] = lat_gps
        st.session_state["gps_lon"] = lon_gps

        col1, col2 = st.columns(2)
        if col1.button("🌍 → Astro & Wetter Dashboard", type="primary"):
            st.session_state["dash_city"] = f"{lat_gps},{lon_gps}"
            st.query_params.clear()
            st.rerun()
        if col2.button("🌙 → Mond-Daten für diesen Ort"):
            st.info("Wechsle zu '🌙 Aktuelle Mond-Daten' und wähle eine nahe Stadt.")
    else:
        st.info("""
        💡 **Hinweis:** Der Browser fragt nach der Erlaubnis für den Standortzugriff.
        Falls du die Anfrage ablehnst, kannst du im Dashboard den Ort manuell eingeben.
        """)
        st.markdown("**Oder wähle direkt eine Stadt:**")
        city_sel = st.selectbox("Stadt", CITY_LIST)
        if st.button("✅ Diese Stadt verwenden"):
            lat, lon = CITY_COORDS[city_sel]
            st.session_state["gps_lat"] = lat
            st.session_state["gps_lon"] = lon
            st.session_state["dash_city"] = city_sel
            st.success(f"✅ {city_sel} ausgewählt ({lat}°N, {lon}°O)")

# ════════════════════════════════════════════════════════════════
#  🌍 ASTRO & WETTER DASHBOARD
# ════════════════════════════════════════════════════════════════

elif tool == "🌍 Astro & Wetter Dashboard":
    st.header("🌍 Astro & Wetter Dashboard")
    st.markdown("Alles für die Shooting-Planung an einem Ort")

    # Vorausgefüllte Stadt aus GPS-Tool übernehmen
    default_city = st.session_state.get("dash_city", "Leipzig")
    city = st.text_input(
        "📍 Stadt oder Koordinaten (z.B. Berlin oder 52.52,13.40)",
        value=default_city,
        key="dash_input",
    )

    if st.button("🔄 Dashboard aktualisieren", type="primary"):
        try:
            import requests
            API_KEY = st.secrets["OPENWEATHER_API_KEY"]

            # Koordinaten oder Stadtname
            if "," in city:
                lat, lon = map(float, city.split(","))
                w_url = (f"http://api.openweathermap.org/data/2.5/weather"
                         f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de")
            else:
                w_url = (f"http://api.openweathermap.org/data/2.5/weather"
                         f"?q={city}&appid={API_KEY}&units=metric&lang=de")

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

                now     = datetime.now()
                phase   = calculate_moon_phase(now.year, now.month, now.day)
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

                # Tages-Übersicht
                with st.expander("📊 Stunden-Übersicht (heute)"):
                    f_url = (f"http://api.openweathermap.org/data/2.5/forecast"
                             f"?q={city}&appid={API_KEY}&units=metric&lang=de&cnt=8")
                    f_data = requests.get(f_url, timeout=8).json()
                    if f_data.get("cod") == "200":
                        items = f_data["list"]
                        df_h  = pd.DataFrame({
                            "Zeit":    [datetime.fromtimestamp(i["dt"]).strftime("%H:%M") for i in items],
                            "Temp °C": [i["main"]["temp"] for i in items],
                            "Wolken%": [i["clouds"]["all"] for i in items],
                        })
                        st.dataframe(df_h.set_index("Zeit"), use_container_width=True)
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.info("💡 Prüfe deinen API-Key in .streamlit/secrets.toml")

# ═══════════════════════════════════════════
# 📄 PDF-SHOOTING-PLAN
# ═══════════════════════════════════════════
elif tool == "📄 PDF-Planer":
    st.header("📄 PDF-Shooting-Plan Generator")
    st.markdown("Erstelle einen professionellen Plan für dein nächstes Shooting.")

    col1, col2 = st.columns(2)
    with col1:
        p_title = st.text_input("📸 Projektname", value="Canon EOS R Shooting")
        p_date = st.date_input("📅 Datum", datetime.now())
        p_loc = st.text_input("📍 Ort", value="Berlin")
    with col2:
        p_subj = st.text_input("🎯 Motiv", value="Landschaft / Portrait")
        p_client = st.text_input("👤 Kunde / Auftraggeber", value="Privat")
    
    # Ausrüstung & Settings
    equip = st.text_area("🎒 Equipment-Liste (je Zeile ein Item)", 
                         height=100,
                         value="Kamera: Canon EOS R\nObjektiv: RF 24-70mm f/2.8\nStativ: Manfrotto\nFilter: ND 1000, Polfilter\nAkkus: 3x LP-E6NH")
    
    notes = st.text_area("📝 Notizen & Ablauf", 
                         height=100,
                         value="08:00 Aufbau\n08:30 Golden Hour\n10:00 Backup\n")

    if st.button("📄 PDF Generieren & Herunterladen", type="primary"):
        try:
            from fpdf import FPDF
            import io
            
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(31, 111, 235) # Streamlit Blau
            pdf.cell(0, 20, "SHOOTING PLAN", ln=True, align="C")
            pdf.line(10, 30, 200, 30)
            
            # Meta Daten
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, f"Projekt: {p_title}", ln=True)
            pdf.cell(0, 8, f"Datum: {p_date.strftime('%d.%m.%Y')} | Ort: {p_loc}", ln=True)
            pdf.cell(0, 8, f"Motiv: {p_subj} | Kunde: {p_client}", ln=True)
            pdf.ln(5)
            
            # Equipment
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_fill_color(240, 246, 252)
            pdf.cell(0, 10, "  Ausruestung & Settings", ln=True, fill=True)
            pdf.set_font("Helvetica", size=11)
            for line in equip.split('\n'):
                if line.strip():
                    pdf.cell(0, 7, f"- {line}", ln=True)
            
            pdf.ln(5)
            
            # Ablauf
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "  Ablauf & Notizen", ln=True, fill=True)
            pdf.set_font("Helvetica", size=11)
            for line in notes.split('\n'):
                if line.strip():
                    pdf.multi_cell(0, 7, line)
            
            # Footer
            pdf.set_y(-20)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 10, "Erstellt mit Canon EOS R Pro Tool | Web Version", ln=True, align="C")
            
            # Speichern & Download
            pdf_output = pdf.output(dest="S").encode("latin-1", "replace")
            st.download_button(
                label="⬇️ PDF Speichern",
                data=pdf_output,
                file_name=f"Shooting_Plan_{p_date.strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"Fehler beim Erstellen: {e}")

# ════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════

st.divider()
st.markdown("""
<div style='text-align:center; color:#8B949E; font-size:0.85em;'>
    📷 Canon EOS R – Pro Tool v7.0 (Optimiert) | 28 Tools<br>
    Mondphase: Jean-Meeus-Algorithmus | GPS: Query-Params-Methode<br>
    Alle Berechnungen sind Richtwerte – Praxistests empfohlen.
</div>
""", unsafe_allow_html=True)

