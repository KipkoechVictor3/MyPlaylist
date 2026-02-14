import asyncio
import requests
from playwright.async_api import async_playwright

CHANNELS_API = "https://api.cdn-live.tv/api/v1/channels/?user=streamsports99&plan=vip"
TARGET_CODES = ["us", "gb", "ca", "au", "nz", "za"]
ACCEPTED_KEYWORDS = ["astro", "abc", "bein", "paramount", "fox soccer", "fox sport", "cbs", "cnn", "cnbc", "usa network"]
REFERER_SITE = "https://streamsports99.website/"
VLC_UA = "Mozilla/50 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
BATCH_SIZE = 15 

# Mapping for Group Titles
COUNTRY_GROUPS = {
    "gb": "UK✦Stream Sports",
    "us": "USA✦Stream Sports",
    "za": "ZA✦Stream Sports",
    "ca": "CA✦Stream Sports",
    "au": "AU✦Stream Sports",
    "nz": "NZ✦Stream Sports"
}

TVG_MAP = {
    "Premier.Sports.1.HD.ie":"Premier Sports 1","Premier.Sports.1.ie":"Premier Sports 1","Premier.Sports.2.HD.ie":"Premier Sports 2","Premier.Sports.2.ie":"Premier Sports 2",
    "SkySp.Action.uk":"Sky Sports Action","SkySp.ActionHD.uk":"Sky Sports Action","SkySportsArena.uk":"Sky Sports Arena","SkySp.Cricket.uk":"Sky Sports Cricket","SkySpCricket.HD.uk":"Sky Sports Cricket",
    "SkySp.F1.uk":"Sky Sports F1","SkySp.F1.HD.uk":"Sky Sports F1","SkySp.Fball.uk":"Sky Sports Football","SkySp.Fball.HD.uk":"Sky Sports Football",
    "SkySp.Golf.uk":"Sky Sports Golf","SkySp.Golf.HD.uk":"Sky Sports Golf","SkySpMainEv.uk":"Sky Sports Main Event","SkySpMainEvHD.uk":"Sky Sports Main Event",
    "SkySp.Mix.HD.uk":"Sky Sports Mix","SkySp.PL.HD.uk":"Sky Sports Premier League","SkySp.Racing.uk":"Sky Sports Racing","SkySp.Racing.HD.uk":"Sky Sports Racing","SkySp.Tennis.HD.uk":"Sky Sports Tennis",
    "TNT.Sports.1.HD.uk":"TNT Sports 1","TNT.Sports.2.HD.uk":"TNT Sports 2","TNT.Sports.3.HD.uk":"TNT Sports 3","TNT.Sports.4.HD.uk":"TNT Sports 4","TNT.Sports.Ultimate.uk":"TNT Sports 5",
    "TSN.1.ca2":"TSN 1","TSN.2.ca2":"TSN 2","TSN.3.ca2":"TSN 3","TSN.4.ca2":"TSN 4","TSN.5.ca2":"TSN 5",
    "beINSports1.au":"beIN SPORTS 1","beINSports2.au":"beIN SPORTS 2","beINSports3.au":"beIN SPORTS 3",
    "Live.Event.us":"Stan Sport 1","Live.Event.us":"Stan Sport 2","Live.Event.us":"Stan Sport 3","Live.Event.us":"Stan Sport 4","Live.Event.us":"Stan Sport 5","Live.Event.us":"Stan Sport 6","Live.Event.us":"Stan Sport 7","Live.Event.us":"Stan Sport 8",
    "Live.Event.us":"Stan Sport 9","Live.Event.us":"Stan Sport 10","Live.Event.us":"Stan Sport 11","Live.Event.us":"Stan Sport 12","Live.Event.us":"Stan Sport 13","Live.Event.us":"Stan Sport 14","Live.Event.us":"Stan Sport 15","Live.Event.us":"Stan Sport 16",
    "Live.Event.us":"Stan Sport 17","Live.Event.us":"Stan Sport 18","Live.Event.us":"Stan Sport 19","Live.Event.us":"Stan Sport 20",
    "Sky.Sport.1.nz":"Sky Sport 1","Sky.Sport.2.nz":"Sky Sport 2","Sky.Sport.3.nz":"Sky Sport 3","Sky.Sport.4.nz":"Sky Sport 4","Sky.Sport.5.nz":"Sky Sport 5","Sky.Sport.6.nz":"Sky Sport 6","Sky.Sport.7.nz":"Sky Sport 7","Sky.Sport.Premier.League.nz":"Sky Sport 8",
"210.dstv_com":"SuperSport Action","212.dstv_com":"SuperSport Cricket","205.dstv_com":"SuperSport Football","213.dstv_com":"SuperSport Golf","201.dstv_com":"SuperSport Grandstand","204.dstv_com":"SuperSport LaLiga","241.dstv_com":"SuperSport Maximo 1","215.dstv_com":"SuperSport Motorsport","203.dstv_com":"SuperSport Premier League","211.dstv_com":"SuperSport Rugby","214.dstv_com":"SuperSport Tennis","206.dstv_com":"SuperSport Variety 1","207.dstv_com":"SuperSport Variety 2",
"208.dstv_com":"SuperSport Variety 3","209.dstv_com":"SuperSport Variety 4", 
    "Astro.Premier.League.3.my": "Astro Premier League 3", "Astro.Premier.League.4.my": "Astro Premier League 4", "Astro.Premier.League.5.my": "Astro Premier League 5", "Hub.Premier.10.sg": "Hub Premier 10","Hub.Premier.11.sg": "Hub Premier 11",
    "Hub.Premier.1.sg": "Hub Premier 1","Hub.Premier.2.sg": "Hub Premier 2","Hub.Premier.3.sg": "Hub Premier 3","Hub.Premier.4.sg": "Hub Premier 4","Hub.Premier.5.sg": "Hub Premier 5","Hub.Premier.6.sg": "Hub Premier 6","Hub.Premier.7.sg": "Hub Premier 7",
    "Hub.Premier.8.sg": "Hub Premier 8","Hub.Premier.9.sg": "Hub Premier 9","Hub.Sports.1.HD.sg": "Hub Sports 1", "ITV1.HD.uk": "ITV 1","ITV2.HD.uk": "ITV 2", "ITV3.HD.uk": "ITV 3","ITV4.HD.uk": "ITV 4","Astro.Football":"Astro Football","Astro.Grandstand":"Astro Grandstand",
    "Astro.Premier.League.2":"Astro Premier League 2","Astro.Premier.League.3":"Astro Premier League 3","Astro.Premier.League.4":"Astro Premier League 4","Astro.Premier.League.5":"Astro Premier League 5"
}

