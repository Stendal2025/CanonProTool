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

    col_btn, _ = st.columns([1, 3])
    if col_btn.button("📍 Standort abrufen", use_container_width=True):
        st.session_state.gps_requested = True
        st.rerun()

    if st.session_state.gps_requested:
        st.markdown("""
        <div id="gps-status" style="background:#161B22;padding:12px;border-radius:8px;text-align:center;border:1px solid #30363D;">
            <p style="color:#58A6FF;margin:0 0 12px 0;" id="gps-txt">...</p>
            <a id="gps-link" href="javascript:void(0)"
               style="display:none;padding:12px;background:#238636;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                ✅ Koordinaten übernehmen
            </a>
        </div>
        <script>
        var old=sessionStorage.getItem('gps_data');
        if(old){
            var d=JSON.parse(old);
            document.getElementById('gps-txt').textContent=d.txt;
            var link=document.getElementById('gps-link');
            link.style.display='inline-block';
            link.onclick=function(e){
                e.preventDefault();
                var u=new URL(window.location.href);
                u.searchParams.set('lat',d.lat);
                u.searchParams.set('lon',d.lon);
                window.location.href=u.toString();
            };
        } else if(!navigator.geolocation){
            document.getElementById('gps-txt').textContent='\u274C Geolocation nicht unterst\u00FCtzt';
        } else {
            document.getElementById('gps-txt').textContent='\u23F3 Standort wird ermittelt...';
            navigator.geolocation.getCurrentPosition(function(pos){
                var lat=pos.coords.latitude.toFixed(6);
                var lon=pos.coords.longitude.toFixed(6);
                document.getElementById('gps-txt').textContent='\u2705 '+lat+', '+lon+' (Ort wird gesucht...)';
                fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat='+lat+'&lon='+lon+'&zoom=10&addressdetails=1',{
                    headers:{'Accept-Language':'de','User-Agent':'CanonProTool/1.0'}
                })
                .then(function(r){return r.json()})
                .then(function(data){
                    var ort='Unbekannter Ort';
                    if(data&&data.address){
                        var a=data.address;
                        ort=a.city||a.town||a.village||a.municipality||a.county||a.state||a.country||'Unbekannter Ort';
                    }
                    var txt='\u2705 '+lat+', '+lon+' (nahe '+ort+')';
                    document.getElementById('gps-txt').textContent=txt;
                    sessionStorage.setItem('gps_data',JSON.stringify({lat:lat,lon:lon,txt:txt}));
                    var link=document.getElementById('gps-link');
                    link.style.display='inline-block';
                    link.onclick=function(e){
                        e.preventDefault();
                        var u=new URL(window.location.href);
                        u.searchParams.set('lat',lat);
                        u.searchParams.set('lon',lon);
                        window.location.href=u.toString();
                    };
                })
                .catch(function(){
                    var txt='\u2705 '+lat+', '+lon;
                    document.getElementById('gps-txt').textContent=txt;
                    sessionStorage.setItem('gps_data',JSON.stringify({lat:lat,lon:lon,txt:txt}));
                    var link=document.getElementById('gps-link');
                    link.style.display='inline-block';
                    link.onclick=function(e){
                        e.preventDefault();
                        var u=new URL(window.location.href);
                        u.searchParams.set('lat',lat);
                        u.searchParams.set('lon',lon);
                        window.location.href=u.toString();
                    };
                });
            },function(err){
                document.getElementById('gps-txt').textContent='\u274C Fehler: '+err.message;
            },{enableHighAccuracy:true,timeout:10000});
        }
        </script>
        """, unsafe_allow_html=True)

    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")
    if lat_q and lon_q:
        st.session_state.gps_coords = f"{lat_q},{lon_q}"
        st.session_state.gps_temp_coords = f"{lat_q},{lon_q}"
        st.query_params.clear()
        st.session_state.gps_requested = False
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
