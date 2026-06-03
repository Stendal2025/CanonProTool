import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def render_gps():
    st.header("📍 Standort automatisch erkennen")
    if "gps_coords" not in st.session_state:
        st.session_state.gps_coords = None
    if "gps_temp_coords" not in st.session_state:
        st.session_state.gps_temp_coords = None

    gps_html = """
<div style="padding:10px;box-sizing:border-box;font-family:sans-serif;">
<button id="gps-btn" style="padding:12px;background:#1F6FEB;color:white;border:none;border-radius:8px;cursor:pointer;width:100%;margin-bottom:10px;font-size:16px;">📍 Standort abrufen</button>
<div id="gps-res" style="display:none;background:#161B22;padding:12px;border-radius:8px;text-align:center;border:1px solid #30363D;">
<p id="gps-txt" style="color:#58A6FF;font-family:monospace;margin:0 0 12px 0;font-size:14px;"></p>
</div></div>
<script>
document.getElementById('gps-btn').onclick=function(){
var txt=document.getElementById('gps-txt');
var res=document.getElementById('gps-res');
txt.textContent='⏳ Standort wird ermittelt...';
res.style.display='block';
if(!navigator.geolocation){txt.textContent='❌ Geolocation nicht unterstützt';return;}
navigator.geolocation.getCurrentPosition(function(pos){
var lat=pos.coords.latitude.toFixed(6);
var lon=pos.coords.longitude.toFixed(6);
txt.textContent='✅ Koordinaten gefunden – unten auf "Übernehmen" klicken';
var u=new URL(window.parent.location.href);
u.searchParams.set('lat',lat);u.searchParams.set('lon',lon);
window.parent.history.replaceState({},'',u.toString());
},function(err){
txt.textContent='❌ Fehler: '+err.message;
},{enableHighAccuracy:true,timeout:10000});};
</script>"""
    components.html(gps_html, height=160)

    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")

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
        use_lat = lat_q if lat_q else manual_lat
        use_lon = lon_q if lon_q else manual_lon
        st.session_state.gps_coords = f"{use_lat},{use_lon}"
        st.session_state.gps_temp_coords = f"{use_lat},{use_lon}"
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
            st.cache_data.clear()
            st.rerun()
