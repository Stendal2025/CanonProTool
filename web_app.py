# web_app.py - Canon EOS R Pro Tool (Web Version) - VOLLSTÄNDIG
import streamlit as st
import math
import pandas as pd
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
#  IMPORTS FÜR LIVE-TOOL
# ═══════════════════════════════════════════
try:
    from astral import LocationInfo
    from astral.sun import sun
    import pytz
except Exception as e:
    st.error(f"⚠️ Import-Fehler: {type(e).__name__}: {e}")
    st.stop()
# ═══════════════════════════════════════════
# HILFSFUNKTIONEN FÜR MOND & MILCHSTRAßE
# ═══════════════════════════════════════════
def calculate_moon_phase(year, month, day):
    """Berechnet die Mondphase (0-1) für ein gegebenes Datum"""
    import math
    diff = year - 1900
    ref = diff % 19
    ref = ref if ref <= 9 else ref - 19
    days = (ref * 11) % 30
    days += month - 1
    days += day
    if month < 3:
        days += 1
    days = days % 30
    return days / 29.53

def get_moon_phase_info(phase):
    """Gibt Informationen zur Mondphase zurück"""
    if phase < 0.03 or phase > 0.97:
        return "🌑 Neumond", 0, "Perfekt für Milchstraße & Deep Sky!"
    elif phase < 0.22:
        return "🌒 Zunehmende Sichel", phase * 100, "Gut für frühe Abendfotos"
    elif phase < 0.28:
        return "🌓 Erstes Viertel", 50, "Interessante Schatten am Mond"
    elif phase < 0.47:
        return "🌔 Zunehmender Mond", phase * 100, "Zu hell für Milchstraße"
    elif phase < 0.53:
        return "🌕 Vollmond", 100, "Perfekt für Mondlandschaften"
    elif phase < 0.72:
        return "🌖 Abnehmender Mond", (1-phase) * 100, "Gut für späte Nacht"
    elif phase < 0.78:
        return "🌗 Letztes Viertel", 50, "Mond geht spät auf"
    else:
        return "🌘 Abnehmende Sichel", (1-phase) * 100, "Gut für Morgenaufnahmen"

def get_milky_way_recommendation(score, moon_phase):
    """Gibt Empfehlungen für Milchstraßen-Fotografie"""
    if score >= 85:
        return "🟢 Hervorragend! Perfekte Bedingungen für Milchstraße."
    elif score >= 65:
        return "🟡 Gut! Milchstraße sichtbar, leichte Einschränkungen."
    elif score >= 40:
        return "🟠 Mäßig. Warte auf dunklere Mondphase oder bessere Saison."
    else:
        return "🔴 Schlecht. Zu hell oder falsche Jahreszeit."

def get_moon_recommendation(phase):
    """Gibt Empfehlungen für Mondfotografie"""
    if 0.45 <= phase <= 0.55:
        return "🌕 Perfekt für Vollmond-Aufnahmen!"
    elif 0.20 <= phase <= 0.30 or 0.70 <= phase <= 0.80:
        return "🌓 Ideal für Halbmond mit schönen Schatten."
    else:
        return "🌙 Interessante Sichel-Phase für kreative Aufnahmen."
def get_astro_recommendation(score, moon_illum):
    if score >= 80:
        return "🟢 **Perfekt!** Ideales Datum für Astrofotografie. Pack die Kamera ein!"
    elif score >= 60:
        return "🟡 **Gut!** Gute Bedingungen. Milchstraße sichtbar."
    elif score >= 40:
        return "🟠 **Mäßig.** Geht, aber warte auf dunklere Mondphase für bessere Ergebnisse."
    else:
        return "🔴 **Schlecht.** Zu hell oder falsche Jahreszeit. Besseres Datum suchen."
def get_moon_phase_name(phase):
    """Wandelt Mondphase in Text um (astral-kompatibel)"""
    if phase < 1 or phase > 28:
        return "🌑 Neumond"
    elif phase < 6:
        return "🌒 Zunehmende Sichel"
    elif phase < 8:
        return "🌓 Erstes Viertel"
    elif phase < 13:
        return "🌔 Zunehmender Mond"
    elif phase < 15:
        return "🌕 Vollmond"
    elif phase < 20:
        return "🌖 Abnehmender Mond"
    elif phase < 22:
        return "🌗 Letztes Viertel"
    else:
        return "🌘 Abnehmende Sichel"

def get_best_photo_times(now, sun_data, moon_phase):
    """Empfiehlt beste Foto-Zeiten basierend auf Sonne & Mond"""
    times = []
    
    # Goldene Stunde
    sunrise = sun_data['sunrise']
    sunset = sun_data['sunset']
    times.append(f"🌅 Morgen: {(sunrise - timedelta(minutes=30)).strftime('%H:%M')} - {(sunrise + timedelta(minutes=30)).strftime('%H:%M')}")
    times.append(f"🌆 Abend: {(sunset - timedelta(minutes=30)).strftime('%H:%M')} - {(sunset + timedelta(minutes=30)).strftime('%H:%M')}")
    
    # Blaue Stunde
    times.append(f"🌄 Blaue Stunde: {(sunrise - timedelta(minutes=45)).strftime('%H:%M')} - {sunrise.strftime('%H:%M')}")
    
    # Astro (wenn Mond dunkel = Phase < 4 oder > 24)
    if moon_phase < 4 or moon_phase > 24:
        times.append("🌌 Milchstraße: 23:00 - 04:00 (dunkle Nacht)")
    
    return "\n".join(times)   

# ═══════════════════════════════════════════
#  MOBILE OPTIMIZATION
# ═══════════════════════════════════════════
MOBILE_CSS = """
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .stApp { max-width: 100% !important; }
        section[data-testid="stSidebar"] {
            min-width: 280px !important;
            max-width: 280px !important;
        }
        .stTextInput > div > div > input,
        .stSelectbox > div > div {
            font-size: 16px !important;
            min-height: 44px !important;
        }
        .stButton > button {
            min-height: 44px !important;
            min-width: 100px !important;
        }
        body, .stMarkdown, .stText {
            font-size: 16px !important;
            -webkit-text-size-adjust: 100% !important;
        }
    }
    input, select, textarea { font-size: 16px !important; }
</style>
"""

