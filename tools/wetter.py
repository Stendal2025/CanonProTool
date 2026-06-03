from datetime import datetime

import streamlit as st
import pandas as pd
import requests


def render_live_wetter():
    st.header("☁️ Live-Wetter Analyse")
    st.markdown("Detaillierte Daten & Shooting-Empfehlungen")
    city_input = st.text_input("📍 Stadt oder Koordinaten (z.B. Berlin oder 50.46,7.46)", value=st.session_state.gps_coords)
    if st.button("🔄 Analyse starten", type="primary"):
        try:
            from database import get_api_key
            API_KEY = get_api_key("OPENWEATHER_API_KEY")
            lat, lon = None, None
            if "," in city_input:
                try:
                    parts = city_input.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                except Exception:
                    st.error("❌ Ungültiges Format. Bitte: 52.52,13.40")
                    st.stop()
            url = (
                f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/weather?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )
            res = requests.get(url, timeout=8)
            data = res.json()
            if data.get("cod") != 200:
                st.error(f"❌ {data.get('message','Unbekannter Fehler')}")
            else:
                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                pressure = data["main"]["pressure"]
                visibility = data.get("visibility", 10000) / 1000
                wind = data["wind"]["speed"] * 3.6
                wind_gust = data["wind"].get("gust", 0) * 3.6
                clouds = data["clouds"]["all"]
                desc = data["weather"][0]["description"]
                icon = data["weather"][0]["icon"]
                sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
                sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")
                st.subheader(f"📸 {desc.capitalize()} | {temp:.1f}°C (gefühlt {feels_like:.1f}°C)")
                st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png", width=100)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💨 Wind", f"{wind:.1f} km/h", delta=f"Böen: {wind_gust:.1f}" if wind_gust > 0 else None)
                    st.metric("☁️ Bewölkung", f"{clouds}%")
                    st.metric("💧 Luftfeuchtigkeit", f"{humidity}%")
                with col2:
                    st.metric("👁️ Sichtweite", f"{visibility:.1f} km")
                    st.metric("🌡️ Luftdruck", f"{pressure} hPa")
                    st.caption("Hoher Druck = oft stabiles Licht")
                with col3:
                    st.metric("🌅 Aufgang", sunrise)
                    st.metric("🌇 Untergang", sunset)
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
                if score >= 80:
                    st.success(f"⭐⭐⭐ **PERFEKT (Score: {score})**\n\n" + "\n".join(notes))
                elif score >= 50:
                    st.info(f"⭐⭐ **GUT (Score: {score})**\n\n" + "\n".join(notes))
                else:
                    st.warning(f"⭐ **SCHWIERIG (Score: {score})**\n\n" + "\n".join(notes))
        except Exception as e:
            st.error(f"Fehler: {e}")


def render_5tage_prognose():
    st.header("📅 5-Tage-Wettervorhersage")
    city_input = st.text_input("📍 Stadt oder Koordinaten", value=st.session_state.gps_coords)
    if st.button("📊 Vorhersage laden", type="primary"):
        try:
            from database import get_api_key
            API_KEY = get_api_key("OPENWEATHER_API_KEY")
            lat, lon = None, None
            if "," in city_input:
                try:
                    parts = city_input.replace(" ", "").split(",")
                    lat, lon = float(parts[0]), float(parts[1])
                except Exception:
                    st.error("❌ Ungültiges Format. Bitte: 52.52,13.40")
                    st.stop()
            url = (
                f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
                if lat else
                f"https://api.openweathermap.org/data/2.5/forecast?q={city_input}&appid={API_KEY}&units=metric&lang=de"
            )
            data = requests.get(url, timeout=8).json()
            if data.get("cod") != "200":
                st.error(f"❌ {data.get('message','Unbekannter Fehler')}")
            else:
                times, temps, daily = [], [], {}
                for item in data["list"]:
                    dt = datetime.fromtimestamp(item["dt"])
                    day = dt.strftime("%d.%m.")
                    times.append(dt.strftime("%d.%m. %H:%M"))
                    temps.append(item["main"]["temp"])
                    if day not in daily:
                        daily[day] = {"min": item["main"]["temp_min"], "max": item["main"]["temp_max"], "desc": item["weather"][0]["description"]}
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
