SHUTTER_MAP: dict[str, float] = {
    "1/8000": 1 / 8000, "1/4000": 1 / 4000, "1/2000": 1 / 2000,
    "1/1000": 1 / 1000, "1/500":  1 / 500,  "1/250":  1 / 250,
    "1/125":  1 / 125,  "1/60":   1 / 60,   "1/30":   1 / 30,
    "1/15":   1 / 15,   "1/8":    1 / 8,    "1/4":    1 / 4,
    "1/2":    1 / 2,    "1":      1.0,       "2":      2.0,
    "4":      4.0,      "8":      8.0,       "15":     15.0,
    "30":     30.0,     "60":     60.0,
}

CITY_COORDS: dict[str, tuple[float, float]] = {
    "Berlin":     (52.520, 13.405),
    "München":    (48.135, 11.582),
    "Hamburg":    (53.551,  9.994),
    "Köln":       (50.938,  6.960),
    "Frankfurt":  (50.111,  8.682),
    "Wien":       (48.208, 16.374),
    "Zürich":     (47.377,  8.542),
    "Stuttgart":  (48.775,  9.182),
    "Düsseldorf": (51.227,  6.773),
    "Leipzig":    (51.340, 12.375),
}
CITY_LIST = sorted(CITY_COORDS.keys())

COC_MAP: dict[str, float] = {
    "Vollformat (36×24 mm)":      0.030,
    "APS-C Canon (1.6×)":         0.019,
    "APS-C Nikon/Sony (1.5×)":    0.020,
    "Micro 4/3 (2.0×)":           0.015,
}

CROP_MAP: dict[str, float] = {
    "Vollformat (1.0×)":        1.0,
    "APS-C Canon (1.6×)":       1.6,
    "APS-C Nikon/Sony (1.5×)":  1.5,
    "Micro 4/3 (2.0×)":         2.0,
    "1 Zoll (2.7×)":            2.7,
    "Smartphone (~6×)":         6.0,
}

SHUTTERS_ALL = [
    "1/8000","1/4000","1/2000","1/1000","1/500","1/250",
    "1/125","1/60","1/30","1/15","1/8","1/4","1/2",
    "1","2","4","8","15","30","60",
]

ND_FILTERS = [
    ("Kein Filter", 0, 1), ("ND2 (1 Stop)", 1, 2), ("ND4 (2 Stops)", 2, 4),
    ("ND8 (3 Stops)", 3, 8), ("ND16 (4 Stops)", 4, 16), ("ND32 (5 Stops)", 5, 32),
    ("ND64 (6 Stops)", 6, 64), ("ND128 (7 Stops)", 7, 128), ("ND256 (8 Stops)", 8, 256),
    ("ND512 (9 Stops)", 9, 512), ("ND1000 (10 Stops)", 10, 1000), ("ND2000 (11 Stops)", 11, 2000),
    ("ND4000 (12 Stops)", 12, 4000),
]

BATTERY_MAP = {
    "LP-E6NH (2130 mAh) – ~370 Shots": 370,
    "LP-E6N  (1865 mAh) – ~350 Shots": 350,
    "LP-E6   (1800 mAh) – ~300 Shots": 300,
}

KUESTEN_ORTE = {
    "Rügen (Deutschland)": "54.32, 13.09",
    "Sylt (Deutschland)": "54.91, 8.31",
    "Norddeich (Deutschland)": "53.60, 7.15",
    "Cuxhaven (Deutschland)": "53.87, 8.70",
    "Norderney (Deutschland)": "53.71, 7.15",
    "Amrum (Deutschland)": "54.63, 8.33",
    "St. Peter-Ording (Deutschland)": "54.31, 8.62",
    "Ostende (Belgien)": "51.23, 2.93",
    "Dünkirchen (Frankreich)": "51.03, 2.38",
    "Le Havre (Frankreich)": "49.49, 0.11",
    "Brest (Frankreich)": "48.39, -4.49",
    "Liverpool (UK)": "53.41, -3.00",
    "Brighton (UK)": "50.82, -0.14",
    "Amsterdam (Niederlande)": "52.37, 4.90",
}

LENSES = [
    {"Name": "RF 14-35mm f/4L IS",      "Typ": "Weitwinkel Zoom",  "f/": 4.0,    "Gewicht": "540g",  "IS": "✅", "Preis": "~1.600€"},
    {"Name": "RF 15-35mm f/2.8L IS",    "Typ": "Weitwinkel Zoom",  "f/": 2.8,    "Gewicht": "840g",  "IS": "✅", "Preis": "~2.500€"},
    {"Name": "RF 24-70mm f/2.8L IS",    "Typ": "Standard Zoom",    "f/": 2.8,    "Gewicht": "900g",  "IS": "✅", "Preis": "~2.700€"},
    {"Name": "RF 24-105mm f/4L IS",     "Typ": "Standard Zoom",    "f/": 4.0,    "Gewicht": "700g",  "IS": "✅", "Preis": "~1.200€"},
    {"Name": "RF 50mm f/1.2L USM",      "Typ": "Standard Prime",   "f/": 1.2,    "Gewicht": "950g",  "IS": "❌", "Preis": "~2.400€"},
    {"Name": "RF 50mm f/1.8 STM",       "Typ": "Standard Prime",   "f/": 1.8,    "Gewicht": "160g",  "IS": "❌", "Preis": "~230€"},
    {"Name": "RF 85mm f/1.2L USM",      "Typ": "Portrait Prime",   "f/": 1.2,    "Gewicht": "1195g", "IS": "❌", "Preis": "~3.000€"},
    {"Name": "RF 85mm f/2 Macro IS",    "Typ": "Portrait Prime",   "f/": 2.0,    "Gewicht": "500g",  "IS": "✅", "Preis": "~700€"},
    {"Name": "RF 70-200mm f/2.8L IS",   "Typ": "Tele Zoom",        "f/": 2.8,    "Gewicht": "1070g", "IS": "✅", "Preis": "~2.900€"},
    {"Name": "RF 100-500mm f/4.5-7.1L", "Typ": "Supertele Zoom",   "f/": "4.5-7","Gewicht": "1370g", "IS": "✅", "Preis": "~3.000€"},
    {"Name": "RF 100mm f/2.8L Macro IS","Typ": "Makro Prime",      "f/": 2.8,    "Gewicht": "730g",  "IS": "✅", "Preis": "~1.500€"},
]

