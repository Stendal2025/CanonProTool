import pandas as pd
import streamlit as st


def render_gps():
    st.header("📍 Standort eingeben")
    if "gps_coords" not in st.session_state:
        st.session_state.gps_coords = None
    if "gps_temp_coords" not in st.session_state:
        st.session_state.gps_temp_coords = None

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
    if st.session_state.gps_coords:
        st.divider()
        st.success(f"### ✅ Aktueller Standort: `{st.session_state.gps_coords}`")
        try:
            lat_f, lon_f = map(float, str(st.session_state.gps_coords).split(","))
            st.map(pd.DataFrame({"lat": [lat_f], "lon": [lon_f]}))
        except (ValueError, TypeError):
            pass
        if st.button("🗑️ Standort löschen"):
            st.session_state.gps_coords = None
            st.session_state.gps_temp_coords = None
            st.cache_data.clear()
            st.rerun()
