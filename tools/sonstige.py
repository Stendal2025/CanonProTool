import io
import math
import datetime as dt
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import requests

from config import LENSES, KI_DB, GUIDES, WB_DATA, BATTERY_MAP, KUESTEN_ORTE, SHUTTERS_ALL, SHUTTERS_LOG, ND_FILTERS
from utils import calculate_moon_phase, moon_phase_info, get_tide_photo_tip, milky_way_score, astro_recommendation
from database import get_logbook, add_logbook_entry, clear_logbook, get_spots, add_spot, clear_spots, get_api_key, set_setting, DB_PATH


def render_weissabgleich():
    st.header("🌡️ Weißabgleich & Farbtemperatur")
    for name, kelvin, color in WB_DATA:
        c1, c2 = st.columns([2, 3])
        c1.markdown(f"<span style='color:{color};font-weight:bold'>{name}</span>", unsafe_allow_html=True)
        c2.code(kelvin)
    st.info("💡 **Tipp:** Immer manuellen WB in Kelvin setzen statt Auto – stabilere Farben im Timelapse!")


def render_objektive():
    st.header("🔭 RF Objektiv-Datenbank")
    typ_filter = st.multiselect("🏷️ Typ filtern:", sorted({l["Typ"] for l in LENSES}))
    filtered = [l for l in LENSES if not typ_filter or l["Typ"] in typ_filter]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=450)
    st.info(f"📊 {len(filtered)} von {len(LENSES)} Objektiven angezeigt")


