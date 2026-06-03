from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import requests
import pytz

from config import CITY_COORDS, CITY_LIST
from utils import calculate_moon_phase, moon_phase_info, milky_way_score, astro_recommendation, get_best_photo_times

ASTRAL_OK = False
_ASTRAL_ERR = ""
try:
    from astral import LocationInfo
    from astral.sun import sun
    ASTRAL_OK = True
except Exception as e:
    _ASTRAL_ERR = str(e)


def render_mond_milchstrasse():
    st.header("🌙 Mondphasen & Milchstraße Sichtbarkeit")
    city_sel = st.selectbox("📍 Stadt", ["(manuell)"] + CITY_LIST)
    col1, col2 = st.columns(2)
    with col1:
        date_str = st.text_input("📅 Datum (TT.MM.JJJJ)", value=datetime.now().strftime("%d.%m.%Y"))
    with col2:
        if city_sel != "(manuell)":
            latitude, longitude = CITY_COORDS[city_sel]
            st.number_input("🌍 Breitengrad", value=latitude, disabled=True, key="mw_lat")
            st.number_input("🌍 Längengrad", value=longitude, disabled=True, key="mw_lon")
        else:
            default_coords = st.session_state.get("gps_coords", "51.34,12.38")
            coords_input = st.text_input("📍 Koordinaten (Breitengrad, Längengrad)", value=default_coords)
            try:
                if "," in coords_input:
                    parts = coords_input.replace(" ", "").split(",")
                    latitude, longitude = float(parts[0]), float(parts[1])
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        st.error("❌ Ungültige Koordinaten")
                        st.stop()
                else:
                    latitude, longitude = 51.34, 12.38
                    except (ValueError, TypeError, KeyError):
                latitude, longitude = 51.34, 12.38
    option = st.selectbox("🎯 Fokus", ["Milchstraße", "Mondfotografie", "Deep Sky", "Nordlichter"])
    if st.button("🔍 Berechnen", type="primary"):
        try:
            day, month, year = map(int, date_str.split("."))
            phase = calculate_moon_phase(year, month, day)
            p_name, p_illum, p_tip = moon_phase_info(phase)
            if option == "Milchstraße":
                score = milky_way_score(phase, month)
                best_time = "22:30–04:00" if 4 <= month <= 9 else "03:00–06:00"
                rec = "🟢 Hervorragend!" if score >= 85 else "🟡 Gut!" if score >= 65 else "🟠 Mäßig." if score >= 40 else "🔴 Schlecht."
            elif option == "Mondfotografie":
                score = p_illum
                best_time = "Abends nach Sonnenuntergang"
                rec = "🌕 Vollmond – perfekt!" if 0.45 < phase < 0.55 else "🌙 Interessante Phase"
            elif option == "Deep Sky":
                score = max(0, 100 - p_illum)
                best_time = "Mitternacht–Morgengrauen"
                rec = "🔭 Dunkler Himmel – ideal!" if score > 80 else "⚠️ Auf Neumond warten."
            else:
                if abs(latitude) > 58:
                    score = max(0, 100 - p_illum) * (1.0 if month in range(10, 13) or month in range(1, 4) else 0.5)
                    best_time = "21:00–02:00"
                    rec = "🌌 Aurora möglich bei klarem Himmel!"
                else:
                    score = 15
                    best_time = "–"
                    rec = "📍 Zu weit südlich – >58° Breite nötig (Skandinavien, Island)"
            st.success(f"""
            ### 📊 Ergebnis – {date_str} | 📍 {latitude:.4f}, {longitude:.4f}
            **🌙 Mondphase:** {p_name}  Beleuchtung: **{p_illum:.0f}%** | {p_tip}
            **⭐ Bewertung:** {score:.0f}/100  {rec}
            **⏰ Beste Zeit:** {best_time}
            """)
            st.info("💡 **Tipps:** 🌑 Neumond = dunkelster Himmel  |  🌕 Vollmond = zu hell für Milchstraße  Milchstraße-Saison: März–Oktober (Peak: Juni–August)")
        except ValueError:
            st.error("⚠️ Ungültiges Datum. Format: TT.MM.JJJJ (z.B. 15.08.2025)")
        except Exception as e:
            st.error(f"❌ Fehler: {type(e).__name__}: {e}")


