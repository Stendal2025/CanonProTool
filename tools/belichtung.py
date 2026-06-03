import math
import pandas as pd
import streamlit as st
from config import SHUTTERS_ALL, CROP_MAP, COC_MAP
from utils import parse_shutter, evaluate_exposure, calculate_nd, calculate_dof, calculate_flash


def render_belichtung():
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


def render_nd_rechner():
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
        st.caption("💡 Tippe auf das **Kopier-Icon** rechts im Code-Block!")


def render_schaerfentiefe():
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
        far_str   = "∞" if far == float("inf") else f"{far:.2f} m"
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


def render_focus_stacking():
    st.header("🔬 Focus Stacking Assistant")
    st.markdown("Berechne exakte Fokusschritte für maximale Schärfentiefe")
    col1, col2 = st.columns(2)
    with col1:
        focal = st.number_input(" Brennweite (mm)", min_value=10, max_value=600, value=100)
        aperture = st.number_input("🔘 Blende (f/)", min_value=1.0, max_value=32.0, value=5.6, step=0.1)
    with col2:
        sensor = st.selectbox("📐 Sensor", ["Vollformat (0.03mm)", "APS-C (0.02mm)", "Micro 4/3 (0.015mm)"])
        coc = 0.03 if "Voll" in sensor else (0.02 if "APS" in sensor else 0.015)
        start_dist_m = st.number_input("📏 Start-Entfernung (m)", min_value=0.1, max_value=1000.0, value=0.5, step=0.1)
        overlap = st.slider("🔄 Überlappung (%)", 10, 90, 30)
    if st.button("✅ Fokusschritte berechnen", type="primary"):
        try:
            H = (focal**2) / (aperture * coc) + focal
            D_start = start_dist_m * 1000
            S_near = (H * D_start) / (H + D_start)
            if D_start >= H:
                st.success(f"✅ **Alles scharf!** Dein Startpunkt ({start_dist_m}m) liegt hinter der hyperfokalen Distanz ({H/1000:.2f}m).")
                st.info("💡 Du brauchst kein Stacking! Stelle auf f/{aperture} und fokusiere auf {start_dist_m}m.")
            else:
                S_far = (H * D_start) / (H - D_start)
                dof = S_far - S_near
                step_size_mm = dof * ((100 - overlap) / 100)
                step_size_cm = step_size_mm / 10
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


def render_nd_stacking():
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
    with st.expander("➕ Dritten Filter hinzufügen (optional)"):
        filter_c = st.selectbox("🔺 Filter C", [f[0] for f in ND_FILTERS], index=0)
        use_c = st.checkbox("Filter C aktivieren", value=False)
    if st.button("✅ Stacking berechnen", type="primary"):
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


def render_blitz():
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


def render_rauschen():
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
                    "ISO": i, "SNR (dB)": f"{max(40-s*5.5,8):.1f}",
                    "Dynamik (EV)": f"{max(13.5-s*0.8,5):.1f}",
                    "Empfehlung": "✅" if max(40-s*5.5, 8) >= 25 else "⚠️",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)


def render_histogramm():
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
            color_map = {"Luminanz": "#E0E0E0", "🔴 Rot": "#FF4444", "🟢 Grün": "#44FF44", "🔵 Blau": "#4444FF"}
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


def render_vergleich():
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


def render_crop_faktor():
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
        ref = [{"Sensor": k, "Crop-Faktor": v, "50 mm entspricht": f"{50*v:.0f} mm FF-Äquivalent"} for k, v in CROP_MAP.items()]
        st.dataframe(pd.DataFrame(ref), use_container_width=True)
