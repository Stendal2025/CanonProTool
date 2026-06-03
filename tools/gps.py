import streamlit as st
import streamlit.components.v1 as components


def render_gps():
    st.header("📍 Standort automatisch erkennen")
    if "gps_coords" not in st.session_state:
        st.session_state.gps_coords = None
    if "gps_temp_coords" not in st.session_state:
        st.session_state.gps_temp_coords = None
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
                const gpsUrl = new URL(window.location.href);
                gpsUrl.searchParams.set('lat', lat);
                gpsUrl.searchParams.set('lon', lon);
                document.getElementById('gps-link').href = gpsUrl.toString();
            })
            .catch(() => {
                txt.textContent = `✅ ${lat}, ${lon}`;
                const gpsUrl = new URL(window.location.href);
                gpsUrl.searchParams.set('lat', lat);
                gpsUrl.searchParams.set('lon', lon);
                document.getElementById('gps-link').href = gpsUrl.toString();
            });
        }, err => {
            txt.textContent = `❌ Fehler: ${err.message}`;
        }, {enableHighAccuracy:true, timeout:10000});
    };
    </script>
    """
    components.html(gps_html, height=220)
    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")
    if lat_q and lon_q:
        st.session_state.gps_coords = f"{lat_q},{lon_q}"
        st.session_state.gps_temp_coords = f"{lat_q},{lon_q}"
        st.query_params.clear()
        st.success(f"✅ GPS übernommen: `{st.session_state.gps_coords}`")
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.markdown("### 📍 Koordinaten übernehmen")
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
        if st.button("🗑️ Standort löschen"):
            st.session_state.gps_coords = None
            st.session_state.gps_temp_coords = None
            st.cache_data.clear()
            st.rerun()