def render_gezeiten():
    st.header("🌊 Gezeiten & Tide-Rechner")
    st.markdown("Ebbe & Flut für Küstenfotografie & Tauchplanung")
    eingabe_methode = st.radio("📍 Standort wählen:", ["🏖️ Bekannter Küstenort", "📍 Eigene Koordinaten", "📍 GPS-Standort nutzen"], index=0)
    lat, lon = None, None
    if eingabe_methode == "🏖️ Bekannter Küstenort":
        ort_name = st.selectbox("Wähle einen Ort:", list(KUESTEN_ORTE.keys()))
        lat_str, lon_str = KUESTEN_ORTE[ort_name].split(",")
        lat, lon = float(lat_str.strip()), float(lon_str.strip())
        st.info(f"📍 Gewählt: **{ort_name}** ({lat:.4f}, {lon:.4f})")
    elif eingabe_methode == "📍 Eigene Koordinaten":
        default_coords = st.session_state.get("gps_coords", "54.32, 13.09")
        coords_input = st.text_input("Koordinaten eingeben (Breitengrad, Längengrad)", value=default_coords)
        if st.button(" Koordinaten prüfen"):
            try:
                if not coords_input or "," not in coords_input:
                    st.error("❌ Bitte gib Koordinaten im Format ein: **54.32, 13.09**")
                    st.stop()
                clean_input = coords_input.strip().replace(" ", "")
                parts = clean_input.split(",")
                if len(parts) != 2:
                    st.error("❌ Genau 2 Werte erwartet: Breitengrad, Längengrad")
                    st.stop()
                lat = float(parts[0])
                lon = float(parts[1])
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
    else:
        if "gps_coords" in st.session_state and st.session_state.gps_coords:
            try:
                lat, lon = map(float, st.session_state.gps_coords.split(","))
                st.success(f"✅ GPS-Standort übernommen: {lat:.4f}, {lon:.4f}")
            except (ValueError, TypeError, KeyError):
                st.warning("⚠️ GPS-Daten nicht verfügbar. Bitte andere Methode wählen.")
                lat, lon = 54.32, 13.09
        else:
            st.warning("⚠️ Kein GPS-Standort gespeichert. Bitte zuerst 📍 GPS-Standort Tool nutzen.")
            lat, lon = 54.32, 13.09
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
            API_KEY = get_api_key("WORLD_TIDES_API_KEY")
            if not API_KEY:
                st.warning("⚠️ **API-Key nicht hinterlegt!**")
                st.info("🔑 **So bekommst du einen kostenlosen Key:**\n1. Gehe zu [worldtides.info](https://www.worldtides.info/)\n2. Registriere dich (kostenlos, E-Mail genügt)\n3. Erstelle einen API Key\n4. Trage ihn in den **⚙️ Einstellungen** der App ein oder in `.streamlit/secrets.toml`")
                st.stop()
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
                    df = pd.DataFrame([
                        {"Zeit": datetime.fromtimestamp(e["dt"]).strftime("%H:%M"),
                         "Typ": "🌊 Hochwasser" if e["type"] == "High" else "🏖️ Niedrigwasser",
                         "Höhe": f"{e['height']:.2f} m",
                         "Foto-Tipp": get_tide_photo_tip(e["type"])} for e in extremes
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    low_tides = [e for e in extremes if e["type"] == "Low"]
                    high_tides = [e for e in extremes if e["type"] == "High"]
                    if low_tides:
                        st.info(f"🏖️ **Niedrigwasser:** {low_tides[0]['height']:.2f}m um {datetime.fromtimestamp(low_tides[0]['dt']).strftime('%H:%M')} Uhr → Ideal für Watt & Spiegelungen")
                    if high_tides:
                        st.info(f"🌊 **Hochwasser:** {high_tides[0]['height']:.2f}m um {datetime.fromtimestamp(high_tides[0]['dt']).strftime('%H:%M')} Uhr → Dramatische Brandung & Wellen")
        except Exception as e:
            st.error(f"❌ Fehler: {type(e).__name__}: {e}")
            st.info("💡 Prüfe deine Internetverbindung und API-Key")


def render_pdf_planer():
    st.header("📄 PDF-Shooting-Plan Generator")
    col1, col2 = st.columns(2)
    with col1:
        p_title = st.text_input("📸 Projektname", value="Canon EOS R Shooting")
        p_date = st.date_input("📅 Datum", datetime.now())
        p_loc = st.text_input("📍 Ort", value="Berlin")
    with col2:
        p_subj = st.text_input("🎯 Motiv", value="Landschaft / Portrait")
        p_client = st.text_input("👤 Auftraggeber", value="Privat")
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
            pdf.cell(0, 8, f"Datum: {p_date.strftime('%d.%m.%Y')} | Ort: {p_loc}", ln=True)
            pdf.cell(0, 8, f"Motiv: {p_subj} | Kunde: {p_client}", ln=True)
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
            st.download_button(label="⬇️ PDF Speichern", data=pdf_bytes,
                               file_name=f"Shooting_Plan_{p_date.strftime('%Y%m%d')}.pdf", mime="application/pdf")
        except ImportError:
            st.error("fpdf2 fehlt: pip install fpdf2")
        except Exception as e:
            st.error(f"Fehler beim Erstellen: {e}")


def render_planer():
    st.header("📝 Aufnahme-Planer & Logbuch")
    tab1, tab2 = st.tabs(["➕ Neuer Eintrag", "📖 Logbuch"])
    with tab1:
        c1, c2 = st.columns(2)
        loc = c1.text_input("📍 Ort")
        sub = c2.text_input("📸 Motiv")
        c3, c4 = st.columns(2)
        iso_log = c3.selectbox("ISO", [100,200,400,800,1600,3200], key="log_iso")
        ap_log = c4.selectbox("Blende", [1.4,1.8,2.8,4,5.6,8,11,16], key="log_ap")
        sh_log = st.selectbox("Verschluss", SHUTTERS_LOG, key="log_sh")
        notes = st.text_area("📝 Notizen")
        rating = st.slider("⭐ Bewertung", 1, 5, 3)
        if st.button("➕ Speichern", type="primary"):
            if loc or sub:
                add_logbook_entry(
                    date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    loc=loc, sub=sub,
                    settings=f"ISO {iso_log} | f/{ap_log} | {sh_log}",
                    notes=notes, rating="⭐" * rating,
                )
                st.success("✅ Gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte Ort oder Motiv eingeben.")
    with tab2:
        entries = get_logbook()
        if entries:
            search = st.text_input("🔍 Suchen…")
            if search:
                entries = get_logbook(search)
            for entry in entries:
                with st.expander(f"📸 {entry['date']} | {entry['loc']} – {entry['sub']} {entry['rating']}"):
                    st.markdown(f"- **📍 Ort:** {entry['loc']}\n- **📸 Motiv:** {entry['sub']}\n- **⚙️ Settings:** `{entry['settings']}`\n- **📝 Notizen:** {entry['notes']}")
            st.divider()
            st.markdown("**📤 Exportieren**")
            entries_df = pd.DataFrame([dict(e) for e in entries])
            c1, c2 = st.columns(2)
            c1.download_button("📥 CSV", entries_df.to_csv(index=False).encode("utf-8"), "logbuch.csv", "text/csv", use_container_width=True)
            c2.download_button("📥 JSON", entries_df.to_json(orient="records", force_ascii=False).encode("utf-8"), "logbuch.json", "application/json", use_container_width=True)
            if st.button("🗑️ Alle löschen"):
                clear_logbook()
                st.rerun()
        else:
            st.info("📭 Noch keine Einträge.")


def render_spots():
    st.header("🗺️ Foto-Spot Manager")
    tab1, tab2 = st.tabs(["➕ Spot hinzufügen", "📌 Meine Spots"])
    with tab1:
        c1, c2 = st.columns(2)
        name = c1.text_input("📍 Name des Spots")
        typ = c2.selectbox("🏷️ Typ", ["Landschaft","Portrait","Street","Architektur","Astro","Sonstiges"])
        c3, c4 = st.columns(2)
        lat = c3.number_input("🌐 Breitengrad", value=51.34, format="%.4f")
        lon = c4.number_input("🌐 Längengrad", value=12.38, format="%.4f")
        beste = st.text_input("⏰ Beste Zeit")
        notes = st.text_area("📝 Notizen")
        if st.button("➕ Spot speichern", type="primary"):
            if name:
                add_spot(name=name, typ=typ, lat=lat, lon=lon, beste_zeit=beste, notizen=notes)
                st.success(f"✅ '{name}' gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte einen Namen eingeben.")
    with tab2:
        spots = get_spots()
        if spots:
            df = pd.DataFrame([dict(s) for s in spots], columns=["id","name","typ","lat","lon","beste_zeit","notizen"])
            df_display = df.rename(columns={"name":"Name","typ":"Typ","lat":"Lat","lon":"Lon","beste_zeit":"Beste Zeit","notizen":"Notizen"})
            st.dataframe(df_display[["Name","Typ","Lat","Lon","Beste Zeit","Notizen"]], use_container_width=True)
            last = spots[0]
            st.markdown(f"🔗 [Letzten Spot auf Google Maps öffnen](https://maps.google.com/?q={last['lat']},{last['lon']})")
            st.divider()
            st.markdown("**📤 Exportieren**")
            c1, c2 = st.columns(2)
            c1.download_button("📥 CSV", df.to_csv(index=False).encode("utf-8"), "spots.csv", "text/csv", use_container_width=True)
            c2.download_button("📥 JSON", df.to_json(orient="records", force_ascii=False).encode("utf-8"), "spots.json", "application/json", use_container_width=True)
            if st.button("🗑️ Alle Spots löschen"):
                clear_spots()
                st.rerun()
        else:
            st.info("📭 Noch keine Spots gespeichert.")


def render_timelapse():
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
            frames = duration * fps
            total_sec = frames * interval
            h = int(total_sec // 3600)
            m = int((total_sec % 3600) // 60)
            s = int(total_sec % 60)
            size_map = {"RAW (~30 MB)": 30, "JPEG Fine (~10 MB)": 10, "JPEG Normal (~5 MB)": 5}
            size_gb = frames * size_map[file_format] / 1024
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
        | Motiv | Intervall |
        |-------|-----------|
        | Wolken (schnell) | 1–3s |
        | Sonnenuntergang | 3–5s |
        | Sternenhimmel | 20–30s |
        | Baustelle | 5–15 min |
        | Pflanzenwachstum | 15–30 min |
        """)


def render_exif():
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
                    tags = {ExifTags.TAGS[k]: str(v) for k, v in exif_data.items() if k in ExifTags.TAGS and not isinstance(v, bytes)}
                    IMPORTANT = ["Make","Model","ExposureTime","FNumber","ISOSpeedRatings","FocalLength","DateTimeOriginal","LensModel"]
                    st.subheader("📸 Kamera-Einstellungen")
                    for key in IMPORTANT:
                        if key in tags:
                            st.markdown(f"**{key}:** `{tags[key]}`")
                    with st.expander("📋 Alle EXIF-Daten"):
                        st.dataframe(pd.DataFrame(list(tags.items()), columns=["Tag","Wert"]), use_container_width=True, height=400)
        except ImportError:
            st.error("Pillow fehlt: pip install Pillow")
        except Exception as e:
            st.error(f"Fehler beim Lesen der EXIF-Daten: {e}")
    else:
        st.info("👆 Lade ein Foto hoch, um EXIF-Daten anzuzeigen.")


def render_ki():
    st.header("🤖 KI Fotografie-Assistent")
    scene = st.text_area("📝 Szene beschreiben", placeholder="z.B. 'Sonnenuntergang am See'", height=80)
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
            found = False
            for key, (title, settings, tips) in KI_DB.items():
                if key in scene.lower():
                    st.success(f"### {title}\n**Settings:** `{settings}`\n**Tipps:** {tips}")
                    found = True
                    break
            if not found:
                st.info("### 📸 Allgemein\n**Settings:** `ISO 200 | f/5.6 | 1/125s`\nBeschreibe deine Szene genauer.")


def render_cheat_sheets():
    st.header("📋 Schnellreferenz-Karten")
    sheet = st.selectbox("📑 Kategorie:", list(GUIDES.keys()))
    st.code(GUIDES[sheet], language="text")


def render_filter_sim():
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
                "Kein Filter", "ND2  (1 Stop dunkler)", "ND8  (3 Stops dunkler)",
                "ND64 (6 Stops dunkler)", "ND1000 (10 Stops dunkler)", "Schwarzweiß (S/W)",
                "Warmton (Sunset-Look)", "Kaltton (Blaustich)", "Kontrast erhöhen",
                "Soft-Focus / Glow", "Vignette",
            ])
            intensity = st.slider("Intensität", 0.0, 1.0, 0.8, 0.05)
            img_f = img.copy()
            if "ND2" in filt:
                img_f = ImageEnhance.Brightness(img_f).enhance(max(0.05, 1.0 - 0.50 * intensity))
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
                b = b.point(lambda p: max(0, int(p * (1.0 - 0.25 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kaltton" in filt:
                r, g, b = img_f.split()
                r = r.point(lambda p: max(0, int(p * (1.0 - 0.20 * intensity))))
                b = b.point(lambda p: min(255, int(p * (1.0 + 0.30 * intensity))))
                img_f = Image.merge("RGB", (r, g, b))
            elif "Kontrast" in filt:
                img_f = ImageEnhance.Contrast(img_f).enhance(1.0 + intensity * 1.5)
            elif "Soft-Focus" in filt:
                blurred = img_f.filter(ImageFilter.GaussianBlur(radius=int(intensity * 8)))
                img_f = Image.blend(img_f, blurred, alpha=intensity * 0.6)
            elif "Vignette" in filt:
                w_px, h_px = img_f.size
                arr = np.array(img_f, dtype=float)
                cx, cy = w_px / 2, h_px / 2
                Y, X = np.ogrid[:h_px, :w_px]
                dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
                mask = np.clip(1 - intensity * np.clip(dist - 0.5, 0, 1) * 1.5, 0, 1)
                arr = (arr * mask[:, :, np.newaxis]).clip(0, 255).astype("uint8")
                img_f = Image.fromarray(arr)
            with col2:
                st.image(img_f, caption=f"Filter: {filt}", use_container_width=True)
            buf = io.BytesIO()
            img_f.save(buf, format="JPEG", quality=92)
            st.download_button("⬇️ Gefiltertes Bild herunterladen", buf.getvalue(), "filtered_photo.jpg", "image/jpeg")
        except ImportError:
            st.error("Pillow / numpy fehlen: pip install Pillow numpy")
        except Exception as e:
            st.error(f"Fehler: {e}")
    else:
        st.info("👆 Lade ein Bild hoch, um Filter zu simulieren.")


def render_video():
    st.header("🎬 Video-Modus Guide")
    tab1, tab2, tab3 = st.tabs(["📊 Specs", "⚙️ Settings", "🎞️ 180°-Regel"])
    with tab1:
        st.markdown("""
        ### 📹 Canon EOS R Video-Spezifikationen
        | Modus | Auflösung | FPS | Crop |
        |-------|-----------|-----|------|
        | 4K UHD | 3840×2160 | 24p | 1.74× |
        | 4K UHD | 3840×2160 | 30p | 1.74× |
        | Full HD | 1920×1080 | 60p | 1.0× |
        | Full HD | 1920×1080 | 120p | 1.0× |
        """)
    with tab2:
        st.markdown("""
        ### ⚙️ Empfohlene Settings
        **🎬 Cinematic:** 24fps | 1/50s | C-Log | ND-Filter
        **📺 YouTube:** 30fps | 1/60s | Standard | Dual Pixel AF
        **⚡ Slow-Mo:** 120fps | 1/250s | Viel Licht erforderlich
        """)
    with tab3:
        fps_v = st.selectbox("FPS wählen:", [24, 25, 30, 50, 60, 120])
        shutter_180 = fps_v * 2
        st.success(f"**{fps_v} fps → 1/{shutter_180}s Verschlusszeit** (180°-Regel)")


def render_bearbeitung():
    st.header("🎨 Fotobearbeitung & Post-Processing")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Grundbearbeitung", "🌈 Farben", "✨ Effekte", "🌙 Astro", "📚 Workflows"])
    with tab1:
        st.markdown("#### Basis-Korrektur (Lightroom)")
        col1, col2 = st.columns(2)
        with col1:
            exp_val = st.slider("Belichtung", -2.0, 2.0, 0.0, 0.1)
            contrast_v = st.slider("Kontrast", -50, 100, 20)
            highlights = st.slider("Lichter", -100, 100, -40)
        with col2:
            shadows = st.slider("Tiefen", -100, 100, 40)
            whites = st.slider("Weiß", -100, 100, 10)
            blacks = st.slider("Schwarz", -100, 100, -10)
        st.success(f"Belichtung: {exp_val:+.1f} | Kontrast: {contrast_v:+d}\nLichter: {highlights:+d} | Tiefen: {shadows:+d} | Weiß: {whites:+d} | Schwarz: {blacks:+d}")
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
        clarity = st.slider("Klarheit", -50, 100, 20)
        dehaze = st.slider("Dunst entfernen", -50, 100, 15)
        vignette = st.slider("Vignette", -100, 100, -20)
        grain = st.slider("Körnigkeit", 0, 100, 10)
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
        | Zweck | Format | Qualität | Größe | Farbraum |
        |-------|--------|----------|-------|----------|
        | Web/Social | JPEG | 80–85% | 2048px | sRGB |
        | Druck | TIFF | 100% | 300DPI | AdobeRGB |
        | Archiv | DNG | – | Orig. | – |
        """)


def render_akku():
    st.header("🔋 Akku-Kalkulator")
    battery = st.selectbox("🔋 Akku-Typ", list(BATTERY_MAP.keys()))
    cap = BATTERY_MAP[battery]
    spm = st.number_input("⏱️ Shots/Minute", 0.5, 10.0, 2.0, 0.5)
    col1, col2, col3 = st.columns(3)
    lcd = col1.slider("📱 LCD-Nutzung (%)", 0, 100, 50)
    flash = col2.slider("💡 Blitz-Nutzung (%)", 0, 100, 20)
    wifi = col3.slider("📡 WiFi/BT (%)", 0, 100, 30)
    ibis = st.checkbox("📷 IBIS aktiv", value=True)
    if st.button("✅ Berechnen", type="primary"):
        factor = max(0.3, 1.0 - (lcd / 100) * 0.15 - (flash / 100) * 0.20 - (wifi / 100) * 0.10 - (0.05 if ibis else 0))
        shots = int(cap * factor)
        mins = shots / spm if spm > 0 else 0
        h, m = int(mins // 60), int(mins % 60)
        c1, c2, c3 = st.columns(3)
        c1.metric("📸 Shots", f"{shots:,}")
        c2.metric("⏱️ Laufzeit", f"{h}h {m}min")
        c3.metric("⚡ Effizienz", f"{factor*100:.0f}%")
        if factor < 0.6:
            st.warning("⚠️ Hoher Verbrauch – Ersatzakku einpacken!")
        akkus = math.ceil((8 * 60 * spm) / max(shots, 1))
        st.info(f"💡 Für 8h Shooting: ca. **{akkus} Akkus** empfohlen")


def render_unterwasser():
    st.header("🤿 Unterwasser-Fotografie Assistant")
    st.markdown("Settings & Tipps für Canon EOS R & Apexcam ActionCam")
    col1, col2 = st.columns(2)
    with col1:
        depth = st.slider(" Tiefe (m)", 0, 60, 5)
        visibility = st.slider("👁️ Sichtweite (m)", 1, 30, 10)
    with col2:
        water_type = st.selectbox("💧 Wasser-Typ", ["Tropisch/Klar", "Gemäßigt", "Trüb/Kalt"])
        use_flash = st.checkbox("💡 Blitz/Licht nutzen", value=True)
    tab1, tab2 = st.tabs(["📷 Canon EOS R (Pro)", "🏄 Apexcam (Action)"])
    with tab1:
        st.subheader("📷 Canon EOS R Settings")
        c1, c2 = st.columns(2)
        if use_flash:
            wb_val = "4800K – 5200K (Blitz)"
        else:
            base_wb = {"Tropisch/Klar": 5600, "Gemäßigt": 6000, "Trüb/Kalt": 6500}
            wb_val = f"{min(base_wb[water_type] + (depth * 25), 8000)}K"
        c1.metric("⚖️ Weißabgleich", wb_val)
        c1.metric(" Bildformat", "RAW + JPEG (Fine)")
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
        with st.expander("🐙 Apexcam Profi-Tipps"):
            st.markdown("""
            1. **Get Close or Go Home:** ActionCams haben kleine Sensoren. Geh nah ran (<1m), sonst wird alles grau/blau.
            2. **Housing prüfen:** Die Apexcam M80 Air ist 40m wasserdicht *nackt*, aber für Fotos immer das Gehäuse nutzen!
            3. **Touchscreen nass:** Deaktiviere "Touch Lock" oder nutze den "Mode"-Knopf am Gehäuse, da der Screen nass oft "spinnt".
            4. **Akku:** Kälteschutz (Neopren-Hülle) hilft bei kaltem Wasser.
            """)
        if visibility < 5:
            st.warning("⚠️ Trübes Wasser: Apexcam leidet hier mehr als die Canon. Nutze Weitwinkel-Makro-Linse (Wet Lens)!")
    st.divider()
    st.subheader("🌊 Umgebungs-Analyse")
    if depth <= 3:
        lost_colors = "Keine"
    elif depth <= 8:
        lost_colors = "Rot"
    elif depth <= 15:
        lost_colors = "Rot, Orange"
    else:
        lost_colors = "Rot, Orange, Gelb, Grün"
    st.metric("🎨 Verlorene Farben ab dieser Tiefe", lost_colors)
    with st.expander("✅ Pre-Dive Checkliste"):
        for c in ["O-Ring reinigen & einfetten", "Speicherkarte formatiert?", "Akku voll (Kälte-Reserve einkalkulieren)", "Gehäuse-Vakuumtest gemacht?", "Objektiv trocken? (Keine Fingerabdrücke)"]:
            st.checkbox(c, key=f"uw_{c}")


def render_pdf_export():
    st.header("📄 Shooting-Plan erstellen")
    st.markdown("Erstelle einen professionellen PDF-Bericht für Kunden oder als Checkliste.")
    try:
        from fpdf import FPDF
    except ImportError:
        st.error("❌ Fehler: 'fpdf2' ist nicht installiert. Bitte zu requirements.txt hinzufügen!")
        st.stop()
    st.subheader("📝 Planungsdetails")
    col1, col2 = st.columns(2)
    with col1:
        pdf_client = st.text_input("Kunde / Projekt", placeholder="z. B. Hochzeit Müller")
        default_loc = ""
        if st.session_state.get("gps_coords"):
            gps = st.session_state.gps_coords
            if "," in str(gps):
                default_loc = f"{gps.split(',')[0].strip()}, {gps.split(',')[1].strip()}"
            else:
                default_loc = str(gps)
        pdf_loc = st.text_input("Ort / Location", value=default_loc)
    with col2:
        pdf_date = st.date_input("Datum", value=dt.date.today())
        pdf_weather = st.text_input("Wetter / Bedingungen", placeholder="z. B. Sonne, 22°C")
    pdf_notes = st.text_area("Notizen & Settings (Kamera, Objektive, Ablauf...)", height=150,
                             placeholder="• 16:00 Uhr: Golden Hour Start\n• Objektiv: 50mm 1.2\n• ND1000 für Wasser...")
    if st.button("📄 PDF generieren & Download", type="primary"):
        if not pdf_client or not pdf_loc:
            st.warning("⚠️ Bitte mindestens Kunde und Ort angeben.")
        else:
            try:
                class ShootingPDF(FPDF):
                    def header(self):
                        self.set_font("Helvetica", 'B', 15)
                        self.set_text_color(41, 98, 255)
                        self.cell(0, 10, 'Canon EOS R - Shooting Plan', 0, 1, 'C')
                        self.ln(5)
                        self.set_draw_color(200, 200, 200)
                        self.line(10, 25, 200, 25)
                        self.ln(10)
                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica", 'I', 8)
                        self.set_text_color(128, 128, 128)
                        self.cell(0, 10, f'Erstellt mit Canon EOS R Pro Tool | {datetime.now().strftime("%d.%m.%Y")}', 0, 0, 'C')
                pdf = ShootingPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
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
                pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
                st.success("✅ PDF erfolgreich erstellt!")
                st.download_button(label="📥 PDF Herunterladen", data=pdf_bytes,
                                   file_name=f"ShootingPlan_{pdf_date.strftime('%Y%m%d')}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Fehler bei der Erstellung: {e}")
    st.divider()
    st.caption("💡 Tipp: Die PDF ist optimiert für den Druck und den Versand per E-Mail.")


def render_einstellungen():
    st.header("⚙️ Einstellungen")
    tab1, tab2 = st.tabs(["🔑 API-Keys", "🗄️ Datenbank"])
    with tab1:
        st.markdown("API-Keys werden in der lokalen SQLite-Datenbank gespeichert. In Streamlit Cloud überschreiben `secrets.toml`-Werte.")
        st.divider()
        ow_current = get_api_key("OPENWEATHER_API_KEY") or ""
        ow_display = ow_current[:8] + "…" if len(ow_current) > 10 else (ow_current or "—")
        st.metric("🌤️ OpenWeatherMap", "✅ Konfiguriert" if ow_current else "❌ Fehlt", ow_display)
        ow_new = st.text_input("Neuen OpenWeatherMap API-Key eingeben", type="password", key="ow_input")
        c1, c2 = st.columns(2)
        if c1.button("💾 Speichern", key="save_ow"):
            if ow_new:
                set_setting("OPENWEATHER_API_KEY", ow_new)
                st.success("✅ OpenWeatherMap Key gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte einen Key eingeben.")
        if c2.button("🌤️ Testen", key="test_ow"):
            key_to_test = ow_new or ow_current
            if key_to_test:
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=Berlin&appid={key_to_test}&units=metric", timeout=5)
                    if r.status_code == 200:
                        st.success(f"✅ Key gültig! Berlin: {r.json()['main']['temp']:.1f}°C")
                        if ow_new:
                            set_setting("OPENWEATHER_API_KEY", ow_new)
                            st.rerun()
                    else:
                        st.error(f"❌ Fehler: {r.json().get('message', 'Ungültiger Key')}")
                except requests.RequestException as e:
                    st.error(f"❌ Verbindungsfehler: {e}")
            else:
                st.warning("⚠️ Kein Key zum Testen vorhanden.")
        st.divider()
        wt_current = get_api_key("WORLD_TIDES_API_KEY") or ""
        wt_display = wt_current[:8] + "…" if len(wt_current) > 10 else (wt_current or "—")
        st.metric("🌊 WorldTides", "✅ Konfiguriert" if wt_current else "❌ Fehlt", wt_display)
        wt_new = st.text_input("Neuen WorldTides API-Key eingeben", type="password", key="wt_input")
        c3, c4 = st.columns(2)
        if c3.button("💾 Speichern", key="save_wt"):
            if wt_new:
                set_setting("WORLD_TIDES_API_KEY", wt_new)
                st.success("✅ WorldTides Key gespeichert!")
                st.rerun()
            else:
                st.warning("Bitte einen Key eingeben.")
        if c4.button("🌊 Testen", key="test_wt"):
            key_to_test = wt_new or wt_current
            if key_to_test:
                try:
                    r = requests.get(f"https://www.worldtides.info/api/v3?lat=54.32&lon=13.09&key={key_to_test}&start=1700000000&length=3600&extremes", timeout=5)
                    data = r.json()
                    if r.status_code == 200 and data.get("status") == 200:
                        st.success("✅ Key gültig! Gezeitendaten empfangen.")
                        if wt_new:
                            set_setting("WORLD_TIDES_API_KEY", wt_new)
                            st.rerun()
                    else:
                        st.error(f"❌ Fehler: {data.get('error', 'Ungültiger Key')}")
                except requests.RequestException as e:
                    st.error(f"❌ Verbindungsfehler: {e}")
            else:
                st.warning("⚠️ Kein Key zum Testen vorhanden.")
    with tab2:
        st.metric("📂 Datenbank-Pfad", DB_PATH)
        c5, c6 = st.columns(2)
        if c5.button("🗑️ Alle Logbuch-Einträge löschen"):
            clear_logbook()
            st.success("✅ Logbuch gelöscht!")
            st.rerun()
        if c6.button("🗑️ Alle Spots löschen"):
            clear_spots()
            st.success("✅ Spots gelöscht!")
            st.rerun()