# ═══════════════════════════════════════════
#  KONFIGURATION
# ═══════════════════════════════════════════
st.set_page_config(
    page_title="Canon EOS R – Pro Tool",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(MOBILE_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
    .main {background-color: #0A0E14; color: #F0F6FC;}
    h1, h2, h3 {color: #58A6FF;}
    .stButton>button {
        background-color: #1F6FEB;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton>button:hover {background-color: #58A6FF;}
    .metric-card {
        background-color: #161B22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363D;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
#  BERECHNUNGSFUNKTIONEN
# ═══════════════════════════════════════════
def calculate_nd(base, stops):
    return base * (2 ** stops)

def evaluate_exposure(iso, aperture, shutter):
    ev = math.log2((aperture ** 2) / shutter)
    ev_c = ev - math.log2(iso / 100)
    if ev_c < 6:    return ev_c, "⚫ Sehr dunkel"
    elif ev_c < 10: return ev_c, "🔵 Dunkel"
    elif ev_c < 13: return ev_c, "🟢 Optimal"
    elif ev_c < 15: return ev_c, "🟡 Hell"
    else:           return ev_c, "🔴 Überbelichtet"

def calculate_dof(focal_mm, aperture, distance_m, coc=0.030):
    fm = focal_mm / 1000
    h = (focal_mm ** 2) / (aperture * coc * 1000)
    dn = (h * distance_m) / (h + (distance_m - fm))
    df = (h * distance_m) / (h - (distance_m - fm)) if distance_m < h else float('inf')
    return dn, df, (df - dn if df != float('inf') else float('inf')), h

def calculate_golden_hour(sr, ss):
    fmt = "%H:%M"
    sunrise = datetime.strptime(sr, fmt)
    sunset  = datetime.strptime(ss, fmt)
    return {
        "golden_morning": (sunrise.strftime(fmt), (sunrise + timedelta(minutes=60)).strftime(fmt)),
        "golden_evening": ((sunset - timedelta(minutes=60)).strftime(fmt), sunset.strftime(fmt)),
        "blue_morning":   ((sunrise - timedelta(minutes=30)).strftime(fmt), sunrise.strftime(fmt)),
        "blue_evening":   (sunset.strftime(fmt), (sunset + timedelta(minutes=30)).strftime(fmt)),
    }

def calculate_flash(gn, distance, iso=100):
    f = math.sqrt(iso / 100)
    return round((gn * f) / distance, 1)

def calculate_star(focal):
    return round(500 / focal, 1)

# ═══════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════
st.title("📷 CANON EOS R – PRO TOOL")
st.markdown("**Web Version** | 23 Photography Tools")
st.divider()

# ═══════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ═══════════════════════════════════════════
st.sidebar.title("🔧 Tools")
tool = st.sidebar.radio(
    "Wähle ein Werkzeug:",
    [
        "🏠 Home",
        "🕶️ ND Rechner",
        "📐 Schärfentiefe",
        "📊 Belichtung",
        "🌅 Golden Hour",
        "🔦 Blitz",
        "🌙 Sternspuren",
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
        "🎨 Filter-Sim"
        "🌙 Mond & Milchstraße"
        "🌠 Sternspuren",
        "🎨 Bearbeitung",
        "🌙 Aktuelle Mond-Daten"
    ],
    index=0
)

# ═══════════════════════════════════════════
#  HOME
# ═══════════════════════════════════════════
if tool == "🏠 Home":
    st.header("Willkommen beim Canon EOS R Pro Tool!")
    st.markdown("""
    ### 📸 Was kann diese App?
    - **26 professionelle Rechner** für Fotografie
    - **Belichtungsdreieck** optimieren
    - **Schärfentiefe** berechnen
    - **Goldene Stunde** planen
    - **ND Filter** kalkulieren
    ### 🚀 Schnellstart
    Wähle links ein Tool aus der Sidebar!
    """)
    col1, col2, col3 = st.columns(3)
    with col1: st.info("📊 **Belichtung**\n\nEV-Werte berechnen")
    with col2: st.success("📐 **Schärfentiefe**\n\nDoF kalkulieren")
    with col3: st.warning("🌅 **Planung**\n\nGolden Hour Times")

# ═══════════════════════════════════════════
#  ND RECHNER
# ═══════════════════════════════════════════
elif tool == "🕶️ ND Rechner":
    st.header("🕶️ ND Filter Rechner")
    col1, col2 = st.columns(2)
    with col1:
        base_time = st.selectbox(
            "Basiszeit (ohne ND)",
            [
                "1/8000", "1/4000", "1/2000", "1/1000", "1/500", "1/250", 
                "1/125", "1/60", "1/30", "1/15", "1/8", "1/4", "1/2", 
                "1", "2", "4", "8", "15", "30", "60"
            ],
            index=6
        )
        # Berechnung: Wandelt "1/125" → 0.008, "30" → 30.0
        if "/" in base_time:
            base_sec = 1 / float(base_time.split("/")[1])
        else:
            base_sec = float(base_time)
    with col2:
        nd_stops = st.slider("ND Stops", 1, 10, 3,
                             help="ND8=3 Stops | ND64=6 Stops | ND1000=10 Stops")

    if st.button("✅ Berechnen", type="primary"):
        result_sec = calculate_nd(base_sec, nd_stops)
        if result_sec >= 3600:
            result_str = f"{result_sec/3600:.1f} Stunden"
        elif result_sec >= 60:
            result_str = f"{result_sec/60:.1f} Minuten"
        elif result_sec >= 1:
            result_str = f"{result_sec:.1f} Sekunden"
        else:
            result_str = f"1/{int(1/result_sec)}s"
        st.success(f"""
        ### Ergebnis:
        - **ND Filter:** ND{2**nd_stops} ({nd_stops} Stops)
        - **Neue Belichtungszeit:** {result_str}
        - **Von:** {base_time} → **Zu:** {result_str}
        """)
        if result_sec > 300:
            st.warning("⚠️ Sehr lange Belichtung! Stativ + Fernauslöser empfohlen.")

# ═══════════════════════════════════════════
#  SCHÄRFENTIEFE
# ═══════════════════════════════════════════
elif tool == "📐 Schärfentiefe":
    st.header("📐 Schärfentiefe-Rechner")
    col1, col2, col3 = st.columns(3)
    with col1: focal = st.number_input("Brennweite (mm)", 14, 400, 50)
    with col2: aperture = st.selectbox("Blende (f/)",
                   [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16,22], index=4)
    with col3: distance = st.number_input("Entfernung (m)", 0.5, 100.0, 3.0, 0.1)

    sensor = st.selectbox("Sensor", ["Vollformat (36x24mm)","APS-C Canon (1.6x)","Micro 4/3"])
    coc_map = {"Vollformat (36x24mm)": 0.030, "APS-C Canon (1.6x)": 0.019, "Micro 4/3": 0.015}
    coc = coc_map[sensor]

    if st.button("✅ Berechnen", type="primary"):
        near, far, total, hyper = calculate_dof(focal, aperture, distance, coc)
        far_str   = "∞" if far   == float('inf') else f"{far:.2f}m"
        total_str = "∞" if total == float('inf') else f"{total:.2f}m"
        st.success(f"""
        ### 📊 Ergebnisse:
        - **Nahpunkt:** {near:.2f}m
        - **Fernpunkt:** {far_str}
        - **Schärfentiefe:** {total_str}
        - **Hyperfokale Distanz:** {hyper:.2f}m
        """)
        if distance >= hyper:
            st.info("💡 Du fokussierst jenseits der hyperfokalen Distanz – alles bis ∞ ist scharf!")

# ═══════════════════════════════════════════
#  BELICHTUNG
# ═══════════════════════════════════════════
elif tool == "📊 Belichtung":
    st.header("📊 Belichtungs-Bewerter")
    col1, col2, col3 = st.columns(3)
    with col1: iso = st.selectbox("ISO", [100,200,400,800,1600,3200,6400,12800], index=0)
    with col2: aperture = st.selectbox("Blende", [1.4,1.8,2.8,4.0,5.6,8.0,11,16,22], index=3)
    with col3:
        shutter_str = st.selectbox("Verschlusszeit",
            ["1/8000","1/4000","1/2000","1/1000","1/500",
             "1/250","1/125","1/60","1/30","1/15","1/8","1/4","1/2","1","2","4","8","15","30"])
        shutter = eval(shutter_str) if "/" in shutter_str else float(shutter_str)

    if st.button("📊 Bewerten", type="primary"):
        ev, rating = evaluate_exposure(iso, aperture, shutter)
        st.success(f"""
        ### Ergebnis:
        - **EV-Wert:** {ev:.2f}
        - **Bewertung:** {rating}
        - **ISO {iso} | f/{aperture} | {shutter_str}**
        """)

# ═══════════════════════════════════════════
#  GOLDEN HOUR
# ═══════════════════════════════════════════
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
        except:
            st.error("⚠️ Bitte gültiges Format HH:MM eingeben (z.B. 06:30)")

# ═══════════════════════════════════════════
#  BLITZ
# ═══════════════════════════════════════════
elif tool == "🔦 Blitz":
    st.header("🔦 Blitz-Rechner (Leitzahl)")
    col1, col2, col3 = st.columns(3)
    with col1: gn       = st.number_input("Leitzahl (GN)", 10, 100, 58)
    with col2: distance = st.number_input("Entfernung (m)", 1.0, 50.0, 5.0)
    with col3: iso      = st.selectbox("ISO", [100,200,400,800,1600], index=0)

    if st.button("✅ Berechnen", type="primary"):
        ap = calculate_flash(gn, distance, iso)
        st.success(f"""
        ### Ergebnis:
        - **Empfohlene Blende:** f/{ap}
        - **GN {gn} | {distance}m | ISO {iso}**
        """)
        with st.expander("📋 Reichweiten-Tabelle"):
            rows = [{"Blende": f"f/{f}", "Max. Reichweite": f"{gn * math.sqrt(iso/100) / f:.1f}m"}
                    for f in [2.8, 4.0, 5.6, 8.0, 11, 16]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ═══════════════════════════════════════════
#  STERNSPUREN
# ═══════════════════════════════════════════
elif tool == "🌙 Sternspuren":
    st.header("🌙 Sternspuren & Astro")
    col1, col2 = st.columns(2)
    with col1: focal = st.number_input("Brennweite (mm)", 14, 400, 24)
    with col2: rule  = st.selectbox("Regel", ["500er Regel (Vollformat)", "300er Regel (APS-C)"])

    if st.button("✅ Berechnen", type="primary"):
        divisor = 500 if "500" in rule else 300
        max_exp = round(divisor / focal, 1)
        frames  = int(1800 / max_exp)
        st.success(f"""
        ### Ergebnis:
        - **Max. Belichtungszeit:** {max_exp}s
        - **Bilder pro 30 Min:** ~{frames}
        - **Brennweite:** {focal}mm
        """)
        st.info("💡 Neumond | ISO 3200-6400 | f/1.4-2.8 | MF auf ∞")

# ═══════════════════════════════════════════
#  KI-ASSISTENT
# ═══════════════════════════════════════════
elif tool == "🤖 KI":
    st.header("🤖 KI Fotografie-Assistent")
    scene = st.text_area("📝 Szene beschreiben", placeholder="z.B. 'sonnenuntergang am see'", height=80)

    st.markdown("**Quick-Presets:**")
    cols = st.columns(4)
    presets = ["sunset","portrait","night","landscape","street","macro","sport","astro"]
    for i, p in enumerate(presets):
        if cols[i % 4].button(f"📸 {p.capitalize()}", use_container_width=True, key=f"ki_{p}"):
            scene = p

    if st.button("🤖 KI Vorschlag", type="primary"):
        if not scene.strip():
            st.warning("Bitte Szene beschreiben oder Preset wählen.")
        else:
            db = {
                "sunset":    ("🌅 SUNSET",    "ISO 100 | f/8 | 1/125s",   "GND-Filter | Stativ | Bracketing"),
                "portrait":  ("👤 PORTRAIT",  "ISO 100 | f/1.8 | 1/200s", "Eye-AF | 85mm | Offener Schatten"),
                "night":     ("🌙 NACHT",     "ISO 1600 | f/2.8 | 10s",   "Stativ | Fernauslöser | RAW"),
                "landscape": ("🏔️ LANDSCHAFT","ISO 100 | f/11 | 1/60s",   "Stativ | Polfilter | Golden Hour"),
                "street":    ("🏙️ STREET",    "ISO 400 | f/5.6 | 1/250s", "35mm | Zone Focus | Burst"),
                "macro":     ("🔬 MAKRO",     "ISO 200 | f/8 | 1/160s",   "Focus Stack | Stativ | Diffusor"),
                "sport":     ("⚡ SPORT",     "ISO 800 | f/4 | 1/1000s",  "AI Servo | Burst | 70-200mm"),
                "astro":     ("🌌 ASTRO",     "ISO 3200 | f/1.8 | 20s",   "500er Regel | Neumond | MF ∞"),
            }
            found = False
            for key, (title, settings, tips) in db.items():
                if key in scene.lower():
                    st.success(f"### {title}\n**Settings:** `{settings}`\n**Tipps:** {tips}")
                    found = True
                    break
            if not found:
                st.info("### 📸 Allgemein\n**Settings:** `ISO 200 | f/5.6 | 1/125s`\nBeschreibe deine Szene genauer für spezifischere Empfehlungen.")

# ═══════════════════════════════════════════
#  WEISSABGLEICH
# ═══════════════════════════════════════════
elif tool == "🌡️ Weißabgleich":
    st.header("🌡️ Weißabgleich & Farbtemperatur")
    data = [
        ("🕯️ Kerzenlicht",   "1800–2000 K", "#FF6B35"),
        ("💡 Glühlampe",     "2700–3200 K", "#FFA500"),
        ("🌅 Sonnenaufgang", "3000–3500 K", "#FF8C42"),
        ("📸 Blitz",         "5000–5500 K", "#FFFEF0"),
        ("☀️ Tageslicht",    "5200–5800 K", "#FFFFF0"),
        ("⛅ Bewölkt",       "6000–6500 K", "#E8F0FF"),
        ("🏔️ Schatten",      "7000–8000 K", "#D0E0FF"),
        ("🌌 Blaue Stunde",  "9000–12000 K","#9090FF"),
    ]
    for name, kelvin, color in data:
        c1, c2 = st.columns([2, 3])
        c1.markdown(f"<span style='color:{color};font-weight:bold'>{name}</span>", unsafe_allow_html=True)
        c2.code(kelvin)

# ═══════════════════════════════════════════
#  CHEAT SHEETS
# ═══════════════════════════════════════════
elif tool == "📋 Cheat Sheets":
    st.header("📋 Schnellreferenz-Karten")
    sheet = st.selectbox("📑 Kategorie:",
        ["Portrait","Landschaft","Nacht/Astro","Street","Makro","Sport","Hochzeit"])
    guides = {
        "Portrait": """
👤 PORTRAIT
══════════════════════════════
Brennweite:  85-135mm
Blende:      f/1.4 - f/2.8
ISO:         100-400
Verschluss:  1/200s+

FOKUS:   Eye-AF | Single Point
LICHT:   Offener Schatten | Golden Hour
TIPPS:   Augen im oberen Drittel
""",
        "Landschaft": """
🏔️ LANDSCHAFT
══════════════════════════════
Brennweite:  16-35mm
Blende:      f/8 - f/16
ISO:         100
Verschluss:  Stativ!

FOKUS:   1/3 der Szene | Hyperfokus
FILTER:  Polfilter + GND
ZEIT:    Golden Hour | Blaue Stunde
""",
        "Nacht/Astro": """
🌙 NACHT & ASTRO
══════════════════════════════
Brennweite:  14-24mm
Blende:      f/1.4 - f/2.8
ISO:         1600-6400
Verschluss:  500 / Brennweite

FOKUS:   MF auf hellen Stern
SETUP:   Neumond | Stativ | RAW
STACKEN: Sequator / Starry Landscape
""",
        "Street": """
🏙️ STREET
══════════════════════════════
Brennweite:  28-50mm (35mm klassisch)
Blende:      f/5.6 - f/8
ISO:         Auto (max 3200)
Verschluss:  1/250s+

TECHNIK:  Zone Focus @ 3m
TIPPS:    Unauffällig | Burst | Hüfte
""",
        "Makro": """
🔬 MAKRO
══════════════════════════════
Brennweite:  90-105mm Makro
Blende:      f/5.6 - f/11
ISO:         200-800
Verschluss:  1/160s+

FOKUS:   MF | Focus Stacking
LICHT:   Diffuses Licht | Ringblitz
STATIV:  Makroschlitten empfohlen
""",
        "Sport": """
⚡ SPORT
══════════════════════════════
Brennweite:  70-400mm
Blende:      f/2.8 - f/4
ISO:         800-3200
Verschluss:  1/1000s minimum!

AF:      AI Servo | Zone AF
BURST:   High-Speed Continuous
TIPP:    Action voraussehen
""",
        "Hochzeit": """
💍 HOCHZEIT
══════════════════════════════
ISO:         400-1600 (Kirche: 3200)
Blende:      f/2.8 - f/4
Verschluss:  1/250s+

EQUIPMENT: 2 Bodies! | 24-70 + 70-200
BACKUP:    Dual Card | 4+ Akkus
SHOT LIST: Getting Ready → Tanz
"""
    }
    st.code(guides[sheet], language="text")

# ═══════════════════════════════════════════
#  CROP-FAKTOR
# ═══════════════════════════════════════════
elif tool == "🔄 Crop-Faktor":
    st.header("🔄 Crop-Faktor Rechner")
    st.markdown("Äquivalente Brennweite & Blende zwischen Sensorgrößen berechnen")

    col1, col2 = st.columns(2)
    with col1:
        focal    = st.number_input("Brennweite (mm)", 10, 800, 50)
        aperture = st.selectbox("Blende (f/)", [1.2,1.4,1.8,2.0,2.8,4.0,5.6,8.0,11,16], index=4)
    with col2:
        crop_factors = {
            "Vollformat (1.0x)":          1.0,
            "APS-C Canon (1.6x)":         1.6,
            "APS-C Nikon/Sony (1.5x)":    1.5,
            "Micro 4/3 (2.0x)":           2.0,
            "1 Zoll (2.7x)":              2.7,
            "Smartphone (~6x)":           6.0,
        }
        sensor_from = st.selectbox("Von Sensor:", list(crop_factors.keys()), index=0)
        sensor_to   = st.selectbox("Nach Sensor:", list(crop_factors.keys()), index=1)

    if st.button("✅ Berechnen", type="primary"):
        cf_from = crop_factors[sensor_from]
        cf_to   = crop_factors[sensor_to]
        # Umrechnung über Vollformat-Äquivalent
        focal_ff    = focal * cf_from
        aperture_ff = aperture * cf_from
        equiv_focal    = focal_ff / cf_to
        equiv_aperture = aperture_ff / cf_to

        st.success(f"""
        ### 📊 Ergebnis:
        
        **Original ({sensor_from}):**
        - Brennweite: `{focal}mm` | Blende: `f/{aperture}`
        
        **Vollformat-Äquivalent:**
        - Brennweite: `{focal_ff:.0f}mm` | Blende: `f/{aperture_ff:.1f}`
        
        **Äquivalent auf {sensor_to}:**
        - Brennweite: `{equiv_focal:.0f}mm` | Blende: `f/{equiv_aperture:.1f}`
        """)

    with st.expander("📋 Crop-Faktor Referenz"):
        ref = [{"Sensor": k, "Crop-Faktor": v, "50mm entspricht": f"{50*v:.0f}mm FF-Äquivalent"}
               for k, v in crop_factors.items()]
        st.dataframe(pd.DataFrame(ref), use_container_width=True)

# ═══════════════════════════════════════════
#  EXIF
# ═══════════════════════════════════════════
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
                    tags = {}
                    for k, v in exif_data.items():
                        if k in ExifTags.TAGS and not isinstance(v, bytes):
                            tags[ExifTags.TAGS[k]] = str(v)
                    important = ["Make","Model","ExposureTime","FNumber",
                                 "ISOSpeedRatings","FocalLength","DateTimeOriginal","LensModel"]
                    st.subheader("📸 Kamera-Einstellungen")
                    for key in important:
                        if key in tags:
                            st.markdown(f"**{key}:** `{tags[key]}`")
                    with st.expander("📋 Alle EXIF-Daten"):
                        st.dataframe(pd.DataFrame(list(tags.items()), columns=["Tag","Wert"]),
                                     use_container_width=True, height=400)
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Foto hoch, um EXIF-Daten anzuzeigen.")

# ═══════════════════════════════════════════
#  TIMELAPSE
# ═══════════════════════════════════════════
elif tool == "⏱️ Timelapse":
    st.header("⏱️ Timelapse-Rechner")
    tab1, tab2 = st.tabs(["📊 Berechnung","💡 Tipps"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1: duration = st.number_input("🎬 Video-Länge (Sek)", min_value=1, value=30)
        with col2: fps      = st.selectbox("📊 FPS", [24,25,30,60], index=0)
        with col3: interval = st.number_input("⏱️ Intervall (Sek)", min_value=1, value=5)

        file_format = st.selectbox("💾 Format", ["RAW (~30MB)","JPEG Fine (~10MB)","JPEG Normal (~5MB)"])

        if st.button("✅ Berechnen", type="primary"):
            frames    = duration * fps
            total_sec = frames * interval
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            s = int(total_sec % 60)
            size_map  = {"RAW (~30MB)": 30, "JPEG Fine (~10MB)": 10, "JPEG Normal (~5MB)": 5}
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
                st.warning("⚠️ Mehr als 64 GB Speicher nötig!")
            if total_sec > 14400:
                st.warning("⚠️ Aufnahmedauer über 4 Stunden – mehrere Akkus einplanen!")

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

        **⚙️ Settings:**
        - ✓ Manueller Modus (M)
        - ✓ Fester Weißabgleich (Kelvin)
        - ✓ Manueller Fokus
        - ✓ Stativ + Fernauslöser
        """)

# ═══════════════════════════════════════════
#  PLANER
# ═══════════════════════════════════════════
elif tool == "📝 Planer":
    st.header("📝 Aufnahme-Planer & Logbuch")
    if "logbook" not in st.session_state:
        st.session_state.logbook = []

    tab1, tab2 = st.tabs(["➕ Neuer Eintrag","📖 Logbuch"])

    with tab1:
        c1, c2 = st.columns(2)
        loc = c1.text_input("📍 Ort")
        sub = c2.text_input("📸 Motiv")
        c3, c4 = st.columns(2)
        iso_log = c3.selectbox("ISO", [100,200,400,800,1600,3200], key="log_iso")
        ap_log  = c4.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], key="log_ap")
        sh_log  = st.selectbox("Verschluss",
            ["1/1000","1/500","1/250","1/125","1/60","1/30","1/15","1s","2s","4s"], key="log_sh")
        notes   = st.text_area("📝 Notizen")
        rating  = st.slider("⭐ Bewertung", 1, 5, 3)

        if st.button("➕ Speichern", type="primary"):
            if loc or sub:
                st.session_state.logbook.append({
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "loc":      loc,
                    "sub":      sub,
                    "settings": f"ISO {iso_log} | f/{ap_log} | {sh_log}",
                    "notes":    notes,
                    "rating":   "⭐" * rating
                })
                st.success("✅ Gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte Ort oder Motiv eingeben.")

    with tab2:
        if st.session_state.logbook:
            search = st.text_input("🔍 Suchen...")
            entries = st.session_state.logbook
            if search:
                entries = [e for e in entries if search.lower() in str(e).lower()]
            for entry in reversed(entries):
                with st.expander(f"📸 {entry['date']} | {entry['loc']} – {entry['sub']} {entry['rating']}"):
                    st.markdown(f"""
                    - **📍 Ort:** {entry['loc']}
                    - **📸 Motiv:** {entry['sub']}
                    - **⚙️ Settings:** `{entry['settings']}`
                    - **📝 Notizen:** {entry['notes']}
                    """)
            if st.button("🗑️ Alle löschen"):
                st.session_state.logbook = []
                st.rerun()
        else:
            st.info("📭 Noch keine Einträge.")

# ═══════════════════════════════════════════
#  VERGLEICH
# ═══════════════════════════════════════════
elif tool == "⚖️ Vergleich":
    st.header("⚖️ Einstellungs-Vergleich")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🅰️ Setup A")
        a_iso    = st.selectbox("ISO", [100,200,400,800,1600,3200,6400], index=0, key="a_iso")
        a_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], index=3, key="a_ap")
        a_sh_str = st.selectbox("Verschluss",
            ["1/8000","1/4000","1/2000","1/1000","1/500","1/250",
             "1/125","1/60","1/30","1/15","1/8","1/4","1/2","1","2","4"], index=6, key="a_sh")
        a_sh = eval(a_sh_str) if "/" in a_sh_str else float(a_sh_str)

    with col2:
        st.subheader("🅱️ Setup B")
        b_iso    = st.selectbox("ISO", [100,200,400,800,1600,3200,6400], index=0, key="b_iso")
        b_ap     = st.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], index=3, key="b_ap")
        b_sh_str = st.selectbox("Verschluss",
            ["1/8000","1/4000","1/2000","1/1000","1/500","1/250",
             "1/125","1/60","1/30","1/15","1/8","1/4","1/2","1","2","4"], index=6, key="b_sh")
        b_sh = eval(b_sh_str) if "/" in b_sh_str else float(b_sh_str)

    if st.button("⚖️ Vergleichen", type="primary"):
        ev_a = math.log2((a_ap**2) / a_sh) - math.log2(a_iso / 100)
        ev_b = math.log2((b_ap**2) / b_sh) - math.log2(b_iso / 100)
        diff = ev_a - ev_b
        c1, c2, c3 = st.columns(3)
        c1.metric("🅰️ Setup A", f"EV {ev_a:.2f}")
        c2.metric("🅱️ Setup B", f"EV {ev_b:.2f}")
        c3.metric("Δ Differenz", f"{abs(diff):.1f} Stops")
        if abs(diff) < 0.1:
            st.success("✅ Gleiche Belichtung!")
        elif diff > 0:
            st.info(f"☀️ Setup A ist {abs(diff):.1f} Stops heller")
        else:
            st.info(f"🌙 Setup B ist {abs(diff):.1f} Stops heller")

# ═══════════════════════════════════════════
#  OBJEKTIVE
# ═══════════════════════════════════════════
elif tool == "🔭 Objektive":
    st.header("🔭 RF Objektiv-Datenbank")
    lenses = [
        {"Name":"RF 14-35mm f/4L IS",       "Typ":"Weitwinkel Zoom", "f/":4.0,    "Gewicht":"540g",  "IS":"✅","Preis":"~1.600€"},
        {"Name":"RF 15-35mm f/2.8L IS",     "Typ":"Weitwinkel Zoom", "f/":2.8,    "Gewicht":"840g",  "IS":"✅","Preis":"~2.500€"},
        {"Name":"RF 24-70mm f/2.8L IS",     "Typ":"Standard Zoom",   "f/":2.8,    "Gewicht":"900g",  "IS":"✅","Preis":"~2.700€"},
        {"Name":"RF 24-105mm f/4L IS",      "Typ":"Standard Zoom",   "f/":4.0,    "Gewicht":"700g",  "IS":"✅","Preis":"~1.200€"},
        {"Name":"RF 50mm f/1.2L USM",       "Typ":"Standard Prime",  "f/":1.2,    "Gewicht":"950g",  "IS":"❌","Preis":"~2.400€"},
        {"Name":"RF 50mm f/1.8 STM",        "Typ":"Standard Prime",  "f/":1.8,    "Gewicht":"160g",  "IS":"❌","Preis":"~230€"},
        {"Name":"RF 85mm f/1.2L USM",       "Typ":"Portrait Prime",  "f/":1.2,    "Gewicht":"1195g", "IS":"❌","Preis":"~3.000€"},
        {"Name":"RF 85mm f/2 Macro IS",     "Typ":"Portrait Prime",  "f/":2.0,    "Gewicht":"500g",  "IS":"✅","Preis":"~700€"},
        {"Name":"RF 70-200mm f/2.8L IS",    "Typ":"Tele Zoom",       "f/":2.8,    "Gewicht":"1070g", "IS":"✅","Preis":"~2.900€"},
        {"Name":"RF 100-500mm f/4.5-7.1L",  "Typ":"Supertele Zoom",  "f/":"4.5-7","Gewicht":"1370g", "IS":"✅","Preis":"~3.000€"},
        {"Name":"RF 100mm f/2.8L Macro IS", "Typ":"Makro Prime",     "f/":2.8,    "Gewicht":"730g",  "IS":"✅","Preis":"~1.500€"},
    ]
    typ_filter = st.multiselect("🏷️ Typ filtern:", list(set(l["Typ"] for l in lenses)))
    filtered = [l for l in lenses if not typ_filter or l["Typ"] in typ_filter]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=450)
    st.info(f"📊 {len(filtered)} von {len(lenses)} Objektiven")

# ═══════════════════════════════════════════
#  VIDEO
# ═══════════════════════════════════════════
elif tool == "🎬 Video":
    st.header("🎬 Video-Modus Guide")
    tab1, tab2, tab3 = st.tabs(["📊 Specs","⚙️ Settings","🎞️ 180° Regel"])

    with tab1:
        st.markdown("""
        ### 📹 Canon EOS R Video-Spezifikationen
        | Modus   | Auflösung   | FPS  | Crop   |
        |---------|-------------|------|--------|
        | 4K UHD  | 3840×2160   | 24p  | 1.74x  |
        | 4K UHD  | 3840×2160   | 30p  | 1.74x  |
        | Full HD | 1920×1080   | 60p  | 1.0x   |
        | Full HD | 1920×1080   | 120p | 1.0x   |
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
        st.success(f"**{fps_v} fps → 1/{shutter_180}s Verschlusszeit** (180° Regel)")
        st.markdown("""
        | FPS | 180° Shutter |
        |-----|-------------|
        | 24  | 1/50s       |
        | 30  | 1/60s       |
        | 60  | 1/120s      |
        | 120 | 1/250s      |
        """)

# ═══════════════════════════════════════════
#  AKKU
# ═══════════════════════════════════════════
elif tool == "🔋 Akku":
    st.header("🔋 Akku-Kalkulator")
    battery = st.selectbox("🔋 Akku-Typ",
        ["LP-E6NH (2130mAh) – ~370 Shots",
         "LP-E6N  (1865mAh) – ~350 Shots",
         "LP-E6   (1800mAh) – ~300 Shots"])
    base_map = {
        "LP-E6NH (2130mAh) – ~370 Shots": 370,
        "LP-E6N  (1865mAh) – ~350 Shots": 350,
        "LP-E6   (1800mAh) – ~300 Shots": 300,
    }
    cap = base_map[battery]
    spm = st.number_input("⏱️ Shots/Minute", 0.5, 10.0, 2.0, 0.5)

    col1, col2, col3 = st.columns(3)
    lcd   = col1.slider("📱 LCD-Nutzung (%)", 0, 100, 50)
    flash = col2.slider("💡 Blitz-Nutzung (%)", 0, 100, 20)
    wifi  = col3.slider("📡 WiFi/BT (%)", 0, 100, 30)
    ibis  = st.checkbox("📷 IBIS aktiv", value=True)

    if st.button("✅ Berechnen", type="primary"):
        factor  = 1.0
        factor -= (lcd   / 100) * 0.15
        factor -= (flash / 100) * 0.20
        factor -= (wifi  / 100) * 0.10
        factor -= 0.05 if ibis else 0
        factor  = max(0.3, factor)

        shots = int(cap * factor)
        mins  = shots / spm if spm > 0 else 0
        h, m  = int(mins // 60), int(mins % 60)

        c1, c2, c3 = st.columns(3)
        c1.metric("📸 Shots", f"{shots:,}")
        c2.metric("⏱️ Laufzeit", f"{h}h {m}min")
        c3.metric("⚡ Effizienz", f"{factor*100:.0f}%")

        if factor < 0.6:
            st.warning("⚠️ Hoher Verbrauch – Ersatzakku einpacken!")
        akkus_needed = math.ceil((8 * 60 * spm) / shots)
        st.info(f"💡 Für 8h Shooting: ca. **{akkus_needed} Akkus** empfohlen")

# ═══════════════════════════════════════════
#  RAUSCHEN
# ═══════════════════════════════════════════
elif tool == "📡 Rauschen":
    st.header("📡 Sensor-Rauschen & Dynamikumfang")
    st.markdown("Analysiere das Rauschverhalten des Canon EOS R Sensors")

    iso = st.selectbox("ISO wählen:", [100,200,400,800,1600,3200,6400,12800,25600])

    if st.button("📊 Analysieren", type="primary"):
        stops = math.log2(iso / 100)
        dr    = max(13.5 - stops * 0.8, 5.0)
        snr   = max(40   - stops * 5.5, 8.0)

        if snr >= 35:   rating = "🟢 Exzellent"
        elif snr >= 25: rating = "🟡 Gut"
        elif snr >= 15: rating = "🟠 Akzeptabel"
        else:           rating = "🔴 Stark verrauscht"

        c1, c2, c3 = st.columns(3)
        c1.metric("📉 SNR",          f"{snr:.1f} dB")
        c2.metric("🌈 Dynamikumfang",f"{dr:.1f} EV")
        c3.metric("📊 Bewertung",    rating)

        # ISO-Tabelle
        with st.expander("📋 Alle ISO-Werte im Vergleich"):
            rows = []
            for i in [100,200,400,800,1600,3200,6400,12800,25600]:
                s = math.log2(i / 100)
                rows.append({
                    "ISO":          i,
                    "SNR (dB)":     f"{max(40 - s*5.5, 8):.1f}",
                    "Dynamik (EV)": f"{max(13.5 - s*0.8, 5):.1f}",
                    "Empfehlung":   "✅" if max(40 - s*5.5, 8) >= 25 else "⚠️"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.info("""
    💡 **Tipps für weniger Rauschen:**
    - ETTR: Rechtsbündig belichten (Highlights knapp unter Clipping)
    - RAW statt JPEG – mehr Spielraum in Post
    - Mehrere Bilder stacken (z.B. mit Sequator)
    - In-Camera Rauschreduzierung: AUS (besser in Lightroom)
    """)

# ═══════════════════════════════════════════
#  FOTO-SPOTS
# ═══════════════════════════════════════════
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
        lat   = c3.number_input("🌐 Breitengrad",  value=48.1351, format="%.4f")
        lon   = c4.number_input("🌐 Längengrad",   value=11.5820, format="%.4f")
        beste = st.text_input("⏰ Beste Zeit (z.B. Golden Hour / Sommer)")
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
            df_spots = pd.DataFrame(st.session_state.spots)
            st.dataframe(df_spots, use_container_width=True)

            last = st.session_state.spots[-1]
            maps_url = f"https://maps.google.com/?q={last['Lat']},{last['Lon']}"
            st.markdown(f"🔗 [Letzten Spot auf Google Maps öffnen]({maps_url})")

            if st.button("🗑️ Alle Spots löschen"):
                st.session_state.spots = []
                st.rerun()
        else:
            st.info("📭 Noch keine Spots gespeichert.")

# ═══════════════════════════════════════════
#  WETTER
# ═══════════════════════════════════════════
elif tool == "☁️ Wetter":
    st.header("☁️ Wetter-Assistent für Fotografen")
    col1, col2 = st.columns(2)
    temp   = col1.number_input("🌡️ Temperatur (°C)", value=15)
    wind   = col2.number_input("💨 Wind (km/h)", value=10)
    clouds = st.slider("☁️ Bewölkung (%)", 0, 100, 40)
    cond   = st.selectbox("Bedingung", ["☀️ Klar","⛅ Teilweise","☁️ Bedeckt","🌧️ Regen","🌫️ Nebel","❄️ Schnee"])

    if st.button("📊 Foto-Bedingungen prüfen", type="primary"):
        recs = []
        # Licht
        if clouds < 30:
            recs.append("🌅 Perfekt für Golden Hour & Sunset – klarer Horizont!")
        elif clouds < 60:
            recs.append("⛅ Gut für dramatische Landschaften mit Wolkenstruktur")
        else:
            recs.append("☁️ Weiches Diffuslicht – ideal für Portrait & Makro")
        # Wind
        if wind > 40:
            recs.append("💨 Sehr windig! Stativ beschweren, min. 1/500s, Tele meiden")
        elif wind > 20:
            recs.append("💨 Mäßiger Wind – auf Verwacklung achten, Stativ stabilisieren")
        # Temperatur
        if temp < 0:
            recs.append("❄️ Kalt! Akku in der Jackentasche warm halten, Fingerhandschuhe")
        elif temp > 35:
            recs.append("☀️ Heiß! Kamera vor direkter Sonne schützen, Hitzeschutz beachten")
        # Spezial
        if "Nebel" in cond:
            recs.append("🌫️ Nebel = mystische Stimmung! Kontrast & Klarheit in Post anheben")
        if "Regen" in cond:
            recs.append("🌧️ Regen: Wetterschutz/Regenhülle | Nach dem Regen = tolle Reflexionen!")
        if "Schnee" in cond:
            recs.append("❄️ Schnee: Belichtung +1 EV | Weißabgleich manuell | Akkus warm halten")

        st.info("✅ **Foto-Wetter Analyse:**\n\n" + "\n\n".join(recs))

# ═══════════════════════════════════════════
#  HISTOGRAMM
# ═══════════════════════════════════════════
elif tool == "📈 Histogramm":
    st.header("📈 Belichtungs-Histogramm Simulator")
    st.markdown("Simuliere ein Histogramm basierend auf EV-Wert und Kontrast")

    ev       = st.slider("EV Wert (Helligkeit)", 0, 20, 12)
    contrast = st.slider("Kontrast (Szene)", 10, 100, 50)
    channel  = st.selectbox("Kanal", ["Luminanz","🔴 Rot","🟢 Grün","🔵 Blau"])

    if st.button("📊 Generieren", type="primary"):
        try:
            import numpy as np
            center = int((ev / 20) * 255)
            x = np.arange(256)
            sigma = contrast / 2
            y = 1000 * np.exp(-((x - center)**2) / (2 * sigma**2))

            color_map = {
                "Luminanz":  "#E0E0E0",
                "🔴 Rot":    "#FF4444",
                "🟢 Grün":   "#44FF44",
                "🔵 Blau":   "#4444FF"
            }
            df_hist = pd.DataFrame({"Pixelwert": x, "Häufigkeit": y.astype(int)})
            st.bar_chart(df_hist.set_index("Pixelwert"),
                         color=color_map[channel],
                         use_container_width=True)

            if ev > 17:
                st.warning("🔴 Überbelichtet – Highlights werden abgeschnitten (Clipping)!")
            elif ev < 4:
                st.warning("🔵 Unterbelichtet – Schattenbereiche verlieren Details!")
            else:
                st.success("🟢 Gut belichtet! Tipp: Etwas nach rechts (ETTR) für weniger Rauschen.")
        except ImportError:
            st.error("numpy nicht verfügbar. Bitte installieren: pip install numpy")

# ═══════════════════════════════════════════
#  FILTER-SIMULATOR
# ═══════════════════════════════════════════
elif tool == "🎨 Filter-Sim":
    st.header("🎨 Filter-Simulator")
    st.markdown("Simuliere ND-, Farb- und Kreativfilter auf deinem Foto")

    uploaded = st.file_uploader("🖼️ Foto hochladen", type=["jpg","png","jpeg","webp"])

    if uploaded:
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            img = Image.open(uploaded).convert("RGB")

            col1, col2 = st.columns(2)
            with col1:
                st.image(img, caption="Original", use_container_width=True)

            filt     = st.selectbox("🎨 Filter wählen", [
                "Kein Filter",
                "ND2  (1 Stop dunkler)",
                "ND8  (3 Stops dunkler)",
                "ND64 (6 Stops dunkler)",
                "ND1000 (10 Stops dunkler)",
                "Schwarzweiß (S/W)",
                "Warmton (Sunset-Look)",
                "Kaltton (Blaustich)",
                "Kontrast erhöhen",
                "Soft-Focus / Glow",
                "Vignette",
            ])
            intensity = st.slider("Intensität", 0.0, 1.0, 0.8, 0.05)

            img_f = img.copy()

            if "ND2" in filt:
                img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.5 * intensity))
            elif "ND8" in filt:
                img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.875 * intensity))
            elif "ND64" in filt:
                img_f = ImageEnhance.Brightness(img_f).enhance(max(0.02, 1.0 - 0.984 * intensity))
            elif "ND1000" in filt:
                img_f = ImageEnhance.Brightness(img_f).enhance(max(0.01, 0.001 + (1 - intensity) * 0.1))
            elif "Schwarzweiß" in filt:
                img_f = img_f.convert("L").convert("RGB")
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 0.5)
            elif "Warmton" in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: min(255, int(p * (1.0 + 0.25 * intensity))))
                g = g.point(lambda p: min(255, int(p * (1.0 + 0.05 * intensity))))
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
                # Mischen von Original + Blur
                img_f = Image.blend(img_f, blurred, alpha=intensity * 0.6)
            elif "Vignette" in filt:
                import numpy as np
                w, h_px = img_f.size
                arr = __import__('numpy').array(img_f, dtype=float)
                cx, cy = w / 2, h_px / 2
                Y, X = __import__('numpy').ogrid[:h_px, :w]
                dist = __import__('numpy').sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
                mask = 1 - intensity * __import__('numpy').clip(dist - 0.5, 0, 1) * 1.5
                mask = __import__('numpy').clip(mask, 0, 1)
                for c in range(3):
                    arr[:, :, c] = arr[:, :, c] * mask
                img_f = Image.fromarray(arr.clip(0, 255).astype('uint8'))

            with col2:
                st.image(img_f, caption=f"Filter: {filt}", use_container_width=True)

            # Download-Button
            from io import BytesIO
            buf = BytesIO()
            img_f.save(buf, format="JPEG", quality=92)
            st.download_button(
                label="⬇️ Gefiltertes Bild herunterladen",
                data=buf.getvalue(),
                file_name="filtered_photo.jpg",
                mime="image/jpeg"
            )

        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Bild hoch, um Filter zu simulieren.")
        st.markdown("""
        **Verfügbare Filter:**
        - 🕶️ ND2 / ND8 / ND64 / ND1000 – Belichtungssimulation
        - ⚫ Schwarzweiß – Klassischer S/W-Look
        - 🌅 Warmton – Sonnenuntergangs-Feeling
        - 🌊 Kaltton – Kühler Blaustich
        - 🔲 Kontrast – Knackigere Bilder
        - 🌫️ Soft-Focus – Verträumter Glow
        - 🔵 Vignette – Dunkle Ecken
        """)
# ═══════════════════════════════════════════
# 🌙 MOND & MILCHSTRAßE
# ═══════════════════════════════════════════
elif tool == "🌙 Mond & Milchstraße":
    st.header("🌙 Mondphasen & Milchstraße Sichtbarkeit")
    st.markdown("Berechne optimale Termine für Astrofotografie und Milchstraßen-Aufnahmen.")
    
    col1, col2 = st.columns(2)
    with col1:
        date_str = st.text_input("📅 Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y"))
    with col2:
        latitude = st.number_input("🌍 Breitengrad", min_value=-90.0, max_value=90.0, value=50.0, help="Deutschland: ~47-55°")
    
    option = st.selectbox("🎯 Fokus", ["Milchstraße", "Mondfotografie", "Deep Sky", "Nordlichter"])
    
    if st.button("🔍 Berechnen", type="primary"):
        try:
            day, month, year = map(int, date_str.split("."))
            
            # Mondphase berechnen (0-1, wobei 0 = Neumond, 0.5 = Vollmond)
            moon_phase = calculate_moon_phase(year, month, day)
            phase_name, illumination, phase_desc = get_moon_phase_info(moon_phase)
            
            # Milchstraße-Saison (besser von März-Oktober auf der Nordhalbkugel)
            if 3 <= month <= 10:
                season_score = 1.0 - abs(month - 6.5) * 0.1  # Peak im Juni/Juli
                season_text = "🌌 Hauptsaison"
            else:
                season_score = 0.3
                season_text = "🌨️ Nebensaison (schwierig)"
            
            # Mond-Helligkeit (dunkler = besser für Milchstraße)
            darkness = 1.0 - abs(moon_phase - 0.0)  # 1.0 bei Neumond, 0 bei Vollmond
            if moon_phase > 0.4 and moon_phase < 0.6:
                darkness = 0.0  # Vollmond = zu hell
            
            # Gesamtbewertung
            if option == "Milchstraße":
                score = season_score * darkness * 100
                best_time = "23:00 - 04:00 Uhr" if 4 <= month <= 9 else "03:00 - 06:00 Uhr"
                recommendation = get_milky_way_recommendation(score, moon_phase)
            elif option == "Mondfotografie":
                score = (1.0 - darkness) * 100  # Heller Mond = besser
                best_time = "Abends nach Sonnenuntergang"
                recommendation = get_moon_recommendation(moon_phase)
            elif option == "Deep Sky":
                score = darkness * 100  # Dunkler Himmel = besser
                best_time = "Mitternacht - Morgengrauen"
                recommendation = "🔭 Perfekt für Deep Sky! Neumond oder schmale Sichel." if darkness > 0.8 else "⚠️ Warte auf dunklere Mondphase."
            else:  # Nordlichter
                if latitude > 60 or latitude < -60:
                    score = darkness * (1.0 if month in [10, 11, 12, 1, 2, 3] else 0.5) * 100
                    best_time = "21:00 - 02:00 Uhr"
                    recommendation = "🌌 Gute Aurora-Chance bei klarem Himmel!"
                else:
                    score = 20
                    best_time = "Nicht optimal (zu weit südlich)"
                    recommendation = "📍 Für Nordlichter brauchst du >60° Breite (Nordskandinavien, Island, Kanada)"
            
            # Anzeige
            st.success(f"""
            ### 📊 Ergebnis für {date_str}:
            
            **🌙 Mondphase:** {phase_name}  
            - Beleuchtung: {illumination:.0f}%  
            - {phase_desc}
            
            **{season_text}**  
            - Saison-Score: {season_score*100:.0f}%
            
            **⭐ Gesamtbewertung:** {score:.0f}/100  
            {recommendation}
            
            **⏰ Beste Zeit:** {best_time}
            """)
            
            # Tipps
            st.info("""
            ### 💡 Profi-Tipps:
            - 🌑 **Neumond** = Dunkler Himmel (ideal für Milchstraße)
            - 🌓 **Halbmond** = Interessante Mondlandschaften + etwas Himmel
            - 🌕 **Vollmond** = Zu hell für Milchstraße, aber gut für Mond/Landschaft
            - 📍 Milchstraße-Zentrum: März-Oktober, am besten Juni-August
            - 🎯 Fokus: 15-30 Sek. Belichtung, f/2.8 oder offener, ISO 1600-3200
            """)
            
        except Exception as e:
            st.error(f"⚠️ Ungültiges Datum. Bitte im Format TT.MM.JJJJ eingeben (z.B. 15.08.2025)\nFehler: {e}")
# ═══════════════════════════════════════════
# 🌠 STERNPUREN (Ausführlich)
# ═══════════════════════════════════════════
elif tool == "🌠 Sternspuren":
    st.header("🌠 Sternspuren & Astrofotografie")
    st.markdown("""
    **Berechne perfekte Einstellungen für atemberaubende Nachtaufnahmen**
    
    Von scharfen Sternen bis zu dramatischen Sternspuren – hier findest du alle Werkzeuge.
    """)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Sternspuren", "⭐ Scharfe Sterne", "📐 Planung", "📚 Tipps"])
    
    with tab1:
        st.subheader("🌌 Sternspuren berechnen")
        st.markdown("Erzeuge dramatische Kreisbahnen der Sterne um den Polarstern")
        
        col1, col2 = st.columns(2)
        with col1:
            total_time = st.number_input("Gesamtzeit (Minuten)", min_value=10, max_value=480, value=60)
            interval = st.number_input("Intervall zwischen Bildern (Sekunden)", min_value=1, max_value=30, value=5)
        with col2:
            shutter = st.selectbox("Belichtungszeit pro Bild", 
                                  ["10s", "15s", "20s", "25s", "30s"], index=2)
            iso = st.selectbox("ISO", [400, 800, 1600, 3200], index=2)
        
        if st.button(" Berechnen", type="primary"):
            shutter_sec = int(shutter.replace("s", ""))
            total_seconds = total_time * 60
            num_frames = total_seconds // (shutter_sec + interval)
            trail_length = (total_time / 4) * 15  # Grad
            
            st.success(f"""
            ### 📈 Ergebnis:
            - **Anzahl Bilder:** {num_frames:,}
            - **Gesamtzeit:** {total_time} Minuten ({total_seconds/60:.1f} Stunden)
            - **Sternspur-Länge:** {trail_length:.1f}° am Himmel
            - **Speicherbedarf:** ~{num_frames * 30 / 1024:.1f} GB (RAW)
            
            ### ⚙️ Empfohlene Settings:
            - Verschluss: {shutter}
            - ISO: {iso}
            - Blende: f/2.8 oder offener
            - Fokus: Manuell auf ∞
            """)
            
            st.info("""
            💡 **Stacking-Software:**
            - Windows: StarStaX (kostenlos)
            - Mac/Linux: Starry Landscape Stacker
            - Online: Sequator (einfach & schnell)
            """)
    
    with tab2:
        st.subheader("⭐ Scharfe Sterne (ohne Spuren)")
        st.markdown("Perfekt für Milchstraße & Deep-Sky-Fotografie")
        
        col1, col2 = st.columns(2)
        with col1:
            focal_sharp = st.number_input("Brennweite (mm)", min_value=14, max_value=400, value=24)
            sensor_type = st.selectbox("Sensor-Typ", 
                                      ["Vollformat", "APS-C (Canon 1.6x)", "APS-C (Nikon 1.5x)", "Micro 4/3 (2x)"])
        with col2:
            aperture_sharp = st.selectbox("Blende", [1.2, 1.4, 1.8, 2.0, 2.8, 4.0], index=3)
        
        # Crop-Faktor
        crop_map = {"Vollformat": 1.0, "APS-C (Canon 1.6x)": 1.6, 
                   "APS-C (Nikon 1.5x)": 1.5, "Micro 4/3 (2x)": 2.0}
        crop = crop_map[sensor_type]
        
        # 500er Regel
        max_exp_500 = 500 / (focal_sharp * crop)
        max_exp_npf = (35 * aperture_sharp + 30) / (focal_sharp * crop)
        
        st.success(f"""
        ### 📐 Maximale Belichtungszeit:
        
        **500er Regel (einfach):** {max_exp_500:.1f} Sekunden
        
        **NPF Regel (präzise):** {max_exp_npf:.1f} Sekunden
        
        ### 🎯 Empfohlene Einstellungen:
        - **Belichtung:** {max_exp_npf:.0f} Sekunden
        - **ISO:** 1600-3200 (je nach Licht)
        - **Blende:** f/{aperture_sharp} oder weiter öffnen
        - **Fokus:** Manuell auf hellsten Stern
        
        **Tipp:** Bei {max_exp_npf:.0f}s bleiben Sterne punktförmig!
        """)
        
        st.info("""
        📊 **NPF vs. 500er Regel:**
        - NPF ist genauer (berücksichtigt Blende & Sensor)
        - 500er Regel ist konservativer (längere Belichtung)
        - Für 100% scharfe Sterne: NPF verwenden
        - Für Web/Social Media: 500er Regel reicht
        """)
    
    with tab3:
        st.subheader("📅 Astro-Planung")
        st.markdown("Beste Bedingungen für Nachtaufnahmen")
        
        col1, col2 = st.columns(2)
        with col1:
            date_plan = st.text_input("Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y"))
            location = st.text_input("Ort", value="Deutschland")
        with col2:
            light_pollution = st.selectbox("Lichtverschmutzung", 
                                          ["Bortle 1-2 (Sehr dunkel)", 
                                           "Bortle 3-4 (Dunkel)", 
                                           "Bortle 5-6 (Vorstadt)", 
                                           "Bortle 7-9 (Stadt)"])
        
        if st.button("🔍 Bedingungen prüfen"):
            try:
                day, month, year = map(int, date_plan.split("."))
                moon_phase = calculate_moon_phase(year, month, day)
                _, moon_illum, _ = get_moon_phase_info(moon_phase)
                
                # Saison
                season = "🌌 Hauptsaison (März-Oktober)" if 3 <= month <= 10 else "🌨️ Nebensaison"
                season_score = 1.0 if 3 <= month <= 10 else 0.4
                
                # Bewertung
                darkness_score = (100 - moon_illum) / 100
                bortle_map = {"Bortle 1-2 (Sehr dunkel)": 1.0, "Bortle 3-4 (Dunkel)": 0.7,
                             "Bortle 5-6 (Vorstadt)": 0.4, "Bortle 7-9 (Stadt)": 0.1}
                light_score = bortle_map[light_pollution]
                
                total_score = (darkness_score * 0.4 + season_score * 0.3 + light_score * 0.3) * 100
                
                st.success(f"""
                ### 📊 Bewertung für {date_plan}:
                
                **🌙 Mond:** {moon_illum:.0f}% beleuchtet  
                **{season}**  
                **💡 Lichtverschmutzung:** {light_pollution}
                
                ### ⭐ Gesamtscore: {total_score:.0f}/100
                
                {get_astro_recommendation(total_score, moon_illum)}
                """)
                
            except:
                st.error("⚠️ Ungültiges Datum. Bitte TT.MM.JJJJ Format.")
    
    with tab4:
        st.markdown("""
        ### 📚 Kompletter Guide: Sternspuren & Astrofotografie
        
        #### 🎒 Equipment-Checkliste:
        - ✅ Stativ (stabil, windfest)
        - ✅ Fernauslöser/Intervalometer
        - ✅ Stirnlampe (Rotlicht-Modus)
        - ✅ Ersatzakkus (Kälte verkürzt Laufzeit!)
        - ✅ Speicherkarten (mind. 64 GB)
        - ✅ Warme Kleidung (auch im Sommer!)
        
        #### ⚙️ Kamera-Einstellungen:
        **Sternspuren:**
        - Modus: Manuell (M)
        - Format: RAW (mehr Spielraum in Post)
        - Weißabgleich: 3500-4000K (oder Auto)
        - Rauschreduzierung: AUS (dauert zu lang)
        - Bildstabilisator: AUS
        
        **Scharfe Sterne:**
        - Fokus: Manuell auf hellsten Stern (Live View 10x)
        - Belichtung: NPF-Regel (siehe Tab 2)
        - ISO: 1600-6400 (je nach Kamera)
        - Blende: So weit wie möglich (f/1.4-f/2.8)
        
        #### 📍 Location finden:
        - **Dark Sky Finder:** darksitefinder.com
        - **Light Pollution Map:** lightpollutionmap.info
        - **Milchstraße-Sichtbarkeit:** timeanddate.com/astronomy
        
        #### 🎨 Nachbearbeitung:
        1. **Stacking:** Sequator (Windows) oder Starry Landscape Stacker (Mac)
        2. **Lightroom:** 
           - Belichtung +0.5 bis +1.0
           - Kontrast +20
           - Tiefen +40
           - Klarheit +30
           - Vibrance +25
        3. **Farben:** 
           - Milchstraße: Blau/Lila-Töne betonen
           - Sterne: Natürliche Farben erhalten
        
        #### ⚠️ Häufige Fehler:
        - ❌ Zu kurze Gesamtzeit (<30 Min.)
        - ❌ Falscher Fokus (nicht auf ∞!)
        - ❌ Wind (Stativ wackelt)
        - ❌ Kondensation (Objektiv beschlägt)
        - ❌ Lichtverschmutzung (zu nah an Städten)
        
        #### 🌟 Profi-Tipps:
        -  Apps: PhotoPills, Stellarium Mobile, Sky Guide
        - 🌡️ Tau-Kappe verhindert Beschlag
        - 🔋 Akkus warm halten (Innentasche)
        - 📸 Testaufnahme bei ISO 6400 (Fokus prüfen)
        - 🌙 Neumond = dunkelster Himmel
        """)
# ═══════════════════════════════════════════
# 🎨 BEARBEITUNG (Ausführlich)
# ═══════════════════════════════════════════
elif tool == "🎨 Bearbeitung":
    st.header("🎨 Fotobearbeitung & Post-Processing")
    st.markdown("""
    **Vom RAW zum Meisterwerk – Professionelle Bearbeitungsschritte**
    
    Kompletter Workflow für Lightroom, Photoshop & Co.
    """)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Grundbearbeitung", "🌈 Farben", "✨ Effekte", 
        "🌙 Astro-Bearbeitung", "📚 Workflows"
    ])
    
    with tab1:
        st.subheader("📊 Basis-Korrektur (Lightroom/Camera Raw)")
        st.markdown("Der fundamentale Workflow für jedes Foto")
        
        st.markdown("""
        #### 1️⃣ **Objektivkorrektur** (IMMER zuerst!)
        - ✅ Profil-Korrektur aktivieren
        - ✅ Chromatische Aberration entfernen
        - ✅ Transformieren (gerade Linien)
        
        #### 2️⃣ **Weißabgleich**
        - Temperatur: 5000-5500K (Tageslicht)
        - Tönung: Leicht ins Magenta (+5 bis +10)
        - Oder: Pipette auf neutrales Grau
        
        #### 3️⃣ **Belichtung anpassen**
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            exp_val = st.slider("Belichtung", -2.0, 2.0, 0.0, 0.1)
            contrast = st.slider("Kontrast", -50, 100, 20)
            highlights = st.slider("Lichter", -100, 100, -40)
        with col2:
            shadows = st.slider("Tiefen", -100, 100, 40)
            whites = st.slider("Weiß", -100, 100, 10)
            blacks = st.slider("Schwarz", -100, 100, -10)
        
        st.success(f"""
        ### 📋 Deine Einstellungen:
        - Belichtung: {exp_val:+.1f}
        - Kontrast: {contrast:+d}
        - Lichter: {highlights:+d} | Tiefen: {shadows:+d}
        - Weiß: {whites:+d} | Schwarz: {blacks:+d}
        
        💡 **Tipp:** Histogramm im Auge behalten – keine Clipping-Warnungen!
        """)
        
        st.markdown("""
        #### 4️⃣ **Tonwertkurve** (optional)
        - Leichte S-Kurve für mehr Kontrast
        - Tiefen leicht anheben (nicht zu viel!)
        - Lichter sanft absenken
        
        #### 5️⃣ **Schärfen & Rauschreduzierung**
        - Schärfen: 40-60
        - Radius: 0.8-1.2
        - Detail: 25-50
        - Rauschreduzierung: 20-40 (bei hohem ISO)
        """)
    
    with tab2:
        st.subheader("🌈 Farbkorrektur & Stimmung")
        
        st.markdown("""
        #### 🎨 **HSL / Farbe** (Hue, Saturation, Luminance)
        
        **Häufige Anpassungen:**
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🔵 Blau (Himmel):**")
            blue_sat = st.slider("Sättigung", -100, 100, 20, key="blue_sat")
            blue_lum = st.slider("Helligkeit", -100, 100, -20, key="blue_lum")
            
            st.markdown("**🟢 Grün (Natur):**")
            green_hue = st.slider("Farbton", -100, 100, -10, key="green_hue")
            green_sat = st.slider("Sättigung", -100, 100, -15, key="green_sat")
        
        with col2:
            st.markdown("**🟠 Orange (Haut/Sunset):**")
            orange_sat = st.slider("Sättigung", -100, 100, 10, key="orange_sat")
            orange_lum = st.slider("Helligkeit", -100, 100, 5, key="orange_lum")
            
            st.markdown("**🟣 Lila (Milchstraße):**")
            purple_sat = st.slider("Sättigung", -100, 100, 30, key="purple_sat")
        
        st.info("""
        #### 🎭 **Farbtonkurve** (Advanced)
        - RGB-Kanal: Leichte S-Kurve
        - Rot: Tiefen leicht anheben (+5)
        - Blau: Lichter leicht absenken (-5)
        - Grün: Meist neutral lassen
        
        #### 🌟 **Split Toning**
        - Lichter: Warm (Orange/Gold, Sättigung 10-20)
        - Tiefen: Kühl (Blau, Sättigung 5-15)
        - Balance: 60-70 (mehr Lichter)
        """)
    
    with tab3:
        st.subheader("✨ Kreative Effekte")
        
        st.markdown("""
        #### 🌫️ **Atmosphäre & Klarheit**
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            clarity = st.slider("Klarheit", -50, 100, 20)
            dehaze = st.slider("Dunst entfernen", -50, 100, 15)
            texture = st.slider("Textur", -100, 100, 10)
        with col2:
            vignette = st.slider("Vignette", -100, 100, -20)
            grain = st.slider("Körnigkeit", 0, 100, 10)
        
        st.success(f"""
        ### Einstellungen:
        - Klarheit: {clarity:+d}
        - Dunst: {dehaze:+d}
        - Textur: {texture:+d}
        - Vignette: {vignette:+d}
        - Körnigkeit: {grain}
        """)
        
        st.markdown("""
        #### 🎯 **Effekt-Empfehlungen nach Genre:**
        
        **Landschaft:**
        - Klarheit: +30 bis +50
        - Dunst: +20 bis +40
        - Vignette: -15 bis -30
        
        **Portrait:**
        - Klarheit: -10 bis +10 (weich)
        - Textur: -20 (Haut glätten)
        - Vignette: -10 bis -20
        
        **Astro:**
        - Klarheit: +40 bis +60
        - Dunst: +30 bis +50
        - Körnigkeit: 15-25 (Film-Look)
        
        **Street:**
        - Klarheit: +20 bis +40
        - Körnigkeit: 20-40 (Vintage)
        - Vignette: -20 bis -40
        """)
    
    with tab4:
        st.subheader("🌙 Astro-Bearbeitung (Spezial)")
        st.markdown("Workflow für Milchstraße & Sternenhimmel")
        
        st.markdown("""
        #### 📊 **Schritt-für-Schritt:**
        
        **1. Stacking (VOR Lightroom!)**
        - Software: Sequator (Win) / Starry Landscape Stacker (Mac)
        - Bilder laden (20-50 Aufnahmen)
        - "Align stars" aktivieren
        - Output: 16-bit TIFF
        """)
        
        astro_exp = st.expander("📋 Kompletter Astro-Workflow")
        with astro_exp:
            st.markdown("""
            **2. Grundkorrektur (Lightroom):**
            - Weißabgleich: 3500-4000K (kühl)
            - Belichtung: +0.5 bis +1.0
            - Kontrast: +30
            - Tiefen: +50
            - Lichter: -30
            - Weiß: +20
            - Schwarz: -20
            
            **3. HSL-Anpassungen:**
            - Blau: Sättigung +40, Helligkeit -20
            - Lila: Sättigung +50
            - Rot/Orange: Sättigung +20 (Sterne)
            
            **4. Detail:**
            - Schärfen: 60-80
            - Rauschreduzierung: 20-30
            - Luminanz: 25
            - Farbe: 50
            
            **5. Lokale Anpassungen:**
            - Verlaufsfilter (Himmel): Belichtung +0.5
            - Radialfilter (Milchstraße): Klarheit +40
            - Pinsel (Vordergrund): Belichtung +0.3
            
            **6. Finale Korrekturen:**
            - Klarheit: +40
            - Dunst: +30
            - Vignette: -20
            """)
        
        st.info("""
        #### 🎨 **Farben der Milchstraße betonen:**
        - Kern: Orange/Rot (alte Sterne)
        - Arme: Blau/Lila (junge Sterne, Nebel)
        - Staub: Dunkle Bänder (Kontrast erhöhen)
        
        #### ⚠️ **Nicht übertreiben!**
        - Natürlichkeit bewahren
        - Keine "Neon-Farben"
        - Rauschen nicht komplett entfernen (Details verlieren)
        """)
    
    with tab5:
        st.markdown("""
        ### 📚 Komplette Workflows nach Genre
        
        #### 🏔️ **Landschaftsfotografie**
        1. Objektivkorrektur
        2. Weißabgleich (5500K)
        3. Belichtung (Histogramm zentrieren)
        4. Lichter -50, Tiefen +40
        5. Klarheit +40, Dunst +30
        6. HSL: Blau +30 Sättigung, Grün -15
        7. Schärfen: 60
        8. Vignette: -20
        
        #### 👤 **Portrait**
        1. Objektivkorrektur
        2. Weißabgleich (Hauttöne natürlich)
        3. Belichtung (Haut nicht überbelichten!)
        4. Lichter -30, Tiefen +20
        5. Textur -20 (Haut glätten)
        6. Orange: Helligkeit +10, Sättigung -5
        7. Schärfen: 40 (nur Augen!)
        8. Vignette: -15
        
        #### 🌃 **Street Photography**
        1. Objektivkorrektur
        2. Schwarz-Weiß oder kontrastreich
        3. Belichtung: Leicht unterbelichten (-0.3)
        4. Kontrast: +40
        5. Klarheit: +30
        6. Körnigkeit: 25 (Vintage-Look)
        7. Vignette: -30
        8. Gradationskurve: Starke S-Kurve
        
        #### 🌙 **Astrofotografie**
        1. Stacking (Sequator)
        2. Weißabgleich: 3800K
        3. Belichtung: +0.7
        4. Tiefen: +50, Lichter: -30
        5. Klarheit: +50, Dunst: +40
        6. Blau/Lila: Sättigung +50
        7. Schärfen: 70
        8. Rauschreduzierung: 25
        
        #### 🎪 **Event/Hochzeit**
        1. Objektivkorrektur
        2. Weißabgleich (Lichtverhältnisse anpassen)
        3. Belichtung: Sicher (+0.3)
        4. Lichter -40 (Kleider nicht ausbrennen!)
        5. Tiefen +30
        6. Hauttöne: Orange Helligkeit +5
        7. Schärfen: 50
        8. Vignette: -10
        
        ---
        
        ### 💾 Export-Einstellungen
        
        **Für Web/Social Media:**
        - Format: JPEG
        - Qualität: 80-85%
        - Größe: 2048px (längste Seite)
        - Farbraum: sRGB
        - Schärfen für Bildschirm
        
        **Für Druck:**
        - Format: TIFF oder JPEG 100%
        - Auflösung: 300 DPI
        - Farbraum: Adobe RGB
        - Keine Größenänderung
        
        **Für Archiv:**
        - Format: Original-RAW + XMP
        - Oder: DNG (Digital Negative)
        - 1:1 Kopie, keine Kompression
        """)
        
        st.success("""
        ### 🎯 Goldene Regeln der Bearbeitung:
        
        1. **Weniger ist mehr** – Natürlichkeit bewahren
        2. **RAW fotografieren** – Maximum an Informationen
        3. **Nicht-destruktiv** – Immer Kopien bearbeiten
        4. **Kalibrierter Monitor** – Farben stimmen nur so
        5. **Pausen machen** – Frische Augen sehen besser
        6. **Vergleichen** – Vorher/Nachher (Y-Taste)
        7. **Lernen** – Von Profis inspirieren lassen
        
        **Software-Empfehlungen:**
        - 🥇 **Lightroom Classic** (Allrounder, Abo)
        - 🥈 **Capture One** (Profi, teuer)
        - 🥉 **Darktable** (Kostenlos, Open Source)
        - 🎨 **Photoshop** (Compositing, Retusche)
        - 🌟 **Luminar Neo** (KI-gestützt, einfach)
        """)
# ═══════════════════════════════════════════
# 🌙 AKTUELLE MOND- & SONNEN-DATEN (Live)
# ═══════════════════════════════════════════
elif tool == "🌙 Aktuelle Mond-Daten":
    st.header("🌙 Live-Sonnen- & Mond-Daten")
    st.markdown("Präzise Zeiten basierend auf deinem Standort")
    
    city = st.text_input("📍 Standort", value="Berlin", help="Berlin, München, Hamburg, Köln, Frankfurt, Wien, Zürich")
    
    if st.button("🔄 Jetzt berechnen", type="primary"):
        try:
            coords = {
                "Berlin": (52.52, 13.405), "München": (48.1351, 11.5820),
                "Hamburg": (53.5511, 9.9937), "Köln": (50.9375, 6.9603),
                "Frankfurt": (50.1109, 8.6821), "Wien": (48.2082, 16.3738), "Zürich": (47.3769, 8.5417)
            }
            lat, lon = coords.get(city.strip(), (52.52, 13.405))
            
            city_info = LocationInfo(city, "DE", "Europe/Berlin", lat, lon)
            now = datetime.now(pytz.timezone("Europe/Berlin"))
            
            # ☀️ Sonne (astral v3 kompatibel)
            s = sun(city_info.observer, date=now.date(), tzinfo=now.tzinfo)
            
            # 🌙 Mond (eigene Funktion, da astral v3 'moon' entfernt hat)
            m_phase = calculate_moon_phase(now.year, now.month, now.day)
            m_name, m_illum, _ = get_moon_phase_info(m_phase)
            
            st.success(f"""
            ### 📅 {now.strftime('%d.%m.%Y %H:%M')}
            
            **🌞 Sonne**
            • Aufgang: `{s['sunrise'].strftime('%H:%M')}`
            • Untergang: `{s['sunset'].strftime('%H:%M')}`
            • Goldene Stunde: `{(s['sunrise']-timedelta(minutes=30)).strftime('%H:%M')} – {s['sunrise'].strftime('%H:%M')}`
            
            **🌙 Mond**
            • Phase: `{m_name}`
            • Beleuchtung: `{m_illum:.0f}%`
            
            **📸 Foto-Empfehlung**
            {get_best_photo_times(now, s, m_phase * 29.53)}
            """)
        except Exception as e:
            st.error(f"❌ {type(e).__name__}: {e}")
            st.info("💡 Tipp: Prüfe den Stadtnamen oder nutze Koordinaten")
        
                



# ═══════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════
st.divider()
st.markdown("""
<div style='text-align:center; color:#8B949E; font-size:0.85em;'>
    📷 Canon EOS R – Pro Tool v6.0 | Web Version | 23 Tools<br>
    Alle Berechnungen sind Richtwerte – Praxistests empfohlen.
</div>
""", unsafe_allow_html=True)