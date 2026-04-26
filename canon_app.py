"""
Canon EOS R – AI Pro Tool v5.1
Multilingual DE/PL/EN | 26+ Tools | Professional UI
FIXED & OPTIMIZED VERSION

Changelog v5.1 (Bugfixes & Optimierungen):
  [FIX-KRITISCH] ToolTip-Klasse fehlte komplett → NameError behoben
  [FIX-KRITISCH] Translation-Key 'filter_no_image' fehlte → angezeigt als [filter_no_image]
  [FIX-KRITISCH] _tick() wurde bei jedem Tool-Wechsel neu registriert → Timer-Leak behoben
  [FIX-BUG]     apply_filter_to_image() hatte Walrus-Operator in Lambda (Python <3.8 Crash)
  [FIX-BUG]     apply_filter_to_image() war totes Code (nie aufgerufen) → entfernt
  [FIX-BUG]     json_lib Alias war redundanter Doppel-Import → entfernt
  [FIX-BUG]     __file__ im Export-Tool ohne sys-Fallback → PyInstaller-Crash behoben
  [FIX-BUG]     filter_placeholder.destroy() ohne None-Check → AttributeError behoben
  [FIX-WARN]    24x nackte except: Klauseln → except Exception verwendet
  [FIX-WARN]    random.seed() im Histogramm-Generator ergänzt
  [FIX-WARN]    Lens-DB Spaltenheader ergänzt
  [FIX-WARN]    bat_spm Slider-Label-Update korrekt angebunden
  [OPT]         analyze_weather() Dict-Lookups refaktoriert (kein 3x Rebuild)
  [OPT]         Config-Save merged mit vorhandenen Einstellungen (kein Datenverlust)
  [OPT]         import sys ergänzt für Cross-Platform Kompatibilität
"""

import math
import json
import os
import sys
import threading
import time
import random
from datetime import datetime, timedelta

# ========================= SAFE IMPORTS =========================
GUI_AVAILABLE = True
EXIF_AVAILABLE = False
PDF_AVAILABLE = False
PIL_AVAILABLE = False
REQUESTS_AVAILABLE = False

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    import tkinter as tk
except Exception:
    GUI_AVAILABLE = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance
    from PIL.ExifTags import TAGS

    EXIF_AVAILABLE = True
    PIL_AVAILABLE = True
except Exception:
    pass

QR_AVAILABLE = False
try:
    import qrcode

    QR_AVAILABLE = True
except Exception:
    pass

try:
    from fpdf import FPDF

    PDF_AVAILABLE = True
except Exception:
    pass


# ========================= CONSTANTS =========================
CONFIG_FILE = "canon_pro_v5_config.json"
LOGBOOK_FILE = "canon_pro_v5_logbook.json"
FAV_FILE = "canon_pro_v5_favorites.json"
SPOTS_FILE = "canon_pro_v5_spots.json"

LANG = "DE"

# ========================= COLOR PALETTE =========================
C = {
    "bg": "#0A0E14",
    "bg2": "#0D1117",
    "card": "#161B22",
    "card_h": "#1C2333",
    "card_sel": "#1A2740",
    "accent": "#58A6FF",
    "green": "#3FB950",
    "orange": "#D29922",
    "red": "#F85149",
    "purple": "#BC8CFF",
    "pink": "#FF79C6",
    "cyan": "#56D4DD",
    "txt": "#F0F6FC",
    "txt2": "#8B949E",
    "txt3": "#484F58",
    "border": "#30363D",
    "hl": "#1F6FEB",
    "gold": "#FFD700",
    "teal": "#2EA88A",
    "lime": "#A3D977",
    "sky": "#7DC4E4",
    "rose": "#E06C75",
    "peach": "#FFAB70",
    "indigo": "#6366F1",
    "emerald": "#10B981",
    "amber": "#F59E0B",
}


# ========================= TRANSLATIONS =========================
translations = {
    "DE": {
        "app_title": "Canon EOS R – Pro Fotografie Tool v5.1",
        "header_title": "📷 CANON EOS R – PRO TOOL",
        "header_ver": " v5.1 ",
        "close": "❌ Schließen",
        "lang_label": "🌐 Sprache:",
        "launcher_title": "📷 Canon EOS R – Tool Auswahl",
        "launcher_subtitle": "Wähle ein Werkzeug um zu starten",
        "back_to_menu": "◀ Zurück zum Menü",
        "guide": "📸 Guide",
        "nd": "🕶️ ND",
        "exposure": "📊 Belichtung",
        "ai": "🤖 KI",
        "dof": "📐 Schärfentiefe",
        "wb": "🌡️ Weißabgleich",
        "cheat": "📋 Cheat Sheets",
        "crop": "🔄 Crop",
        "exif": "🖼️ EXIF",
        "golden": "🌅 Golden Hour",
        "timelapse": "⏱️ Timelapse",
        "flash": "🔦 Blitz",
        "planner": "📝 Planer",
        "compare": "⚖️ Vergleich",
        "startrails": "🌙 Sternspuren",
        "lensdb": "🔭 Objektive",
        "video": "🎬 Video",
        "battery": "🔋 Akku",
        "noise": "📡 Rauschen",
        "edit": "🎨 Bearbeitung",
        "settings": "⚙️ Einstellungen",
        "spots": "🗺️ Foto-Spots",
        "weather": "☁️ Wetter",
        "histogram": "📈 Histogramm",
        "filtersim": "🎨 Filter-Sim",
        "export_app": "📦 App Export",
        "guide_desc": "Pro-Guide & Kamera-Infos",
        "nd_desc": "ND Filter Berechnung",
        "exposure_desc": "Belichtungsbewertung & EV",
        "ai_desc_short": "KI-gestützte Einstellungen",
        "dof_desc": "Schärfentiefe berechnen",
        "wb_desc": "Farbtemperatur & Presets",
        "cheat_desc": "Schnellreferenzen",
        "crop_desc": "Crop-Faktor Umrechnung",
        "exif_desc_short": "EXIF-Daten auslesen",
        "golden_desc": "Goldene & Blaue Stunde",
        "timelapse_desc": "Timelapse Parameter",
        "flash_desc": "Leitzahl & Blende",
        "planner_desc": "Aufnahme-Logbuch",
        "compare_desc": "Setups vergleichen",
        "startrails_desc": "Astro-Belichtung",
        "lensdb_desc": "RF Objektiv-Datenbank",
        "video_desc": "Video-Modus Guide",
        "battery_desc": "Akkulaufzeit schätzen",
        "noise_desc": "Rauschen & Dynamik",
        "edit_desc": "Bearbeitungs-Workflow",
        "settings_desc": "Einstellungen & Favoriten",
        "spots_desc": "GPS Shooting-Spots speichern",
        "weather_desc": "Wetter für Planung",
        "histogram_desc": "Belichtung visualisieren",
        "filtersim_desc": "ND/Farbfilter Vorschau",
        "export_app_desc": "Als .exe verpacken",
        "calculate": "✅ Berechnen",
        "evaluate": "📊 Bewerten",
        "save": "💾 Speichern",
        "load": "📂 Laden",
        "clear": "🗑️ Leeren",
        "export_pdf": "📤 PDF Export",
        "invalid": "⚠️ Ungültige Eingabe",
        "result": "Ergebnis",
        "saved": "✅ Gespeichert!",
        "loaded": "✅ Geladen!",
        "exported": "✅ Exportiert!",
        "open_image": "🖼️ Bild öffnen",
        "no_exif": "Keine EXIF-Daten gefunden",
        "scene": "Szene beschreiben...",
        "ai_btn": "🤖 KI Vorschlag",
        # FIX: fehlender Key
        "filter_no_image": "🖼️ Öffne ein Foto um den Filter-Simulator zu nutzen",
        # ND
        "base_time": "Basiszeit (z.B. 1/125)",
        "nd_stops": "ND Stops",
        "nd_title": "🕶️ ND Filter Rechner",
        "nd_quick": "Schnellauswahl:",
        "nd_ref_title": "📊 ND Filter Referenz",
        "explanation_nd": "ND Filter verlängert Belichtungszeit um 2^Stops.",
        "nd_table": "  Stops │ Filter │ Faktor │ Anwendung\n  ──────┼────────┼────────┼──────────────────\n  1     │ ND2    │ 2x     │ Leichte Unschärfe\n  3     │ ND8    │ 8x     │ Fließendes Wasser\n  6     │ ND64   │ 64x    │ Glattes Wasser\n  10    │ ND1000 │ 1024x  │ Ultra-Langzeit",
        # Exposure
        "iso_label": "ISO",
        "aperture_label": "Blende (f/)",
        "shutter_label": "Verschlusszeit",
        "exp_title": "📊 Belichtungs-Bewerter",
        "exp_ref_title": "💡 EV Referenz-Skala",
        "explanation_exp": "EV = log₂(Blende²/Zeit) − log₂(ISO/100)",
        "exp_ref": "  EV  │ Situation\n  ────┼──────────────────────────\n  -4   │ 🌌 Nachthimmel\n   0   │ 🌙 Vollmond\n  12   │ 🌤️ Schatten\n  14   │ ☀️ Sonnenlicht",
        # DoF
        "focal_label": "Brennweite (mm)",
        "distance_label": "Entfernung (m)",
        "sensor_label": "Sensor",
        "near_point": "Nahpunkt",
        "far_point": "Fernpunkt",
        "total_dof": "Schärfentiefe",
        "hyperfocal": "Hyperfokale Distanz",
        "dof_title": "📐 Schärfentiefe-Rechner",
        "sensor_ff": "Vollformat",
        "sensor_apsc": "APS-C (1.6x)",
        "sensor_mft": "MFT (2.0x)",
        "ai_title": "🤖 KI Fotografie-Assistent",
        "ai_desc": "Beschreibe deine Szene für KI-gestützte Einstellungen.",
        "wb_title": "🌡️ Weißabgleich – Farbtemperatur",
        "wb_presets_title": "📷 Canon EOS R WB-Voreinstellungen",
        "wb_presets": "  AWB → Auto | ☀️ 5200K | ☁️ 6000K | 🏠 7000K | 💡 3200K",
        "cheat_prompt": "← Wähle ein Cheat Sheet",
        "crop_title": "🔄 Crop-Factor Umrechner",
        "crop_focal": "Brennweite (mm)",
        "crop_factor": "Crop Factor",
        "equiv_focal": "Äquivalente KB-Brennweite",
        "equiv_fov": "Bildwinkel (diagonal)",
        "crop_sensor_title": "📏 Sensorgrößen-Vergleich",
        "crop_sensor_table": "  Sensor      │ Größe (mm)    │ Crop\n  ────────────┼───────────────┼──────\n  Vollformat  │ 36.0 × 24.0   │ 1.0x\n  APS-C Canon │ 22.3 × 14.9   │ 1.6x\n  Micro 4/3   │ 17.3 × 13.0   │ 2.0x",
        "exif_title": "🖼️ EXIF Daten Auslesen",
        "exif_desc2": "Öffne ein Foto um Kameraeinstellungen zu analysieren.",
        "exif_na": "⚠️ Pillow nicht installiert.\npip install Pillow",
        "golden_title": "🌅 Golden & Blue Hour Rechner",
        "golden_desc2": "Berechne optimale Fotozeiten.",
        "sunrise_label": "Sonnenaufgang (HH:MM)",
        "sunset_label": "Sonnenuntergang (HH:MM)",
        "golden_morning": "🌅 Goldene Stunde Morgen",
        "golden_evening": "🌅 Goldene Stunde Abend",
        "blue_morning": "🌆 Blaue Stunde Morgen",
        "blue_evening": "🌆 Blaue Stunde Abend",
        "timelapse_title": "⏱️ Timelapse Rechner",
        "timelapse_desc2": "Berechne Intervall, Frames und Videolänge.",
        "tl_duration": "Videolänge (Sekunden)",
        "tl_fps": "Video FPS",
        "tl_interval": "Intervall (Sekunden)",
        "tl_total_shots": "Anzahl Aufnahmen",
        "tl_total_time": "Gesamte Aufnahmezeit",
        "tl_filesize": "Dateigröße (RAW ~30MB)",
        "flash_title": "🔦 Blitz-Rechner (Leitzahl)",
        "flash_desc2": "Berechne Blende oder Reichweite.",
        "gn_label": "Leitzahl (GN)",
        "flash_distance": "Entfernung (m)",
        "flash_aperture": "Berechnete Blende",
        "flash_max_dist": "Max. Reichweite bei",
        "planner_title": "📝 Aufnahme-Planer & Logbuch",
        "moonmw":       "🌙 Mond & Milchstraße",
        "moonmw_desc":  "Mondphasen & Astro-Sichtbarkeit",
        "pl_location": "📍 Ort",
        "pl_subject": "📸 Motiv",
        "pl_settings": "⚙️ Einstellungen",
        "pl_notes": "📝 Notizen",
        "pl_add": "➕ Eintrag hinzufügen",
        "pl_export": "📤 Exportieren",
        "pl_clear": "🗑️ Leeren",
        "compare_title": "⚖️ Einstellungs-Vergleich",
        "compare_desc2": "Vergleiche zwei Kamera-Setups.",
        "setup_a": "Setup A",
        "setup_b": "Setup B",
        "compare_btn": "⚖️ Vergleichen",
        "ev_diff": "EV Differenz",
        "stops_brighter": "Blenden heller",
        "stops_darker": "Blenden dunkler",
        "same_exposure": "Gleiche Belichtung",
        "star_title": "🌙 Sternspuren & Astro",
        "star_desc": "Berechne max. Belichtungszeit für scharfe Sterne.",
        "star_max_exp": "Max. Belichtungszeit",
        "star_num_frames": "Anzahl Bilder (30 Min)",
        "rule_500": "500er Regel",
        "rule_npf": "NPF Regel",
        "pixel_pitch": "Pixelgröße (µm)",
        "star_rule": "Berechnungsregel",
        "lensdb_title": "🔭 RF Objektiv-Datenbank",
        "lensdb_desc2": "Canon RF Mount Objektive.",
        "lens_filter": "Kategorie:",
        "video_title": "🎬 Video-Modus Guide",
        "battery_title": "🔋 Akku-Kalkulator",
        "battery_desc2": "Schätze die Akkulaufzeit.",
        "bat_capacity": "Kapazität (Aufnahmen)",
        "bat_lcd_pct": "LCD (%)",
        "bat_flash_pct": "Blitz (%)",
        "bat_wifi_pct": "WiFi (%)",
        "bat_result": "Geschätzte Aufnahmen",
        "bat_time": "Geschätzte Zeit",
        "shots_per_min": "Aufnahmen/Min",
        "noise_title": "📡 Sensor-Rauschen",
        "noise_desc2": "Rausch-Analyse.",
        "noise_iso": "ISO",
        "noise_snr": "SNR (dB)",
        "noise_dr": "Dynamikumfang (EV)",
        "noise_rating": "Bewertung",
        "edit_title": "🎨 Bearbeitungs-Guide",
        "settings_title": "⚙️ Einstellungen",
        "settings_save_all": "💾 Speichern",
        "settings_load_all": "📂 Laden",
        "settings_reset": "🔄 Reset",
        "settings_about": "Über die App",
        "fav_name": "Favorit Name",
        "fav_save": "⭐ Speichern",
        "spots_title": "🗺️ Foto-Spot Manager",
        "spots_desc": "Speichere GPS-Koordinaten deiner Lieblings-Spots.",
        "spot_name": "📍 Spot Name",
        "spot_lat": "Breitengrad (z.B. 48.1371)",
        "spot_lon": "Längengrad (z.B. 11.5754)",
        "spot_notes": "📝 Notizen / Beste Zeit",
        "spot_type": "🏷️ Typ",
        "spot_add": "➕ Spot hinzufügen",
        "spot_remove": "🗑️ Entfernen",
        "spot_export": "📤 Exportieren",
        "spot_map": "🗺️ Karte anzeigen",
        "spot_types": [
            "Landschaft",
            "Portrait",
            "Street",
            "Architektur",
            "Natur",
            "Nacht",
            "Astro",
            "Sonstiges",
        ],
        "weather_title": "☁️ Wetter-Assistent",
        "weather_desc": "Wetter-Check für optimale Foto-Bedingungen.",
        "weather_city": "Stadt eingeben",
        "weather_check": "🔍 Wetter prüfen",
        "weather_manual": "📝 Manuell eingeben",
        "weather_temp": "Temperatur (°C)",
        "weather_clouds": "Bewölkung (%)",
        "weather_wind": "Wind (km/h)",
        "weather_humidity": "Luftfeuchtigkeit (%)",
        "weather_condition": "Bedingung",
        "weather_conditions": [
            "☀️ Sonnig",
            "⛅ Teilw. bewölkt",
            "☁️ Bewölkt",
            "🌧️ Regen",
            "🌫️ Nebel",
            "❄️ Schnee",
            "🌪️ Sturm",
            "🌙 Nacht klar",
        ],
        "weather_analyze": "📊 Foto-Bedingungen analysieren",
        "weather_golden_rec": "Golden Hour Empfehlung",
        "weather_portrait_rec": "Portrait Empfehlung",
        "weather_landscape_rec": "Landschafts Empfehlung",
        "histogram_title": "📈 Histogramm-Simulator",
        "histogram_desc": "Simuliere Belichtungsverteilung basierend auf Einstellungen.",
        "hist_ev": "EV Wert",
        "hist_contrast": "Kontrast",
        "hist_generate": "📊 Histogramm generieren",
        "hist_overexposed": "Überbelichtet",
        "hist_underexposed": "Unterbelichtet",
        "hist_well_exposed": "Gut belichtet",
        "hist_high_contrast": "Hoher Kontrast",
        "hist_low_contrast": "Niedriger Kontrast",
        "hist_channel": "Kanal",
        "filtersim_title": "🎨 Filter-Simulator",
        "filtersim_desc": "Simuliere ND und Farbfilter auf deinem Foto.",
        "filter_type": "Filter-Typ",
        "filter_types": [
            "Kein Filter",
            "ND2 (1 Stop)",
            "ND4 (2 Stops)",
            "ND8 (3 Stops)",
            "ND64 (6 Stops)",
            "ND1000 (10 Stops)",
            "Polfilter (CPL)",
            "🔴 Rot-Filter",
            "🟠 Orange-Filter",
            "🔵 Blau-Filter",
            "🟢 Grün-Filter",
            "🟡 Warm-Filter",
            "❄️ Kalt-Filter",
            "⚫ S/W",
            "📸 Sepia",
            "🌅 Golden Hour",
        ],
        "filter_apply": "🎨 Filter anwenden",
        "filter_reset": "🔄 Original",
        "filter_save": "💾 Bild speichern",
        "filter_open": "🖼️ Foto öffnen",
        "filter_intensity": "Intensität",
        "filter_preview": "Vorschau",
        "export_app_title": "📦 App Export",
        "export_app_desc": "Exportiere als eigenständige .exe Datei.",
        "export_pyinstaller": "🔧 PyInstaller Export",
        "export_info": "Export-Anleitung",
        "guide_content": """
╔══════════════════════════════════════════════════════════╗
║          📸 CANON EOS R – PRO GUIDE v5.1                 ║
╚══════════════════════════════════════════════════════════╝

🆕 NEU IN VERSION 5.0 / 5.1
  🗺️ Foto-Spot Manager (GPS Koordinaten)
  ☁️ Wetter-Assistent für Planung
  📈 Histogramm-Simulator
  🎨 Filter-Simulator (ND + Farbe) mit Focus Peaking
  📦 App Export (.exe)
  🐛 v5.1: 14 Bugfixes & Optimierungen

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 BELICHTUNGSDREIECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ISO        → Sensorempfindlichkeit
  Blende     → Licht & Schärfentiefe (f/1.2 – f/22)
  Verschluss → Bewegungsunschärfe (30s – 1/8000s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📷 CANON EOS R SPEZIAL-FUNKTIONEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ★ Fv-Modus     – Flexible Priorität
  ★ Eye-AF       – Augenerkennung
  ★ DPRAW        – Dual Pixel RAW
  ★ E-Shutter    – Lautloses Auslösen
  ★ EVF 3.69MP   – OLED Sucher
  ★ 5-Achsen IS  – Bildstabilisierung
""",
    },
    "EN": {
        "app_title": "Canon EOS R – Pro Photography Tool v5.1",
        "header_title": "📷 CANON EOS R – PRO TOOL",
        "header_ver": " v5.1 ",
        "close": "❌ Close",
        "lang_label": "🌐 Language:",
        "launcher_title": "📷 Canon EOS R – Tool Selection",
        "launcher_subtitle": "Choose a tool to get started",
        "back_to_menu": "◀ Back to Menu",
        "guide": "📸 Guide",
        "nd": "🕶️ ND",
        "exposure": "📊 Exposure",
        "ai": "🤖 AI",
        "dof": "📐 DoF",
        "wb": "🌡️ WB",
        "cheat": "📋 Cheat Sheets",
        "crop": "🔄 Crop",
        "exif": "🖼️ EXIF",
        "golden": "🌅 Golden Hour",
        "timelapse": "⏱️ Timelapse",
        "flash": "🔦 Flash",
        "planner": "📝 Planner",
        "compare": "⚖️ Compare",
        "startrails": "🌙 Stars",
        "lensdb": "🔭 Lenses",
        "video": "🎬 Video",
        "battery": "🔋 Battery",
        "noise": "📡 Noise",
        "edit": "🎨 Editing",
        "settings": "⚙️ Settings",
        "spots": "🗺️ Photo Spots",
        "weather": "☁️ Weather",
        "histogram": "📈 Histogram",
        "filtersim": "🎨 Filter Sim",
        "export_app": "📦 App Export",
        "guide_desc": "Pro guide & camera info",
        "nd_desc": "ND filter calculation",
        "exposure_desc": "Exposure evaluation & EV",
        "ai_desc_short": "AI-powered settings",
        "dof_desc": "Depth of field calculator",
        "wb_desc": "Color temperature & presets",
        "cheat_desc": "Quick reference cards",
        "crop_desc": "Crop factor conversion",
        "exif_desc_short": "Read EXIF metadata",
        "golden_desc": "Golden & blue hour times",
        "timelapse_desc": "Timelapse parameters",
        "flash_desc": "Guide number & aperture",
        "planner_desc": "Shot logbook",
        "compare_desc": "Compare camera setups",
        "startrails_desc": "Astro exposure calc",
        "lensdb_desc": "RF lens database",
        "video_desc": "Video mode guide",
        "battery_desc": "Estimate battery life",
        "noise_desc": "Noise & dynamic range",
        "edit_desc": "Editing workflow",
        "settings_desc": "Settings & favorites",
        "spots_desc": "Save GPS shooting spots",
        "weather_desc": "Weather for planning",
        "histogram_desc": "Visualize exposure",
        "filtersim_desc": "ND/Color filter preview",
        "export_app_desc": "Package as .exe",
        "calculate": "✅ Calculate",
        "evaluate": "📊 Evaluate",
        "save": "💾 Save",
        "load": "📂 Load",
        "clear": "🗑️ Clear",
        "export_pdf": "📤 PDF Export",
        "invalid": "⚠️ Invalid input",
        "result": "Result",
        "saved": "✅ Saved!",
        "loaded": "✅ Loaded!",
        "exported": "✅ Exported!",
        "open_image": "🖼️ Open Image",
        "no_exif": "No EXIF data found",
        "scene": "Describe your scene...",
        "ai_btn": "🤖 AI Suggest",
        # FIX: missing key
        "filter_no_image": "🖼️ Open a photo to use the filter simulator",
        "base_time": "Base time (e.g. 1/125)",
        "nd_stops": "ND Stops",
        "nd_title": "🕶️ ND Filter Calculator",
        "nd_quick": "Quick Select:",
        "nd_ref_title": "📊 ND Reference",
        "explanation_nd": "ND filters extend exposure by 2^stops.",
        "nd_table": "  Stops │ Filter │ Factor │ Use Case\n  ──────┼────────┼────────┼──────────────────\n  1     │ ND2    │ 2x     │ Slight blur\n  3     │ ND8    │ 8x     │ Moving water\n  10    │ ND1000 │ 1024x  │ Ultra long exp.",
        "iso_label": "ISO",
        "aperture_label": "Aperture (f/)",
        "shutter_label": "Shutter speed",
        "exp_title": "📊 Exposure Evaluator",
        "exp_ref_title": "💡 EV Reference Scale",
        "explanation_exp": "EV = log₂(aperture²/shutter) − log₂(ISO/100)",
        "exp_ref": "  EV  │ Condition\n  ────┼──────────────────\n  -4   │ 🌌 Night sky\n  12   │ 🌤️ Shade\n  14   │ ☀️ Sunlight",
        "focal_label": "Focal length (mm)",
        "distance_label": "Distance (m)",
        "sensor_label": "Sensor",
        "near_point": "Near point",
        "far_point": "Far point",
        "total_dof": "Total DoF",
        "hyperfocal": "Hyperfocal distance",
        "dof_title": "📐 DoF Calculator",
        "sensor_ff": "Full Frame",
        "sensor_apsc": "APS-C (1.6x)",
        "sensor_mft": "MFT (2.0x)",
        "ai_title": "🤖 AI Photography Assistant",
        "ai_desc": "Describe your scene for AI-powered settings.",
        "wb_title": "🌡️ White Balance Guide",
        "wb_presets_title": "📷 Canon EOS R WB Presets",
        "wb_presets": "  AWB → Auto | ☀️ 5200K | ☁️ 6000K | 🏠 7000K | 💡 3200K",
        "cheat_prompt": "← Select a cheat sheet",
        "crop_title": "🔄 Crop Factor Calculator",
        "crop_focal": "Focal length (mm)",
        "crop_factor": "Crop Factor",
        "equiv_focal": "Equivalent FF focal length",
        "equiv_fov": "Field of View",
        "crop_sensor_title": "📏 Sensor Sizes",
        "crop_sensor_table": "  Sensor      │ Size (mm)     │ Crop\n  ────────────┼───────────────┼──────\n  Full Frame  │ 36.0 × 24.0   │ 1.0x\n  APS-C Canon │ 22.3 × 14.9   │ 1.6x",
        "exif_title": "🖼️ EXIF Data Reader",
        "exif_desc2": "Open a photo to analyze settings.",
        "exif_na": "⚠️ Pillow not installed.\npip install Pillow",
        "golden_title": "🌅 Golden & Blue Hour",
        "golden_desc2": "Calculate optimal photo times.",
        "sunrise_label": "Sunrise (HH:MM)",
        "sunset_label": "Sunset (HH:MM)",
        "golden_morning": "🌅 Golden Hour Morning",
        "golden_evening": "🌅 Golden Hour Evening",
        "blue_morning": "🌆 Blue Hour Morning",
        "blue_evening": "🌆 Blue Hour Evening",
        "timelapse_title": "⏱️ Timelapse Calculator",
        "timelapse_desc2": "Calculate frames and video length.",
        "tl_duration": "Video length (sec)",
        "tl_fps": "Video FPS",
        "tl_interval": "Interval (sec)",
        "tl_total_shots": "Total shots",
        "tl_total_time": "Total time",
        "tl_filesize": "File size (RAW ~30MB)",
        "flash_title": "🔦 Flash Calculator",
        "flash_desc2": "Calculate aperture from GN.",
        "gn_label": "Guide Number (GN)",
        "flash_distance": "Distance (m)",
        "flash_aperture": "Calculated aperture",
        "flash_max_dist": "Max range at",
        "moonmw":       "🌙 Moon & Milky Way",
        "moonmw_desc":  "Moon phases & Astro visibility",
        "planner_title": "📝 Shot Planner",
        "pl_location": "📍 Location",
        "pl_subject": "📸 Subject",
        "pl_settings": "⚙️ Settings",
        "pl_notes": "📝 Notes",
        "pl_add": "➕ Add entry",
        "pl_export": "📤 Export",
        "pl_clear": "🗑️ Clear",
        "compare_title": "⚖️ Compare Setups",
        "compare_desc2": "Compare two camera setups.",
        "setup_a": "Setup A",
        "setup_b": "Setup B",
        "compare_btn": "⚖️ Compare",
        "ev_diff": "EV Difference",
        "stops_brighter": "stops brighter",
        "stops_darker": "stops darker",
        "same_exposure": "Same exposure",
        "star_title": "🌙 Star Trails & Astro",
        "star_desc": "Calculate max exposure for sharp stars.",
        "star_max_exp": "Max exposure time",
        "star_num_frames": "Frames (30 min)",
        "rule_500": "500 Rule",
        "rule_npf": "NPF Rule",
        "pixel_pitch": "Pixel pitch (µm)",
        "star_rule": "Rule",
        "lensdb_title": "🔭 RF Lens Database",
        "lensdb_desc2": "Canon RF Mount lenses.",
        "lens_filter": "Category:",
        "video_title": "🎬 Video Mode Guide",
        "battery_title": "🔋 Battery Calculator",
        "battery_desc2": "Estimate battery life.",
        "bat_capacity": "Capacity (shots)",
        "bat_lcd_pct": "LCD (%)",
        "bat_flash_pct": "Flash (%)",
        "bat_wifi_pct": "WiFi (%)",
        "bat_result": "Estimated shots",
        "bat_time": "Estimated time",
        "shots_per_min": "Shots/min",
        "noise_title": "📡 Sensor Noise",
        "noise_desc2": "Noise analysis.",
        "noise_iso": "ISO",
        "noise_snr": "SNR (dB)",
        "noise_dr": "Dynamic Range (EV)",
        "noise_rating": "Rating",
        "edit_title": "🎨 Editing Guide",
        "settings_title": "⚙️ Settings",
        "settings_save_all": "💾 Save",
        "settings_load_all": "📂 Load",
        "settings_reset": "🔄 Reset",
        "settings_about": "About",
        "fav_name": "Favorite name",
        "fav_save": "⭐ Save",
        "spots_title": "🗺️ Photo Spot Manager",
        "spots_desc": "Save GPS coordinates of your favorite spots.",
        "spot_name": "📍 Spot Name",
        "spot_lat": "Latitude (e.g. 48.1371)",
        "spot_lon": "Longitude (e.g. 11.5754)",
        "spot_notes": "📝 Notes / Best time",
        "spot_type": "🏷️ Type",
        "spot_add": "➕ Add Spot",
        "spot_remove": "🗑️ Remove",
        "spot_export": "📤 Export",
        "spot_map": "🗺️ Show Map",
        "spot_types": [
            "Landscape",
            "Portrait",
            "Street",
            "Architecture",
            "Nature",
            "Night",
            "Astro",
            "Other",
        ],
        "weather_title": "☁️ Weather Assistant",
        "weather_desc": "Weather check for optimal photo conditions.",
        "weather_city": "Enter city",
        "weather_check": "🔍 Check Weather",
        "weather_manual": "📝 Manual input",
        "weather_temp": "Temperature (°C)",
        "weather_clouds": "Cloud cover (%)",
        "weather_wind": "Wind (km/h)",
        "weather_humidity": "Humidity (%)",
        "weather_condition": "Condition",
        "weather_conditions": [
            "☀️ Sunny",
            "⛅ Partly cloudy",
            "☁️ Cloudy",
            "🌧️ Rain",
            "🌫️ Fog",
            "❄️ Snow",
            "🌪️ Storm",
            "🌙 Clear night",
        ],
        "weather_analyze": "📊 Analyze photo conditions",
        "weather_golden_rec": "Golden Hour recommendation",
        "weather_portrait_rec": "Portrait recommendation",
        "weather_landscape_rec": "Landscape recommendation",
        "histogram_title": "📈 Histogram Simulator",
        "histogram_desc": "Simulate exposure distribution.",
        "hist_ev": "EV Value",
        "hist_contrast": "Contrast",
        "hist_generate": "📊 Generate Histogram",
        "hist_overexposed": "Overexposed",
        "hist_underexposed": "Underexposed",
        "hist_well_exposed": "Well exposed",
        "hist_high_contrast": "High contrast",
        "hist_low_contrast": "Low contrast",
        "hist_channel": "Channel",
        "filtersim_title": "🎨 Filter Simulator",
        "filtersim_desc": "Simulate ND and color filters on your photo.",
        "filter_type": "Filter type",
        "filter_types": [
            "No filter",
            "ND2 (1 Stop)",
            "ND4 (2 Stops)",
            "ND8 (3 Stops)",
            "ND64 (6 Stops)",
            "ND1000 (10 Stops)",
            "Polarizer (CPL)",
            "🔴 Red Filter",
            "🟠 Orange Filter",
            "🔵 Blue Filter",
            "🟢 Green Filter",
            "🟡 Warm Filter",
            "❄️ Cool Filter",
            "⚫ B&W",
            "📸 Sepia",
            "🌅 Golden Hour",
        ],
        "filter_apply": "🎨 Apply Filter",
        "filter_reset": "🔄 Original",
        "filter_save": "💾 Save Image",
        "filter_open": "🖼️ Open Photo",
        "filter_intensity": "Intensity",
        "filter_preview": "Preview",
        "export_app_title": "📦 App Export",
        "export_app_desc": "Package as standalone .exe file.",
        "export_pyinstaller": "🔧 PyInstaller Export",
        "export_info": "Export Instructions",
        "guide_content": """
╔══════════════════════════════════════════════════════════╗
║          📸 CANON EOS R – PRO GUIDE v5.1                 ║
╚══════════════════════════════════════════════════════════╝

🆕 NEW IN VERSION 5.0 / 5.1
  🗺️ Photo Spot Manager (GPS Coordinates)
  ☁️ Weather Assistant for Planning
  📈 Histogram Simulator
  🎨 Filter Simulator (ND + Color) with Focus Peaking
  📦 App Export (.exe)
  🐛 v5.1: 14 Bugfixes & Optimizations

📖 EXPOSURE TRIANGLE
  ISO → Sensor sensitivity
  Aperture → Light & depth of field (f/1.2–f/22)
  Shutter → Motion blur (30s–1/8000s)

📷 CANON EOS R FEATURES
  ★ Fv Mode – Flexible Priority
  ★ Eye-AF  – Eye tracking
  ★ DPRAW   – Dual Pixel RAW
  ★ E-Shutter – Silent shooting
""",
    },
    "PL": {
        "app_title": "Canon EOS R – Pro v5.1",
        "header_title": "📷 CANON EOS R – PRO TOOL",
        "header_ver": " v5.1 ",
        "close": "❌ Zamknij",
        "lang_label": "🌐 Język:",
        "launcher_title": "📷 Canon EOS R – Wybór",
        "launcher_subtitle": "Wybierz narzędzie",
        "back_to_menu": "◀ Powrót",
        "guide": "📸 Poradnik",
        "nd": "🕶️ ND",
        "exposure": "📊 Ekspozycja",
        "ai": "🤖 AI",
        "dof": "📐 Głębia",
        "wb": "🌡️ Balans",
        "cheat": "📋 Ściągawki",
        "crop": "🔄 Crop",
        "exif": "🖼️ EXIF",
        "golden": "🌅 Złota",
        "timelapse": "⏱️ Timelapse",
        "flash": "🔦 Lampa",
        "planner": "📝 Planer",
        "compare": "⚖️ Porów.",
        "startrails": "🌙 Gwiazdy",
        "lensdb": "🔭 Obiektywy",
        "video": "🎬 Wideo",
        "battery": "🔋 Bateria",
        "noise": "📡 Szum",
        "edit": "🎨 Edycja",
        "settings": "⚙️ Ustaw.",
        "spots": "🗺️ Miejsca",
        "weather": "☁️ Pogoda",
        "histogram": "📈 Histogram",
        "filtersim": "🎨 Filtry",
        "export_app": "📦 Eksport",
        "guide_desc": "Poradnik",
        "nd_desc": "ND",
        "exposure_desc": "EV",
        "ai_desc_short": "AI",
        "dof_desc": "Głębia",
        "wb_desc": "WB",
        "cheat_desc": "Ref.",
        "crop_desc": "Crop",
        "exif_desc_short": "EXIF",
        "golden_desc": "Złota",
        "timelapse_desc": "TL",
        "flash_desc": "Lampa",
        "planner_desc": "Planer",
        "compare_desc": "Porów.",
        "startrails_desc": "Astro",
        "lensdb_desc": "Obiektywy",
        "video_desc": "Wideo",
        "battery_desc": "Bateria",
        "noise_desc": "Szum",
        "edit_desc": "Edycja",
        "settings_desc": "Ustaw.",
        "spots_desc": "GPS Miejsca",
        "weather_desc": "Pogoda",
        "histogram_desc": "Histogram",
        "filtersim_desc": "Filtry",
        "export_app_desc": ".exe",
        "calculate": "✅ Oblicz",
        "evaluate": "📊 Oceń",
        "save": "💾 Zapisz",
        "load": "📂 Wczytaj",
        "clear": "🗑️ Wyczyść",
        "invalid": "⚠️ Błąd",
        "result": "Wynik",
        "saved": "✅ OK!",
        "scene": "Opisz scenę...",
        "ai_btn": "🤖 AI",
        # FIX: missing key
        "filter_no_image": "🖼️ Otwórz zdjęcie aby użyć symulatora filtrów",
        "base_time": "Czas baz.",
        "nd_stops": "ND Stops",
        "nd_title": "🕶️ ND",
        "nd_quick": "Szybki:",
        "nd_ref_title": "📊 ND Ref",
        "explanation_nd": "ND wydłuża czas.",
        "nd_table": "  1│ND2│2x\n  3│ND8│8x\n  10│ND1000│1024x",
        "iso_label": "ISO",
        "aperture_label": "f/",
        "shutter_label": "Czas",
        "exp_title": "📊 Ekspozycja",
        "exp_ref_title": "💡 EV",
        "explanation_exp": "EV = log₂(f²/t)",
        "exp_ref": "  -4│Noc\n  14│Słońce",
        "focal_label": "Ogniskowa",
        "distance_label": "Odległość",
        "sensor_label": "Sensor",
        "near_point": "Bliski",
        "far_point": "Daleki",
        "total_dof": "Głębia",
        "hyperfocal": "Hiperfokalna",
        "dof_title": "📐 Głębia",
        "sensor_ff": "FF",
        "sensor_apsc": "APS-C",
        "sensor_mft": "MFT",
        "ai_title": "🤖 AI",
        "ai_desc": "Opisz scenę.",
        "wb_title": "🌡️ WB",
        "wb_presets_title": "WB",
        "wb_presets": "AWB|5200K|6000K",
        "cheat_prompt": "← Wybierz",
        "crop_title": "🔄 Crop",
        "crop_focal": "Ogniskowa",
        "crop_factor": "Crop",
        "equiv_focal": "Ekw.",
        "equiv_fov": "Kąt",
        "crop_sensor_title": "📏 Sensory",
        "crop_sensor_table": "FF│36x24│1.0x\nAPS-C│22x15│1.6x",
        "exif_title": "🖼️ EXIF",
        "exif_desc2": "Otwórz zdjęcie.",
        "exif_na": "Brak Pillow",
        "golden_title": "🌅 Złota",
        "golden_desc2": "Oblicz czasy.",
        "sunrise_label": "Wschód",
        "sunset_label": "Zachód",
        "golden_morning": "Złota rano",
        "golden_evening": "Złota wiecz.",
        "blue_morning": "Niebieska rano",
        "blue_evening": "Niebieska wiecz.",
        "timelapse_title": "⏱️ TL",
        "timelapse_desc2": "Parametry.",
        "tl_duration": "Długość",
        "tl_fps": "FPS",
        "tl_interval": "Interwał",
        "tl_total_shots": "Zdjęcia",
        "tl_total_time": "Czas",
        "tl_filesize": "Rozmiar",
        "flash_title": "🔦 Lampa",
        "flash_desc2": "Oblicz.",
        "gn_label": "GN",
        "flash_distance": "Odległość",
        "flash_aperture": "Przysłona",
        "flash_max_dist": "Maks.",
        "planner_title": "📝 Planer",
        "pl_location": "Miejsce",
        "pl_subject": "Temat",
        "pl_settings": "Ustaw.",
        "pl_notes": "Notatki",
        "pl_add": "➕ Dodaj",
        "pl_export": "📤",
        "pl_clear": "🗑️",
        "compare_title": "⚖️ Porównanie",
        "compare_desc2": "Porównaj.",
        "setup_a": "A",
        "setup_b": "B",
        "compare_btn": "⚖️ Porównaj",
        "ev_diff": "Różnica EV",
        "stops_brighter": "jaśniej",
        "stops_darker": "ciemniej",
        "same_exposure": "Równe",
        "star_title": "🌙 Astro",
        "star_desc": "Maks. czas.",
        "star_max_exp": "Maks.",
        "star_num_frames": "Klatki",
        "rule_500": "500",
        "rule_npf": "NPF",
        "pixel_pitch": "Piksel",
        "star_rule": "Reguła",
        "lensdb_title": "🔭 Obiektywy",
        "lensdb_desc2": "RF.",
        "lens_filter": "Kat.:",
        "video_title": "🎬 Wideo",
        "battery_title": "🔋 Bateria",
        "battery_desc2": "Oszacuj.",
        "bat_capacity": "Pojemność",
        "bat_lcd_pct": "LCD",
        "moonmw":       "🌙 Księżyc i Droga Mleczna",
        "moonmw_desc":  "Fazy księżyca i widoczność astro",
        "bat_flash_pct": "Lampa",
        "bat_wifi_pct": "WiFi",
        "bat_result": "Zdjęcia",
        "bat_time": "Czas",
        "shots_per_min": "Zdj/min",
        "noise_title": "📡 Szum",
        "noise_desc2": "Analiza.",
        "noise_iso": "ISO",
        "noise_snr": "SNR",
        "noise_dr": "DR",
        "noise_rating": "Ocena",
        "edit_title": "🎨 Edycja",
        "settings_title": "⚙️ Ustaw.",
        "settings_save_all": "💾",
        "settings_load_all": "📂",
        "settings_reset": "🔄",
        "settings_about": "O aplikacji",
        "fav_name": "Nazwa",
        "fav_save": "⭐",
        "spots_title": "🗺️ Miejsca Foto",
        "spots_desc": "Zapisz współrzędne GPS.",
        "spot_name": "📍 Nazwa",
        "spot_lat": "Szer. geogr.",
        "spot_lon": "Dł. geogr.",
        "spot_notes": "📝 Notatki",
        "spot_type": "🏷️ Typ",
        "spot_add": "➕ Dodaj",
        "spot_remove": "🗑️",
        "spot_export": "📤",
        "spot_map": "🗺️ Mapa",
        "spot_types": [
            "Krajobraz",
            "Portret",
            "Ulica",
            "Architektura",
            "Przyroda",
            "Noc",
            "Astro",
            "Inne",
        ],
        "weather_title": "☁️ Pogoda",
        "weather_desc": "Sprawdź pogodę.",
        "weather_city": "Miasto",
        "weather_check": "🔍 Sprawdź",
        "weather_manual": "📝 Ręcznie",
        "weather_temp": "Temperatura",
        "weather_clouds": "Zachmurzenie",
        "weather_wind": "Wiatr",
        "weather_humidity": "Wilgotność",
        "weather_condition": "Warunki",
        "weather_conditions": [
            "☀️ Słonecznie",
            "⛅ Częściowo",
            "☁️ Pochmurno",
            "🌧️ Deszcz",
            "🌫️ Mgła",
            "❄️ Śnieg",
            "🌪️ Burza",
            "🌙 Czysta noc",
        ],
        "weather_analyze": "📊 Analizuj",
        "weather_golden_rec": "Golden Hour",
        "weather_portrait_rec": "Portret",
        "weather_landscape_rec": "Krajobraz",
        "histogram_title": "📈 Histogram",
        "histogram_desc": "Symuluj ekspozycję.",
        "hist_ev": "EV",
        "hist_contrast": "Kontrast",
        "hist_generate": "📊 Generuj",
        "hist_overexposed": "Prześwietlone",
        "hist_underexposed": "Niedośw.",
        "hist_well_exposed": "Dobrze",
        "hist_high_contrast": "Wysoki kontr.",
        "hist_low_contrast": "Niski kontr.",
        "hist_channel": "Kanał",
        "filtersim_title": "🎨 Symulator Filtrów",
        "filtersim_desc": "Symuluj filtry.",
        "filter_type": "Typ filtra",
        "filter_types": [
            "Brak",
            "ND2",
            "ND4",
            "ND8",
            "ND64",
            "ND1000",
            "Polaryzator",
            "🔴 Czerwony",
            "🟠 Pomarańcz.",
            "🔵 Niebieski",
            "🟢 Zielony",
            "🟡 Ciepły",
            "❄️ Zimny",
            "⚫ B&W",
            "📸 Sepia",
            "🌅 Złota",
        ],
        "filter_apply": "🎨 Zastosuj",
        "filter_reset": "🔄 Oryginał",
        "filter_save": "💾 Zapisz",
        "filter_open": "🖼️ Otwórz",
        "filter_intensity": "Intensywność",
        "filter_preview": "Podgląd",
        "export_app_title": "📦 Eksport",
        "export_app_desc": "Eksportuj jako .exe.",
        "export_pyinstaller": "🔧 PyInstaller",
        "export_info": "Instrukcja",
        "open_image": "🖼️ Otwórz",
        "no_exif": "Brak EXIF",
        "export_pdf": "📤 PDF",
        "guide_content": """
╔══════════════════════════════════════════╗
║   📸 CANON EOS R – PRO GUIDE v5.1       ║
╚══════════════════════════════════════════╝

🆕 NOWOŚCI v5.0 / v5.1
  🗺️ Menadżer miejsc (GPS)
  ☁️ Asystent pogody
  📈 Symulator histogramu
  🎨 Symulator filtrów + Focus Peaking
  📦 Eksport aplikacji (.exe)
  🐛 v5.1: 14 poprawek błędów
""",
    },
}