KI_DB = {
    "sunset":    ("🌅 SUNSET",    "ISO 100 | f/8 | 1/125s",    "GND-Filter | Stativ | Bracketing"),
    "portrait":  ("👤 PORTRAIT",  "ISO 100 | f/1.8 | 1/200s",  "Eye-AF | 85 mm | Offener Schatten"),
    "night":     ("🌙 NACHT",     "ISO 1600 | f/2.8 | 10s",    "Stativ | Fernauslöser | RAW"),
    "landscape": ("🏔️ LANDSCHAFT","ISO 100 | f/11 | 1/60s",    "Stativ | Polfilter | Golden Hour"),
    "street":    ("🏙️ STREET",    "ISO 400 | f/5.6 | 1/250s",  "35 mm | Zone Focus | Burst"),
    "macro":     ("🔬 MAKRO",     "ISO 200 | f/8 | 1/160s",    "Focus Stack | Stativ | Diffusor"),
    "sport":     ("⚡ SPORT",     "ISO 800 | f/4 | 1/1000s",   "AI Servo | Burst | 70–200 mm"),
    "astro":     ("🌌 ASTRO",     "ISO 3200 | f/1.8 | 20s",    "500er-Regel | Neumond | MF ∞"),
}

GUIDES = {
    "Portrait": """
👤 PORTRAIT
══════════════════════════════
Brennweite:  85–135 mm
Blende:      f/1.4 – f/2.8
ISO:         100–400
Verschluss:  1/200s+
FOKUS:   Eye-AF | Single Point
LICHT:   Offener Schatten | Golden Hour
TIPPS:   Augen im oberen Drittel | Burst
""",
    "Landschaft": """
🏔️ LANDSCHAFT
══════════════════════════════
Brennweite:  16–35 mm
Blende:      f/8 – f/16
ISO:         100
Verschluss:  Stativ!
FOKUS:   1/3 der Szene | Hyperfokus
FILTER:  Polfilter + GND
ZEIT:    Golden Hour | Blaue Stunde
""",
    "Nacht/Astro": """
🌙 NACHT & ASTRO
══════════════════════════════
Brennweite:  14–24 mm
Blende:      f/1.4 – f/2.8
ISO:         1600–6400
Verschluss:  500 ÷ Brennweite (max)
FOKUS:   MF auf hellen Stern
SETUP:   Neumond | Stativ | RAW
STACK:   Sequator / Starry Landscape
""",
    "Street": """
🏙️ STREET
══════════════════════════════
Brennweite:  28–50 mm (35 mm klassisch)
Blende:      f/5.6 – f/8
ISO:         Auto (max 3200)
Verschluss:  1/250s+
TECHNIK:  Zone Focus @ 3 m
TIPPS:    Unauffällig | Burst | Hüfte
""",
    "Makro": """
🔬 MAKRO
══════════════════════════════
Brennweite:  90–105 mm Makro
Blende:      f/5.6 – f/11
ISO:         200–800
Verschluss:  1/160s+
FOKUS:   MF | Focus Stacking
LICHT:   Diffuses Licht | Ringblitz
STATIV:  Makroschlitten empfohlen
""",
    "Sport": """
⚡ SPORT
══════════════════════════════
Brennweite:  70–400 mm
Blende:      f/2.8 – f/4
ISO:         800–3200
Verschluss:  1/1000s minimum!
AF:      AI Servo | Zone AF
BURST:   High-Speed Continuous
TIPP:    Action voraussehen
""",
    "Hochzeit": """
💍 HOCHZEIT
══════════════════════════════
ISO:         400–1600 (Kirche: 3200)
Blende:      f/2.8 – f/4
Verschluss:  1/250s+
EQUIPMENT: 2 Bodies! | 24–70 + 70–200
BACKUP:    Dual Card | 4+ Akkus
SHOT LIST: Getting Ready → Tanz
""",
}

WB_DATA = [
    ("🕯️ Kerzenlicht",    "1800–2000 K", "#FF6B35"),
    ("💡 Glühlampe",      "2700–3200 K", "#FFA500"),
    ("🌅 Sonnenaufgang",  "3000–3500 K", "#FF8C42"),
    ("📸 Blitz",          "5000–5500 K", "#FFFEF0"),
    ("☀️ Tageslicht",     "5200–5800 K", "#FFFFF0"),
    ("⛅ Bewölkt",        "6000–6500 K", "#E8F0FF"),
    ("🏔️ Schatten",      "7000–8000 K", "#D0E0FF"),
    ("🌌 Blaue Stunde",   "9000–12000 K","#9090FF"),
]

SHUTTERS_LOG = ["1/1000","1/500","1/250","1/125","1/60","1/30","1/15","1s","2s","4s"]
