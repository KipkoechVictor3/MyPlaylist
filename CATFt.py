import re
import requests

# --- Configuration ---
SOURCES = {
    "CAT TV": "https://raw.githubusercontent.com/cattviptv2605/iptv/main/cattv.m3u",
    "FreeView": "https://raw.githubusercontent.com/sni2007/sni2007/c9f1465208d09519f5f11fa3863001aa1ff939a8/Freeview"
}
OUTPUT_M3U_FILE = "Combined_Sports.m3u"
MAPPING_URL = "https://www.dropbox.com/scl/fi/ow8s16pbppb2dnu3ernmp/channel_mappings.txt?rlkey=zu3a1voqbh3f17etup39h5svx&st=th57uic2&dl=1"

TARGET_KEYWORDS = [
    "hubpremier", "hubsports", "nowpremier", "skysports", "astro", 
    "foxsport", "now sports", "tntsport", "supersport", 
    "food network", "skysport"
]

FREEVIEW_KEYWORDS = [
    "love", "astro premier", "spotv", "bbc", "food", "rock", 
    "hbo", "cinemax", "hits", "axn", "animal", "nick", "bein", "universal"
]

CHANNEL_MAPPINGS = {}

def clean_for_comparison(text: str) -> str:
    text = text.lower()
    text = text.replace("()", "").replace("_", " ")
    text = re.sub(r'\b(hd|sd|4k|uhd|fhd)\b', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def load_mappings():
    print(f"📥 Loading remote 3-column mappings...", end='', flush=True)
    try:
        r = requests.get(MAPPING_URL, timeout=10)
        r.raise_for_status()
        pattern = re.compile(r'"([^"]*)"\s*:\s*"([^"]*)"\s*:\s*"([^"]*)"')
        matches = pattern.findall(r.text)
        for tid, tname, cname in matches:
            match_key = clean_for_comparison(cname)
            CHANNEL_MAPPINGS[match_key] = {
                "tid": tid.strip(), 
                "tname": tname.strip(),
                "display": cname.strip()
            }
        print(f" [OK] Found {len(CHANNEL_MAPPINGS)} IDs", flush=True)
    except Exception as e: 
        print(f" [FAILED] {e}", flush=True)

def structure_name(name: str) -> str:
    # 1. Remove junk
    name = re.sub(r'(?i)\s*(warpdooball|github|dooballfree|Ultraman\s*\d+)', '', name)
    
    # 2. Fix CamelCase/No-space SkySports (e.g., SkySportsAction -> Sky Sports Action)
    name = re.sub(r'(?i)SkySports', 'Sky Sports ', name)
    name = re.sub(r'(?i)SkySport(\d)', r'Sky Sport \1', name)
    
    # 3. Fix other brand spacing
    name = re.sub(r'(?i)hubpremier', 'Hub Premier ', name)
    name = re.sub(r'(?i)hubsports', 'Hub Sports ', name)
    name = re.sub(r'(?i)nowpremier', 'Now Premier ', name)
    name = re.sub(r'(?i)tntsport(\d?)', r'TNT Sports \1', name)
    name = re.sub(r'(?i)beinsport', 'Bein Sport ', name)
    
    # 4. Handle Sky NZ underscores
    name = re.sub(r'(?i)Sky\s*Sport\s*(\d+)[_|\s]*NZ', r'Sky Sport \1', name)
    
    # 5. Generic spacing for numbers and camelCase
    name = name.replace("_", " ")
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    name = re.sub(r'(\d+)', r' \1 ', name)
    
    return re.sub(r'\s+', ' ', name).strip()

def process_sources():
    final_playlist = []
    name_tracker = {}

    for source_name, url in SOURCES.items():
        print(f"📡 Fetching {source_name}...", end='', flush=True)
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            lines = r.text.splitlines()
            print(f" [OK]", flush=True)
        except Exception as e:
            print(f" [ERROR] {e}", flush=True)
            continue

        current_extinf = None
        current_meta = []

        for line in lines:
            line = line.strip()
            if not line: continue

            if line.startswith("#EXTINF"):
                current_extinf = line
                current_meta = []
            elif line.startswith("#KODIPROP") or line.startswith("#EXTVLCOPT"):
                current_meta.append(line)
            elif line.startswith("http"):
                if current_extinf:
                    raw_name = current_extinf.split(',')[-1].strip()
                    
                    # STRICT EXCLUSION: Skip German/Bundesliga content
                    upper_raw = raw_name.upper().replace(" ", "")
                    if any(x in upper_raw for x in ["BUNDESLIGA", "SKYSPORTDE"]):
                        current_extinf = None
                        continue

                    is_match = False
                    tid, tname, display_at_end = "", "", ""

                    if source_name == "FreeView":
                        if any(kw.lower() in raw_name.lower() for kw in FREEVIEW_KEYWORDS):
                            is_match = True
                            name_tracker[raw_name] = name_tracker.get(raw_name, 0) + 1
                            display_at_end = f"{raw_name} {name_tracker[raw_name]}" if name_tracker[raw_name] > 1 else raw_name
                            tid, tname = "", display_at_end
                    else:
                        if any(kw.lower() in raw_name.lower() for kw in TARGET_KEYWORDS):
                            is_match = True
                            reformed_name = structure_name(raw_name)
                            lookup_key = clean_for_comparison(reformed_name)
                            
                            mapping = CHANNEL_MAPPINGS.get(lookup_key)
                            if mapping:
                                tid = mapping["tid"]
                                tname = mapping["tname"]
                                display_at_end = mapping["display"]
                                status = f"✅ Mapped ({tid})"
                            else:
                                tid = ""
                                tname = reformed_name
                                display_at_end = reformed_name
                                status = "❌ Unmapped"

                            print(f"    [{source_name}] {reformed_name[:25]:<25} | {status}")

                    if is_match:
                        logo_match = re.search(r'tvg-logo="([^"]*)"', current_extinf)
                        logo = logo_match.group(1) if logo_match else ""
                        new_extinf = f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{tname}" tvg-logo="{logo}" group-title="{source_name}",{display_at_end}'
                        final_playlist.append((new_extinf, current_meta, line))

                current_extinf = None
    return final_playlist

def main():
    load_mappings()
    processed = process_sources()
    with open(OUTPUT_M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, meta, url in processed:
            f.write(f"{extinf}\n")
            for m in meta: f.write(f"{m}\n")
            f.write(f"{url}\n")
    print(f"\n🎉 Saved {len(processed)} channels to {OUTPUT_M3U_FILE}")

if __name__ == "__main__":
    main()