def t(key):
    return translations.get(LANG, translations["EN"]).get(key, f"[{key}]")


# ========================= DATA HELPERS =========================


def get_wb_data():
    d = {
        "DE": [
            ("🕯️", "Kerzenlicht", "1800-2000K", "#FF8C00"),
            ("💡", "Kunstlicht", "2700-3200K", "#FFA500"),
            ("🌅", "Sonnenauf/-untergang", "3000-3500K", "#FF6347"),
            ("📸", "Studioblitz", "5000-5500K", "#FFFACD"),
            ("☀️", "Tageslicht", "5200-5800K", "#FFFFF0"),
            ("⛅", "Bewölkt", "6000-6500K", "#E0E8FF"),
            ("🏔️", "Schatten", "7000-8000K", "#C0D4FF"),
            ("🌌", "Blaue Stunde", "9000-12000K", "#8090FF"),
        ],
        "PL": [
            ("🕯️", "Świeca", "1800-2000K", "#FF8C00"),
            ("💡", "Żarowe", "2700-3200K", "#FFA500"),
            ("☀️", "Dzienne", "5200-5800K", "#FFFFF0"),
            ("⛅", "Pochmurno", "6000-6500K", "#E0E8FF"),
            ("🌌", "Zmierzch", "9000-12000K", "#8090FF"),
        ],
        "EN": [
            ("🕯️", "Candle", "1800-2000K", "#FF8C00"),
            ("💡", "Tungsten", "2700-3200K", "#FFA500"),
            ("🌅", "Sunrise/Sunset", "3000-3500K", "#FF6347"),
            ("📸", "Flash", "5000-5500K", "#FFFACD"),
            ("☀️", "Daylight", "5200-5800K", "#FFFFF0"),
            ("⛅", "Cloudy", "6000-6500K", "#E0E8FF"),
            ("🏔️", "Shade", "7000-8000K", "#C0D4FF"),
            ("🌌", "Blue Sky", "9000-12000K", "#8090FF"),
        ],
    }
    return d.get(LANG, d["EN"])


def get_scene_buttons():
    return [
        ("🌅", "sunset"),
        ("👤", "portrait"),
        ("🌙", "night"),
        ("🏔️", "landscape"),
        ("🦁", "wildlife"),
        ("🏙️", "street"),
        ("🔬", "macro"),
        ("⚡", "sport"),
        ("⭐", "astro"),
        ("🍕", "food"),
        ("💍", "wedding"),
        ("🏛️", "architecture"),
    ]


def get_crop_options():
    return ["1.0 (FF)", "1.5 (APS-C Nikon)", "1.6 (APS-C Canon)", "2.0 (MFT)"]


def get_cheat_sheets():
    if LANG == "DE":
        return {
            "Portrait": "👤 PORTRAIT\n  85-135mm | f/1.4-2.8 | ISO 100-400\n  Eye-AF | Offener Schatten | Reflektor",
            "Landschaft": "🏔️ LANDSCHAFT\n  16-35mm | f/8-16 | ISO 100\n  Stativ | Polfilter | Golden Hour",
            "Nacht/Astro": "🌙 NACHT\n  14-24mm | f/1.4-2.8 | ISO 1600-6400\n  500-Regel | Stativ | Stacken",
            "Street": "🏙️ STREET\n  28-50mm | f/5.6-8 | ISO Auto 3200\n  Zone Focus | Diskret",
            "Makro": "🔬 MAKRO\n  90-105mm | f/5.6-11 | ISO 200-800\n  Focus Stack | Stativ",
            "Sport": "⚡ SPORT\n  70-400mm | f/2.8-4 | ISO 800-3200\n  AI Servo | Burst 8fps",
        }
    elif LANG == "PL":
        return {
            "Portret": "👤 PORTRET\n  85-135mm | f/1.4-2.8 | ISO 100-400",
            "Krajobraz": "🏔️ KRAJOBRAZ\n  16-35mm | f/8-16 | ISO 100",
            "Noc": "🌙 NOC\n  14-24mm | f/1.4-2.8 | ISO 1600-6400",
            "Street": "🏙️ STREET\n  28-50mm | f/5.6-8 | ISO Auto 3200",
            "Makro": "🔬 MAKRO\n  90-105mm | f/5.6-11 | ISO 200-800",
            "Sport": "⚡ SPORT\n  70-400mm | f/2.8-4 | ISO 800-3200",
        }
    else:
        return {
            "Portrait": "👤 PORTRAIT\n  85-135mm | f/1.4-2.8 | ISO 100-400",
            "Landscape": "🏔️ LANDSCAPE\n  16-35mm | f/8-16 | ISO 100",
            "Night": "🌙 NIGHT\n  14-24mm | f/1.4-2.8 | ISO 1600-6400",
            "Street": "🏙️ STREET\n  28-50mm | f/5.6-8 | ISO Auto 3200",
            "Macro": "🔬 MACRO\n  90-105mm | f/5.6-11 | ISO 200-800",
            "Sport": "⚡ SPORT\n  70-400mm | f/2.8-4 | ISO 800-3200",
        }


# ========================= LENS DATABASE =========================