def render_aktuelle_mond_daten():
    st.header("🌙 Live-Sonnen- & Mond-Daten")
    if not ASTRAL_OK:
        st.error(f"⚠️ astral/pytz nicht installiert: {_ASTRAL_ERR}")
        st.stop()
    st.subheader("📍 Standort festlegen")
    city_sel = st.selectbox("Stadt aus Liste", ["(manuell / GPS)"] + CITY_LIST, index=0)
    lat, lon = None, None
    if city_sel != "(manuell / GPS)":
        lat, lon = CITY_COORDS[city_sel]
        st.info(f"🏙️ Gewählt: **{city_sel}** ({lat:.4f}, {lon:.4f})")
    else:
        default_coords = st.session_state.get("gps_coords", "51.34, 12.38")
        coords_input = st.text_input("📍 Koordinaten eingeben", value=default_coords)
        try:
            if "," in coords_input:
                parts = coords_input.replace(" ", "").split(",")
                lat, lon = float(parts[0]), float(parts[1])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    st.error("❌ Ungültige Koordinaten. Bereich: Lat -90..90, Lon -180..180")
                    st.stop()
            else:
                lat, lon = 51.34, 12.38
        except Exception:
            lat, lon = 51.34, 12.38
    if st.button("🔄 Jetzt berechnen", type="primary"):
        try:
            tz = pytz.timezone("Europe/Berlin")
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


def render_sternspuren():
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
                phase     = calculate_moon_phase(yr, mo, d)
                _, illum, _ = moon_phase_info(phase)
                lp_score = {"Bortle 1–2 (Sehr dunkel)":1.0, "Bortle 3–4 (Dunkel)":0.7,
                            "Bortle 5–6 (Vorstadt)":0.4, "Bortle 7–9 (Stadt)":0.1}[lp]
                season = 1.0 if 3 <= mo <= 10 else 0.4
                total_sc = ((100 - illum)/100 * 0.4 + season * 0.3 + lp_score * 0.3) * 100
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


def render_astro_wetter_dashboard():
    st.header("🌍 Astro & Wetter Dashboard")
    st.markdown("Alles für die Shooting-Planung an einem Ort")
    default_city = st.session_state.get("dash_city", "Berlin")
    city = st.text_input("📍 Stadt oder Koordinaten (z.B. Berlin oder 52.52,13.40)", value=default_city, key="dash_input")
    if st.button("🔄 Dashboard aktualisieren", type="primary"):
        try:
            from database import get_api_key
            API_KEY = get_api_key("OPENWEATHER_API_KEY")
            lat, lon = None, None
            if "," in city:
                try:
                    parts = city.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        st.error("❌ Ungültige Koordinaten. Breitengrad: -90 bis 90, Längengrad: -180 bis 180")
                        st.stop()
                except (ValueError, IndexError):
                    st.error("❌ Ungültiges Koordinaten-Format. Bitte: 52.52,13.40 (ohne Leerzeichen)")
                    st.stop()
            if lat is not None:
                w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
            else:
                w_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=de"
            w = requests.get(w_url, timeout=8).json()
            if w.get("cod") != 200:
                st.error(f"❌ {w.get('message', 'Unbekannter Fehler')}")
            else:
                temp = w["main"]["temp"]
                clouds = w["clouds"]["all"]
                wind = w["wind"]["speed"] * 3.6
                desc = w["weather"][0]["description"]
                icon = w["weather"][0]["icon"]
                sr_ts = datetime.fromtimestamp(w["sys"]["sunrise"]).strftime("%H:%M")
                ss_ts = datetime.fromtimestamp(w["sys"]["sunset"]).strftime("%H:%M")
                now = datetime.now()
                phase = calculate_moon_phase(now.year, now.month, now.day)
                m_name, m_illum, m_tip = moon_phase_info(phase)
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("☁️ Live-Wetter")
                    st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png", width=60)
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
                mw_sc = milky_way_score(phase, now.month)
                st.info(f"""
                ### 📸 Shooting-Empfehlung
                {astro_recommendation(astro_sc)}
                **Milchstraße-Score:** {mw_sc:.0f}/100
                """)
                with st.expander("📊 Stunden-Übersicht (heute)"):
                    if lat is not None:
                        f_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de&cnt=8"
                    else:
                        f_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=de&cnt=8"
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
