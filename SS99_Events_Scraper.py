import asyncio
import requests
from playwright.async_api import async_playwright

# Configuration
EVENTS_API = "https://api.cdn-live.tv/api/v1/events/sports/?user=streamsports99&plan=vip"
# We only care about these channel_codes provided in the API
ALLOWED_CHANNEL_CODES = ["au", "gb", "us", "za", "sg", "uk", "nz", "th", "id"]

REFERER_SITE = "https://streamsports99.website/"
VLC_UA = "Mozilla/50 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
BATCH_SIZE = 5 

async def sniff_event_m3u8(context, event_name, channel_data, index, total):
    player_url = channel_data.get("url")
    chan_name = channel_data.get("channel_name")
    page = await context.new_page()
    found_url = None

    async def handle_request(request):
        nonlocal found_url
        if ".m3u8" in request.url and not found_url:
            found_url = request.url
            print(f"    [{index}/{total}] FOUND: {event_name} on {chan_name}", flush=True)

    page.on("request", handle_request)
    try:
        await page.goto(player_url, wait_until="load", timeout=30000)
        for _ in range(15): 
            if found_url: break
            await asyncio.sleep(1)
    except: pass
    finally: await page.close()
    
    return {
        "event_display_name": f"{event_name} ✦ {chan_name}",
        "m3u8": found_url,
        "category": channel_data.get("category", "Sports"),
        "logo": channel_data.get("image", "")
    }

async def main():
    try:
        print("--- Fetching Events Data ---", flush=True)
        response = requests.get(EVENTS_API, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
        sports_data = raw_data.get("cdn-live-tv", {})
    except Exception as e:
        print(f"API Error: {e}", flush=True); return

    queue = []
    
    print("--- Analyzing Channels by Region Code ---", flush=True)
    
    # Iterate through Sport Categories (Soccer, NBA, etc.)
    for sport_cat, matches in sports_data.items():
        if not isinstance(matches, list): continue
        
        cat_count = 0
        for match in matches:
            event_title = f"{match.get('homeTeam', 'TBA')} vs {match.get('awayTeam', 'TBA')}"
            # Fallback to tournament if team names are missing
            if "TBA" in event_title:
                event_title = match.get("tournament", "Live Event")
                
            channels = match.get("channels", [])
            
            if isinstance(channels, list):
                for chan in channels:
                    # CRITICAL FIX: We look at the channel's specific code
                    chan_code = str(chan.get("channel_code", "")).lower().strip()
                    
                    if chan_code in ALLOWED_CHANNEL_CODES:
                        chan["category"] = sport_cat.replace("-", " ").capitalize()
                        queue.append({
                            "event_name": event_title,
                            "channel": chan
                        })
                        cat_count += 1
        
        if cat_count > 0:
            print(f" > {sport_cat.capitalize()}: {cat_count} region-matched streams queued", flush=True)

    total_count = len(queue)
    if total_count == 0:
        print("\n[!] No channels matched your target region codes (us, gb, au, etc.).", flush=True)
        return

    print(f"\nStarting Extraction for {total_count} streams...\n", flush=True)

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent=VLC_UA,
            extra_http_headers={"Referer": REFERER_SITE, "Origin": REFERER_SITE}
        )

        final_results = []
        for i in range(0, total_count, BATCH_SIZE):
            batch = queue[i:i + BATCH_SIZE]
            tasks = [
                sniff_event_m3u8(context, item["event_name"], item["channel"], i + idx + 1, total_count) 
                for idx, item in enumerate(batch)
            ]
            results = await asyncio.gather(*tasks)
            final_results.extend(results)

        # Playlist Generation
        with open("SS99_Events.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for item in final_results:
                if item["m3u8"]:
                    display_name = item["event_display_name"]
                    group = f"{item['category']} ✦ SS Live"
                    
                    # Group title: Category | SS99
                    # tvg-id: Static "Live.Event.us" for all
                    f.write(f'#EXTINF:-1 tvg-id="Live.Event.us" tvg-logo="{item["logo"]}" group-title="{group}", {display_name}\n')
                    f.write(f"#EXTVLCOPT:http-origin=https://cdn-live.tv\n")
                    f.write(f"#EXTVLCOPT:http-referrer=https://cdn-live.tv/\n")
                    f.write(f"#EXTVLCOPT:http-user-agent={VLC_UA}\n")
                    f.write(f"{item['m3u8']}\n")

        await browser.close()
    print(f"\nEvents finished. Saved to SS99_Events.m3u8", flush=True)

if __name__ == "__main__":
    asyncio.run(main())