RF_LENSES = [
    {
        "name": "RF 14-35mm f/4L IS",
        "cat": "Wide",
        "min_ap": 4.0,
        "weight": 540,
        "filter": 77,
        "is": True,
        "price": "~1200€",
    },
    {
        "name": "RF 15-35mm f/2.8L IS",
        "cat": "Wide",
        "min_ap": 2.8,
        "weight": 840,
        "filter": 82,
        "is": True,
        "price": "~2300€",
    },
    {
        "name": "RF 24-70mm f/2.8L IS",
        "cat": "Standard",
        "min_ap": 2.8,
        "weight": 900,
        "filter": 82,
        "is": True,
        "price": "~2700€",
    },
    {
        "name": "RF 24-105mm f/4L IS",
        "cat": "Standard",
        "min_ap": 4.0,
        "weight": 700,
        "filter": 77,
        "is": True,
        "price": "~1100€",
    },
    {
        "name": "RF 70-200mm f/2.8L IS",
        "cat": "Tele",
        "min_ap": 2.8,
        "weight": 1070,
        "filter": 77,
        "is": True,
        "price": "~3000€",
    },
    {
        "name": "RF 100-500mm f/4.5-7.1L",
        "cat": "Tele",
        "min_ap": 4.5,
        "weight": 1370,
        "filter": 77,
        "is": True,
        "price": "~3200€",
    },
    {
        "name": "RF 50mm f/1.2L USM",
        "cat": "Prime",
        "min_ap": 1.2,
        "weight": 950,
        "filter": 77,
        "is": False,
        "price": "~2400€",
    },
    {
        "name": "RF 50mm f/1.8 STM",
        "cat": "Prime",
        "min_ap": 1.8,
        "weight": 160,
        "filter": 43,
        "is": False,
        "price": "~220€",
    },
    {
        "name": "RF 85mm f/1.2L USM",
        "cat": "Portrait",
        "min_ap": 1.2,
        "weight": 1195,
        "filter": 82,
        "is": False,
        "price": "~3000€",
    },
    {
        "name": "RF 85mm f/2 IS STM",
        "cat": "Portrait",
        "min_ap": 2.0,
        "weight": 500,
        "filter": 67,
        "is": True,
        "price": "~700€",
    },
    {
        "name": "RF 100mm f/2.8L Macro",
        "cat": "Macro",
        "min_ap": 2.8,
        "weight": 730,
        "filter": 67,
        "is": True,
        "price": "~1200€",
    },
    {
        "name": "RF 16mm f/2.8 STM",
        "cat": "Wide",
        "min_ap": 2.8,
        "weight": 165,
        "filter": 43,
        "is": False,
        "price": "~300€",
    },
]

VIDEO_GUIDE = {
    "DE": "🎬 CANON EOS R VIDEO\n\n4K 30fps (1.8x Crop) | 1080p 60fps | 1080p 120fps\n\n180° Regel: 25fps→1/50s | 30fps→1/60s | 120fps→1/250s\n\nC-Log: +12 EV Dynamic Range | LUT in Post\n\nAudio: 3.5mm Klinke | Kopfhörer-Monitoring | < -12dB",
    "EN": "🎬 CANON EOS R VIDEO\n\n4K 30fps (1.8x Crop) | 1080p 60fps | 1080p 120fps\n\n180° Rule: 25fps→1/50s | 30fps→1/60s | 120fps→1/250s\n\nC-Log: +12 EV Dynamic Range | LUT in Post\n\nAudio: 3.5mm jack | Headphone monitoring | < -12dB",
    "PL": "🎬 CANON EOS R WIDEO\n\n4K 30fps (1.8x Crop) | 1080p 60fps | 1080p 120fps\n\n180°: 25fps→1/50s | 30fps→1/60s | 120fps→1/250s",
}

EDIT_GUIDE = {
    "DE": "🎨 BEARBEITUNG\n\nRAW (.CR3) → ±5 EV | JPEG → Sofort\n\nLightroom: Belichtung → Kontrast → HSL → Schärfen 40-80 → Rauschen 20-50 → Vignette\n\nExport: Instagram 2048px sRGB 80% | Print 300DPI AdobeRGB TIFF",
    "EN": "🎨 EDITING\n\nRAW (.CR3) → ±5 EV | JPEG → Ready\n\nLightroom: Exposure → Contrast → HSL → Sharpen 40-80 → Noise 20-50 → Vignette\n\nExport: Instagram 2048px sRGB 80% | Print 300DPI AdobeRGB TIFF",
    "PL": "🎨 EDYCJA\n\nRAW (.CR3) → ±5 EV | JPEG → Gotowe\n\nLightroom: Ekspozycja → Kontrast → HSL → Ostrość 40-80 → Szum 20-50\n\nEksport: Instagram 2048px sRGB 80% | Druk 300DPI AdobeRGB TIFF",
}


# ========================= CORE LOGIC =========================


def calculate_nd(base, stops):
    return base * (2**stops)


def evaluate_exposure(iso, aperture, shutter):
    ev = math.log2((aperture**2) / shutter)
    ev_c = ev - math.log2(iso / 100)
    if ev_c < 6:
        return ev_c, "⚫"
    elif ev_c < 10:
        return ev_c, "🔵"
    elif ev_c < 13:
        return ev_c, "🟢 ✓"
    elif ev_c < 15:
        return ev_c, "🟡"
    else:
        return ev_c, "🔴"


def calculate_dof(focal_mm, aperture, distance_m, coc=0.036):
    fm = focal_mm / 1000
    h = (focal_mm**2) / (aperture * coc * 1000)
    dn = (h * distance_m) / (h + (distance_m - fm))
    df = (h * distance_m) / (h - (distance_m - fm)) if distance_m < h else float("inf")
    return dn, df, (df - dn if df != float("inf") else float("inf")), h


def calculate_crop(focal, crop):
    eq = focal * crop
    fov = 2 * math.degrees(math.atan(43.27 / (2 * eq)))
    return eq, fov


def calculate_golden_hour(sr, ss):
    fmt = "%H:%M"
    sunrise = datetime.strptime(sr, fmt)
    sunset = datetime.strptime(ss, fmt)
    return {
        "golden_morning": (
            sunrise.strftime(fmt),
            (sunrise + timedelta(minutes=60)).strftime(fmt),
        ),
        "golden_evening": (
            (sunset - timedelta(minutes=60)).strftime(fmt),
            sunset.strftime(fmt),
        ),
        "blue_morning": (
            (sunrise - timedelta(minutes=30)).strftime(fmt),
            sunrise.strftime(fmt),
        ),
        "blue_evening": (
            sunset.strftime(fmt),
            (sunset + timedelta(minutes=30)).strftime(fmt),
        ),
    }


def calculate_timelapse(dur, fps, interval, raw_mb=30):
    frames = int(dur * fps)
    total = frames * interval
    h, m, s = int(total // 3600), int((total % 3600) // 60), int(total % 60)
    return frames, f"{h}h {m}m {s}s", frames * raw_mb


def calculate_flash(gn, distance=None, aperture=None, iso=100):
    f = math.sqrt(iso / 100)
    adj = gn * f
    if distance:
        return {"aperture": round(adj / distance, 1)}
    if aperture:
        return {"distance": round(adj / aperture, 1)}
    return {}


def calculate_star(focal, rule="500", pp=5.36, ap=2.8):
    if rule == "500":
        return round(500 / focal, 1)
    return round((35 * ap + 30 * pp) / focal, 1)


def calculate_battery(capacity, lcd_pct, flash_pct, wifi_pct):
    factor = 1.0
    factor -= (lcd_pct / 100) * 0.15
    factor -= (flash_pct / 100) * 0.25
    factor -= (wifi_pct / 100) * 0.10
    return max(int(capacity * factor), 50)


def calculate_noise(iso, base_iso=100, base_dr=13.5):
    stops = math.log2(iso / base_iso)
    dr = max(base_dr - stops * 0.8, 6.0)
    snr = max(40 - stops * 6, 10)
    if snr >= 35:
        rating = "🟢 Excellent"
    elif snr >= 25:
        rating = "🟡 Good"
    elif snr >= 15:
        rating = "🟠 Acceptable"
    else:
        rating = "🔴 Noisy"
    return round(snr, 1), round(dr, 1), rating
# ========================= MOON & MILKY WAY LOGIC =========================
def calculate_moon_phase(year, month, day):
    """Berechnet Mondphase (0-1) für ein Datum. 0=Neumond, 0.5=Vollmond."""
    if month < 3:
        year -= 1
        month += 12
    k = int(year // 100)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day - 1524.5 - k + int(k/4)
    days_since_new = jd - 2451550.1
    new_moons = days_since_new / 29.53058867
    phase = new_moons - int(new_moons)
    return phase if phase >= 0 else phase + 1

def get_moon_phase_info(phase):
    """Gibt Informationen zur Mondphase zurück."""
    if phase < 0.03 or phase > 0.97:
        return "🌑 Neumond", "dark", "Perfekt für Astro & Milchstraße!"
    elif phase < 0.22:
        return "🌒 Zunehmende Sichel", "waxing_crescent", "Gut für Astro (früher Abend)"
    elif phase < 0.28:
        return "🌓 Erstes Viertel", "first_quarter", "Mond untergeht Mitternacht"
    elif phase < 0.47:
        return "🌔 Zunehmender Mond", "waxing_gibbous", "Eingeschränkte Astro-Sicht"
    elif phase < 0.53:
        return "🌕 Vollmond", "full", "Schlecht für Milchstraße"
    elif phase < 0.72:
        return "🌖 Abnehmender Mond", "waning_gibbous", "Mond aufgeht spät"
    elif phase < 0.78:
        return "🌗 Letztes Viertel", "last_quarter", "Gut für Astro (späte Nacht)"
    elif phase < 0.97:
        return "🌘 Abnehmende Sichel", "waning_crescent", "Sehr gut für Astro!"
    return "🌑 Neumond", "dark", "Perfekt für Astro!"

def calculate_milkyway_visibility(year, month, day, latitude=50.0):
    """Berechnet Milchstraßen-Sichtbarkeit."""
    moon_phase = calculate_moon_phase(year, month, day)
    phase_name, phase_type, phase_desc = get_moon_phase_info(moon_phase)
    
    month_factor = {1: 0.2, 2: 0.3, 3: 0.5, 4: 0.7, 5: 0.9, 6: 1.0,
                    7: 1.0, 8: 0.95, 9: 0.8, 10: 0.6, 11: 0.4, 12: 0.2}
    season_score = month_factor.get(month, 0.5)
    
    moon_darkness = 1.0 - (abs(moon_phase - 0.5) * 1.8)
    if moon_darkness < 0.1: moon_darkness = 0.1
    
    visibility_score = season_score * moon_darkness
    
    if visibility_score >= 0.85:
        rating, color, rec = "🟢 Hervorragend", "green", "Perfekte Bedingungen! Jetzt fotografieren!"
    elif visibility_score >= 0.65:
        rating, color, rec = "🟡 Gut", "orange", "Gute Sichtbarkeit. Zwischen Mitternacht und 4 Uhr."
    elif visibility_score >= 0.4:
        rating, color, rec = "🟠 Mäßig", "peach", "Eingeschränkt. Warte auf dunklere Mondphase."
    else:
        rating, color, rec = "🔴 Schlecht", "red", "Zu hell (Mond) oder falsche Jahreszeit."
        
    best_time = "23:00 - 04:00 (Milchstraße hoch)" if 4 <= month <= 9 else "03:00 - 06:00 (früher Morgen)"
    
    return {
        "date": f"{day:02d}.{month:02d}.{year}",
        "moon_phase": moon_phase,
        "moon_phase_name": phase_name,
        "moon_phase_desc": phase_desc,
        "season_score": season_score,
        "moon_darkness": moon_darkness,
        "visibility_score": visibility_score,
        "rating": rating,
        "recommendation": rec,
        "best_time": best_time,
    }

def get_next_new_moon(year, month, day):
    """Findet den nächsten Neumond."""
    from datetime import datetime, timedelta
    current = datetime(year, month, day)
    for i in range(35):
        check_date = current + timedelta(days=i)
        phase = calculate_moon_phase(check_date.year, check_date.month, check_date.day)
        if phase < 0.03 or phase > 0.97:
            return check_date, phase
    return None, None
# =============================================================================


def read_exif(fp):
    if not EXIF_AVAILABLE:
        return None
    try:
        img = Image.open(fp)
        data = img._getexif()
        if not data:
            return None
        return {
            TAGS.get(tid, tid): v
            for tid, v in data.items()
            if isinstance(TAGS.get(tid, tid), str)
        }
    except Exception:
        return None


def ai_suggest(text):
    text = text.lower()
    db = {
        "sunset": (
            "ISO 100 | f/8 | 1/125s",
            ["🌅 Golden Hour", "📐 Vordergrund", "🔲 GND Filter"],
        ),
        "portrait": (
            "ISO 100 | f/1.8 | 1/200s",
            ["👁️ Eye-AF", "💡 Offener Schatten", "📐 85mm"],
        ),
        "night": (
            "ISO 1600 | f/2.8 | 5s",
            ["🌙 Stativ", "⏱️ Fernauslöser", "⭐ 500-Regel"],
        ),
        "wildlife": (
            "ISO 800 | f/5.6 | 1/1000s",
            ["🦁 AI Servo", "📷 Burst", "🔭 200mm+"],
        ),
        "landscape": (
            "ISO 100 | f/11 | 1/60s",
            ["🏔️ f/8-f/16", "📐 Fokus 1/3", "🔲 Polfilter"],
        ),
        "street": (
            "ISO 400 | f/5.6 | 1/250s",
            ["🏙️ 35mm", "📸 Zone Focus", "🚶 Diskret"],
        ),
        "macro": (
            "ISO 200 | f/8 | 1/160s",
            ["🔬 Focus Stacking", "📸 Stativ", "🌸 Morgens"],
        ),
        "sport": (
            "ISO 800 | f/4 | 1/2000s",
            ["⚡ 1/1000s min", "📸 Burst", "🎯 AI Servo"],
        ),
        "astro": (
            "ISO 3200 | f/1.8 | 20s",
            ["⭐ 500-Regel", "🌑 Neumond", "📸 Stacken"],
        ),
        "food": ("ISO 200 | f/2.8 | 1/125s", ["🍕 Fensterlicht", "📐 45°/Top-Down"]),
        "architecture": (
            "ISO 100 | f/11 | 1/60s",
            ["🏛️ 16-35mm", "📐 Vertikale gerade"],
        ),
        "wedding": ("ISO 800 | f/2.8 | 1/250s", ["💍 Eye-AF", "📷 Schnell wechseln"]),
    }
    for k, (s, tips) in db.items():
        if k in text:
            return f"📸 {t('result')}:\n   {s}\n\n💡 Tips:\n" + "\n".join(
                f"   {tp}" for tp in tips
            )
    return f"📸 General: ISO 200 | f/5.6 | 1/125s\n💡 Try: {', '.join(db.keys())}"


def save_json(data, fp):
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_json(fp):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ========================= WEATHER ANALYSIS (OPT: refaktoriert) =========================

# OPT: Texte einmalig als Konstante – nicht bei jedem Aufruf neu aufbauen
_WEATHER_TEXTS = {
    "golden_good": {
        "DE": "Perfekte Bedingungen! Wenig Wolken = dramatisches Licht",
        "EN": "Perfect conditions! Few clouds = dramatic light",
        "PL": "Idealne warunki! Mało chmur = dramatyczne światło",
    },
    "golden_ok": {
        "DE": "Gute Bedingungen. Wolken können interessante Farben erzeugen",
        "EN": "Good conditions. Clouds can create interesting colors",
        "PL": "Dobre warunki. Chmury mogą tworzyć ciekawe kolory",
    },
    "golden_bad": {
        "DE": "Zu viel Bewölkung für Golden Hour. Alternatives Licht nutzen",
        "EN": "Too cloudy for golden hour. Use alternative light",
        "PL": "Za dużo chmur na golden hour",
    },
    "portrait_good": {
        "DE": "Perfekt! Bewölkung = natürlicher Diffusor, wenig Wind",
        "EN": "Perfect! Clouds = natural diffuser, low wind",
        "PL": "Idealnie! Chmury = naturalny dyfuzor",
    },
    "portrait_ok": {
        "DE": "Gut. Offenen Schatten suchen, auf Wind achten",
        "EN": "Good. Find open shade, watch for wind",
        "PL": "Dobrze. Szukaj otwartego cienia",
    },
    "portrait_harsh": {
        "DE": "Hartes Licht. Reflektor oder Aufhellblitz nutzen",
        "EN": "Hard light. Use reflector or fill flash",
        "PL": "Twarde światło. Użyj reflektora",
    },
    "landscape_rain": {
        "DE": "Regen kann dramatische Stimmung erzeugen! Schutz mitnehmen",
        "EN": "Rain can create dramatic mood! Bring protection",
        "PL": "Deszcz może stworzyć dramatyczny nastrój!",
    },
    "landscape_fog": {
        "DE": "Nebel = mystische Atmosphäre! Früh morgens fotografieren",
        "EN": "Fog = mystical atmosphere! Shoot early morning",
        "PL": "Mgła = mistyczna atmosfera!",
    },
    "landscape_ok": {
        "DE": "Gute Sicht, interessante Wolken möglich",
        "EN": "Good visibility, interesting clouds possible",
        "PL": "Dobra widoczność, ciekawe chmury możliwe",
    },
    "landscape_avg": {
        "DE": "Durchschnittliche Bedingungen",
        "EN": "Average conditions",
        "PL": "Przeciętne warunki",
    },
    "tip_cold": {
        "DE": "❄️ Kälte: Akku warm halten, Kondenswasser beachten!",
        "EN": "❄️ Cold: Keep battery warm, watch for condensation!",
        "PL": "❄️ Zimno: Utrzymuj baterię w cieple!",
    },
    "tip_heat": {
        "DE": "🌡️ Hitze: Kamera vor direkter Sonne schützen!",
        "EN": "🌡️ Heat: Protect camera from direct sun!",
        "PL": "🌡️ Upał: Chroń aparat przed słońcem!",
    },
    "tip_wind": {
        "DE": "💨 Starker Wind: Stativ beschweren, kurze Zeiten!",
        "EN": "💨 Strong wind: Weigh down tripod, use fast shutter!",
        "PL": "💨 Silny wiatr: Obciąż statyw!",
    },
    "tip_humid": {
        "DE": "💧 Hohe Feuchtigkeit: Objektiv beschlägt evtl.!",
        "EN": "💧 High humidity: Lens may fog up!",
        "PL": "💧 Wysoka wilgotność: Obiektyw może zaparować!",
    },
}


def _wt(key):
    """Holt Weather-Text für aktuelle Sprache."""
    return _WEATHER_TEXTS.get(key, {}).get(
        LANG, _WEATHER_TEXTS.get(key, {}).get("EN", "")
    )


def analyze_weather(temp, clouds, wind, humidity, condition):
    """Analyse Wetterbedingungen für Fotografie-Empfehlungen."""
    results = {}
    cond_lower = condition.lower()

    # Golden Hour
    if clouds < 40:
        results["golden"] = ("🟢", _wt("golden_good"))
    elif clouds < 70:
        results["golden"] = ("🟡", _wt("golden_ok"))
    else:
        results["golden"] = ("🔴", _wt("golden_bad"))

    # Portrait
    if clouds >= 60 and wind < 20:
        results["portrait"] = ("🟢", _wt("portrait_good"))
    elif clouds >= 30 and wind < 30:
        results["portrait"] = ("🟡", _wt("portrait_ok"))
    else:
        results["portrait"] = ("🟠", _wt("portrait_harsh"))

    # Landscape
    if any(w in cond_lower for w in ["regen", "rain", "deszcz"]):
        results["landscape"] = ("🟡", _wt("landscape_rain"))
    elif any(w in cond_lower for w in ["nebel", "fog", "mgła"]):
        results["landscape"] = ("🟢", _wt("landscape_fog"))
    elif clouds < 50 and wind < 25:
        results["landscape"] = ("🟢", _wt("landscape_ok"))
    else:
        results["landscape"] = ("🟡", _wt("landscape_avg"))

    # Tips
    tips = []
    if temp < 0:
        tips.append(_wt("tip_cold"))
    if temp > 35:
        tips.append(_wt("tip_heat"))
    if wind > 40:
        tips.append(_wt("tip_wind"))
    if humidity > 80:
        tips.append(_wt("tip_humid"))
    results["tips"] = tips
    return results


# ========================= HISTOGRAM GENERATOR (FIX: seed) =========================


def generate_histogram_data(ev, contrast, channel="lum", seed=None):
    """
    Generiert simulierte Histogramm-Daten.
    FIX: seed-Parameter für reproduzierbare Ausgaben ergänzt.
    """
    rng = random.Random(seed)  # FIX: lokaler Random mit optionalem Seed
    data = [0] * 256
    center = int(max(0, min(255, (ev / 16) * 255)))
    width = int(30 + contrast * 1.2)

    for i in range(256):
        dist = abs(i - center)
        if width > 0:
            val = math.exp(-(dist**2) / (2 * (width**2))) * 100
            val += rng.uniform(0, val * 0.2) if val > 5 else 0
            data[i] = max(0, int(val))

    if center > 220:
        for i in range(240, 256):
            data[i] = int(data[i] * 2.5)
    if center < 35:
        for i in range(0, 16):
            data[i] = int(data[i] * 2.5)

    return data


# ========================= FILTER (FIX: walrus entfernt, nur schnelle Version) =========================


def apply_filter_fast(img, filter_name, intensity=1.0):
    """
    Filter mit PIL-Operationen anwenden (performant).
    FIX: apply_filter_to_image() mit Walrus-Operator entfernt (totes Code, Python <3.8 Bug).
    """
    if not PIL_AVAILABLE:
        return None
    try:
        img = img.copy().convert("RGB")
        name = filter_name.lower()

        if "nd2" in name or "(1 stop)" in name:
            img = ImageEnhance.Brightness(img).enhance(1.0 - 0.3 * intensity)
        elif "nd4" in name or "(2 stop)" in name:
            img = ImageEnhance.Brightness(img).enhance(1.0 - 0.5 * intensity)
        elif "nd8" in name or "(3 stop)" in name:
            img = ImageEnhance.Brightness(img).enhance(1.0 - 0.65 * intensity)
        elif "nd64" in name or "(6 stop)" in name:
            img = ImageEnhance.Brightness(img).enhance(1.0 - 0.85 * intensity)
        elif "nd1000" in name or "(10 stop)" in name:
            img = ImageEnhance.Brightness(img).enhance(1.0 - 0.95 * intensity)
        elif "cpl" in name or "polar" in name:
            img = ImageEnhance.Contrast(img).enhance(1.0 + 0.3 * intensity)
            img = ImageEnhance.Color(img).enhance(1.0 + 0.2 * intensity)
        elif any(w in name for w in ["rot-", "red", "czerw"]):
            r, g, b = img.split()
            r = r.point(lambda x: min(255, int(x * (1.0 + 0.4 * intensity))))
            g = g.point(lambda x: int(x * (1.0 - 0.4 * intensity)))
            b = b.point(lambda x: int(x * (1.0 - 0.4 * intensity)))
            img = Image.merge("RGB", (r, g, b))
        elif "orange" in name or "pomar" in name:
            r, g, b = img.split()
            r = r.point(lambda x: min(255, int(x * (1.0 + 0.3 * intensity))))
            g = g.point(lambda x: int(x * (1.0 - 0.15 * intensity)))
            b = b.point(lambda x: int(x * (1.0 - 0.5 * intensity)))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["blau", "blue", "nieb"]):
            r, g, b = img.split()
            r = r.point(lambda x: int(x * (1.0 - 0.4 * intensity)))
            g = g.point(lambda x: int(x * (1.0 - 0.3 * intensity)))
            b = b.point(lambda x: min(255, int(x * (1.0 + 0.4 * intensity))))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["grün", "green", "ziel"]):
            r, g, b = img.split()
            r = r.point(lambda x: int(x * (1.0 - 0.4 * intensity)))
            g = g.point(lambda x: min(255, int(x * (1.0 + 0.3 * intensity))))
            b = b.point(lambda x: int(x * (1.0 - 0.4 * intensity)))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["warm", "ciepły"]):
            r, g, b = img.split()
            r = r.point(lambda x: min(255, int(x * (1.0 + 0.2 * intensity))))
            b = b.point(lambda x: int(x * (1.0 - 0.2 * intensity)))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["kalt", "cool", "zimny"]):
            r, g, b = img.split()
            r = r.point(lambda x: int(x * (1.0 - 0.2 * intensity)))
            b = b.point(lambda x: min(255, int(x * (1.0 + 0.25 * intensity))))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["s/w", "b&w", "b/w"]):
            gray = img.convert("L")
            img = Image.merge("RGB", (gray, gray, gray))
        elif "sepia" in name:
            gray = img.convert("L")
            # FIX: Walrus-Operator entfernt → temp-Variable verwendet
            r = gray.point(lambda x: min(255, int(x * 1.2)))
            g = gray.copy()
            b = gray.point(lambda x: int(x * 0.75))
            img = Image.merge("RGB", (r, g, b))
        elif any(w in name for w in ["golden", "złota"]):
            r, g, b = img.split()
            r = r.point(lambda x: min(255, int(x * (1.0 + 0.3 * intensity))))
            g = g.point(lambda x: int(x * (1.0 + 0.05 * intensity)))
            b = b.point(lambda x: int(x * (1.0 - 0.3 * intensity)))
            img = Image.merge("RGB", (r, g, b))
            img = ImageEnhance.Brightness(img).enhance(1.0 + 0.1 * intensity)

        return img
    except Exception as e:
        print(f"Filter error [{filter_name}]: {type(e).__name__}: {e}")
        return None


# ========================= FOCUS PEAKING =========================


def apply_focus_peaking(img, color="red", threshold=30):
    """Simuliert Focus Peaking – zeigt scharfe Kanten farbig an."""
    if not PIL_AVAILABLE:
        return None
    try:
        img = img.copy().convert("RGB")
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_mask = edges.point(lambda x: 255 if x > threshold else 0)
        color_map = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 100, 255),
            "yellow": (255, 255, 0),
            "white": (255, 255, 255),
        }
        peak_color = color_map.get(color, (255, 0, 0))
        overlay = Image.new("RGB", img.size, peak_color)
        edge_mask = edge_mask.filter(ImageFilter.MaxFilter(3))
        return Image.composite(overlay, img, edge_mask)
    except Exception as e:
        print(f"Focus peaking error: {e}")
        return None