def get_tvg_id(channel_name):
    clean_name = channel_name.strip().lower()
    # Search for direct or fuzzy match in map values
    for tid, map_name in TVG_MAP.items():
        if map_name.strip().lower() == clean_name:
            return tid
    return ""

async def sniff_m3u8(context, channel_data, index, total):
    player_url = channel_data.get("url")
    name = channel_data.get("name")
    tid = get_tvg_id(name)
    page = await context.new_page()
    found_url = None

    async def handle_request(request):
        nonlocal found_url
        if ".m3u8" in request.url and not found_url:
            found_url = request.url
            print(f"    [{index}/{total}] MATCH: {name} | ID: {tid if tid else 'N/A'} -> {found_url}", flush=True)

    page.on("request", handle_request)
    try:
        await page.goto(player_url, wait_until="load", timeout=25000)
        for _ in range(12): 
            if found_url: break
            await asyncio.sleep(1)
    except: pass
    finally: await page.close()
    
    return {"name": name, "m3u8": found_url, "data": channel_data, "tvg_id": tid}

async def main():
    try:
        data = requests.get(CHANNELS_API).json()
        all_channels = data.get("channels", [])
    except Exception as e:
        print(f"API Error: {e}", flush=True); return

    queue = []
    for c in all_channels:
        code = c.get("code", "").lower()
        name_lower = c.get("name", "").lower()
        if code in TARGET_CODES:
            if code == "us":
                if any(kw in name_lower for kw in ACCEPTED_KEYWORDS):
                    queue.append(c)
            else:
                queue.append(c)

    total_count = len(queue)
    print(f"Starting parallel extraction (Batch Size: {BATCH_SIZE}) for {total_count} channels...\n", flush=True)

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent=VLC_UA,
            extra_http_headers={"Referer": REFERER_SITE, "Origin": REFERER_SITE}
        )

        final_results = []
        for i in range(0, total_count, BATCH_SIZE):
            batch = queue[i:i + BATCH_SIZE]
            tasks = [sniff_m3u8(context, channel, i + idx + 1, total_count) for idx, channel in enumerate(batch)]
            results = await asyncio.gather(*tasks)
            final_results.extend(results)
            print(f"[*] Completed through channel {min(i + BATCH_SIZE, total_count)} of {total_count}", flush=True)

        with open("SSpo99.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in final_results:
                if item["m3u8"]:
                    name = item["name"]
                    m3u8 = item["m3u8"]
                    code = item["data"].get("code", "").lower()
                    logo = item["data"].get("image", "")
                    tid = item["tvg_id"]
                    
                    # Dynamic Group Title based on country code
                    group = COUNTRY_GROUPS.get(code, "Stream Sports99")
                    
                    f.write(f'#EXTINF:-1 tvg-id="{tid}" tvg-logo="{logo}" group-title="{group}", {name}\n')
                    f.write(f"#EXTVLCOPT:http-origin=https://cdn-live.tv\n")
                    f.write(f"#EXTVLCOPT:http-referrer=https://cdn-live.tv/\n")
                    f.write(f"#EXTVLCOPT:http-user-agent={VLC_UA}\n")
                    f.write(f"{m3u8}\n")

        await browser.close()
    print(f"\nExtraction finished. Total valid links: {len([x for x in final_results if x['m3u8']])}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())