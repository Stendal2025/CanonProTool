import pandas as pd
import streamlit as st


def render_gps():
    st.header("📍 Standort automatisch erkennen")
    if "gps_coords" not in st.session_state:
        st.session_state.gps_coords = None
    if "gps_temp_coords" not in st.session_state:
        st.session_state.gps_temp_coords = None
    if "gps_requested" not in st.session_state:
        st.session_state.gps_requested = False

    if st.button("📍 Standort abrufen", use_container_width=True, key="gps_locate"):
        st.session_state.gps_requested = True
        st.rerun()

    if st.session_state.get("gps_requested"):
        st.markdown("""
        <div id="gps-result" style="background:#161B22;padding:12px;border-radius:8px;border:1px solid #30363D;margin-bottom:12px;">
            <p id="gps-text" style="color:#58A6FF;margin:0;text-align:center;">...</p>
        </div>
        <script>
        var gps_cached = sessionStorage.getItem('gps_coords');
        if(gps_cached){
            var d = JSON.parse(gps_cached);
            document.getElementById('gps-text').textContent = d.label;
            var u = new URL(window.location.href);
            u.searchParams.set('lat', d.lat);
            u.searchParams.set('lon', d.lon);
            window.history.replaceState({}, '', u.toString());
        } else if(navigator.geolocation){
            navigator.geolocation.getCurrentPosition(function(pos){
                var lat = pos.coords.latitude.toFixed(6);
                var lon = pos.coords.longitude.toFixed(6);
                var label = '✅ ' + lat + ', ' + lon;
                document.getElementById('gps-text').textContent = label;
                sessionStorage.setItem('gps_coords', JSON.stringify({lat:lat, lon:lon, label:label}));
                var u = new URL(window.location.href);
                u.searchParams.set('lat', lat);
                u.searchParams.set('lon', lon);
                window.history.replaceState({}, '', u.toString());
            }, function(err){
                document.getElementById('gps-text').textContent = '❌ Fehler: ' + err.message;
            }, {enableHighAccuracy:true, timeout:10000});
        } else {
            document.getElementById('gps-text').textContent = '❌ Geolocation nicht unterstützt';
        }
        </script>
        """, unsafe_allow_html=True)

    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")

    default_coords = st.session_state.get("gps_temp_coords")
    if default_coords and "," in default_coords:
        default_lat, default_lon = default_coords.split(",")
    elif lat_q and lon_q:
        default_lat, default_lon = lat_q, lon_q
    else:
        default_lat, default_lon = "50.43", "7.47"

    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.text_input("Breitengrad", value=default_lat)
    with col2:
        manual_lon = st.text_input("Längengrad", value=default_lon)

    if st.button("✅ Übernehmen", use_container_width=True, type="primary", key="gps_adopt"):
        use_lat = lat_q if lat_q else manual_lat
        use_lon = lon_q if lon_q else manual_lon
        st.session_state.gps_coords = f"{use_lat},{use_lon}"
        st.session_state.gps_temp_coords = f"{use_lat},{use_lon}"
        st.session_state.gps_requested = False
        st.query_params.clear()
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
            st.session_state.gps_requested = False
            st.cache_data.clear()
            st.rerun()
