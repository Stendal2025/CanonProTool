import math
import hashlib
from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components
import requests

from config import SHUTTER_MAP, CITY_COORDS


def copy_button(text_to_copy: str, label: str = " Kopieren"):
    btn_id = f"btn_{hashlib.md5(text_to_copy.encode()).hexdigest()}"
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
        "golden_morning": (sunrise.strftime(fmt), (sunrise + timedelta(minutes=60)).strftime(fmt)),
        "golden_evening": ((sunset - timedelta(minutes=60)).strftime(fmt), sunset.strftime(fmt)),
        "blue_morning":   ((sunrise - timedelta(minutes=30)).strftime(fmt), sunrise.strftime(fmt)),
        "blue_evening":   (sunset.strftime(fmt), (sunset + timedelta(minutes=30)).strftime(fmt)),
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


@st.cache_data(ttl=3600)
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
    except requests.RequestException:
        pass
    return None
