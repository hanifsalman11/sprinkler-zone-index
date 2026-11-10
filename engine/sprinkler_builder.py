import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/sprinkler-zone-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3").strip()
CUSTOM_SPRINKLER = os.environ.get("CUSTOM_SPRINKLER", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_sprinklers.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Head Model / Lawn Scenario, Supply GPM, Dynamic PSI, GPM per Head, Head Spacing Ft, Lawn Area Sq Ft, Pipe Spec)
SEED_SPRINKLERS = [
    ("Hunter PGP-ADJ / PGP Ultra Rotor (3.0 GPM #3.0 Nozzle)", 12.0, 50, 3.0, 32, 5000, "1-Inch Schedule 40 PVC / Poly"),
    ("Rain Bird 5000 / 5004-PC Plus Rotor (3.0 GPM Rain Curtain)", 12.0, 50, 3.0, 32, 5000, "1-Inch Schedule 40 PVC / Poly"),
    ("Hunter MP Rotator MP1000 / MP2000 High-Efficiency Nozzle", 10.0, 45, 0.75, 18, 4000, "3/4-Inch or 1\" PVC / Poly"),
    ("Rain Bird R-VAN 14 / 18 / 24 Rotary Nozzle Retrofit", 10.0, 45, 0.85, 18, 4000, "3/4-Inch or 1\" PVC / Poly"),
    ("Rain Bird 1804-SAM-PRS30 Pop-Up Fixed Spray (15-Ft Nozzle)", 11.0, 45, 1.85, 15, 3500, "1-Inch Schedule 40 PVC"),
    ("Hunter Pro-Spray PRS40 + MP3000 (30-Ft Radius Rotator)", 12.0, 50, 1.50, 28, 6000, "1-Inch Schedule 40 PVC"),
    ("Hunter PGJ-04 Mid-Range Gear-Drive Rotor (2.0 GPM)", 10.0, 45, 2.00, 22, 4000, "3/4-Inch or 1\" Poly/PVC"),
    ("Rain Bird 3504-PC SAM Mid-Range Rotor (2.0 GPM Nozzle)", 10.0, 45, 2.00, 22, 4000, "3/4-Inch or 1\" Poly/PVC"),
    ("K-Rain RPS75 & MiniPro Gear-Drive Rotor Zone Sizing", 12.0, 50, 2.80, 30, 5000, "1-Inch PVC / Poly Pipe"),
    ("Orbit Saturn III & Voyager II Gear-Drive Rotor Zone Sizing", 11.0, 45, 2.50, 26, 4500, "3/4-Inch or 1\" Poly/PVC"),
    ("Hunter PGV-101G 1-Inch 24VAC Manifold Solenoid Valve", 14.0, 55, 3.00, 32, 6000, "1-Inch Action Manifold"),
    ("Rain Bird DV100 & JTV 1-Inch Solenoid Valve Manifold", 14.0, 55, 3.00, 32, 6000, "1-Inch Schedule 40 Manifold"),
    ("Febco 765-1 (1-Inch) vs 765-3/4 Pressure Vacuum Breaker", 14.0, 55, 3.00, 32, 6500, "1-Inch Brass PVB Backflow"),
    ("Zurn Wilkins 720A & Watts 800M4-QT 1\" Backflow Preventer", 13.0, 50, 3.00, 32, 6000, "1-Inch Brass PVB Backflow"),
    ("Rachio 3 Smart 8-Zone vs 16-Zone Wi-Fi Sprinkler Controller", 12.0, 50, 2.50, 28, 7500, "18/8 Multi-Strand Wire"),
    ("Orbit B-hyve XR 8-Zone & 16-Zone Smart Indoor/Outdoor Timer", 12.0, 50, 2.50, 28, 7000, "18/8 Multi-Strand Wire"),
    ("Hunter I-20 Ultra & I-25 Commercial Stainless Rotor Zone", 16.0, 60, 4.00, 38, 10000, "1-1/4\" Schedule 40 Mainline"),
    ("Rain Bird Falcon 6504 Large-Turf & Pasture Rotor Sizing", 18.0, 65, 4.50, 42, 12000, "1-1/4\" Schedule 40 Mainline"),
    ("3/4-Inch (9 GPM Limit) vs 1-Inch (15 GPM Limit) Sprinkler Pipe", 13.0, 50, 3.00, 32, 5500, "5 FPS Velocity Rule"),
    ("100-Lb SIDR-7 / 160-PSI Polyethylene Pipe vs Sch 40 PVC", 12.0, 50, 2.80, 30, 5000, "1-Inch Poly Pinch Clamps"),
    ("2,500 Sq Ft Small Front Yard Sprinkler Zone & Head Sizing", 10.0, 45, 2.00, 22, 2500, "3/4-Inch or 1\" PVC/Poly"),
    ("5,000 Sq Ft Suburban Lawn Sprinkler Zone & Manifold Sizing", 12.0, 50, 3.00, 32, 5000, "1-Inch PVC / Poly Pipe"),
    ("7,500 Sq Ft Quarter-Acre Lawn Sprinkler Zone & Valve Sizing", 13.0, 55, 3.00, 32, 7500, "1-Inch Schedule 40 PVC"),
    ("10,000 Sq Ft Half-Acre Lot Sprinkler Zone & Controller Sizing", 15.0, 55, 3.00, 34, 10000, "1-Inch or 1-1/4\" Mainline"),
    ("15,000 Sq Ft Estate Lawn 12-to-16 Zone Irrigation Sizing", 16.0, 60, 3.20, 35, 15000, "1-1/4\" Main + 1\" Laterals"),
    ("8 GPM Low-Flow Well Pump Lawn Sprinkler Zone Sizing", 8.0, 45, 1.50, 24, 4500, "MP Rotator Low-GPM Zones"),
    ("10 GPM City Water Meter (5/8\") Lawn Sprinkler Zone Sizing", 10.0, 50, 2.50, 28, 5000, "3/4\" or 1\" Lateral Pipe"),
    ("15 GPM High-Flow 1\" Water Meter Lawn Sprinkler Sizing", 15.0, 60, 3.00, 32, 8000, "1-Inch Lateral Pipe"),
    ("1.5 HP Cast-Iron Lawn Sprinkler Booster Pump (Lake/Well)", 22.0, 65, 3.50, 35, 10000, "1-1/4\" Suction + 1\" Zones"),
    ("Drip Irrigation Pressure Regulator (25 PSI) & GPH Emitter Zone", 8.0, 25, 0.50, 12, 1500, "1/2-Inch Poly Drip Tubing")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=12.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_sprinkler_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial GPM × Lawn Area × Head Type Permutator.
    """
    discovered = []
    seeds = [
        "how many sprinkler heads per zone ",
        "hunter pgp rotor ",
        "rain bird 5000 rotor ",
        "sprinkler zone calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "how many" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        gpm_m = re.search(r"\b(8|10|12|14|15|18|20)\s*gpm\b", cleaned)
                        sup_gpm = float(gpm_m.group(1)) if gpm_m else 12.0
                        discovered.append((cleaned.title(), sup_gpm, 50, 3.0, 30, 5000, "1-Inch Schedule 40 PVC"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    gpm_supplies = [8.0, 10.0, 12.0, 14.0, 16.0, 20.0]
    lawn_areas = [3000, 4500, 6000, 8000, 10000, 14000]
    head_types = [
        ("Hunter PGP / Rain Bird 5000 Rotors (3.0 GPM)", 3.0, 32),
        ("Mid-Range Gear Rotors (2.0 GPM)", 2.0, 22),
        ("High-Efficiency MP Rotators (0.8 GPM)", 0.8, 18),
        ("Fixed Pop-Up Spray Heads (1.8 GPM)", 1.8, 15)
    ]
    for s_gpm in gpm_supplies:
        for l_area in lawn_areas:
            for h_desc, h_gpm, h_sp in head_types:
                combo_title = f"{l_area:,} Sq Ft Lawn on {s_gpm:g} GPM Supply ({h_desc})"
                test_slug = slugify(f"{combo_title}-heads-per-zone-calculator")
                if test_slug not in published_slugs:
                    p_spec = "3/4-Inch Poly/PVC" if s_gpm <= 10.0 else ("1-Inch PVC/Poly" if s_gpm <= 16.0 else "1-1/4\" Mainline PVC")
                    discovered.append((combo_title, s_gpm, 50, h_gpm, h_sp, l_area, p_spec))
                    if len(discovered) >= 25:
                        return discovered
    return discovered


def build_deterministic_sprinkler_data(sprk_tuple):
    """
    LAPIS 3: Mesin Fisika Hidrolika Pipa Irigasi (5-FPS Rule) & ASABE Precipitation Rate (100% Bebas Gagal).
    """
    model_name, supply_gpm, dyn_psi, head_gpm, spacing_ft, lawn_sqft, pipe_spec = sprk_tuple

    # 1. Batas Debit Aman Zona (75% dari Bucket Test Supply GPM, dan dibatasi oleh 5 FPS Pipe Velocity):
    # Batas 5 FPS: Pipa 3/4" = max 9.0 GPM; Pipa 1" = max 14.5 GPM; Pipa 1-1/4" = max 24.0 GPM
    pipe_cap_gpm = 9.0 if "3/4" in pipe_spec else (22.0 if "1-1/4" in pipe_spec else 14.5)
    safe_zone_gpm = round(min(supply_gpm * 0.78, pipe_cap_gpm), 1)

    # 2. Jumlah Kepala Sprinkler Maksimal Per Zona & Total Kepala untuk Seluruh Taman (Head-to-Head Spacing):
    max_heads_per_zone = max(2, int(math.floor(safe_zone_gpm / max(0.3, float(head_gpm)))))
    actual_zone_gpm = round(max_heads_per_zone * head_gpm, 1)

    area_per_head_sqft = max(140.0, float(spacing_ft * spacing_ft * 0.65))
    total_heads_needed = max(6, int(math.ceil(lawn_sqft / area_per_head_sqft)))
    total_zones_needed = max(2, int(math.ceil(float(total_heads_needed) / float(max_heads_per_zone))))

    # 3. ASABE Precipitation Rate (Inches/Hour) & Durasi Siram (Menit untuk 0.50 inci air):
    # PR (in/hr) = (96.25 * Head_GPM) / (Spacing_Ft * Spacing_Ft)
    precip_rate_in_hr = round((96.25 * head_gpm) / max(100.0, float(spacing_ft * spacing_ft * 0.75)), 2)
    precip_rate_in_hr = max(0.35, min(1.85, precip_rate_in_hr))
    runtime_min_for_half_in = int(round((0.50 / precip_rate_in_hr) * 60.0))

    # Ukuran Smart Controller (8-Zone vs 12-Zone vs 16-Zone)
    ctrl_zones = 8 if total_zones_needed <= 8 else (12 if total_zones_needed <= 12 else 16)

    return {
        "system_name": model_name,
        "pipe_spec": pipe_spec,
        "seo_title": f"{model_name} Heads Per Zone, GPM & Pipe Size Calculator (2026)",
        "meta_description": f"Calculate exact sprinkler heads per zone ({max_heads_per_zone} heads @ {actual_zone_gpm} GPM), total solenoid zones ({total_zones_needed} zones / {total_heads_needed} heads), 5-FPS {pipe_spec} sizing, and {runtime_min_for_half_in}-min runtime for {model_name}.",
        "specs": {
            "supply_flow_gpm": supply_gpm,
            "working_pressure_psi": dyn_psi,
            "safe_zone_design_gpm": safe_zone_gpm,
            "gpm_per_head": head_gpm,
            "head_spacing_ft": spacing_ft,
            "max_heads_per_zone": max_heads_per_zone,
            "actual_zone_flow_gpm": actual_zone_gpm,
            "lawn_area_sqft": lawn_sqft,
            "total_sprinkler_heads": total_heads_needed,
            "total_solenoid_zones": total_zones_needed,
            "precipitation_rate_in_hr": precip_rate_in_hr,
            "runtime_minutes_half_inch": runtime_min_for_half_in,
            "recommended_controller_zones": ctrl_zones,
            "pipe_spec": pipe_spec
        },
        "hydraulic_verdict": f"With a raw water supply of {supply_gpm:g} GPM at {dyn_psi} PSI and a 5.0 ft/sec Hazen-Williams pipe velocity ceiling inside {pipe_spec}, your maximum safe design flow is {safe_zone_gpm} GPM per zone. Using {head_gpm} GPM nozzles spaced {spacing_ft} feet head-to-head ({model_name}), you can run up to {max_heads_per_zone} sprinkler heads per zone ({actual_zone_gpm} GPM/zone). Covering {lawn_sqft:,} sq. ft. of turf requires {total_heads_needed} total heads divided across a {total_zones_needed}-Zone Solenoid Valve Manifold controlled by an {ctrl_zones}-Zone Smart Wi-Fi Timer, running {runtime_min_for_half_in} minutes per zone ({precip_rate_in_hr}\" per hour precipitation rate) to apply 0.5 inches of water.",
        "hardware_bundle": [
            {
                "badge": f"{ctrl_zones}-Zone Wi-Fi Controller",
                "title": f"{ctrl_zones}-Zone Smart Wi-Fi Weather-Skipping Sprinkler Controller (Rachio 3 / Orbit B-hyve / Rain Bird)",
                "price_range": "$119 - $249",
                "amazon_query": f"{ctrl_zones} Zone Smart WiFi Sprinkler Controller Rachio Orbit B-hyve Rain Bird",
                "irr_note": f"Automates all {total_zones_needed} zones ({runtime_min_for_half_in} min/zone) and skips watering automatically before rainstorms."
            },
            {
                "badge": f"{total_zones_needed}-Valve 1\" Manifold Kit",
                "title": "Pre-Assembled 1-Inch 24VAC Solenoid Valve Manifold System (Hunter PGV-101G / Rain Bird DV100) + Valve Box",
                "price_range": "$94 - $229",
                "amazon_query": "Hunter PGV Rain Bird 1 Inch 4 Valve Sprinkler Manifold Kit Valve Box",
                "irr_note": f"Flows {actual_zone_gpm} GPM per zone with <2 PSI pressure loss and swivels apart with O-ring unions—no PVC glue required."
            },
            {
                "badge": f"{total_heads_needed}+ Pack Rotors / Heads",
                "title": f"Contractor Case 4\" Pop-Up Gear-Drive Rotors / High-Efficiency Nozzles + Swing Joint Funny Pipe Kit",
                "price_range": "$89 - $259",
                "amazon_query": "Hunter PGP ADJ Rain Bird 5004 Rotor Sprinkler Heads Pack Funny Pipe",
                "irr_note": f"Head-to-head {spacing_ft}-ft spacing delivers {precip_rate_in_hr} in/hr uniform coverage without dry brown donuts."
            },
            {
                "badge": "1\" Brass PVB Backflow",
                "title": "1-Inch Brass Pressure Vacuum Breaker (PVB) Backflow Preventer (Febco 765 / Zurn Wilkins) + 18/8 Wire",
                "price_range": "$129 - $329",
                "amazon_query": "Febco 765 1 Inch Pressure Vacuum Breaker Backflow Preventer Sprinkler Wire",
                "irr_note": "Required by plumbing code to prevent lawn fertilizers and stagnant puddle water from backsiphoning into home drinking water."
            }
        ],
        "irrigation_checklist": [
            f"Never exceed the 5.0 Feet-Per-Second (FPS) Pipe Velocity Rule: 3/4-inch pipe maxes out at 9 GPM, and 1-inch pipe maxes out at 14.5 GPM. Running {actual_zone_gpm} GPM per zone through {pipe_spec} prevents destructive water hammer when 24VAC solenoid valves snap shut.",
            f"Design for 100% Head-to-Head Coverage ({spacing_ft}-ft throw radius = {spacing_ft}-ft spacing between heads): spacing heads 2x their radius apart leaves dead brown triangles every July.",
            "Never mix Gear-Drive Rotors (~0.45 in/hr precipitation rate) and Fixed Pop-Up Spray Heads (~1.55 in/hr precipitation rate) on the same solenoid valve zone—spray heads put down water 3.5x faster and will flood one area while rotors underwater the rest.",
            "Matched Nozzle GPM by Arc Angle: if a 90° quarter-circle corner rotor uses a 1.5 GPM nozzle, a 180° half-circle side rotor on the same zone should use a 3.0 GPM nozzle, and a 360° center rotor should use a 6.0 GPM nozzle so all areas receive equal water depth."
        ],
        "faqs": [
            {
                "q": f"How many {model_name} heads can I put on one zone with {supply_gpm:g} GPM?",
                "a": f"Using a 78% hydraulic safety margin on your {supply_gpm:g} GPM supply (and respecting the 5-FPS velocity limit of {pipe_spec}) gives {safe_zone_gpm} usable GPM per zone. Dividing {safe_zone_gpm} GPM by {head_gpm} GPM per head allows {max_heads_per_zone} heads per zone ({actual_zone_gpm} GPM total)."
            },
            {
                "q": f"How many sprinkler zones do I need for a {lawn_sqft:,} sq ft lawn?",
                "a": f"At {spacing_ft}-foot head-to-head spacing, covering {lawn_sqft:,} sq. ft. requires approximately {total_heads_needed} sprinkler heads. At {max_heads_per_zone} heads per zone, divide your manifold into {total_zones_needed} zones paired with an {ctrl_zones}-zone smart controller."
            },
            {
                "q": f"How many minutes per zone should I run {model_name}?",
                "a": f"With a precipitation rate of {precip_rate_in_hr} inches per hour ($\\text{{PR}} = [96.25 \\times {head_gpm}] \\div \\text{{Area}}$), applying 0.50 inches of water per watering day takes {runtime_min_for_half_in} minutes per zone ($0.50 \\div {precip_rate_in_hr} \\times 60 = {runtime_min_for_half_in}\\text{{ min}}$)."
            }
        ]
    }


def generate_sprinkler_data(sprk_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_sprinkler_data(sprk_tuple)

    model_name, supply_gpm, dyn_psi, head_gpm, spacing_ft, lawn_sqft, pipe_spec = sprk_tuple
    det_fallback = build_deterministic_sprinkler_data(sprk_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Irrigation Designer (CID — Irrigation Association) & Turf Hydraulic Engineer. Create an accurate 2026 lawn sprinkler heads-per-zone, 5-FPS pipe velocity, solenoid valve manifold, and precipitation rate runtime guide for: "{model_name}".
Baseline specs: Supply={supply_gpm} GPM @ {dyn_psi} PSI (Safe Zone Design={sp['safe_zone_design_gpm']} GPM), Nozzle={head_gpm} GPM ({spacing_ft}ft Head-to-Head Spacing), Max Heads/Zone={sp['max_heads_per_zone']} ({sp['actual_zone_flow_gpm']} GPM/zone), Lawn={lawn_sqft} sq ft ({sp['total_sprinkler_heads']} total heads / {sp['total_solenoid_zones']} zones), Precipitation Rate={sp['precipitation_rate_in_hr']} in/hr ({sp['runtime_minutes_half_inch']} min runtime for 0.5" water), Pipe={pipe_spec}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "system_name": "{model_name}",
  "pipe_spec": "{pipe_spec}",
  "seo_title": "{model_name} Heads Per Zone, GPM & Pipe Size Calculator (2026)",
  "meta_description": "Calculate exact lawn sprinkler heads per zone, 5-FPS PVC/Poly pipe size, solenoid valve manifold count, and watering runtime minutes for {model_name}.",
  "specs": {{
    "supply_flow_gpm": {supply_gpm},
    "working_pressure_psi": {dyn_psi},
    "safe_zone_design_gpm": {sp['safe_zone_design_gpm']},
    "gpm_per_head": {head_gpm},
    "head_spacing_ft": {spacing_ft},
    "max_heads_per_zone": {sp['max_heads_per_zone']},
    "actual_zone_flow_gpm": {sp['actual_zone_flow_gpm']},
    "lawn_area_sqft": {lawn_sqft},
    "total_sprinkler_heads": {sp['total_sprinkler_heads']},
    "total_solenoid_zones": {sp['total_solenoid_zones']},
    "precipitation_rate_in_hr": {sp['precipitation_rate_in_hr']},
    "runtime_minutes_half_inch": {sp['runtime_minutes_half_inch']},
    "recommended_controller_zones": {sp['recommended_controller_zones']},
    "pipe_spec": "{pipe_spec}"
  }},
  "hydraulic_verdict": "3-sentence technical summary stating safe GPM per zone under the 5-FPS pipe velocity rule, max heads per zone, total zones for {lawn_sqft} sq ft, and runtime minutes per zone.",
  "hardware_bundle": [
    {{
      "badge": "{sp['recommended_controller_zones']}-Zone Wi-Fi Controller",
      "title": "{sp['recommended_controller_zones']}-Zone Smart Wi-Fi Weather-Sense Sprinkler Controller (Rachio / Orbit / Rain Bird)",
      "price_range": "$119 - $249",
      "amazon_query": "{sp['recommended_controller_zones']} Zone Smart WiFi Sprinkler Controller Rachio Orbit Rain Bird",
      "irr_note": "1-sentence smart weather-skipping and zone scheduling note"
    }},
    {{
      "badge": "{sp['total_solenoid_zones']}-Valve 1\" Manifold",
      "title": "Pre-Assembled 1-Inch 24VAC Solenoid Valve Manifold Kit (Hunter PGV / Rain Bird) + Box",
      "price_range": "$94 - $229",
      "amazon_query": "Hunter PGV Rain Bird 1 Inch Valve Sprinkler Manifold Kit",
      "irr_note": "1-sentence O-ring union assembly and low friction loss note"
    }},
    {{
      "badge": "{sp['total_sprinkler_heads']}+ Pack Sprinkler Heads",
      "title": "Contractor Case 4\" Pop-Up Gear-Drive Rotors / Nozzles + Funny Pipe Swing Joints",
      "price_range": "$89 - $259",
      "amazon_query": "Hunter PGP Rain Bird 5004 Rotor Sprinkler Heads Pack",
      "irr_note": "1-sentence head-to-head spacing uniformity note"
    }},
    {{
      "badge": "1\" Brass PVB Backflow",
      "title": "1-Inch Brass Pressure Vacuum Breaker (PVB) Backflow Preventer (Febco 765) + 18/8 Wire",
      "price_range": "$129 - $329",
      "amazon_query": "Febco 765 1 Inch Pressure Vacuum Breaker Backflow Preventer",
      "irr_note": "1-sentence potable water backsiphon protection note"
    }}
  ],
  "irrigation_checklist": [
    "Step 1 regarding 5.0 FPS pipe velocity limit (9 GPM for 3/4-inch vs 14.5 GPM for 1-inch pipe)",
    "Step 2 regarding 100% head-to-head spacing ({spacing_ft} ft throw = {spacing_ft} ft spacing)",
    "Step 3 regarding never mixing rotors and fixed spray heads on the same valve zone",
    "Step 4 regarding matching nozzle GPM to 90, 180, and 360 degree arcs"
  ],
  "faqs": [
    {{"q": "How many heads per zone can I run with {model_name}?", "a": "Exact supply GPM, 78% design flow, nozzle GPM, and max heads per zone."}},
    {{"q": "Should I use 3/4-inch or 1-inch pipe for my sprinkler system?", "a": "Exact 5-FPS GPM limits and friction loss comparison."}},
    {{"q": "How long should I run each zone for 0.5 inches of water?", "a": "Exact precipitation rate (in/hr) and runtime minutes calculation."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_sprinkler_html_page(data, slug, mon_cfg):
    sys_name = data.get("system_name", "Lawn Irrigation Sprinkler System")
    sp = data.get("specs", {})
    sup_gpm = round(safe_float(sp.get("supply_flow_gpm", 12.0), 12.0), 1)
    psi = int(safe_float(sp.get("working_pressure_psi", 50), 50))
    head_gpm = round(safe_float(sp.get("gpm_per_head", 3.0), 3.0), 2)
    heads_zn = int(safe_float(sp.get("max_heads_per_zone", 3), 3))
    zn_gpm = round(safe_float(sp.get("actual_zone_flow_gpm", 9.0), 9.0), 1)
    lawn_sq = int(safe_float(sp.get("lawn_area_sqft", 5000), 5000))
    tot_heads = int(safe_float(sp.get("total_sprinkler_heads", 12), 12))
    tot_zones = int(safe_float(sp.get("total_solenoid_zones", 4), 4))
    pr_rate = round(safe_float(sp.get("precipitation_rate_in_hr", 0.42), 0.42), 2)
    run_min = int(safe_float(sp.get("runtime_minutes_half_inch", 45), 45))
    pipe_s = sp.get("pipe_spec", "1-Inch Schedule 40 PVC")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Rain+Bird+Hunter+PGP+Rotor+Sprinkler+Valve+Manifold"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{sys_name} Heads Per Zone & GPM Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Hunter PGP Rain Bird Sprinkler")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-emerald-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Irrigation Gear')}</span>
              <span class="text-sm font-bold text-cyan-400">{item.get('price_range', '$89+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🌱 {item.get('irr_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Pipe Size (5 FPS Rule) vs Max Zone GPM & Heads Per Zone Reference Matrix Table
    irr_tiers = [
        ("1/2\" PVC / Poly Pipe", "4.5 GPM Max (@5 FPS)", "1 Rotor (3.0 GPM)", "5 MP Rotators (0.8 GPM)", "Swing Joints / Drip Only"),
        ("3/4\" Schedule 40 PVC / Poly", "9.0 GPM Max (@5 FPS)", "3 Rotors (3.0 GPM ea)", "10 MP Rotators (0.8 GPM)", "Small Yard Laterals"),
        ("1\" Schedule 40 PVC / Poly", "14.5 GPM Max (@5 FPS)", "4–5 Rotors (3.0 GPM ea)", "16 MP Rotators (0.8 GPM)", "Standard Residential Main/Zone"),
        ("1-1/4\" Schedule 40 PVC", "24.0 GPM Max (@5 FPS)", "7–8 Rotors (3.0 GPM ea)", "26 MP Rotators (0.8 GPM)", "Large Estate / Booster Main"),
        ("1-1/2\" Schedule 40 PVC", "33.0 GPM Max (@5 FPS)", "10 Rotors (3.0 GPM ea)", "38 MP Rotators (0.8 GPM)", "Commercial Turf Mainline")
    ]
    matrix_rows_html = ""
    for p_lbl, g_lbl, r_lbl, m_lbl, u_lbl in irr_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{p_lbl}</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{g_lbl}</td>
          <td class="py-3 px-4 text-cyan-400 font-semibold">{r_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{m_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{u_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("irrigation_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-emerald-500 rounded cursor-pointer irr-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>CID Hydraulic Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', sys_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', sys_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">SPRINKLER</span>ZoneIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Rotors, Valves & Controllers →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-emerald-500 text-slate-950 px-3 py-1 rounded-full">{heads_zn} Heads/Zone ({zn_gpm} GPM)</span>
        <span class="text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-3 py-1 rounded-full">{tot_zones} Zones ({tot_heads} Total Heads)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{pipe_s} | Run: {run_min} Min/Zone</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', sys_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-emerald-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>CID 5-FPS Pipe Velocity & Hydrozoning Verdict:</strong> {data.get('hydraulic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE SPRINKLER HEADS PER ZONE, MANIFOLD COUNT & RUNTIME CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {sys_name} Zone, Pipe & Runtime Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your water supply flow rate (Bucket Test GPM), sprinkler nozzle type, total lawn square footage, and pipe size to calculate exact heads per zone, solenoid valve count, and watering minutes.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="gpmSlider" class="text-slate-300">Water Supply Flow Rate (5-Gallon Bucket Test GPM)</label>
              <span class="text-emerald-400 font-bold"><span id="gpmVal">{sup_gpm:g}</span> GPM</span>
            </div>
            <input id="gpmSlider" type="range" min="5.0" max="26.0" step="0.5" value="{sup_gpm}" class="w-full accent-emerald-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="nozzleSelect" class="block text-xs font-medium text-slate-400 mb-1">Sprinkler Head & Nozzle GPM</label>
              <select id="nozzleSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="0.80|18|0.42" {"selected" if head_gpm <= 1.0 else ""}>MP Rotator / R-VAN (0.8 GPM, 18' R)</option>
                <option value="1.80|15|1.55" {"selected" if 1.0 < head_gpm <= 1.9 else ""}>Fixed Pop-Up Spray (1.8 GPM, 15' R)</option>
                <option value="2.00|24|0.48" {"selected" if 1.9 < head_gpm <= 2.4 else ""}>Mid-Range Rotor PGJ (2.0 GPM, 24' R)</option>
                <option value="3.00|32|0.44" {"selected" if head_gpm > 2.4 else ""}>Full Rotor PGP / 5000 (3.0 GPM, 32' R)</option>
              </select>
            </div>
            <div>
              <label for="pipeSelect" class="block text-xs font-medium text-slate-400 mb-1">Zone Lateral Pipe (5-FPS Cap)</label>
              <select id="pipeSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="9.0|3/4&quot; PVC/Poly" {"selected" if "3/4" in pipe_s else ""}>3/4" Pipe (9.0 GPM Max @ 5 FPS)</option>
                <option value="14.5|1&quot; PVC/Poly" {"selected" if "1\"" in pipe_s or "1-Inch" in pipe_s else ""}>1" Pipe (14.5 GPM Max @ 5 FPS)</option>
                <option value="24.0|1-1/4&quot; PVC" {"selected" if "1-1/4" in pipe_s else ""}>1-1/4" Pipe (24.0 GPM Max @ 5 FPS)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="lawnSlider" class="text-slate-300">Total Irrigated Lawn Turf Area (Sq Ft)</label>
              <span class="text-emerald-400 font-bold"><span id="lawnVal">{lawn_sq:,}</span> sq ft</span>
            </div>
            <input id="lawnSlider" type="range" min="1000" max="18000" step="500" value="{lawn_sq}" class="w-full accent-emerald-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Max Heads Per Zone</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="headsZoneOut">{heads_zn}</span> <span class="text-xs font-normal text-slate-400">Heads</span></div>
            <p id="zoneGpmOut" class="text-xs text-emerald-400 font-semibold mt-1">{zn_gpm} GPM / Zone (≤5 FPS)</p>
          </div>

          <div class="bg-slate-950 border border-cyan-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-cyan-400 font-bold">Total Zones & Runtime</span>
            <div class="text-2xl sm:text-3xl font-black text-cyan-400 mt-1"><span id="totZonesOut">{tot_zones}</span> <span class="text-xs font-normal text-slate-400">Zones</span></div>
            <p id="runMinOut" class="text-xs text-slate-300 font-semibold mt-1">{tot_heads} Heads | {run_min} Min/Zone</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="irrAdviceBanner" class="text-sm text-emerald-100 font-medium"></div>
        <a id="dynamicIrrBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Valve Manifold & Rotors on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {sys_name} Controller, Manifold & Rotor Bundle</h2>
        <span class="text-xs text-slate-400">ASABE S398 & IAPMO Backflow Compliant</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Sprinkler Pipe Size, 5-FPS Max GPM Velocity Limit & Heads-Per-Zone Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">PVC / Poly Pipe Size</th>
              <th class="py-3.5 px-4 text-emerald-400">5-FPS Safe Flow Ceiling</th>
              <th class="py-3.5 px-4 text-cyan-400">Full Rotors (3.0 GPM)</th>
              <th class="py-3.5 px-4">MP Rotators (0.8 GPM)</th>
              <th class="py-3.5 px-4">Recommended Application</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">CID Head-to-Head Spacing, 5-FPS Velocity &Matched Precipitation Checklist</h2>
        <span id="irrBadge" class="text-xs font-bold bg-slate-800 text-emerald-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({sys_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} SprinklerZoneIndex. Independent Turf Irrigation Hydraulics & Zone Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const gpmSlider = document.getElementById('gpmSlider');
    const nozzleSelect = document.getElementById('nozzleSelect');
    const pipeSelect = document.getElementById('pipeSelect');
    const lawnSlider = document.getElementById('lawnSlider');
    const gpmVal = document.getElementById('gpmVal');
    const lawnVal = document.getElementById('lawnVal');
    const headsZoneOut = document.getElementById('headsZoneOut');
    const zoneGpmOut = document.getElementById('zoneGpmOut');
    const totZonesOut = document.getElementById('totZonesOut');
    const runMinOut = document.getElementById('runMinOut');
    const irrAdviceBanner = document.getElementById('irrAdviceBanner');
    const dynamicIrrBtn = document.getElementById('dynamicIrrBtn');

    function recalculateSprinkler() {{
      const supGpm = parseFloat(gpmSlider.value);
      const nozParts = nozzleSelect.value.split('|');
      const headGpm = parseFloat(nozParts[0]);
      const spacingFt = parseInt(nozParts[1], 10);
      const prInHr = parseFloat(nozParts[2]);
      const pipeParts = pipeSelect.value.split('|');
      const pipeMaxGpm = parseFloat(pipeParts[0]);
      const pipeLabel = pipeParts[1];
      const lawnSqft = parseInt(lawnSlider.value, 10);

      gpmVal.textContent = supGpm.toFixed(1);
      lawnVal.textContent = lawnSqft.toLocaleString();

      const safeZoneGpm = Math.min(supGpm * 0.78, pipeMaxGpm);
      const maxHeadsPerZone = Math.max(2, Math.floor(safeZoneGpm / headGpm));
      const actualZoneGpm = (maxHeadsPerZone * headGpm).toFixed(1);

      const areaPerHead = Math.max(140.0, spacingFt * spacingFt * 0.65);
      const totalHeads = Math.max(6, Math.ceil(lawnSqft / areaPerHead));
      const totalZones = Math.max(2, Math.ceil(totalHeads / maxHeadsPerZone));
      const ctrlTier = totalZones <= 8 ? 8 : (totalZones <= 12 ? 12 : 16);
      const runMins = Math.round((0.50 / prInHr) * 60.0);

      headsZoneOut.textContent = maxHeadsPerZone;
      zoneGpmOut.textContent = `${{actualZoneGpm}} GPM / Zone (≤5 FPS)`;
      totZonesOut.textContent = totalZones;
      runMinOut.textContent = `${{totalHeads}} Heads | ${{runMins}} Min/Zone`;

      irrAdviceBanner.innerHTML = `🌱 <strong>CID Hydraulic Spec:</strong> With ${{supGpm.toFixed(1)}} GPM supply and ${{pipeLabel}}, run <strong>${{maxHeadsPerZone}} heads per zone (${{actualZoneGpm}} GPM)</strong> across a <strong>${{totalZones}}-Valve 1" Solenoid Manifold</strong> controlled by an <strong>${{ctrlTier}}-Zone Smart Wi-Fi Controller</strong> (${{runMins}} min/zone for 0.5" water).`;
      dynamicIrrBtn.href = `https://${{amzDomain}}/s?k=${{ctrlTier}}+Zone+Smart+WiFi+Sprinkler+Controller+Hunter+PGP+Rain+Bird+Valve+Manifold&tag=${{amzTag}}`;
    }}

    gpmSlider.addEventListener('input', recalculateSprinkler);
    nozzleSelect.addEventListener('change', recalculateSprinkler);
    pipeSelect.addEventListener('change', recalculateSprinkler);
    lawnSlider.addEventListener('input', recalculateSprinkler);
    recalculateSprinkler();

    const checks = document.querySelectorAll('.irr-check');
    const badge = document.getElementById('irrBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Rain+Bird+Hunter+PGP+Rotor+Sprinkler+Valve+Manifold"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-emerald-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-emerald-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('heads_zn', 3)} Heads/Zone ({item.get('zn_gpm', 9.0)} GPM)</span>
            <span class="text-xs text-slate-400">{item.get('zones', 4)} Zones | {item.get('run_min', 45)}m Run</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-emerald-400 transition">{item['system_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-emerald-400">Calculate Heads/Zone, Pipe & Runtime →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SprinklerZoneIndex — Lawn Sprinkler Heads Per Zone, GPM, Pipe Size & Manifold Calculator (2026)</title>
  <meta name="description" content="Calculate exact lawn irrigation sprinkler heads per zone, 5-FPS PVC and poly pipe velocity limits, 24VAC solenoid valve manifold counts, and precipitation rate watering minutes for Hunter PGP, Rain Bird 5000, MP Rotators, and Rachio systems.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="SprinklerZoneIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">SPRINKLER</span>ZoneIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Rotors, Valves & Controllers →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Lawn Sprinkler Heads Per Zone, GPM & Pipe Sizing Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your sprinkler head model, water supply GPM, or lawn area below to calculate maximum heads per zone under the 5-FPS pipe velocity rule, solenoid manifold zones, and watering runtime minutes.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search rotor model, GPM, or lawn size (e.g. Hunter PGP, Rain Bird 5000, MP Rotator, 12 GPM, 5000 Sq Ft, Febco 765...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-emerald-500">
      </div>
    </div>

    <div id="irrGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} SprinklerZoneIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('irrGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SprinklerZoneIndex Lawn Irrigation Zone & Pipe Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Lawn Sprinkler Heads Per Zone, 5-FPS Pipe Velocity & Valve Manifold Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_SPRINKLER:
        candidates.append((CUSTOM_SPRINKLER.strip(), 12.0, 50, 3.0, 32, 5000, "1-Inch Schedule 40 PVC"))
    candidates.extend(SEED_SPRINKLERS)
    candidates.extend(discover_google_sprinkler_queries(published_slugs))

    new_urls = []
    count = 0

    for sprk_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        s_name = sprk_tuple[0]
        slug = slugify(f"{s_name}-heads-per-zone-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating sprinkler zone GPM & manifold calculator for: {s_name}...")
        try:
            data = generate_sprinkler_data(sprk_tuple)
            build_sprinkler_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "system_name": data.get("system_name", s_name),
                "slug": slug,
                "title": data.get("seo_title", f"{s_name} Sprinkler Zone Calculator"),
                "description": data.get("meta_description", ""),
                "heads_zn": int(safe_float(sp.get("max_heads_per_zone", 3), 3)),
                "zn_gpm": round(safe_float(sp.get("actual_zone_flow_gpm", 9.0), 9.0), 1),
                "zones": int(safe_float(sp.get("total_solenoid_zones", 4), 4)),
                "run_min": int(safe_float(sp.get("runtime_minutes_half_inch", 45), 45)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {s_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new lawn sprinkler zone & GPM calculator pages.")


if __name__ == "__main__":
    main()