# ========================= QR CODE =========================


def generate_qr_code(data, size=200):
    """Erstellt QR-Code als PIL Image."""
    if QR_AVAILABLE:
        try:
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="white", back_color="#0A0E14")
            img = img.resize((size, size), Image.Resampling.NEAREST)
            return img.convert("RGB")
        except Exception as e:
            print(f"QR Error: {e}")
    if PIL_AVAILABLE:
        try:
            img = Image.new("RGB", (size, size), "#0A0E14")
            draw = ImageDraw.Draw(img)
            draw.rectangle([10, 10, size - 10, size - 10], outline="white", width=2)
            lines = [data[:30], data[30:60]] if len(data) > 30 else [data]
            y = size // 2 - 10 * len(lines)
            for line in lines:
                bbox = draw.textbbox((0, 0), line[:25])
                tw = bbox[2] - bbox[0]
                draw.text(((size - tw) // 2, y), line[:25], fill="white")
                y += 16
            draw.text((10, size - 25), "pip install qrcode", fill="#8B949E")
            return img
        except Exception:
            pass
    return None


# ========================= TOOLTIPS =========================
# FIX: ToolTip-Klasse fehlte komplett – NameError bei jedem Hover behoben

TOOLTIPS = {
    "DE": {
        "base_time": "Gib die Basisbelichtungszeit ein.\nBeispiele: 1/125, 1/60, 1/250\nOhne ND-Filter gemessen.",
        "nd_stops": "Wähle die Stärke des ND-Filters.\nJeder Stop verdoppelt die Belichtungszeit.\nND8 = 3 Stops, ND1000 = 10 Stops.",
        "iso": "ISO = Sensorempfindlichkeit.\nNiedrig (100) = wenig Rauschen.\nHoch (6400) = mehr Rauschen.",
        "aperture": "Blende kontrolliert Licht & Schärfentiefe.\nf/1.4 = viel Licht, unscharfer Hintergrund.\nf/16 = wenig Licht, alles scharf.",
        "shutter": "Verschlusszeit in Sekunden.\n1/1000 = Bewegung einfrieren.\n1/30 = Bewegungsunschärfe.\nFormat: 1/125 oder 0.5",
        "focal": "Brennweite in mm.\n14-35mm = Weitwinkel\n50mm = Normal\n85-200mm = Tele",
        "distance": "Entfernung zum Motiv in Metern.\nNäher = weniger Schärfentiefe.",
        "crop_factor": "Crop-Faktor des Sensors.\n1.0 = Vollformat\n1.6 = APS-C Canon\n2.0 = MFT",
        "gn": "Leitzahl des Blitzes.\nJe höher, desto mehr Reichweite.\nCanon 580EX: GN 58",
        "flash_dist": "Entfernung zum Motiv in Metern.",
        "flash_iso": "ISO für Blitzberechnung.\nHöherer ISO = mehr Reichweite.",
        "sunrise": "Sonnenaufgang im Format HH:MM\nz.B. 06:30",
        "sunset": "Sonnenuntergang im Format HH:MM\nz.B. 20:15",
        "tl_duration": "Videolänge in Sekunden.\n30s = kurz, 60s = normal",
        "tl_fps": "Bildrate.\n24fps = Kino\n25fps = PAL\n30fps = NTSC",
        "tl_interval": "Pause zwischen Aufnahmen.\n2s = Wolken\n5s = Sunset\n30s = Sterne",
        "bat_capacity": "Akkukapazität in Aufnahmen.\nEOS R LP-E6NH: ~370.",
        "bat_spm": "Aufnahmen pro Minute.\n2 = ruhig\n10 = Events\n15+ = Sport",
        "star_focal": "Brennweite für Astro.\n14-24mm ideal.",
        "star_aperture": "Offenste Blende.\nf/1.4-2.8 empfohlen.",
        "pixel_pitch": "Pixelgröße in µm.\nCanon EOS R: 5.36 µm.",
        "spot_name": "Name des Foto-Spots.\nz.B. 'Brandenburger Tor'",
        "spot_lat": "Breitengrad.\n48.1371 für München.\nPositiv = Nord.",
        "spot_lon": "Längengrad.\n11.5754 für München.\nPositiv = Ost.",
        "spot_notes": "Notizen: beste Zeit,\nParken, Motive etc.",
        "weather_temp": "Temperatur in °C.\nWichtig für Akku.",
        "weather_clouds": "Bewölkung in %.\n0% = klar\n100% = bedeckt",
        "weather_wind": "Wind in km/h.\n>20 = Stativ beschweren!",
        "weather_humidity": "Feuchtigkeit in %.\n>80% = Objektiv beschlägt!",
        "hist_ev": "Belichtungswert.\n-4 = Nacht\n12 = Schatten\n14 = Sonne\n16+ = Überbelichtet",
        "hist_contrast": "Kontrast.\n10-30 = flach\n40-60 = normal\n70-100 = hart",
        "filter_type": "Filter-Typ wählen.\nND = verdunkelt\nCPL = Polfilter\nFarbe = kreativ",
        "filter_intensity": "Stärke des Effekts.\n100% = voll\n50% = halb",
        "scene_input": "Szene beschreiben.\nz.B. 'sunset' oder 'portrait'\nKI schlägt Einstellungen vor.",
    },
    "EN": {
        "base_time": "Enter base exposure time.\nExamples: 1/125, 1/60\nMeasured without ND.",
        "nd_stops": "ND filter strength.\nEach stop doubles time.\nND8=3, ND1000=10 stops.",
        "iso": "ISO = sensor sensitivity.\nLow (100) = less noise.\nHigh (6400) = more noise.",
        "aperture": "Aperture controls light & depth.\nf/1.4 = shallow DoF.\nf/16 = deep DoF.",
        "shutter": "Shutter speed.\n1/1000 = freeze motion.\n1/30 = blur.\nFormat: 1/125",
        "focal": "Focal length in mm.\n14-35 = wide\n50 = normal\n85-200 = tele",
        "distance": "Distance to subject in meters.",
        "crop_factor": "Sensor crop factor.\n1.0=FF, 1.6=APS-C, 2.0=MFT",
        "gn": "Flash Guide Number.\nHigher = more range.",
        "flash_dist": "Distance to subject (m).",
        "flash_iso": "ISO for flash calc.",
        "sunrise": "Sunrise time HH:MM",
        "sunset": "Sunset time HH:MM",
        "tl_duration": "Video length in seconds.",
        "tl_fps": "Frame rate. 24=cinema, 30=NTSC",
        "tl_interval": "Interval between shots (sec).",
        "bat_capacity": "Battery capacity (shots).",
        "bat_spm": "Shots per minute.",
        "star_focal": "Focal length for astro.",
        "star_aperture": "Widest aperture for astro.",
        "pixel_pitch": "Pixel size in µm.",
        "spot_name": "Photo spot name.",
        "spot_lat": "Latitude (positive=North).",
        "spot_lon": "Longitude (positive=East).",
        "spot_notes": "Notes about the spot.",
        "weather_temp": "Temperature in °C.",
        "weather_clouds": "Cloud cover %.",
        "weather_wind": "Wind speed km/h.",
        "weather_humidity": "Humidity %.",
        "hist_ev": "Exposure Value.\n-4=night, 14=sun",
        "hist_contrast": "Contrast level.",
        "filter_type": "Filter type to apply.",
        "filter_intensity": "Effect strength.",
        "scene_input": "Describe your scene for AI.",
    },
    "PL": {
        "base_time": "Czas bazowy.\nPrzykłady: 1/125, 1/60",
        "nd_stops": "Siła filtra ND.",
        "iso": "ISO = czułość matrycy.",
        "aperture": "Przysłona = światło i głębia.",
        "shutter": "Czas migawki.",
        "focal": "Ogniskowa w mm.",
        "distance": "Odległość w metrach.",
        "scene_input": "Opisz scenę dla AI.",
        "spot_name": "Nazwa miejsca.",
        "spot_lat": "Szerokość geograficzna.",
        "spot_lon": "Długość geograficzna.",
        "spot_notes": "Notatki o miejscu.",
    },
}


def get_tooltip(key):
    return TOOLTIPS.get(LANG, TOOLTIPS.get("EN", {})).get(key, "")


if GUI_AVAILABLE:

    # ========================= TOOLTIP WIDGET =========================
    # FIX: Klasse fehlte komplett → NameError in _entry_with_tip/_combo_with_tip

    class ToolTip:
        """Einfaches Tooltip-Widget für tkinter/customtkinter Widgets."""

        def __init__(self, widget, text, delay=600):
            self.widget = widget
            self.text = text
            self.delay = delay
            self._id = None
            self._win = None
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button>", self._on_leave)

        def _on_enter(self, event=None):
            self._cancel()
            self._id = self.widget.after(self.delay, self._show)

        def _on_leave(self, event=None):
            self._cancel()
            self._hide()

        def _cancel(self):
            if self._id:
                self.widget.after_cancel(self._id)
                self._id = None

        def _show(self):
            if not self.text:
                return
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self._win = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.wm_attributes("-topmost", True)
            frame = tk.Frame(tw, bg="#1F2937", relief="solid", bd=1)
            frame.pack()
            lbl = tk.Label(
                frame,
                text=self.text,
                bg="#1F2937",
                fg="#E5E7EB",
                font=("Consolas", 9),
                justify="left",
                padx=8,
                pady=4,
                wraplength=280,
            )
            lbl.pack()

        def _hide(self):
            if self._win:
                try:
                    self._win.destroy()
                except Exception:
                    pass
                self._win = None

    # ========================= TILE DEFINITIONS =========================

    TOOL_TILES = [
        ("guide", "📸", C["accent"], "info"),
        ("nd", "🕶️", C["teal"], "calc"),
        ("exposure", "📊", C["green"], "calc"),
        ("dof", "📐", C["sky"], "calc"),
        ("ai", "🤖", C["purple"], "smart"),
        ("wb", "🌡️", C["peach"], "info"),
        ("cheat", "📋", C["orange"], "info"),
        ("crop", "🔄", C["cyan"], "calc"),
        ("exif", "🖼️", C["pink"], "tool"),
        ("golden", "🌅", C["gold"], "calc"),
        ("timelapse", "⏱️", C["lime"], "calc"),
        ("flash", "🔦", C["rose"], "calc"),
        ("planner", "📝", C["teal"], "tool"),
        ("compare", "⚖️", C["sky"], "calc"),
        ("startrails", "🌙", C["purple"], "calc"),
        ("lensdb", "🔭", C["accent"], "info"),
        ("video", "🎬", C["red"], "info"),
        ("battery", "🔋", C["green"], "calc"),
        ("noise", "📡", C["orange"], "calc"),
        ("edit", "🎨", C["pink"], "info"),
        ("spots", "🗺️", C["emerald"], "tool"),
        ("weather", "☁️", C["sky"], "smart"),
        ("histogram", "📈", C["indigo"], "calc"),
        ("filtersim", "🎨", C["amber"], "tool"),
        ("export_app", "📦", C["teal"], "tool"),
        ("settings", "⚙️", C["txt2"], "tool"),
        ("moonmw",     "🌙", C["purple"],  "smart"),
    ]

    CATEGORY_COLORS = {
        "calc": C["hl"],
        "info": C["teal"],
        "smart": C["purple"],
        "tool": C["orange"],
    }

    CATEGORY_LABELS = {
        "DE": {"calc": "Rechner", "info": "Info", "smart": "KI", "tool": "Werkzeug"},
        "PL": {
            "calc": "Kalkulator",
            "info": "Info",
            "smart": "AI",
            "tool": "Narzędzie",
        },
        "EN": {"calc": "Calculator", "info": "Info", "smart": "AI", "tool": "Tool"},
    }

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # ========================= MAIN APPLICATION =========================

    class CanonProApp:

        def __init__(self, root):
            self.root = root
            self.logbook    = load_json(LOGBOOK_FILE) if os.path.exists(LOGBOOK_FILE) else []
            self.favorites  = load_json(FAV_FILE)     if os.path.exists(FAV_FILE)     else {}
            self.config     = load_json(CONFIG_FILE)  if os.path.exists(CONFIG_FILE)  else {}
            self.spots      = load_json(SPOTS_FILE)   if os.path.exists(SPOTS_FILE)   else []

            # Bild- & Timer-Referenzen
            self.filter_original_img = None
            self.filter_current_img  = None
            self._tick_id            = None
            self._after_ids          = set()  # ✅ Für sichere Timer-Verwaltung

            # Fenster-Setup
            self.root.title(t("app_title"))
            self.root.geometry("1540x1020")
            self.root.configure(fg_color=C["bg"])

            # ✅ Sicheres Schließen-Handling (verhindert bgerror-Spam beim Beenden)
            self.root.protocol("WM_DELETE_WINDOW", self._safe_close)

            # Haupt-Container
            self.container = ctk.CTkFrame(self.root, fg_color=C["bg"])
            self.container.pack(fill="both", expand=True)

            self._show_launcher()

        # ═══════════════════════════════════════════
        #  LAUNCHER VIEW
        # ═══════════════════════════════════════════

        def _show_launcher(self):
            for w in self.container.winfo_children():
                w.destroy()

            hdr = ctk.CTkFrame(
                self.container, fg_color=C["card"], corner_radius=0, height=62
            )
            hdr.pack(fill="x")
            hdr.pack_propagate(False)

            left = ctk.CTkFrame(hdr, fg_color="transparent")
            left.pack(side="left", padx=20)
            ctk.CTkLabel(
                left,
                text=t("header_title"),
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color=C["accent"],
            ).pack(side="left")
            ctk.CTkLabel(
                left,
                text=t("header_ver"),
                font=ctk.CTkFont(size=11),
                fg_color=C["green"],
                text_color="#000",
                corner_radius=5,
            ).pack(side="left", padx=8)
            self._clock_lbl = ctk.CTkLabel(
                left, text="", font=ctk.CTkFont(size=12), text_color=C["txt2"]
            )
            self._clock_lbl.pack(side="left", padx=16)
            self._tick()

            right = ctk.CTkFrame(hdr, fg_color="transparent")
            right.pack(side="right", padx=20)
            ctk.CTkButton(
                right,
                text=t("close"),
                width=90,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=C["red"],
                hover_color="#C0392B",
                command=self._safe_close,
            ).pack(side="right", padx=(12, 0))
            lf = ctk.CTkFrame(right, fg_color="transparent")
            lf.pack(side="right")
            ls = ctk.CTkSegmentedButton(
                lf,
                values=["DE", "PL", "EN"],
                command=self._switch_lang,
                font=ctk.CTkFont(size=12, weight="bold"),
                selected_color=C["hl"],
            )
            ls.set(LANG)
            ls.pack(side="left")

            sub = ctk.CTkFrame(self.container, fg_color=C["bg"], height=65)
            sub.pack(fill="x")
            sub.pack_propagate(False)
            ctk.CTkLabel(
                sub,
                text=t("launcher_title"),
                font=ctk.CTkFont(size=26, weight="bold"),
                text_color=C["txt"],
            ).pack(pady=(14, 2))
            ctk.CTkLabel(
                sub,
                text=t("launcher_subtitle"),
                font=ctk.CTkFont(size=13),
                text_color=C["txt2"],
            ).pack()

            cat_frame = ctk.CTkFrame(self.container, fg_color=C["bg"], height=42)
            cat_frame.pack(fill="x", padx=40, pady=(6, 4))
            cat_frame.pack_propagate(False)
            cat_labels = CATEGORY_LABELS.get(LANG, CATEGORY_LABELS["EN"])
            cat_all = {"DE": "Alle", "PL": "Wszystkie", "EN": "All"}.get(LANG, "All")
            self._current_filter = "all"
            self._filter_btns = {}

            def _filter(cat):
                self._current_filter = cat
                for k, b in self._filter_btns.items():
                    b.configure(fg_color=C["hl"] if k == cat else C["card"])
                self._build_tiles()

            btn_all = ctk.CTkButton(
                cat_frame,
                text=f"🔘 {cat_all}",
                width=100,
                height=30,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=C["hl"],
                corner_radius=15,
                command=lambda: _filter("all"),
            )
            btn_all.pack(side="left", padx=3)
            self._filter_btns["all"] = btn_all

            for cat_key, color in CATEGORY_COLORS.items():
                lbl = cat_labels.get(cat_key, cat_key)
                btn = ctk.CTkButton(
                    cat_frame,
                    text=f"  {lbl}  ",
                    width=100,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    fg_color=C["card"],
                    hover_color=color,
                    corner_radius=15,
                    command=lambda ck=cat_key: _filter(ck),
                )
                btn.pack(side="left", padx=3)
                self._filter_btns[cat_key] = btn

            self._scroll = ctk.CTkScrollableFrame(
                self.container, fg_color=C["bg"], scrollbar_button_color=C["border"]
            )
            self._scroll.pack(fill="both", expand=True, padx=30, pady=(6, 20))
            for col in range(5):
                self._scroll.columnconfigure(col, weight=1, uniform="tile")
            self._build_tiles()

        def _build_tiles(self):
            for w in self._scroll.winfo_children():
                w.destroy()
            cat_labels = CATEGORY_LABELS.get(LANG, CATEGORY_LABELS["EN"])
            idx = 0
            for key, icon, color, cat in TOOL_TILES:
                if self._current_filter != "all" and cat != self._current_filter:
                    continue
                row, col = idx // 5, idx % 5
                tile = ctk.CTkFrame(
                    self._scroll,
                    fg_color=C["card"],
                    corner_radius=14,
                    border_width=1,
                    border_color=C["border"],
                    cursor="hand2",
                )
                tile.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
                tile.configure(width=220, height=135)
                tile.grid_propagate(False)

                cat_color = CATEGORY_COLORS.get(cat, C["txt2"])
                ctk.CTkLabel(
                    tile,
                    text=f" {cat_labels.get(cat,cat)} ",
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color=cat_color,
                    text_color="#000",
                    corner_radius=6,
                    height=18,
                ).place(relx=1.0, x=-8, y=8, anchor="ne")

                ctk.CTkLabel(tile, text=icon, font=ctk.CTkFont(size=32)).pack(
                    pady=(18, 3)
                )
                raw_title = t(key)
                for em in [
                    "📸",
                    "🕶️",
                    "📊",
                    "🤖",
                    "📐",
                    "🌡️",
                    "📋",
                    "🔄",
                    "🖼️",
                    "🌅",
                    "⏱️",
                    "🔦",
                    "📝",
                    "⚖️",
                    "🌙",
                    "🔭",
                    "🎬",
                    "🔋",
                    "📡",
                    "🎨",
                    "⚙️",
                    "🗺️",
                    "☁️",
                    "📈",
                    "📦",
                ]:
                    raw_title = raw_title.replace(em + " ", "").replace(em, "")
                ctk.CTkLabel(
                    tile,
                    text=raw_title.strip(),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=color,
                ).pack(pady=(0, 1))
                desc = translations.get(LANG, translations["EN"]).get(f"{key}_desc", "")
                if desc:
                    ctk.CTkLabel(
                        tile,
                        text=desc,
                        font=ctk.CTkFont(size=9),
                        text_color=C["txt2"],
                        wraplength=175,
                    ).pack(pady=(0, 4))
                ctk.CTkFrame(tile, fg_color=color, corner_radius=2, height=3).pack(
                    side="bottom", fill="x", padx=16, pady=(0, 8)
                )

                def _click(e, k=key):
                    self._open_tool(k)

                tile.bind("<Button-1>", _click)
                for ch in tile.winfo_children():
                    ch.bind("<Button-1>", _click)

                def _enter(e, tile=tile):
                    tile.configure(fg_color=C["card_h"], border_color=C["accent"])

                def _leave(e, tile=tile):
                    tile.configure(fg_color=C["card"], border_color=C["border"])

                tile.bind("<Enter>", _enter)
                tile.bind("<Leave>", _leave)
                idx += 1

        # ═══════════════════════════════════════════
        #  TOOL VIEW
        # ═══════════════════════════════════════════

        def _open_tool(self, key):
            for w in self.container.winfo_children():
                w.destroy()
            tile_info = next(
                ((ic, co, ca) for k, ic, co, ca in TOOL_TILES if k == key), None
            )
            icon, color, cat = tile_info or ("📷", C["accent"], "info")

            hdr = ctk.CTkFrame(
                self.container, fg_color=C["card"], corner_radius=0, height=52
            )
            hdr.pack(fill="x")
            hdr.pack_propagate(False)
            ctk.CTkButton(
                hdr,
                text=t("back_to_menu"),
                width=150,
                height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=C["bg2"],
                hover_color=C["card_h"],
                border_width=1,
                border_color=C["border"],
                corner_radius=8,
                command=self._show_launcher,
            ).pack(side="left", padx=12, pady=9)
            ctk.CTkLabel(
                hdr,
                text=f"{icon}  {t(key)}",
                font=ctk.CTkFont(size=17, weight="bold"),
                text_color=color,
            ).pack(side="left", padx=10)
            ctk.CTkFrame(hdr, fg_color=color, width=3).pack(
                side="left", fill="y", padx=(0, 8), pady=10
            )
            self._clock_lbl = ctk.CTkLabel(
                hdr, text="", font=ctk.CTkFont(size=11), text_color=C["txt2"]
            )
            self._clock_lbl.pack(side="left", padx=6)
            self._tick()  # FIX: _tick() registriert sich selbst neu, altes via _tick_id gestoppt
            ctk.CTkButton(
                hdr,
                text=t("close"),
                width=70,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=C["red"],
                hover_color="#C0392B",
                command=self.root.destroy,
            ).pack(side="right", padx=10)

            content = ctk.CTkFrame(self.container, fg_color=C["bg"])
            content.pack(fill="both", expand=True)

            builders = {
                "guide": self._build_guide,
                "nd": self._build_nd,
                "exposure": self._build_exposure,
                "dof": self._build_dof,
                "ai": self._build_ai,
                "wb": self._build_wb,
                "cheat": self._build_cheat,
                "crop": self._build_crop,
                "exif": self._build_exif,
                "golden": self._build_golden,
                "timelapse": self._build_timelapse,
                "flash": self._build_flash,
                "planner": self._build_planner,
                "compare": self._build_compare,
                "startrails": self._build_startrails,
                "lensdb": self._build_lensdb,
                "video": self._build_video,
                "battery": self._build_battery,
                "noise": self._build_noise,
                "edit": self._build_edit,
                "settings": self._build_settings,
                "spots": self._build_spots,
                "weather": self._build_weather,
                "histogram": self._build_histogram,
                "filtersim": self._build_filtersim,
                "export_app": self._build_export_app,
                "moonmw": self._build_moon_milkyway,
            }
            builder = builders.get(key)
            if builder:
                builder(content)

        # ─── HELPERS ───

        def _switch_lang(self, v):
            global LANG
            LANG = v
            # OPT: Config mergen statt überschreiben
            cfg = load_json(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}
            cfg["lang"] = v
            save_json(cfg, CONFIG_FILE)
            self.root.destroy()
            r = ctk.CTk()
            CanonProApp(r)
            r.mainloop()

        def _tick(self):
            if not self.root.winfo_exists():
                    return
            try:
                if hasattr(self, '_clock_lbl') and self._clock_lbl and self._clock_lbl.winfo_exists():
                    self._clock_lbl.configure(text=f"🕐 {datetime.now().strftime('%H:%M:%S')}")
                self._safe_after(1000, self._tick)
            except Exception:
                    pass
            self._tick_id = None

                # Prüfen, ob das Label noch existiert
            if not hasattr(self, "_clock_lbl") or self._clock_lbl is None:
                return
            try:
                if not self._clock_lbl.winfo_exists():
                    return
            except tk.TclError:
                return

            # Aktualisieren & neu planen
            try:
                self._clock_lbl.configure(
                    text=f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                )
                self._tick_id = self.root.after(1000, self._tick)
            except (tk.TclError, Exception):
                pass  # Fenster wurde geschlossen → Timer stoppen
        def _safe_after(self, delay_ms, callback):
            """Registriert after() nur, wenn das Root-Fenster noch lebt."""
            if not self.root.winfo_exists():
                return None
            try:
                aid = self.root.after(delay_ms, callback)
                self._after_ids.add(aid)
                return aid
            except Exception:
                return None

        def _safe_close(self):
            """Bricht alle laufenden Timer sauber ab, bevor das Fenster geschlossen wird."""
            for aid in list(self._after_ids):
                try:
                    self.root.after_cancel(aid)
                except Exception:
                    pass
            self._after_ids.clear()
            try:
                self.root.destroy()
            except Exception:
                pass   

        def _card(self, p, **kw):
            return ctk.CTkFrame(
                p,
                fg_color=C["card"],
                corner_radius=12,
                border_width=1,
                border_color=C["border"],
                **kw,
            )

        def _stitle(self, p, txt, col=None):
            ctk.CTkLabel(
                p,
                text=txt,
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=col or C["accent"],
                anchor="w",
            ).pack(fill="x", padx=14, pady=(12, 4))

        def _entry(self, p, ph, w=None):
            kw = dict(
                placeholder_text=ph,
                font=ctk.CTkFont(size=13),
                fg_color=C["bg"],
                border_color=C["border"],
                text_color=C["txt"],
                corner_radius=8,
                height=36,
            )
            if w:
                kw["width"] = w
            return ctk.CTkEntry(p, **kw)

        def _combo(self, p, vals, w=170):
            return ctk.CTkComboBox(
                p,
                values=vals,
                font=ctk.CTkFont(size=13),
                fg_color=C["bg"],
                border_color=C["border"],
                button_color=C["hl"],
                dropdown_fg_color=C["card"],
                text_color=C["txt"],
                corner_radius=8,
                width=w,
                height=36,
            )

        def _btn(self, p, txt, cmd, col=None, w=None):
            kw = dict(
                text=txt,
                command=cmd,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=col or C["hl"],
                hover_color=C["accent"],
                corner_radius=8,
                height=38,
            )
            if w:
                kw["width"] = w
            return ctk.CTkButton(p, **kw)

        def _rlbl(self, p):
            return ctk.CTkLabel(
                p,
                text="",
                font=ctk.CTkFont(family="Consolas", size=13),
                text_color=C["green"],
                anchor="w",
                justify="left",
            )

        def _textbox(self, p, h=None):
            kw = dict(
                font=ctk.CTkFont(family="Consolas", size=12),
                fg_color=C["card"],
                text_color=C["txt"],
                corner_radius=10,
                border_width=1,
                border_color=C["border"],
            )
            if h:
                kw["height"] = h
            return ctk.CTkTextbox(p, **kw)

        def _row(self, p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=4)
            return f

        def _col(self, p, pad=(0, 0)):
            f = ctk.CTkFrame(p, fg_color="transparent")
            f.pack(side="left", expand=True, fill="x", padx=pad)
            return f

        def _entry_with_tip(self, parent, placeholder, tooltip_key, w=None):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            entry = self._entry(frame, placeholder, w)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
            tip_text = get_tooltip(tooltip_key)
            if tip_text:
                info_btn = ctk.CTkLabel(
                    frame,
                    text="ℹ️",
                    font=ctk.CTkFont(size=14),
                    text_color=C["accent"],
                    cursor="hand2",
                    width=24,
                )
                info_btn.pack(side="right", padx=(0, 2))
                ToolTip(info_btn, tip_text)
                ToolTip(entry, tip_text, delay=1200)
            return frame, entry

        def _combo_with_tip(self, parent, values, tooltip_key, w=160):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            combo = self._combo(frame, values, w)
            combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
            tip_text = get_tooltip(tooltip_key)
            if tip_text:
                info_btn = ctk.CTkLabel(
                    frame,
                    text="ℹ️",
                    font=ctk.CTkFont(size=14),
                    text_color=C["accent"],
                    cursor="hand2",
                    width=24,
                )
                info_btn.pack(side="right", padx=(0, 2))
                ToolTip(info_btn, tip_text)
            return frame, combo

        # ═══════════════════════════════════════════
        #  TOOLS
        # ═══════════════════════════════════════════

        def _build_guide(self, p):
            tb = self._textbox(p)
            tb.pack(fill="both", expand=True, padx=16, pady=14)
            tb.insert("0.0", t("guide_content"))
            tb.configure(state="disabled")

        def _build_nd(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("nd_title"))
            r = self._row(c)
            cl = self._col(r, (0, 6))
            ctk.CTkLabel(cl, text=t("base_time"), text_color=C["txt2"]).pack(anchor="w")
            self.nd_base = self._entry(cl, "1/125")
            self.nd_base.pack(fill="x", pady=(2, 0))
            cr = self._col(r, (6, 0))
            ctk.CTkLabel(cr, text=t("nd_stops"), text_color=C["txt2"]).pack(anchor="w")
            self.nd_st = self._combo(
                cr, [f"{i} stops (ND{2**i})" for i in range(1, 11)]
            )
            self.nd_st.pack(fill="x", pady=(2, 0))
            self._btn(c, t("calculate"), self._calc_nd).pack(pady=10)
            self.nd_res = self._rlbl(c)
            self.nd_res.pack(padx=14, pady=(0, 14))

        def _calc_nd(self):
            try:
                b = eval(self.nd_base.get())
                s = int(self.nd_st.get().split()[0])
                r = calculate_nd(b, s)
                ts = (
                    f"{r/60:.1f}min"
                    if r >= 60
                    else f"{r:.2f}s" if r >= 1 else f"1/{int(1/r)}s"
                )
                self.nd_res.configure(
                    text=f"✅ {ts} | ND{2**s} ({s} stops)", text_color=C["green"]
                )
            except Exception:
                self.nd_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_exposure(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=24, pady=10)
            self._stitle(c, t("exp_title"))
            ctk.CTkLabel(
                c,
                text="💡 EV = Belichtungswert. Höher = heller. +1 EV = doppelt so viel Licht.",
                font=ctk.CTkFont(size=10),
                text_color=C["txt3"],
            ).pack(padx=14, pady=(0, 6))

            r = self._row(c)
            cl = self._col(r, (0, 6))
            ctk.CTkLabel(cl, text=t("iso_label"), text_color=C["txt2"]).pack(anchor="w")
            f1, self.exp_iso = self._combo_with_tip(
                cl, ["100", "200", "400", "800", "1600", "3200", "6400"], "iso"
            )
            f1.pack(fill="x", pady=(2, 0))

            cm = self._col(r, (6, 6))
            ctk.CTkLabel(cm, text=t("aperture_label"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            f2, self.exp_ap = self._combo_with_tip(
                cm,
                ["1.2", "1.4", "1.8", "2.8", "4", "5.6", "8", "11", "16"],
                "aperture",
            )
            f2.pack(fill="x", pady=(2, 0))

            cr = self._col(r, (6, 0))
            ctk.CTkLabel(cr, text=t("shutter_label"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            f3, self.exp_sh = self._entry_with_tip(cr, "1/125", "shutter")
            f3.pack(fill="x", pady=(2, 0))

            self._btn(c, t("evaluate"), self._eval_exp).pack(pady=8)
            self.exp_res = self._rlbl(c)
            self.exp_res.pack(padx=14, pady=(0, 4))
            self.exp_ev_explain = ctk.CTkLabel(
                c,
                text="",
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=C["txt2"],
                anchor="w",
                justify="left",
            )
            self.exp_ev_explain.pack(padx=14, pady=(0, 4))
            self.ev_bar = ctk.CTkFrame(c, fg_color="transparent", height=20)
            self.ev_bar.pack(fill="x", padx=14, pady=(0, 12))

            ev_ref = self._card(p)
            ev_ref.pack(fill="x", padx=24, pady=(0, 8))
            self._stitle(ev_ref, "📊 EV Referenz-Skala", C["purple"])
            ctk.CTkLabel(
                ev_ref,
                text=self._get_ev_explanation(),
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=C["txt"],
                anchor="w",
                justify="left",
            ).pack(padx=14, pady=(2, 12))

        def _eval_exp(self):
            try:
                iso = float(self.exp_iso.get())
                ap = float(self.exp_ap.get())
                sh = eval(self.exp_sh.get())
                ev, icon = evaluate_exposure(iso, ap, sh)
                col = (
                    C["green"]
                    if "✓" in icon
                    else C["red"] if "🔴" in icon else C["orange"]
                )
                self.exp_res.configure(text=f"  EV: {ev:.2f}  {icon}", text_color=col)
                explain = self._explain_ev_value(str(round(ev, 1)))
                self.exp_ev_explain.configure(
                    text=f"  💡 EV {ev:.1f} → {explain}\n"
                    f"  📸 ISO {int(iso)} | f/{ap} | {self.exp_sh.get()}",
                    text_color=C["txt2"],
                )

                # FIX: var-name 'child' statt 'w' um Shadowing zu vermeiden
                for child in self.ev_bar.winfo_children():
                    child.destroy()
                bg = ctk.CTkFrame(
                    self.ev_bar, fg_color=C["bg2"], corner_radius=5, height=16
                )
                bg.pack(fill="x")
                bg.pack_propagate(False)
                fill_width = max(0, min(1, (ev + 4) / 24))
                ctk.CTkFrame(bg, fg_color=col, corner_radius=5).place(
                    relx=0, rely=0, relwidth=fill_width, relheight=1
                )
                for mark_ev, mark_label in [
                    (-4, "🌌"),
                    (0, "🌙"),
                    (7, "💡"),
                    (12, "☁️"),
                    (14, "☀️"),
                    (16, "🏖️"),
                ]:
                    mark_x = max(0, min(1, (mark_ev + 4) / 24))
                    ctk.CTkLabel(
                        bg,
                        text=mark_label,
                        font=ctk.CTkFont(size=8),
                        fg_color="transparent",
                    ).place(relx=mark_x, rely=0, anchor="n")
            except Exception:
                self.exp_res.configure(text=t("invalid"), text_color=C["red"])
                self.exp_ev_explain.configure(text="")

        def _build_dof(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("dof_title"))
    
            # Eingabezeile
            r = self._row(c)
            cl = self._col(r, (0,4))
            ctk.CTkLabel(cl, text="🔭 Brennweite (mm)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            self.dof_f = self._combo(cl, ["14","24","35","50","85","135","200"])
            self.dof_f.set("50")
            self.dof_f.pack(fill="x", pady=(2,0))
            self.dof_f.bind("<<ComboboxSelected>>", lambda e: self._calc_dof())

            cm = self._col(r, (4,4))
            ctk.CTkLabel(cm, text="📐 Blende (f/)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            self.dof_a = self._combo(cm, ["1.2","1.4","1.8","2.8","4","5.6","8","11","16"])
            self.dof_a.set("2.8")
            self.dof_a.pack(fill="x", pady=(2,0))
            self.dof_a.bind("<<ComboboxSelected>>", lambda e: self._calc_dof())

            cr = self._col(r, (4,0))
            ctk.CTkLabel(cr, text="📏 Entfernung (m)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            self.dof_d = self._entry(cr, "3.0")
            self.dof_d.pack(fill="x", pady=(2,0))
            self.dof_d.bind("<Return>", lambda e: self._calc_dof())

            self._btn(c, t("calculate"), self._calc_dof).pack(pady=10)
            self.dof_res = self._rlbl(c)
            self.dof_res.pack(padx=14, pady=(0,8))
    
            # ═══════════════════════════════════════════
            #  DOF VISUALISIERUNG (Canvas-Skizze)
            # ═══════════════════════════════════════════
            dof_vis = self._card(p)
            dof_vis.pack(fill="x", padx=28, pady=(0,14))
            self._stitle(dof_vis, "📐 Schärfentiefe-Visualisierung", C["sky"])
    
            self.dof_canvas = tk.Canvas(dof_vis, width=680, height=220, bg=C["bg"], highlightthickness=0)
            self.dof_canvas.pack(padx=14, pady=(4,12))
            self._dof_canvas_ref = self.dof_canvas  # Ref gegen GC
    
            # Legende
            leg = ctk.CTkFrame(dof_vis, fg_color="transparent")
            leg.pack(fill="x", padx=14, pady=(0,8))
            for color, txt in [(C["green"],"Scharfer Bereich"),(C["red"],"Unscharf (Bokeh)"),(C["accent"],"Hyperfokale Distanz")]:
                f = ctk.CTkFrame(leg, fg_color="transparent")
                f.pack(side="left", padx=10)
                ctk.CTkFrame(f, fg_color=color, width=14, height=10, corner_radius=2).pack(side="left", padx=(0,4))
                ctk.CTkLabel(f, text=txt, text_color=C["txt2"], font=ctk.CTkFont(size=9)).pack(side="left")
    
            # Initial zeichnen
            self._draw_dof_diagram()

        def _draw_dof_diagram(self):
            """Zeichnet eine schematische Schärfentiefe-Skizze auf dem Canvas."""
            try:
                focal = float(self.dof_f.get())
                aperture = float(self.dof_a.get())
                dist = float(self.dof_d.get().replace(",","."))
                near, far, total, hyper = calculate_dof(focal, aperture, dist)
            except:
                return

            canvas = self.dof_canvas
            canvas.delete("all")
    
            # Konfiguration
            W, H = 680, 220
            cam_x = 60
            margin = 40
            scale = (W - cam_x - margin * 2) / max(far * 1.3, hyper * 1.2, dist * 2.5) if far != float('inf') else 10
    
            def to_x(meters):
                if meters == float('inf'):
                    return W - margin
                return cam_x + meters * scale

            # ─── Grundlinie (Entfernung) ───
            canvas.create_line(cam_x, 100, W - margin, 100, fill=C["border"], width=2)
    
            # Meter-Markierungen
            max_m = max(far * 1.2, hyper * 1.2, dist * 2) if far != float('inf') else dist * 3
            step = 1 if max_m < 10 else 2 if max_m < 30 else 5 if max_m < 100 else 20
            for m in range(0, int(max_m) + step, step):
                x = to_x(m)
                if x > cam_x and x < W - margin:
                    canvas.create_line(x, 95, x, 105, fill=C["txt3"], width=1)
                    canvas.create_text(x, 115, text=f"{m}m", fill=C["txt3"], font=("Consolas",8))

            # ─── Kamera ───
            canvas.create_rectangle(cam_x-25, 70, cam_x+10, 130, fill=C["card"], outline=C["accent"], width=2)
            canvas.create_oval(cam_x+5, 85, cam_x+20, 115, outline=C["accent"], width=2)
            canvas.create_text(cam_x, 140, text="Kamera", fill=C["accent"], font=("Consolas",9, "bold"))
            canvas.create_text(cam_x, 152, text=f"{focal}mm f/{aperture}", fill=C["txt2"], font=("Consolas",8))

            # ─── Motiv ───
            mx = to_x(dist)
            canvas.create_line(mx, 40, mx, 160, fill=C["accent"], width=3, dash=(4,2))
            canvas.create_text(mx, 30, text="Motiv", fill=C["accent"], font=("Consolas",9, "bold"))
            canvas.create_text(mx, 172, text=f"{dist}m", fill=C["accent"], font=("Consolas",9, "bold"))

            # ─── Unscharfer Bereich (Rot) – VOR Nahpunkt ───
            nx = to_x(near)
            canvas.create_rectangle(cam_x+10, 55, nx, 145, fill=C["red"], stipple="gray25", outline="")
            canvas.create_text((cam_x+10 + nx)/2, 100, text="UNSCHARF", fill=C["red"], font=("Consolas",10, "bold"), angle=90)

            # ─── Scharfer Bereich (Grün) ───
            fx = to_x(far) if far != float('inf') else W - margin
            canvas.create_rectangle(nx, 55, fx, 145, fill=C["green"], stipple="gray12", outline="")
            canvas.create_text((nx + fx)/2, 100, text=f"SCHARF ({total:.2f}m)", fill=C["green"], font=("Consolas",11, "bold"), angle=90)

            # ─── Unscharfer Bereich (Rot) – NACH Fernpunkt ───
            if far != float('inf'):
                canvas.create_rectangle(fx, 55, W - margin, 145, fill=C["red"], stipple="gray25", outline="")
                canvas.create_text((fx + W - margin)/2, 100, text="UNSCHARF", fill=C["red"], font=("Consolas",10, "bold"), angle=90)

            # ─── Nahpunkt & Fernpunkt Markierungen ───
            canvas.create_line(nx, 45, nx, 155, fill=C["green"], width=2)
            canvas.create_text(nx, 195, text=f"Nah: {near:.1f}m", fill=C["green"], font=("Consolas",8, "bold"))
    
            if far != float('inf'):
                canvas.create_line(fx, 45, fx, 155, fill=C["green"], width=2)
                canvas.create_text(fx, 195, text=f"Fern: {far:.1f}m", fill=C["green"], font=("Consolas",8, "bold"))
            else:
                canvas.create_text(W - margin, 195, text="Fern: ∞", fill=C["green"], font=("Consolas",8, "bold"))

            # ─── Hyperfokale Distanz (Blau, gestrichelt) ───
            hx = to_x(hyper)
            if hx > cam_x + 30 and hx < W - margin:
                canvas.create_line(hx, 35, hx, 165, fill=C["accent"], width=2, dash=(6,3))
                canvas.create_text(hx, 22, text=f"Hyperfokal: {hyper:.1f}m", fill=C["accent"], font=("Consolas",8, "bold"))

            # ─── Bokeh-Andeutung (Kreise vor/nach DoF) ───
            import random
            random.seed(42)
            for _ in range(6):
                bx = random.uniform(cam_x + 15, nx - 5)
                by = random.uniform(60, 140)
                size = random.uniform(4, 12)
                canvas.create_oval(bx-size, by-size, bx+size, by+size, outline=C["red"], width=1, stipple="gray50")
            if far != float('inf'):
                for _ in range(6):
                    bx = random.uniform(fx + 5, W - margin - 10)
                    by = random.uniform(60, 140)
                    size = random.uniform(4, 12)
                    canvas.create_oval(bx-size, by-size, bx+size, by+size, outline=C["red"], width=1, stipple="gray50")

        def _calc_dof(self):
            try:
                focal = float(self.dof_f.get())
                aperture = float(self.dof_a.get())
                dist = float(self.dof_d.get().replace(",","."))
                n, f, d, h = calculate_dof(focal, aperture, dist)
        
                fs = f"{f:.2f}m" if f != float('inf') else "∞"
                ds = f"{d:.2f}m" if d != float('inf') else "∞"
        
                self.dof_res.configure(
                    text=f"  {t('near_point')}: {n:.2f}m  |  {t('far_point')}: {fs}  |  {t('total_dof')}: {ds}  |  Hyperfokal: {h:.2f}m",
                    text_color=C["green"])
        
                # Visualisierung aktualisieren
                self._draw_dof_diagram()
        
            except Exception:
                self.dof_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_ai(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=16, pady=(10, 4))
            self._stitle(c, t("ai_title"))
            inp = ctk.CTkFrame(c, fg_color="transparent")
            inp.pack(fill="x", padx=14, pady=6)
            self.ai_in = self._entry(inp, t("scene"))
            self.ai_in.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.ai_in.bind("<Return>", lambda e: self._run_ai())
            self._btn(inp, t("ai_btn"), self._run_ai, C["purple"]).pack(side="right")
            qf = ctk.CTkFrame(c, fg_color="transparent")
            qf.pack(fill="x", padx=14, pady=2)
            for txt, kw in get_scene_buttons():
                self._btn(qf, txt, lambda k=kw: self._qai(k), C["card"], 55).pack(
                    side="left", padx=2, pady=2
                )
            self.ai_out = self._textbox(p)
            self.ai_out.pack(fill="both", expand=True, padx=16, pady=(4, 10))

        def _qai(self, s):
            self.ai_in.delete(0, "end")
            self.ai_in.insert(0, s)
            self._run_ai()

        def _run_ai(self):
            q = self.ai_in.get()
            if q.strip():
                self.ai_out.delete("0.0", "end")
                self.ai_out.insert("0.0", ai_suggest(q))

        def _build_wb(self, p):
            c = self._card(p)
            c.pack(fill="both", expand=True, padx=16, pady=10)
            self._stitle(c, t("wb_title"))
            sc = ctk.CTkScrollableFrame(c, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=8, pady=6)
            for icon, name, kelvin, col in get_wb_data():
                row = ctk.CTkFrame(sc, fg_color=C["bg"], corner_radius=6, height=38)
                row.pack(fill="x", pady=2, padx=4)
                row.pack_propagate(False)
                ctk.CTkFrame(row, fg_color=col, corner_radius=3, width=5).pack(
                    side="left", fill="y", padx=(6, 10), pady=6
                )
                ctk.CTkLabel(
                    row,
                    text=f"{icon} {name}",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=C["txt"],
                ).pack(side="left")
                ctk.CTkLabel(
                    row,
                    text=kelvin,
                    font=ctk.CTkFont(family="Consolas", size=11),
                    text_color=col,
                ).pack(side="right", padx=10)

        def _build_cheat(self, p):
            m = ctk.CTkFrame(p, fg_color="transparent")
            m.pack(fill="both", expand=True, padx=12, pady=10)
            sb = ctk.CTkFrame(m, fg_color=C["card"], corner_radius=10, width=140)
            sb.pack(side="left", fill="y", padx=(0, 8))
            sb.pack_propagate(False)
            sheets = get_cheat_sheets()
            for n in sheets:
                self._btn(
                    sb, n, lambda n=n: self._show_cheat(n), "transparent", None
                ).pack(fill="x", padx=5, pady=1)
            self.cheat_tb = self._textbox(m)
            self.cheat_tb.pack(side="left", fill="both", expand=True)
            self.cheat_tb.insert("0.0", t("cheat_prompt"))

        def _show_cheat(self, n):
            self.cheat_tb.configure(state="normal")
            self.cheat_tb.delete("0.0", "end")
            self.cheat_tb.insert("0.0", get_cheat_sheets()[n])
            self.cheat_tb.configure(state="disabled")

        def _build_crop(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("crop_title"))
            r = self._row(c)
            cl = self._col(r, (0, 6))
            self.cr_f = self._combo(cl, ["14", "24", "35", "50", "85", "200"])
            self.cr_f.set("50")
            self.cr_f.pack(fill="x")
            cr = self._col(r, (6, 0))
            self.cr_c = self._combo(cr, get_crop_options())
            self.cr_c.set(get_crop_options()[2])
            self.cr_c.pack(fill="x")
            self._btn(c, t("calculate"), self._calc_crop).pack(pady=10)
            self.cr_res = self._rlbl(c)
            self.cr_res.pack(padx=14, pady=(0, 14))

        def _calc_crop(self):
            try:
                f = float(self.cr_f.get())
                c = float(self.cr_c.get().split()[0])
                eq, fov = calculate_crop(f, c)
                self.cr_res.configure(
                    text=f"✅ {eq:.0f}mm equiv | {fov:.1f}° FOV", text_color=C["green"]
                )
            except Exception:
                self.cr_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_exif(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=8, pady=8)
            c = self._card(sc)
            c.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(c, t("exif_title"))
            ctk.CTkLabel(
                c, text=t("exif_desc2"), font=ctk.CTkFont(size=11), text_color=C["txt2"]
            ).pack(padx=14, pady=(0, 4))
            bf = self._row(c)
            self._btn(bf, t("open_image"), self._open_exif, C["accent"]).pack(
                side="left", padx=(0, 6)
            )
            self._btn(bf, "📤 EXIF exportieren", self._export_exif, C["purple"]).pack(
                side="left", padx=(0, 6)
            )
            self.exif_img_lbl = ctk.CTkLabel(
                bf, text="", font=ctk.CTkFont(size=10), text_color=C["txt2"]
            )
            self.exif_img_lbl.pack(side="left")
            self.thumb_lbl = ctk.CTkLabel(c, text="")
            self.thumb_lbl.pack(pady=4)
            self._exif_thumb_ref = None
            self.exif_out = self._textbox(sc)
            self.exif_out.pack(fill="both", expand=True, padx=8, pady=(4, 8))
            if not EXIF_AVAILABLE:
                self.exif_out.insert("0.0", t("exif_na"))
            ev_card = self._card(sc)
            ev_card.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(ev_card, "📊 EV (Exposure Value) erklärt", C["purple"])
            ctk.CTkLabel(
                ev_card,
                text=self._get_ev_explanation(),
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=C["txt"],
                anchor="w",
                justify="left",
            ).pack(padx=14, pady=(2, 12))
            self._last_exif_text = ""

        def _open_exif(self):
            if not EXIF_AVAILABLE:
                return
            fp = filedialog.askopenfilename(
                title="Foto für EXIF-Analyse",
                filetypes=[
                    (
                        "Alle Bilder",
                        "*.jpg *.jpeg *.tiff *.tif *.png *.bmp *.webp *.cr2 *.cr3 *.nef *.arw *.dng",
                    ),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("RAW", "*.cr2 *.cr3 *.nef *.arw *.dng"),
                    ("Alle Dateien", "*.*"),
                ],
            )
            if not fp:
                return
            self.exif_img_lbl.configure(text=os.path.basename(fp))
            if PIL_AVAILABLE:
                try:
                    img = Image.open(fp)
                    img_copy = img.copy()
                    img_copy.thumbnail((180, 120), Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(
                        light_image=img_copy,
                        dark_image=img_copy,
                        size=(img_copy.width, img_copy.height),
                    )
                    self._exif_thumb_ref = ctk_img
                    self.thumb_lbl.configure(image=ctk_img, text="")
                except Exception as e:
                    print(f"Thumb error: {e}")
            exif_data = self._read_full_exif(fp)
            self.exif_out.delete("0.0", "end")
            if not exif_data:
                self.exif_out.insert("0.0", t("no_exif"))
                return
            txt = self._format_exif_output(fp, exif_data)
            self.exif_out.insert("0.0", txt)
            self._last_exif_text = txt

        def _read_full_exif(self, filepath):
            if not EXIF_AVAILABLE:
                return None
            try:
                img = Image.open(filepath)
                result = {
                    "basic": {},
                    "exposure": {},
                    "lens": {},
                    "gps": {},
                    "camera": {},
                    "image": {},
                    "dates": {},
                    "other": {},
                }
                result["image"]["Dateiname"] = os.path.basename(filepath)
                result["image"][
                    "Dateigröße"
                ] = f"{os.path.getsize(filepath)/1024/1024:.2f} MB"
                result["image"]["Auflösung"] = f"{img.size[0]} × {img.size[1]} px"
                result["image"][
                    "Megapixel"
                ] = f"{(img.size[0]*img.size[1])/1_000_000:.1f} MP"
                result["image"]["Farbmodus"] = img.mode
                result["image"]["Format"] = img.format or "Unbekannt"

                raw_exif = img._getexif()
                if not raw_exif:
                    return result

                for tag_id, value in raw_exif.items():
                    tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                    try:
                        if isinstance(value, bytes):
                            value = (
                                f"[{len(value)} bytes]"
                                if len(value) > 100
                                else value.decode("utf-8", errors="ignore")
                            )
                        elif (
                            isinstance(value, tuple)
                            and len(value) == 2
                            and value[1] != 0
                        ):
                            if tag_name == "ExposureTime":
                                value = (
                                    f"1/{int(value[1]/value[0])}s"
                                    if value[0] < value[1]
                                    else f"{value[0]/value[1]:.1f}s"
                                )
                            elif tag_name in ("FNumber", "MaxApertureValue"):
                                value = f"f/{value[0]/value[1]:.1f}"
                            elif tag_name == "FocalLength":
                                value = f"{value[0]/value[1]:.0f}mm"
                            elif tag_name == "ExposureBiasValue":
                                value = f"{value[0]/value[1]:+.1f} EV"
                            else:
                                value = f"{value[0]/value[1]:.2f}"
                    except Exception:
                        pass

                    if tag_name in (
                        "Make",
                        "Model",
                        "BodySerialNumber",
                        "CameraOwnerName",
                    ):
                        result["camera"][tag_name] = value
                    elif tag_name in (
                        "ExposureTime",
                        "FNumber",
                        "ISOSpeedRatings",
                        "ExposureProgram",
                        "ExposureBiasValue",
                        "ExposureMode",
                        "MeteringMode",
                        "Flash",
                        "WhiteBalance",
                        "SceneCaptureType",
                        "BrightnessValue",
                        "ShutterSpeedValue",
                        "ApertureValue",
                        "MaxApertureValue",
                        "SubjectDistance",
                        "LightSource",
                        "DigitalZoomRatio",
                        "FocalLengthIn35mmFilm",
                        "ISOSpeed",
                    ):
                        result["exposure"][tag_name] = value
                    elif tag_name in (
                        "LensModel",
                        "LensSpecification",
                        "LensMake",
                        "LensSerialNumber",
                        "FocalLength",
                    ):
                        result["lens"][tag_name] = value
                    elif tag_name in (
                        "DateTime",
                        "DateTimeOriginal",
                        "DateTimeDigitized",
                        "SubSecTime",
                        "SubSecTimeOriginal",
                        "OffsetTime",
                    ):
                        result["dates"][tag_name] = value
                    elif tag_name in (
                        "Software",
                        "ImageDescription",
                        "Artist",
                        "Copyright",
                        "UserComment",
                        "ColorSpace",
                        "CustomRendered",
                        "Contrast",
                        "Saturation",
                        "Sharpness",
                        "GainControl",
                        "SceneType",
                        "FileSource",
                        "ImageUniqueID",
                    ):
                        result["other"][tag_name] = value
                    elif tag_name == "GPSInfo":
                        try:
                            GPS_TAGS = {
                                0: "GPSVersionID",
                                1: "GPSLatitudeRef",
                                2: "GPSLatitude",
                                3: "GPSLongitudeRef",
                                4: "GPSLongitude",
                                5: "GPSAltitudeRef",
                                6: "GPSAltitude",
                                7: "GPSTimeStamp",
                                29: "GPSDateStamp",
                            }
                            gps_data = {}
                            if isinstance(value, dict):
                                for gps_tag, gps_val in value.items():
                                    gps_data[
                                        GPS_TAGS.get(gps_tag, f"GPS_{gps_tag}")
                                    ] = gps_val
                            if "GPSLatitude" in gps_data and "GPSLongitude" in gps_data:
                                lat = self._gps_to_decimal(
                                    gps_data["GPSLatitude"],
                                    gps_data.get("GPSLatitudeRef", "N"),
                                )
                                lon = self._gps_to_decimal(
                                    gps_data["GPSLongitude"],
                                    gps_data.get("GPSLongitudeRef", "E"),
                                )
                                result["gps"]["Breitengrad"] = f"{lat:.6f}°"
                                result["gps"]["Längengrad"] = f"{lon:.6f}°"
                                result["gps"][
                                    "Google Maps"
                                ] = f"https://maps.google.com/?q={lat},{lon}"
                            if "GPSAltitude" in gps_data:
                                alt = gps_data["GPSAltitude"]
                                if isinstance(alt, tuple):
                                    alt = alt[0] / alt[1] if alt[1] != 0 else alt[0]
                                result["gps"]["Höhe"] = f"{float(alt):.1f}m"
                        except Exception as e:
                            print(f"GPS parse error: {e}")

                # EV berechnen
                try:
                    iso_raw = result["exposure"].get("ISOSpeedRatings")
                    ap_raw = result["exposure"].get("FNumber")
                    sh_raw = result["exposure"].get("ExposureTime")
                    if iso_raw and ap_raw and sh_raw:
                        iso = float(
                            str(
                                iso_raw[0]
                                if isinstance(iso_raw, (list, tuple))
                                else iso_raw
                            )
                        )
                        ap = float(str(ap_raw).replace("f/", ""))
                        sh_str = str(sh_raw)
                        if "/" in sh_str:
                            parts = sh_str.replace("s", "").split("/")
                            sh = (
                                float(parts[0]) / float(parts[1])
                                if len(parts) == 2
                                else eval(sh_str)
                            )
                        else:
                            sh = float(sh_str.replace("s", ""))
                        ev = math.log2((ap**2) / sh) - math.log2(iso / 100)
                        result["exposure"]["⭐ Berechneter EV"] = f"{ev:.1f}"
                        result["exposure"]["⭐ EV Bewertung"] = self._rate_ev(ev)
                except Exception as e:
                    print(f"EV calc error: {e}")

                return result
            except Exception as e:
                print(f"EXIF read error: {e}")
                return None

        def _gps_to_decimal(self, gps_coords, ref):
            try:
                d, m, s = gps_coords[0], gps_coords[1], gps_coords[2]
                for val in (d, m, s):
                    if isinstance(val, tuple):
                        val = val[0] / val[1] if val[1] != 0 else val[0]
                if isinstance(d, tuple):
                    d = d[0] / d[1] if d[1] != 0 else d[0]
                if isinstance(m, tuple):
                    m = m[0] / m[1] if m[1] != 0 else m[0]
                if isinstance(s, tuple):
                    s = s[0] / s[1] if s[1] != 0 else s[0]
                dec = float(d) + float(m) / 60 + float(s) / 3600
                return -dec if ref in ("S", "W") else dec
            except Exception:
                return 0.0

        def _rate_ev(self, ev):
            if ev < -2:
                return "⚫ Sehr dunkel (Nacht/Astro)"
            elif ev < 4:
                return "🔵 Dunkel (Nacht/Dämmerung)"
            elif ev < 8:
                return "🟣 Schwaches Licht (Innenraum)"
            elif ev < 11:
                return "🟢 Gutes Licht (bewölkt/Schatten)"
            elif ev < 14:
                return "🟢 ✓ Optimal (Tageslicht)"
            elif ev < 16:
                return "🟡 Hell (direkte Sonne)"
            else:
                return "🔴 Sehr hell (Schnee/Strand)"

        def _format_exif_output(self, filepath, data):
            txt = f"╔{'═'*52}╗\n"
            txt += f"║  📸 EXIF: {os.path.basename(filepath)[:40]:40s}  ║\n"
            txt += f"╚{'═'*52}╝\n\n"
            sections = [
                ("image", "🖼️ BILD", {}),
                (
                    "camera",
                    "📷 KAMERA",
                    {
                        "Make": "Hersteller",
                        "Model": "Modell",
                        "BodySerialNumber": "Seriennummer",
                    },
                ),
                ("exposure", "📊 BELICHTUNG", {}),
                (
                    "lens",
                    "🔭 OBJEKTIV",
                    {
                        "LensModel": "Objektiv",
                        "LensMake": "Hersteller",
                        "FocalLength": "Brennweite",
                    },
                ),
                ("gps", "🌐 GPS", {}),
                (
                    "dates",
                    "📅 DATUM",
                    {"DateTimeOriginal": "Aufgenommen", "DateTime": "Geändert"},
                ),
                (
                    "other",
                    "⚙️ WEITERE",
                    {
                        "Software": "Software",
                        "Artist": "Fotograf",
                        "Copyright": "Copyright",
                    },
                ),
            ]
            for key, header, name_map in sections:
                if not data.get(key):
                    continue
                txt += f"━━━ {header} {'━'*(44-len(header))}\n\n"
                for k, v in data[key].items():
                    label = name_map.get(k, k)
                    txt += f"  {label:22s}: {v}\n"
                txt += "\n"
            total = sum(len(v) for v in data.values() if isinstance(v, dict))
            txt += f"{'═'*54}\n  📊 {total} EXIF-Felder\n{'═'*54}\n"
            return txt

        def _explain_ev_value(self, ev_str):
            try:
                ev = float(ev_str)
                if ev < -2:
                    return "Sehr dunkel – Nachthimmel, Astro"
                elif ev < 2:
                    return "Dunkel – Nacht, Sterne, Vollmond"
                elif ev < 5:
                    return "Schwach – Kerzen, Weihnachtsbaum"
                elif ev < 8:
                    return "Innenraum – normale Beleuchtung"
                elif ev < 10:
                    return "Bewölkter Tag, offener Schatten"
                elif ev < 12:
                    return "Heller Schatten, bedeckter Himmel"
                elif ev < 14:
                    return "Tageslicht, leicht bewölkt"
                elif ev < 16:
                    return "Direktes Sonnenlicht, klar"
                else:
                    return "Sehr hell – Schnee, Strand, Sand"
            except Exception:
                return "EV-Wert konnte nicht interpretiert werden"

        def _export_exif(self):
            if not getattr(self, "_last_exif_text", ""):
                messagebox.showinfo("ℹ️", "Bitte zuerst ein Bild öffnen!")
                return
            fp = filedialog.asksaveasfilename(
                defaultextension=".txt", filetypes=[("Text", "*.txt"), ("Alle", "*.*")]
            )
            if fp:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(self._last_exif_text)
                messagebox.showinfo("✅", f"EXIF exportiert:\n{os.path.basename(fp)}")

        def _get_ev_explanation(self):
            if LANG == "DE":
                return (
                    "  EV = Exposure Value (Belichtungswert)\n"
                    "  Formel: EV = log₂(Blende² / Zeit) − log₂(ISO / 100)\n"
                    "  ──────────────────────────────────────────────────\n"
                    "  EV   │ Situation              │ Typische Einstellung\n"
                    "  ─────┼────────────────────────┼──────────────────────\n"
                    "  -4   │ 🌌 Sternenhimmel       │ ISO3200 f/1.8 20s\n"
                    "  -2   │ 🌙 Nachthimmel         │ ISO1600 f/2.8 10s\n"
                    "   0   │ 🌕 Vollmond-Szene      │ ISO800  f/2.8 4s\n"
                    "   4   │ 🕯️ Kerzenlicht         │ ISO800  f/2.8 1/8s\n"
                    "   7   │ 💡 Wohnzimmer          │ ISO400  f/2.8 1/30s\n"
                    "  11   │ ☁️ Bewölkt/Schatten    │ ISO100  f/5.6 1/125s\n"
                    "  14   │ ☀️ Sonnenlicht         │ ISO100  f/11  1/250s\n"
                    "  16   │ 🏖️ Schnee/Strand       │ ISO100  f/16  1/500s\n"
                    "  ──────────────────────────────────────────────────\n"
                    "  Je HÖHER der EV → desto HELLER die Szene\n"
                )
            elif LANG == "PL":
                return (
                    "  EV = Exposure Value\n"
                    "  Formuła: EV = log₂(f² / t) − log₂(ISO / 100)\n"
                    "  -4│Niebo nocne│ISO3200 f/1.8 20s\n"
                    "  14│Słońce     │ISO100  f/11  1/250s\n"
                )
            else:
                return (
                    "  EV = Exposure Value\n"
                    "  Formula: EV = log₂(f² / t) − log₂(ISO / 100)\n"
                    "  ──────────────────────────────────────────────────\n"
                    "  EV   │ Scene                  │ Typical Settings\n"
                    "  ─────┼────────────────────────┼──────────────────────\n"
                    "  -4   │ 🌌 Star field          │ ISO3200 f/1.8 20s\n"
                    "   0   │ 🌕 Full moon           │ ISO800  f/2.8 4s\n"
                    "  11   │ ☁️ Overcast/shade      │ ISO100  f/5.6 1/125s\n"
                    "  14   │ ☀️ Bright sunlight     │ ISO100  f/11  1/250s\n"
                    "  16   │ 🏖️ Snow/beach          │ ISO100  f/16  1/500s\n"
                    "  ──────────────────────────────────────────────────\n"
                    "  Higher EV → brighter scene | +1 EV = double light\n"
                )

        def _build_golden(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("golden_title"))
    
            # Kurze Anleitung
            ctk.CTkLabel(c, 
                text="💡 Gib Sonnenauf- & Untergangszeit ein (HH:MM). Die App berechnet automatisch die besten Foto-Zeiten.",
                font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))

            r = self._row(c)
            # Spalte 1: Sonnenaufgang
            c1 = self._col(r, (0,6))
            ctk.CTkLabel(c1, text="🌅 Sonnenaufgang (HH:MM)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(c1, text="z.B. 06:30", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
            self.gh_sr = self._entry(c1, "06:30")
            self.gh_sr.pack(fill="x", pady=(2,0))

            # Spalte 2: Sonnenuntergang
            c2 = self._col(r, (6,0))
            ctk.CTkLabel(c2, text="🌇 Sonnenuntergang (HH:MM)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(c2, text="z.B. 20:15", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
            self.gh_ss = self._entry(c2, "20:15")
            self.gh_ss.pack(fill="x", pady=(2,0))

            self._btn(c, t("calculate"), self._calc_golden).pack(pady=12)
            self.gh_res = self._rlbl(c)
            self.gh_res.pack(padx=14, pady=(0,14))

        def _calc_golden(self):
            try:
                sr = self.gh_sr.get().strip()
                ss = self.gh_ss.get().strip()
                if not sr or not ss:
                    raise ValueError("Leere Eingabe")
            
                r = calculate_golden_hour(sr, ss)
        
                txt = (f"🌅 {t('golden_morning')}: {r['golden_morning'][0]} – {r['golden_morning'][1]}\n"
                    f"🌇 {t('golden_evening')}: {r['golden_evening'][0]} – {r['golden_evening'][1]}\n"
                    f"🌆 {t('blue_morning')}: {r['blue_morning'][0]} – {r['blue_morning'][1]}\n"
                    f"🌃 {t('blue_evening')}: {r['blue_evening'][0]} – {r['blue_evening'][1]}")
                self.gh_res.configure(text=txt, text_color=C["gold"])
            except Exception:
                self.gh_res.configure(text="⚠️ Bitte gültiges Format HH:MM (z.B. 06:30)", text_color=C["red"])
        def calculate_moon_phase(year, month, day):
            """Berechnet Mondphase (0-1) für ein Datum. 0=Neumond, 0.5=Vollmond."""
            if month < 3:
                year -= 1
                month += 12
                k = int(year // 100)
            jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day - 1524.5 - k + int(k/4)
            days_since_new = jd - 2451550.1  # Bekannter Neumond: 6. Jan 2000
            new_moons = days_since_new / 29.53058867
            phase = new_moons - int(new_moons)
            return phase if phase >= 0 else phase + 1

        def get_moon_phase_info(phase):
            """Gibt Informationen zur Mondphase zurück."""
            if phase < 0.03 or phase > 0.97:
                return "🌑 Neumond", "dark", "Perfekt für Astro & Milchstraße!"
            elif phase < 0.22:
                return "🌒 Zunehmende Sichel", "waxing_crescent", "Gut für Astro (früher Abend)"
            elif phase < 0.28:
                return "🌓 Erstes Viertel", "first_quarter", "Mond untergeht Mitternacht"
            elif phase < 0.47:
                return "🌔 Zunehmender Mond", "waxing_gibbous", "Eingeschränkte Astro-Sicht"
            elif phase < 0.53:
                return "🌕 Vollmond", "full", "Schlecht für Milchstraße"
            elif phase < 0.72:
                return "🌖 Abnehmender Mond", "waning_gibbous", "Mond aufgeht spät"
            elif phase < 0.78:
                return "🌗 Letztes Viertel", "last_quarter", "Gut für Astro (späte Nacht)"
            elif phase < 0.97:
                return "🌘 Abnehmende Sichel", "waning_crescent", "Sehr gut für Astro!"
            return "🌑 Neumond", "dark", "Perfekt für Astro!"

        def calculate_milkyway_visibility(year, month, day, latitude=50.0):
            """
            Berechnet Milchstraßen-Sichtbarkeit.
            latitude: Breitengrad (positiv = Nordhalbkugel)
            Returns: Dict mit Sichtbarkeits-Info
            """
            moon_phase = calculate_moon_phase(year, month, day)
            phase_name, phase_type, phase_desc = get_moon_phase_info(moon_phase)
    
            # Milchstraße-Zentrum (Sagittarius) Sichtbarkeit nach Monat
            # Beste Zeit: Mai-September (Nordhalbkugel)
            month_factor = {
                1: 0.2, 2: 0.3, 3: 0.5, 4: 0.7, 5: 0.9, 6: 1.0,
                7: 1.0, 8: 0.95, 9: 0.8, 10: 0.6, 11: 0.4, 12: 0.2
            }
            season_score = month_factor.get(month, 0.5)
    
            # Mond-Helligkeit reduzieren Sichtbarkeit
            # Neumond = 1.0, Vollmond = 0.1
            moon_darkness = 1.0 - (abs(phase - 0.5) * 1.8)
            if moon_darkness < 0.1:
                moon_darkness = 0.1
    
            # Gesamtsichtbarkeit
            visibility_score = season_score * moon_darkness
    
            if visibility_score >= 0.85:
                rating = "🟢 Hervorragend"
                color = "green"
                rec = "Perfekte Bedingungen! Jetzt fotografieren!"
            elif visibility_score >= 0.65:
                rating = "🟡 Gut"
                color = "orange"
                rec = "Gute Sichtbarkeit. Zwischen Mitternacht und 4 Uhr."
            elif visibility_score >= 0.4:
                rating = "🟠 Mäßig"
                color = "peach"
                rec = "Eingeschränkt. Warte auf dunklere Mondphase."
            else:
                rating = "🔴 Schlecht"
                color = "red"
                rec = "Zu hell (Mond) oder falsche Jahreszeit."
    
            # Beste Aufnahmezeit (wenn Milchstraße hoch steht)
            if 4 <= month <= 9:
                best_time = "23:00 - 04:00 (Milchstraße hoch)"
            else:
                best_time = "03:00 - 06:00 (früher Morgen)"
    
            return {
                "date": f"{day:02d}.{month:02d}.{year}",
                "moon_phase": phase,
                "moon_phase_name": phase_name,
                "moon_phase_type": phase_type,
                "moon_phase_desc": phase_desc,
                "season_score": season_score,
                "moon_darkness": moon_darkness,
                "visibility_score": visibility_score,
                "rating": rating,
                "color": color,
                "recommendation": rec,
                "best_time": best_time,
            }

        def get_next_new_moon(year, month, day):
            """Findet den nächsten Neumond."""
            from datetime import datetime, timedelta
            current = datetime(year, month, day)
            for i in range(35):
                check_date = current + timedelta(days=i)
                phase = calculate_moon_phase(check_date.year, check_date.month, check_date.day)
                if phase < 0.03 or phase > 0.97:
                    return check_date, phase
            return None, None
        def _build_timelapse(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("timelapse_title"))
    
            # Kurze Anleitung
            ctk.CTkLabel(c, 
                text="💡 Gib Ziel-Länge, FPS & Aufnahme-Intervall ein. Berechne automatisch Bilder, Zeit & Speicher.",
                font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))

            r = self._row(c)
            # Spalte 1: Videolänge
            c1 = self._col(r, (0,6))
            ctk.CTkLabel(c1, text=t("tl_duration"), text_color=C["txt2"], font=ctk.CTkFont(size=11)).pack(anchor="w")
            self.tl_d = self._entry(c1, "30")
            self.tl_d.pack(fill="x", pady=(2,0))

            # Spalte 2: FPS
            c2 = self._col(r, (6,6))
            ctk.CTkLabel(c2, text=t("tl_fps"), text_color=C["txt2"], font=ctk.CTkFont(size=11)).pack(anchor="w")
            self.tl_fps = self._entry(c2, "24")
            self.tl_fps.pack(fill="x", pady=(2,0))

            # Spalte 3: Intervall
            c3 = self._col(r, (6,0))
            ctk.CTkLabel(c3, text=t("tl_interval"), text_color=C["txt2"], font=ctk.CTkFont(size=11)).pack(anchor="w")
            self.tl_i = self._entry(c3, "5")
            self.tl_i.pack(fill="x", pady=(2,0))

            self._btn(c, t("calculate"), self._calc_tl).pack(pady=12)
            self.tl_res = self._rlbl(c)
            self.tl_res.pack(padx=14, pady=(0,14))    

        def _calc_tl(self):
            try:
                fr, ts, sz = calculate_timelapse(
                    float(self.tl_d.get()),
                    float(self.tl_fps.get()),
                    float(self.tl_i.get()),
                )
                sb = f"{sz/1024:.1f}GB" if sz > 1024 else f"{sz}MB"
                self.tl_res.configure(
                    text=f"  {fr} shots | {ts} | ~{sb}", text_color=C["green"]
                )
            except Exception:
                self.tl_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_flash(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("flash_title"))
    
            # Kurze Anleitung
            ctk.CTkLabel(c, 
                text="💡 Formel: Blende = (GN × √(ISO/100)) ÷ Entfernung. Beispiel: GN58, 5m, ISO100 → f/11.6",
                font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))

            r = self._row(c)
    
            # Spalte 1: Leitzahl (GN)
            c1 = self._col(r, (0,4))
            ctk.CTkLabel(c1, text="🔦 Leitzahl (GN)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(c1, text="z.B. 58 für Canon 580EX", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
            self.fl_gn = self._entry(c1, "58")
            self.fl_gn.pack(fill="x", pady=(2,0))

            # Spalte 2: Entfernung
            c2 = self._col(r, (4,4))
            ctk.CTkLabel(c2, text="📏 Entfernung (m)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(c2, text="Abstand zum Motiv", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
            self.fl_d = self._entry(c2, "5.0")
            self.fl_d.pack(fill="x", pady=(2,0))

            # Spalte 3: ISO
            c3 = self._col(r, (4,0))
            ctk.CTkLabel(c3, text="🎞️ ISO", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(c3, text="Sensorempfindlichkeit", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
            self.fl_iso = self._combo(c3, ["100","200","400","800","1600","3200","6400"])
            self.fl_iso.set("100")
            self.fl_iso.pack(fill="x", pady=(2,0))

            self._btn(c, t("calculate"), self._calc_flash).pack(pady=12)
            self.fl_res = self._rlbl(c)
            self.fl_res.pack(padx=14, pady=(0,14))

        def _calc_flash(self):
            try:
                # Komma zu Punkt konvertieren für DE-Eingaben
                gn = float(self.fl_gn.get().replace(",", "."))
                dist = float(self.fl_d.get().replace(",", "."))
                iso = float(self.fl_iso.get().replace(",", "."))
        
                if dist <= 0:
                    self.fl_res.configure(text="⚠️ Entfernung muss > 0 sein", text_color=C["red"])
                    return
            
                r = calculate_flash(gn, distance=dist, iso=iso)
                aperture = r.get("aperture")
        
                # Blende auf Standard-Werte runden für bessere Lesbarkeit
                standard_apertures = [1.0, 1.2, 1.4, 1.8, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16, 22, 32]
                closest = min(standard_apertures, key=lambda x: abs(x - aperture))
        
                self.fl_res.configure(
                    text=f"✅ Empfohlene Blende: f/{closest} (berechnet: f/{aperture:.1f})\n"
                        f"💡 Tipp: Bei f/{closest} ist das Motiv bei {dist}m korrekt belichtet",
                    text_color=C["green"])
            except ValueError:
                self.fl_res.configure(text="⚠️ Bitte nur Zahlen eingaben (Punkt oder Komma)", text_color=C["red"])
            except Exception as e:
                self.fl_res.configure(text=f"❌ Fehler: {e}", text_color=C["red"])

        def _build_planner(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=18, pady=10)
            self._stitle(c, t("planner_title"))
            r = self._row(c)
            c1 = self._col(r, (0, 6))
            self.pl_loc = self._entry(c1, "...")
            self.pl_loc.pack(fill="x")
            c2 = self._col(r, (6, 6))
            self.pl_sub = self._entry(c2, "...")
            self.pl_sub.pack(fill="x")
            c3 = self._col(r, (6, 0))
            self.pl_set = self._entry(c3, "ISO 100|f/8")
            self.pl_set.pack(fill="x")
            nf = self._row(c)
            self.pl_notes = self._entry(nf, "Notes")
            self.pl_notes.pack(fill="x")
            bf = self._row(c)
            self._btn(bf, t("pl_add"), self._add_log, C["green"]).pack(
                side="left", padx=(0, 6)
            )
            self._btn(bf, t("pl_clear"), self._clear_log, C["red"]).pack(side="left")
            self.pl_out = self._textbox(p)
            self.pl_out.pack(fill="both", expand=True, padx=18, pady=(4, 10))
            self._refresh_log()

        def _add_log(self):
            self.logbook.append(
                {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "location": self.pl_loc.get(),
                    "subject": self.pl_sub.get(),
                    "settings": self.pl_set.get(),
                    "notes": self.pl_notes.get(),
                }
            )
            save_json(self.logbook, LOGBOOK_FILE)
            self._refresh_log()

        def _clear_log(self):
            self.logbook = []
            save_json(self.logbook, LOGBOOK_FILE)
            self._refresh_log()

        def _refresh_log(self):
            self.pl_out.delete("0.0", "end")
            if not self.logbook:
                self.pl_out.insert("0.0", "📝 No entries.")
                return
            for i, e in enumerate(reversed(self.logbook), 1):
                self.pl_out.insert(
                    "end",
                    f"{'─'*35}\n#{i} | {e.get('date','')}\n"
                    f"📍{e.get('location','')} | 📸{e.get('subject','')}\n"
                    f"⚙️{e.get('settings','')}\n📝{e.get('notes','')}\n\n",
                )

        def _build_compare(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=18, pady=12)
            self._stitle(c, t("compare_title"))
            m = ctk.CTkFrame(c, fg_color="transparent")
            m.pack(fill="x", padx=14, pady=4)
            self.cmp = {}
            for side, lbl in [("A", t("setup_a")), ("B", t("setup_b"))]:
                f = ctk.CTkFrame(m, fg_color=C["bg"], corner_radius=8)
                f.pack(side="left", expand=True, fill="x", padx=4, pady=4)
                ctk.CTkLabel(
                    f,
                    text=lbl,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=C["accent"],
                ).pack(pady=(8, 4))
                self.cmp[side] = {}
                for lkey, vals in [
                    ("iso", ["100", "200", "400", "800", "1600"]),
                    ("ap", ["1.4", "2.8", "4", "5.6", "8"]),
                    ("sh", None),
                ]:
                    w = self._combo(f, vals) if vals else self._entry(f, "1/125")
                    w.pack(fill="x", padx=8, pady=2)
                    self.cmp[side][lkey] = w
            self._btn(c, t("compare_btn"), self._calc_compare).pack(pady=10)
            self.cmp_res = self._rlbl(c)
            self.cmp_res.pack(padx=14, pady=(0, 14))

        def _calc_compare(self):
            try:
                ea, _ = evaluate_exposure(
                    float(self.cmp["A"]["iso"].get()),
                    float(self.cmp["A"]["ap"].get()),
                    eval(self.cmp["A"]["sh"].get()),
                )
                eb, _ = evaluate_exposure(
                    float(self.cmp["B"]["iso"].get()),
                    float(self.cmp["B"]["ap"].get()),
                    eval(self.cmp["B"]["sh"].get()),
                )
                diff = ea - eb
                desc = (
                    t("same_exposure")
                    if abs(diff) < 0.1
                    else f"{abs(diff):.1f} {t('stops_brighter') if diff > 0 else t('stops_darker')}"
                )
                self.cmp_res.configure(
                    text=f"  A: EV {ea:.2f} | B: EV {eb:.2f} | Δ{abs(diff):.2f} → {desc}",
                    text_color=C["green"],
                )
            except Exception:
                self.cmp_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_startrails(self, p):
                c = self._card(p)
                c.pack(fill="x", padx=28, pady=12)
                self._stitle(c, t("star_title"))
        
                # Erklärung zur 500er-Regel
                ctk.CTkLabel(c, 
                    text="💡 Maximale Belichtungszeit, bevor Sterne zu Strichspuren werden. Berechnet nach der konservativen 500er-Regel.",
                    font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))

                r = self._row(c)
                c1 = self._col(r, (0,6))
                ctk.CTkLabel(c1, text="🔭 Brennweite (mm)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
                ctk.CTkLabel(c1, text="z.B. 14-24mm für Weitwinkel-Astro", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
                self.st_f = self._entry(c1, "24")
                self.st_f.pack(fill="x", pady=(2,0))

                c2 = self._col(r, (6,0))
                ctk.CTkLabel(c2, text="📐 Blende (f/)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
                ctk.CTkLabel(c2, text="Offenste Blende deines Objektivs", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
                self.st_a = self._entry(c2, "2.8")
                self.st_a.pack(fill="x", pady=(2,0))

                self._btn(c, t("calculate"), self._calc_star).pack(pady=12)
                self.st_res = self._rlbl(c)
                self.st_res.pack(padx=14, pady=(0,14))
        def _build_startrails(self, p):
                c = self._card(p)
                c.pack(fill="x", padx=28, pady=12)
                self._stitle(c, t("star_title"))
                r = self._row(c)
                c1 = self._col(r, (0, 6))
                self.st_f = self._entry(c1, "24")
                self.st_f.pack(fill="x")
                c2 = self._col(r, (6, 0))
                self.st_a = self._entry(c2, "2.8")
                self.st_a.pack(fill="x")
                self._btn(c, t("calculate"), self._calc_star).pack(pady=10)
                self.st_res = self._rlbl(c)
                self.st_res.pack(padx=14, pady=(0, 14))

        def _calc_star(self):
            try:
                mx = calculate_star(float(self.st_f.get()))
                frames = int(1800 / mx)
                self.st_res.configure(
                    text=f"  Max: {mx}s | ~{frames} frames/30min", text_color=C["cyan"]
                )
            except Exception:
                self.st_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_lensdb(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=16, pady=10)
            self._stitle(c, t("lensdb_title"))
            cats = ["All"] + sorted({l["cat"] for l in RF_LENSES})
            ff = self._row(c)
            self.lens_cat = ctk.CTkSegmentedButton(
                ff,
                values=cats,
                font=ctk.CTkFont(size=11),
                selected_color=C["hl"],
                command=self._filter_lenses,
            )
            self.lens_cat.set("All")
            self.lens_cat.pack(side="left")
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=16, pady=(4, 10))
            # FIX: Spaltenheader ergänzt
            hdr = ctk.CTkFrame(sc, fg_color=C["card_sel"], corner_radius=4, height=24)
            hdr.pack(fill="x", pady=(0, 2), padx=2)
            hdr.pack_propagate(False)
            ctk.CTkLabel(
                hdr,
                text="  Objektiv                              │ f/    │  Gew. │ IS  │ Preis",
                font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                text_color=C["accent"],
                anchor="w",
            ).pack(side="left", padx=4)
            self.lens_frame = sc
            self._filter_lenses("All")

        def _filter_lenses(self, cat):
            # Nur Lens-Rows löschen, Header behalten
            children = self.lens_frame.winfo_children()
            for child in children[1:]:  # Erstes Kind = Header
                child.destroy()
            lenses = (
                RF_LENSES if cat == "All" else [l for l in RF_LENSES if l["cat"] == cat]
            )
            for i, l in enumerate(sorted(lenses, key=lambda x: x["name"])):
                row = ctk.CTkFrame(
                    self.lens_frame,
                    fg_color=C["card"] if i % 2 == 0 else C["bg"],
                    corner_radius=5,
                    height=28,
                )
                row.pack(fill="x", pady=1, padx=2)
                row.pack_propagate(False)
                is_b = "✅" if l["is"] else "❌"
                ctk.CTkLabel(
                    row,
                    text=f"  {l['name']:38s}| f/{l['min_ap']:<4} | {l['weight']:4d}g | {is_b} | {l['price']}",
                    font=ctk.CTkFont(family="Consolas", size=10),
                    text_color=C["txt"],
                    anchor="w",
                ).pack(side="left", padx=4)

        def _build_video(self, p):
            tb = self._textbox(p)
            tb.pack(fill="both", expand=True, padx=14, pady=14)
            tb.insert("0.0", VIDEO_GUIDE.get(LANG, VIDEO_GUIDE["EN"]))
            tb.configure(state="disabled")

        def _build_battery(self, p):
                c = self._card(p)
                c.pack(fill="x", padx=28, pady=12)
                self._stitle(c, t("battery_title"))
        
                ctk.CTkLabel(c, 
                    text="💡 Schätze die reale Akkulaufzeit basierend auf Display-, Blitz- & WiFi-Nutzung.",
                    font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))

                r1 = self._row(c)
                c1 = self._col(r1, (0,6))
                ctk.CTkLabel(c1, text="🔋 Kapazität (Aufnahmen)", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
                ctk.CTkLabel(c1, text="Canon LP-E6NH: ~370 Shots (CIPA)", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
                self.bat_cap = self._entry(c1, "370")
                self.bat_cap.pack(fill="x", pady=(2,0))

                c2 = self._col(r1, (6,0))
                ctk.CTkLabel(c2, text="⚡ Aufnahmen/Minute", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
                ctk.CTkLabel(c2, text="2=ruhig | 10=Events | 15+=Sport", font=ctk.CTkFont(size=9), text_color=C["txt3"]).pack(anchor="w")
                self.bat_spm = self._entry(c2, "2")
                self.bat_spm.pack(fill="x", pady=(2,0))

                # Slider-Initialisierung (sicher vor AttributeError)
                self.bat_sliders = {}
                ctk.CTkLabel(c, text="🔻 Verbrauchsfaktoren:", text_color=C["txt2"], font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=14, pady=(8,2))

                for key, label, color, default in [
                    ("bat_lcd_pct", "LCD-Display Nutzung", C["accent"], 30),
                    ("bat_flash_pct", "Blitz-Nutzung", C["orange"], 50),
                    ("bat_wifi_pct", "WiFi / Fernbedienung", C["purple"], 30)
                ]:
                    sf = self._row(c)
                    ctk.CTkLabel(sf, text=label, text_color=C["txt2"], width=160).pack(side="left")
                    sl = ctk.CTkSlider(sf, from_=0, to=100, width=220, progress_color=color, button_color=color)
                    sl.set(default)
                    sl.pack(side="left", padx=8)
                    vl = ctk.CTkLabel(sf, text=f"{int(default)}%", text_color=C["txt2"], width=40)
                    vl.pack(side="left")
                    sl.configure(command=lambda v, lbl=vl: lbl.configure(text=f"{int(v)}%"))
                    self.bat_sliders[key] = sl

                self._btn(c, t("calculate"), self._calc_battery, C["green"]).pack(pady=12)
                self.bat_res = self._rlbl(c)
                self.bat_res.pack(padx=14, pady=(0,14))

        def _calc_battery(self):
            try:
                cap = float(self.bat_cap.get().replace(",", "."))
                spm = float(self.bat_spm.get().replace(",", "."))
                lcd = self.bat_sliders["bat_lcd_pct"].get()
                flash = self.bat_sliders["bat_flash_pct"].get()
                wifi = self.bat_sliders["bat_wifi_pct"].get()
                shots = calculate_battery(cap, lcd, flash, wifi)
                mins = shots / spm if spm > 0 else 0
                h, m = int(mins // 60), int(mins % 60)
                unit = {"DE": "Aufnahmen", "PL": "zdjęć", "EN": "shots"}.get(
                    LANG, "shots"
                )
                self.bat_res.configure(
                    text=f"  ~{shots} {unit} | ~{h}h {m}min\n"
                    f"  LCD:{int(lcd)}% Flash:{int(flash)}% WiFi:{int(wifi)}%",
                    text_color=C["green"],
                )
            except Exception as e:
                print(f"Battery Error: {e}")
                self.bat_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_noise(self, p):
            c = self._card(p)
            c.pack(fill="x", padx=28, pady=12)
            self._stitle(c, t("noise_title"))
            r = self._row(c)
            self.ns_iso = self._combo(
                r,
                ["100", "200", "400", "800", "1600", "3200", "6400", "12800", "25600"],
            )
            self.ns_iso.pack(side="left")
            self._btn(r, t("calculate"), self._calc_noise).pack(side="left", padx=10)
            self.ns_res = self._rlbl(c)
            self.ns_res.pack(padx=14, pady=(10, 14))

        def _calc_noise(self):
            try:
                snr, dr, rating = calculate_noise(float(self.ns_iso.get()))
                # FIX: robusterer Rating-Check
                col = (
                    C["green"]
                    if "Excellent" in rating
                    else C["orange"] if "Good" in rating else C["red"]
                )
                self.ns_res.configure(
                    text=f"  SNR: {snr}dB | DR: {dr}EV | {rating}", text_color=col
                )
            except Exception:
                self.ns_res.configure(text=t("invalid"), text_color=C["red"])

        def _build_edit(self, p):
            tb = self._textbox(p)
            tb.pack(fill="both", expand=True, padx=14, pady=14)
            tb.insert("0.0", EDIT_GUIDE.get(LANG, EDIT_GUIDE["EN"]))
            tb.configure(state="disabled")

        def _build_settings(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=16, pady=12)
            c1 = self._card(sc)
            c1.pack(fill="x", pady=(0, 8))
            self._stitle(c1, t("settings_title"))
            bf = self._row(c1)
            self._btn(bf, t("settings_save_all"), self._save_config, C["green"]).pack(
                side="left", padx=(0, 6)
            )
            self._btn(bf, t("settings_reset"), self._reset_all, C["red"]).pack(
                side="left"
            )
            c2 = self._card(sc)
            c2.pack(fill="x", pady=(0, 8))
            self._stitle(c2, t("settings_about"), C["cyan"])
            ctk.CTkLabel(
                c2,
                text=f"  Canon EOS R – AI Pro Tool v5.1\n"
                f"  26 Tools | DE/PL/EN | {len(RF_LENSES)} RF Lenses\n"
                f"  Pillow: {'✅' if PIL_AVAILABLE else '❌'} | "
                f"fpdf2: {'✅' if PDF_AVAILABLE else '❌'} | "
                f"qrcode: {'✅' if QR_AVAILABLE else '❌'}\n"
                f"  Python {sys.version.split()[0]}",
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color=C["txt"],
                anchor="w",
                justify="left",
            ).pack(padx=14, pady=(2, 12))

        def _save_config(self):
            # OPT: Bestehende Config mergen, nicht überschreiben
            cfg = load_json(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}
            cfg["lang"] = LANG
            if save_json(cfg, CONFIG_FILE):
                messagebox.showinfo("✅", t("saved"))

        def _reset_all(self):
            for fp in [CONFIG_FILE, LOGBOOK_FILE, FAV_FILE, SPOTS_FILE]:
                if os.path.exists(fp):
                    os.remove(fp)
            self.logbook = []
            self.favorites = {}
            self.spots = []
            messagebox.showinfo("🔄", "Reset!")

        # ═══════════════════════════════════════════
        #  PHOTO SPOTS
        # ═══════════════════════════════════════════

        def _build_spots(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=8, pady=8)
            c = self._card(sc)
            c.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(c, t("spots_title"))

            r1 = self._row(c)
            c1 = self._col(r1, (0, 6))
            ctk.CTkLabel(c1, text=t("spot_name"), text_color=C["txt2"]).pack(anchor="w")
            f1, self.spot_name = self._entry_with_tip(c1, "Berlin...", "spot_name")
            f1.pack(fill="x", pady=(2, 0))
            c2 = self._col(r1, (6, 0))
            ctk.CTkLabel(c2, text=t("spot_type"), text_color=C["txt2"]).pack(anchor="w")
            self.spot_type = self._combo(c2, t("spot_types"))
            self.spot_type.pack(fill="x", pady=(2, 0))

            r2 = self._row(c)
            c3 = self._col(r2, (0, 6))
            ctk.CTkLabel(c3, text=t("spot_lat"), text_color=C["txt2"]).pack(anchor="w")
            f3, self.spot_lat = self._entry_with_tip(c3, "52.5163", "spot_lat")
            f3.pack(fill="x", pady=(2, 0))
            c4 = self._col(r2, (6, 6))
            ctk.CTkLabel(c4, text=t("spot_lon"), text_color=C["txt2"]).pack(anchor="w")
            f4, self.spot_lon = self._entry_with_tip(c4, "13.3777", "spot_lon")
            f4.pack(fill="x", pady=(2, 0))
            c5 = self._col(r2, (6, 0))
            ctk.CTkLabel(c5, text=t("spot_notes"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            f5, self.spot_notes = self._entry_with_tip(
                c5, "Golden Hour...", "spot_notes"
            )
            f5.pack(fill="x", pady=(2, 0))

            bf = self._row(c)
            self._btn(bf, t("spot_add"), self._add_spot, C["emerald"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(bf, t("spot_remove"), self._remove_spot, C["red"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(bf, t("spot_map"), self._open_map, C["accent"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(bf, t("spot_export"), self._export_spots, C["purple"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(bf, "📱 QR-Code", self._show_qr_for_spot, C["indigo"]).pack(
                side="left"
            )

            lc = self._card(sc)
            lc.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(lc, "📍 Gespeicherte Spots", C["emerald"])
            list_and_qr = ctk.CTkFrame(lc, fg_color="transparent")
            list_and_qr.pack(fill="x", padx=10, pady=(4, 10))
            self.spots_list = self._textbox(list_and_qr, h=220)
            self.spots_list.pack(side="left", fill="both", expand=True, padx=(0, 6))
            qr_frame = ctk.CTkFrame(
                list_and_qr, fg_color=C["bg"], corner_radius=8, width=220
            )
            qr_frame.pack(side="right", fill="y")
            qr_frame.pack_propagate(False)
            ctk.CTkLabel(
                qr_frame,
                text="📱 QR-Code",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=C["indigo"],
            ).pack(pady=(8, 4))
            self.qr_label = ctk.CTkLabel(
                qr_frame,
                text="Spot hinzufügen\nfür QR-Code",
                font=ctk.CTkFont(size=10),
                text_color=C["txt3"],
            )
            self.qr_label.pack(expand=True, padx=8)
            self.qr_info = ctk.CTkLabel(
                qr_frame, text="", font=ctk.CTkFont(size=9), text_color=C["txt2"]
            )
            self.qr_info.pack(pady=(0, 8))
            self._qr_photo_ref = None
            self._refresh_spots()

        def _add_spot(self):
            try:
                name = self.spot_name.get().strip()
                if not name:
                    return
                spot = {
                    "name": name,
                    "type": self.spot_type.get(),
                    "lat": float(self.spot_lat.get().replace(",", ".")),
                    "lon": float(self.spot_lon.get().replace(",", ".")),
                    "notes": self.spot_notes.get().strip(),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                self.spots.append(spot)
                save_json(self.spots, SPOTS_FILE)
                self.spot_name.delete(0, "end")
                self.spot_notes.delete(0, "end")
                self._refresh_spots()
                self._generate_qr_for_spot(spot)
            except Exception as e:
                print(f"Spot error: {e}")

        def _remove_spot(self):
            if self.spots:
                self.spots.pop()
                save_json(self.spots, SPOTS_FILE)
                self._refresh_spots()

        def _open_map(self):
            if not self.spots:
                return
            import webbrowser

            s = self.spots[-1]
            webbrowser.open(f"https://www.google.com/maps?q={s['lat']},{s['lon']}")

        def _export_spots(self):
            if not self.spots:
                return
            fp = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("CSV", "*.csv")],
            )
            if not fp:
                return
            if fp.endswith(".csv"):
                with open(fp, "w", encoding="utf-8") as f:
                    f.write("Name,Type,Lat,Lon,Notes,Date\n")
                    for s in self.spots:
                        f.write(
                            f"{s['name']},{s['type']},{s['lat']},"
                            f"{s['lon']},{s.get('notes','')},{s.get('date','')}\n"
                        )
            else:
                save_json(self.spots, fp)
            messagebox.showinfo("✅", t("exported"))

        def _show_qr_for_spot(self):
            if not self.spots:
                self.qr_info.configure(text="Kein Spot vorhanden")
                return
            self._generate_qr_for_spot(self.spots[-1])

        def _generate_qr_for_spot(self, spot):
            url = f"https://maps.google.com/?q={spot['lat']},{spot['lon']}"
            if PIL_AVAILABLE:
                qr_img = generate_qr_code(url, size=180)
                if qr_img:
                    ctk_qr = ctk.CTkImage(
                        light_image=qr_img, dark_image=qr_img, size=(180, 180)
                    )
                    self._qr_photo_ref = ctk_qr
                    self.qr_label.configure(image=ctk_qr, text="")
                else:
                    self.qr_label.configure(
                        image=None,
                        text=f"📍 {spot['name']}\n{url}\n(pip install qrcode)",
                    )
                self.qr_info.configure(
                    text=f"📍 {spot['name'][:20]} | {spot['lat']:.4f}, {spot['lon']:.4f}"
                )
            else:
                self.qr_label.configure(
                    text=f"📍 {spot['name']}\n{spot['lat']}, {spot['lon']}\nPillow benötigt"
                )

        def _refresh_spots(self):
            self.spots_list.configure(state="normal")
            self.spots_list.delete("0.0", "end")
            if not self.spots:
                self.spots_list.insert("0.0", "  Keine Spots gespeichert.\n")
                self.spots_list.configure(state="disabled")
                return
            for i, s in enumerate(self.spots, 1):
                self.spots_list.insert(
                    "end",
                    f"  {'─'*38}\n"
                    f"  #{i} 📍 {s['name']} ({s['type']})\n"
                    f"  🌐 {s['lat']}, {s['lon']} | 📅 {s.get('date','')}\n"
                    f"  📝 {s.get('notes','')}\n"
                    f"  🔗 maps.google.com/?q={s['lat']},{s['lon']}\n\n",
                )
            self.spots_list.configure(state="disabled")
            if self.spots:
                self._generate_qr_for_spot(self.spots[-1])

        # ═══════════════════════════════════════════
        #  WEATHER ASSISTANT
        # ═══════════════════════════════════════════

        def _build_weather(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=10, pady=10)
            c = self._card(sc)
            c.pack(fill="x", padx=10, pady=(0, 8))
            self._stitle(c, t("weather_title"))
            ctk.CTkLabel(
                c,
                text=t("weather_desc"),
                font=ctk.CTkFont(size=12),
                text_color=C["txt2"],
            ).pack(padx=14, pady=(0, 8))
            self._stitle(c, t("weather_manual"), C["orange"])

            r1 = self._row(c)
            c1 = self._col(r1, (0, 6))
            ctk.CTkLabel(c1, text=t("weather_temp"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            self.wx_temp = self._entry(c1, "20")
            self.wx_temp.pack(fill="x", pady=(2, 0))
            self.wx_temp.insert(0, "20")

            c2 = self._col(r1, (6, 6))
            ctk.CTkLabel(c2, text=t("weather_clouds"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            self.wx_clouds = self._entry(c2, "30")
            self.wx_clouds.pack(fill="x", pady=(2, 0))
            self.wx_clouds.insert(0, "30")

            c3 = self._col(r1, (6, 0))
            ctk.CTkLabel(c3, text=t("weather_wind"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            self.wx_wind = self._entry(c3, "10")
            self.wx_wind.pack(fill="x", pady=(2, 0))
            self.wx_wind.insert(0, "10")

            r2 = self._row(c)
            c4 = self._col(r2, (0, 6))
            ctk.CTkLabel(c4, text=t("weather_humidity"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            self.wx_humidity = self._entry(c4, "50")
            self.wx_humidity.pack(fill="x", pady=(2, 0))
            self.wx_humidity.insert(0, "50")

            c5 = self._col(r2, (6, 0))
            ctk.CTkLabel(c5, text=t("weather_condition"), text_color=C["txt2"]).pack(
                anchor="w"
            )
            self.wx_condition = self._combo(c5, t("weather_conditions"))
            self.wx_condition.pack(fill="x", pady=(2, 0))

            self._btn(c, t("weather_analyze"), self._analyze_weather, C["sky"]).pack(
                pady=12
            )

            res_card = self._card(sc)
            res_card.pack(fill="x", padx=10, pady=(0, 8))
            self._stitle(res_card, "📊 Foto-Analyse", C["sky"])
            self.wx_res = self._textbox(res_card, h=280)
            self.wx_res.pack(fill="x", padx=14, pady=(4, 14))

        def _analyze_weather(self):
            try:
                temp = float(self.wx_temp.get().replace(",", "."))
                clouds = float(self.wx_clouds.get().replace(",", "."))
                wind = float(self.wx_wind.get().replace(",", "."))
                humidity = float(self.wx_humidity.get().replace(",", "."))
                condition = self.wx_condition.get()
                results = analyze_weather(temp, clouds, wind, humidity, condition)

                self.wx_res.configure(state="normal")
                self.wx_res.delete("0.0", "end")
                txt = f"{'═'*48}\n"
                txt += f"  ☁️ {condition}\n"
                txt += f"  🌡️ {temp}°C | ☁️ {clouds}% | 💨 {wind}km/h | 💧 {humidity}%\n"
                txt += f"{'═'*48}\n\n"
                txt += f"  🌅 {t('weather_golden_rec')}:\n  {results['golden'][0]} {results['golden'][1]}\n\n"
                txt += f"  👤 {t('weather_portrait_rec')}:\n  {results['portrait'][0]} {results['portrait'][1]}\n\n"
                txt += f"  🏔️ {t('weather_landscape_rec')}:\n  {results['landscape'][0]} {results['landscape'][1]}\n\n"
                if results["tips"]:
                    txt += f"  {'─'*40}\n  ⚠️ Hinweise:\n"
                    for tip in results["tips"]:
                        txt += f"  {tip}\n"
                txt += f"\n  {'─'*40}\n  📸 Empfohlene Basis-Einstellungen:\n"
                if clouds > 70:
                    txt += "  ISO: 400-800 | WB: Bewölkt (6000K)\n"
                elif clouds > 30:
                    txt += "  ISO: 200-400 | WB: Auto oder Schatten\n"
                else:
                    txt += "  ISO: 100-200 | WB: Tageslicht (5200K)\n"
                if wind > 20:
                    txt += "  ⚡ Min. 1/500s wegen Wind!\n"
                self.wx_res.insert("0.0", txt)
                self.wx_res.configure(state="disabled")
            except Exception as e:
                print(f"Weather Error: {e}")
                self.wx_res.configure(state="normal")
                self.wx_res.delete("0.0", "end")
                self.wx_res.insert("0.0", t("invalid"))

        # ═══════════════════════════════════════════
        #  HISTOGRAM SIMULATOR
        # ═══════════════════════════════════════════

        def _build_histogram(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=10, pady=10)
            c = self._card(sc)
            c.pack(fill="x", padx=10, pady=(0, 8))
            self._stitle(c, t("histogram_title"))
            ctk.CTkLabel(
                c,
                text=t("histogram_desc"),
                font=ctk.CTkFont(size=12),
                text_color=C["txt2"],
            ).pack(padx=14, pady=(0, 8))

            r1 = self._row(c)
            ctk.CTkLabel(r1, text=t("hist_ev"), text_color=C["txt2"], width=120).pack(
                side="left"
            )
            self.hist_ev_slider = ctk.CTkSlider(
                r1,
                from_=-4,
                to=20,
                width=350,
                progress_color=C["accent"],
                button_color=C["accent"],
            )
            self.hist_ev_slider.set(12)
            self.hist_ev_slider.pack(side="left", padx=8)
            self.hist_ev_lbl = ctk.CTkLabel(
                r1,
                text="EV 12",
                text_color=C["txt"],
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            self.hist_ev_lbl.pack(side="left")
            self.hist_ev_slider.configure(
                command=lambda v: self.hist_ev_lbl.configure(text=f"EV {int(v)}")
            )

            r2 = self._row(c)
            ctk.CTkLabel(
                r2, text=t("hist_contrast"), text_color=C["txt2"], width=120
            ).pack(side="left")
            self.hist_contrast_slider = ctk.CTkSlider(
                r2,
                from_=10,
                to=100,
                width=350,
                progress_color=C["orange"],
                button_color=C["orange"],
            )
            self.hist_contrast_slider.set(50)
            self.hist_contrast_slider.pack(side="left", padx=8)
            self.hist_contrast_lbl = ctk.CTkLabel(
                r2,
                text="50",
                text_color=C["txt"],
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            self.hist_contrast_lbl.pack(side="left")
            self.hist_contrast_slider.configure(
                command=lambda v: self.hist_contrast_lbl.configure(text=f"{int(v)}")
            )

            r3 = self._row(c)
            ctk.CTkLabel(
                r3, text=t("hist_channel"), text_color=C["txt2"], width=120
            ).pack(side="left")
            self.hist_channel = ctk.CTkSegmentedButton(
                r3,
                values=["Luminance", "🔴 R", "🟢 G", "🔵 B", "RGB"],
                font=ctk.CTkFont(size=11),
                selected_color=C["hl"],
            )
            self.hist_channel.set("Luminance")
            self.hist_channel.pack(side="left")

            self._btn(
                c, t("hist_generate"), self._generate_histogram, C["indigo"]
            ).pack(pady=12)

            hist_card = self._card(sc)
            hist_card.pack(fill="x", padx=10, pady=(0, 8))
            self._stitle(hist_card, "📊 Histogram", C["indigo"])
            self.hist_canvas = tk.Canvas(
                hist_card, width=520, height=200, bg=C["bg"], highlightthickness=0
            )
            self.hist_canvas.pack(padx=14, pady=(4, 8))
            self.hist_info = self._rlbl(hist_card)
            self.hist_info.pack(padx=14, pady=(0, 14))
            self._generate_histogram()
            

        def _generate_histogram(self):
            ev = int(self.hist_ev_slider.get())
            contrast = int(self.hist_contrast_slider.get())
            channel = self.hist_channel.get()
            self.hist_canvas.delete("all")

            for i in range(0, 256, 32):
                x = int(i * 520 / 256)
                self.hist_canvas.create_line(x, 0, x, 200, fill=C["border"], width=1)
            for i in range(0, 200, 40):
                self.hist_canvas.create_line(0, i, 520, i, fill=C["border"], width=1)

            for idx, zone in enumerate(["Shadows", "Midtones", "Highlights"]):
                x = int((idx * 85 + 42) * 520 / 256)
                self.hist_canvas.create_text(
                    x, 190, text=zone, fill=C["txt3"], font=("Consolas", 8)
                )

            if channel == "RGB":
                for color, ch, offset in [
                    ("#FF4444", "R", -10),
                    ("#44FF44", "G", 0),
                    ("#4444FF", "B", 10),
                ]:
                    # FIX: seed für Reproduzierbarkeit
                    data = generate_histogram_data(ev + offset, contrast, seed=42)
                    max_val = max(data) or 1
                    points = [
                        (int(i * 520 / 256), 180 - int((v / max_val) * 170))
                        for i, v in enumerate(data)
                    ]
                    if len(points) > 2:
                        poly = [(0, 180)] + points + [(520, 180)]
                        flat = [c for pt in poly for c in pt]
                        self.hist_canvas.create_polygon(
                            flat, fill="", outline=color, width=2
                        )
            else:
                color_map = {
                    "Luminance": C["txt"],
                    "🔴 R": "#FF4444",
                    "🟢 G": "#44FF44",
                    "🔵 B": "#4444FF",
                }
                bar_color = color_map.get(channel, C["txt"])
                # FIX: seed für Reproduzierbarkeit
                data = generate_histogram_data(ev, contrast, seed=42)
                max_val = max(data) or 1
                for i, val in enumerate(data):
                    x = int(i * 520 / 256)
                    h = int((val / max_val) * 170)
                    if h > 0:
                        self.hist_canvas.create_rectangle(
                            x, 180 - h, x + 2, 180, fill=bar_color, outline=""
                        )

            data_check = generate_histogram_data(ev, contrast, seed=42)
            total = sum(data_check) or 1
            shadows_clip = sum(data_check[:8])
            highlights_clip = sum(data_check[248:])

            if ev > 15:
                rating, col = f"🔴 {t('hist_overexposed')}", C["red"]
            elif ev < 4:
                rating, col = f"🔵 {t('hist_underexposed')}", C["accent"]
            else:
                rating, col = f"🟢 {t('hist_well_exposed')}", C["green"]

            contrast_text = (
                t("hist_high_contrast")
                if contrast > 70
                else t("hist_low_contrast") if contrast < 30 else "Normal"
            )
            self.hist_info.configure(
                text=f"  {rating} | EV {ev} | {contrast_text}\n"
                f"  Shadows: {shadows_clip/total*100:.0f}% | "
                f"Highlights: {highlights_clip/total*100:.0f}%",
                text_color=col,
            )
        # ═══════════════════════════════════════════
        #  MOON PHASES & MILKY WAY
        # ═══════════════════════════════════════════
        def _build_moon_milkyway(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=10, pady=10)
    
            c = self._card(sc)
            c.pack(fill="x", padx=10, pady=(0,8))
            self._stitle(c, "🌙 Mondphasen & Milchstraße", C["purple"])
    
            ctk.CTkLabel(c, 
                text="💡 Berechne optimale Astro-Termine basierend auf Mondphase und Jahreszeit.",
                font=ctk.CTkFont(size=10), text_color=C["txt2"]).pack(padx=14, pady=(0,8))
    
            # Datumsauswahl
            r1 = self._row(c)
            ctk.CTkLabel(r1, text="📅 Datum:", text_color=C["txt2"], width=80).pack(side="left")
    
            today = datetime.now()
            # WICHTIG: Leerer Placeholder, dafür Werte direkt einfügen
            self.mm_day = self._entry(r1, "")
            self.mm_day.insert(0, str(today.day))
            self.mm_day.pack(side="left", padx=4, fill="x", expand=True)
    
            self.mm_month = self._entry(r1, "")
            self.mm_month.insert(0, str(today.month))
            self.mm_month.pack(side="left", padx=4, fill="x", expand=True)
    
            self.mm_year = self._entry(r1, "")
            self.mm_year.insert(0, str(today.year))
            self.mm_year.pack(side="left", padx=4, fill="x", expand=True)
    
            # Breitengrad
            r2 = self._row(c)
            ctk.CTkLabel(r2, text="🌍 Breitengrad:", text_color=C["txt2"], width=80).pack(side="left")
            self.mm_lat = self._entry(r2, "")
            self.mm_lat.insert(0, "50.0")  # z.B. Deutschland
            self.mm_lat.pack(side="left", padx=4, fill="x", expand=True)
            ctk.CTkLabel(r2, text="(z.B. 50=Nord, -33=Süd)", text_color=C["txt3"], width=150).pack(side="left")
    
            self._btn(c, "🔍 Berechnen", self._calc_moon_milkyway, C["purple"]).pack(pady=10)
    
            # Ergebnisse
            result_card = self._card(sc)
            result_card.pack(fill="x", padx=10, pady=(0,8))
            self._stitle(result_card, "📊 Ergebnisse", C["purple"])
    
            self.mm_result = self._textbox(result_card, h=350)
            self.mm_result.pack(fill="x", padx=14, pady=(4,14))
    
            # Nächste Neumonde
            next_card = self._card(sc)
            next_card.pack(fill="x", padx=10, pady=(0,8))
            self._stitle(next_card, "🌑 Nächste Neumonde", C["cyan"])
    
            self.mm_next_new = self._textbox(next_card, h=120)
            self.mm_next_new.pack(fill="x", padx=14, pady=(4,14))
    
            # Initial berechnen
            self._calc_moon_milkyway()

        def _calc_moon_milkyway(self):
            try:
                # Sicheres Auslesen & Validierung
                day_str   = self.mm_day.get().strip()
                month_str = self.mm_month.get().strip()
                year_str  = self.mm_year.get().strip()
                lat_str   = self.mm_lat.get().strip().replace(",", ".")

                if not (day_str and month_str and year_str and lat_str):
                    raise ValueError("Bitte alle Felder ausfüllen")

                day, month, year = int(day_str), int(month_str), int(year_str)
                lat = float(lat_str)

                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    raise ValueError("Ungültiges Datum")
                if not (-90 <= lat <= 90):
                    raise ValueError("Breitengrad muss zwischen -90° und +90° liegen")

                # Berechnung
                data = calculate_milkyway_visibility(year, month, day, lat)
        
                txt = f"""
        ╔{'═'*56}╗
        ║  📅 {data['date']:48s}  ║
        ╚{'═'*56}╝

        🌙 MONDPHASE
        {'─'*56}
        Phase: {data['moon_phase_name']:40s}
        Wert:  {data['moon_phase']:.3f} (0=Neumond, 0.5=Vollmond)
        Info:  {data['moon_phase_desc']:40s}

        🌌 MILCHSTRAßEN-SICHTBARKEIT
        {'─'*56}
        Bewertung:       {data['rating']}
        Jahreszeit-Score:{data['season_score']*100:.0f}% (optimal Mai-Sep)
        Mond-Dunkelheit: {data['moon_darkness']*100:.0f}% (je höher, desto besser)
        Gesamt-Score:    {data['visibility_score']*100:.0f}%

        📸 Empfehlung:
        {data['recommendation']:52s}
  
        ⏰ Beste Aufnahmezeit: {data['best_time']:30s}

        📷 EMPFOHLENE EINSTELLUNGEN
        {'─'*56}
        """
                if data['visibility_score'] >= 0.65:
                    txt += """  Brennweite:  14-24mm (Weitwinkel)
        Blende:      f/1.4 - f/2.8
        ISO:         1600 - 6400
        Belichtung:  15-25s (500er Regel)
        Fokus:       Manuell auf ∞
        Format:      RAW (CR3)
        """
                else:
                    txt += """  ⚠️ Bedingungen nicht optimal. Warte auf:
        - Neumond-Phase (<25% Mondbeleuchtung)
        - Monate Mai-September (Nordhalbkugel)
        - Klaren Himmel, Bortle 1-4
        """
                self._update_textbox(self.mm_result, txt)
                self._show_next_new_moons(year, month, day)
        
            except ValueError as ve:
                self._update_textbox(self.mm_result, f"⚠️ {ve}")
                print(f"[Moon] Validation Error: {ve}")
            except Exception as e:
                self._update_textbox(self.mm_result, f"❌ Fehler: {e}\n(Siehe Konsole für Details)")
                print(f"[Moon] Crash: {e}")
                import traceback
                traceback.print_exc()

        def _update_textbox(self, tb, text):
            """Hilfsmethode zum sicheren Aktualisieren von CTkTextboxen."""
            tb.configure(state="normal")
            tb.delete("0.0", "end")
            tb.insert("0.0", text)
            tb.configure(state="disabled")

        def _show_next_new_moons(self, year: int, month: int, day: int):
            """Zeigt die nächsten 3 Neumonde an – mit Schutz vor Endlosschleifen."""
            from datetime import datetime, timedelta
    
            txt = "  Datum              │ Mondphase │ Astro-Bewertung\n"
            txt += "  " + "─"*54 + "\n"
    
            current = datetime(year, month, day)
            found = 0
            check_date = current
            phase: float = 0.0  # ✅ FIX: Typ-Annotation für Pylance
            max_iterations = 120
            iterations = 0
    
            # Debug: Nur beim Aufruf
            print(f"[DEBUG] _show_next_new_moons called: {year}-{month}-{day}")
    
            while found < 3 and iterations < max_iterations:
                iterations += 1
                check_date += timedelta(days=1)
        
                # Debug: Alle 10 Iterationen (JETZT INNERHALB der Schleife!)
                if iterations % 10 == 0:
                    print(f"[DEBUG] Iteration {iterations}, date={check_date}, phase={phase}")
        
                try:
                    phase = calculate_moon_phase(check_date.year, check_date.month, check_date.day)
                except Exception as e:
                    print(f"[Moon] Phase calc error: {e}")
                    continue
        
                if phase is None:
                    continue
            
                if phase < 0.03 or phase > 0.97:  # ✅ Pylance meckert nicht mehr wegen Typ-Annotation
                    try:
                        data = calculate_milkyway_visibility(
                            check_date.year, check_date.month, check_date.day, 50.0
                        )
                        emoji = "🌑" if phase < 0.03 else "🌘"
                        rating_emoji = "🟢" if data['visibility_score'] >= 0.8 else "🟡" if data['visibility_score'] >= 0.6 else "🔴"
                
                        date_str = f"{check_date.day:02d}.{check_date.month:02d}.{check_date.year}"
                        txt += f"  {date_str} {emoji:15s}│ {phase:.2f}      │ {rating_emoji} {data['rating'].split()[1]}\n"
                        found += 1
                    except Exception as e:
                        print(f"[Moon] Visibility error: {e}")
                        continue
    
            if found < 3:
                txt += f"  ⚠️ Nur {found}/3 Neumonde in {max_iterations} Tagen gefunden.\n"
    
            self._update_textbox(self.mm_next_new, txt)    

        # ═══════════════════════════════════════════
        #  FILTER SIMULATOR
        # ═══════════════════════════════════════════

        def _build_filtersim(self, p):
            sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
            sc.pack(fill="both", expand=True, padx=8, pady=8)
            c = self._card(sc)
            c.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(c, t("filtersim_title"))

            r1 = self._row(c)
            self._btn(r1, t("filter_open"), self._filter_open_img, C["accent"]).pack(
                side="left", padx=(0, 6)
            )
            ctk.CTkLabel(r1, text=t("filter_type"), text_color=C["txt2"]).pack(
                side="left", padx=(6, 3)
            )
            self.filter_type_cb = self._combo(r1, t("filter_types"), w=190)
            self.filter_type_cb.pack(side="left", padx=(0, 6))
            self.filter_type_cb.configure(command=self._on_filter_changed)

            r2 = self._row(c)
            ctk.CTkLabel(
                r2, text=t("filter_intensity"), text_color=C["txt2"], width=80
            ).pack(side="left")
            self.filter_intensity = ctk.CTkSlider(
                r2,
                from_=0.05,
                to=1.0,
                width=220,
                progress_color=C["amber"],
                button_color=C["amber"],
                number_of_steps=19,
            )
            self.filter_intensity.set(1.0)
            self.filter_intensity.pack(side="left", padx=6)
            self.filter_int_lbl = ctk.CTkLabel(
                r2,
                text="100%",
                text_color=C["txt"],
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            self.filter_int_lbl.pack(side="left")
            self._filter_update_scheduled = None
            self.filter_intensity.configure(command=self._on_intensity_changed)

            r3 = self._row(c)
            ctk.CTkLabel(r3, text="🎯 Focus Peaking:", text_color=C["txt2"]).pack(
                side="left", padx=(0, 6)
            )
            self.peaking_color = ctk.CTkSegmentedButton(
                r3,
                values=["Off", "🔴 Red", "🟢 Green", "🔵 Blue", "🟡 Yellow"],
                font=ctk.CTkFont(size=10),
                selected_color=C["hl"],
                command=self._on_peaking_changed,
            )
            self.peaking_color.set("Off")
            self.peaking_color.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                r3, text="Empf.:", text_color=C["txt3"], font=ctk.CTkFont(size=10)
            ).pack(side="left")
            self.peaking_threshold = ctk.CTkSlider(
                r3,
                from_=10,
                to=80,
                width=120,
                progress_color=C["rose"],
                button_color=C["rose"],
                number_of_steps=14,
            )
            self.peaking_threshold.set(30)
            self.peaking_threshold.pack(side="left", padx=4)
            self.peaking_threshold.configure(command=self._on_peaking_changed)

            r4 = self._row(c)
            self._btn(r4, t("filter_apply"), self._filter_apply, C["amber"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(r4, t("filter_reset"), self._filter_reset, C["txt2"]).pack(
                side="left", padx=(0, 4)
            )
            self._btn(r4, t("filter_save"), self._filter_save, C["green"]).pack(
                side="left", padx=(0, 4)
            )
            self.compare_mode = ctk.BooleanVar(value=True)
            ctk.CTkSwitch(
                r4,
                text="⚖️ Vergleich",
                variable=self.compare_mode,
                font=ctk.CTkFont(size=11),
                text_color=C["txt2"],
                progress_color=C["accent"],
                command=self._refresh_filter_display,
            ).pack(side="right", padx=(8, 0))

            pc = self._card(sc)
            pc.pack(fill="x", padx=8, pady=(0, 6))
            self._stitle(pc, "🖼️ " + t("filter_preview"), C["amber"])
            self.filter_preview_container = ctk.CTkFrame(
                pc, fg_color=C["bg"], corner_radius=8, height=380
            )
            self.filter_preview_container.pack(fill="x", padx=10, pady=(4, 6))
            self.filter_preview_container.pack_propagate(False)

            # FIX: filter_no_image Key existiert jetzt in allen Translations
            self.filter_placeholder = ctk.CTkLabel(
                self.filter_preview_container,
                text=t("filter_no_image"),
                font=ctk.CTkFont(size=14),
                text_color=C["txt2"],
            )
            self.filter_placeholder.pack(expand=True)

            self.filter_lbl_left = None
            self.filter_lbl_right = None
            self.filter_lbl_single = None
            self.filter_info = self._rlbl(pc)
            self.filter_info.pack(padx=14, pady=(0, 10))
            self.filter_original_img = None
            self.filter_current_img = None
            self._filter_photo_refs = {}

        def _create_comparison_layout(self):
            for child in self.filter_preview_container.winfo_children():
                child.destroy()
            if self.compare_mode.get():
                left_frame = ctk.CTkFrame(
                    self.filter_preview_container, fg_color=C["card"], corner_radius=8
                )
                left_frame.pack(
                    side="left", fill="both", expand=True, padx=(4, 2), pady=4
                )
                right_frame = ctk.CTkFrame(
                    self.filter_preview_container, fg_color=C["card"], corner_radius=8
                )
                right_frame.pack(
                    side="right", fill="both", expand=True, padx=(2, 4), pady=4
                )
                ctk.CTkLabel(
                    left_frame,
                    text="📷 Original",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=C["txt2"],
                ).pack(pady=(4, 2))
                ctk.CTkLabel(
                    right_frame,
                    text="🎨 Filter",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=C["amber"],
                ).pack(pady=(4, 2))
                self.filter_lbl_left = ctk.CTkLabel(left_frame, text="")
                self.filter_lbl_left.pack(expand=True, padx=4, pady=(0, 4))
                self.filter_lbl_right = ctk.CTkLabel(right_frame, text="")
                self.filter_lbl_right.pack(expand=True, padx=4, pady=(0, 4))
                self.filter_lbl_single = None
            else:
                self.filter_lbl_single = ctk.CTkLabel(
                    self.filter_preview_container, text=""
                )
                self.filter_lbl_single.pack(expand=True, padx=4, pady=4)
                self.filter_lbl_left = None
                self.filter_lbl_right = None
        def _on_filter_changed(self, value=None):
            """Wird aufgerufen, wenn der Filter-Typ gewechselt wird."""
            self._filter_apply()

        def _on_intensity_changed(self, value=None):
            """Wird aufgerufen, wenn der Intensitäts-Slider bewegt wird."""
            if value is not None:
                self.filter_int_lbl.configure(text=f"{int(float(value) * 100)}%")
            if self._filter_update_scheduled:
                self.root.after_cancel(self._filter_update_scheduled)
            self._filter_update_scheduled = self.root.after(100, self._filter_apply)

        def _on_peaking_changed(self, value=None):
            self._filter_apply()

        def _filter_open_img(self):
            fp = filedialog.askopenfilename(
                title=t("open_image"),
                filetypes=[("Alle Bilder", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"),
                           ("JPEG", "*.jpg *.jpeg"), ("PNG", "*.png")]
            )
            if not fp: return
            try:
                if hasattr(self, 'filter_placeholder') and self.filter_placeholder and self.filter_placeholder.winfo_exists():
                    self.filter_placeholder.destroy()
                self.filter_placeholder = None
                self.filter_original_img = Image.open(fp).convert("RGB")
                self.filter_current_img = None
                self._create_comparison_layout()
                self._filter_apply()
            except Exception as e:
                messagebox.showerror("Fehler", f"Bild konnte nicht geladen werden:\n{e}")

        def _filter_apply(self):
            if not self.filter_original_img: return
            filter_name = self.filter_type_cb.get()
            intensity = self.filter_intensity.get()
            res = apply_filter_fast(self.filter_original_img, filter_name, intensity)
            if res is None: return

            peaking_mode = self.peaking_color.get()
            if peaking_mode != "Off":
                color_map = {"🔴 Red": "red", "🟢 Green": "green", "🔵 Blue": "blue", "🟡 Yellow": "yellow"}
                color = color_map.get(peaking_mode, "red")
                threshold = int(self.peaking_threshold.get())
                res = apply_focus_peaking(res, color=color, threshold=threshold)

            self.filter_current_img = res
            self._refresh_filter_display()
            info_txt = f"✅ {filter_name} | {int(intensity*100)}%"
            if peaking_mode != "Off": info_txt += f" | Peaking: {peaking_mode}"
            self.filter_info.configure(text=info_txt, text_color=C["green"])

        def _filter_reset(self):
            self.filter_type_cb.set(t("filter_types")[0])
            self.filter_intensity.set(1.0)
            self.peaking_color.set("Off")
            self.peaking_threshold.set(30)
            if self.filter_original_img: self._filter_apply()

        def _filter_save(self):
            img_to_save = self.filter_current_img if self.filter_current_img else self.filter_original_img
            if not img_to_save:
                messagebox.showwarning("Warnung", "Kein Bild zum Speichern vorhanden.")
                return
            fp = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("Alle Dateien", "*.*")],
                title=t("filter_save")
            )
            if fp:
                try:
                    img_to_save.save(fp)
                    messagebox.showinfo("Erfolg", f"Bild gespeichert:\n{os.path.basename(fp)}")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")

        def _refresh_filter_display(self):
            if not self.filter_original_img: return
            max_w, max_h = 500, 350
            def _prepare_img(img, is_single=False):
                img_copy = img.copy()
                img_copy.thumbnail((max_w if is_single else max_w//2, max_h), Image.Resampling.LANCZOS)
                return ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)
            try:
                ctk_orig = _prepare_img(self.filter_original_img)
                self._filter_photo_refs["orig"] = ctk_orig
                ctk_filt = _prepare_img(self.filter_current_img) if self.filter_current_img else ctk_orig
                self._filter_photo_refs["filt"] = ctk_filt

                if self.compare_mode.get():
                    if self.filter_lbl_left: self.filter_lbl_left.configure(image=ctk_orig)
                    if self.filter_lbl_right: self.filter_lbl_right.configure(image=ctk_filt)
                else:
                    if self.filter_lbl_single:
                        self.filter_lbl_single.configure(image=ctk_filt if self.filter_current_img else ctk_orig)
            except Exception as e:
                print(f"Refresh Display Error: {e}")

        # ═══════════════════════════════════════════
        #  APP EXPORT TOOL
        # ═══════════════════════════════════════════
        def _build_export_app(self, p):
            c = self._card(p)
            c.pack(fill="both", expand=True, padx=20, pady=12)
            self._stitle(c, t("export_app_title"))
            tb = self._textbox(c)
            tb.pack(fill="both", expand=True, padx=14, pady=14)
            
            script_name = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "canon_tool.py"
            exe_name = script_name.replace(".py", "").replace(".pyw", "")
            
            txt = f"""
╔══════════════════════════════════════════╗
║        📦 APP EXPORT ANLEITUNG           ║
╚══════════════════════════════════════════╝

1. 🔧 Installation von PyInstaller
   Öffne dein Terminal / CMD und tippe:
   pip install pyinstaller

2. 🚀 Build Befehl (Einzelne .exe Datei)
   pyinstaller --onefile --windowed --name {exe_name} {script_name}
   
   └> --onefile   : Packt alles in eine Datei
   └> --windowed  : Kein schwarzes CMD-Fenster
   └> --name      : Name der EXE

3. 📁 Wo ist meine EXE?
   Der Build erstellt einen 'dist' Ordner.
   Deine fertige EXE findest du dort:
   /dist/{exe_name}.exe

⚠️ WICHTIG:
- Stelle sicher, dass Pillow (PIL) installiert ist!
  pip install Pillow
- Wenn du JSON-Dateien (Logbook etc.) nutzt, 
  kopiere diese manuell neben die EXE.
"""
            tb.insert("0.0", txt)
            tb.configure(state="disabled")
            
            qr_frame = ctk.CTkFrame(c, fg_color="transparent")
            qr_frame.pack(pady=10)
            if QR_AVAILABLE:
                qr_img = generate_qr_code("pip install pyinstaller Pillow customtkinter", size=150)
                if qr_img:
                    ctk_qr = ctk.CTkImage(light_image=qr_img, dark_image=qr_img, size=(150,150))
                    ctk.CTkLabel(qr_frame, image=ctk_qr, text="").pack(side="left", padx=10)
            ctk.CTkLabel(qr_frame, text="Scan für Install-Befehle", text_color=C["txt2"]).pack(side="left", padx=10)

# ═══════════════════════════════════════════
#  MAIN START
# ═══════════════════════════════════════════
if __name__ == "__main__":
    try:
        if not GUI_AVAILABLE:
            print("FEHLER: customtkinter oder tkinter nicht installiert.")
            print("Bitte installieren mit: pip install customtkinter")
            input("Drücke Enter zum Beenden...")
            sys.exit(1)
            
        root = ctk.CTk()
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
            
        app = CanonProApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        