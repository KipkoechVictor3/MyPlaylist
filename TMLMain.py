import asyncio
from playwright.async_api import async_playwright
import httpx
import os
import re
from urllib.parse import urlparse

# --- Configuration ---
API_ENDPOINT = 'https://api.timstreams.top/main'
BASE_SITE = "https://timstreams.lol"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/KipkoechVictor3/MyPlaylist/main/TMS"

KEYWORDS = ['sky', 'tnt', 'fox', 'tsn', 'usa', 'nick', 'premier', 'fubo', 'cbs', 'abc']

# --- Mappings (DO NOT TOUCH) ---
CHANNEL_MAPPINGS = {
    'ABC': {'name': 'ABC', 'tvg-name': 'ABC', 'tvg-id': 'WABC-DT.us_locals1'},
    'Bein Sports USA': {'name': 'Bein Sports USA', 'tvg-name': 'Bein Sports USA', 'tvg-id': 'beIN.Sports.USA.HD.us2'},
    'CBS': {'name': 'CBS', 'tvg-name': 'CBS', 'tvg-id': 'WCBS-DT.us_locals1'},
    'CW': {'name': 'CW', 'tvg-name': 'CW', 'tvg-id': 'WPIX-DT.us_locals1'},
    'FOX': {'name': 'FOX', 'tvg-name': 'FOX', 'tvg-id': 'WNYW-DT.us_locals1'},
    'History': {'name': 'History', 'tvg-name': 'History', 'tvg-id': 'History.HD.us2'},
    'MeTV': {'name': 'MeTV', 'tvg-name': 'MeTV', 'tvg-id': 'MeTV.Toons.us2'},
    'MTV': {'name': 'MTV', 'tvg-name': 'MTV', 'tvg-id': 'MTV.-.Music.Television.HD.us2'},
    'MUTV': {'name': 'MUTV', 'tvg-name': 'MUTV', 'tvg-id': 'MUTV.HD.uk'},
    'NBA TV': {'name': 'NBA TV', 'tvg-name': 'NBA TV', 'tvg-id': 'NBA.TV.HD.us2'},
    'NBC': {'name': 'NBC', 'tvg-name': 'NBC', 'tvg-id': 'MSNBC.HD.us2'},
    'NBC Sports Bay Area': {'name': 'NBC Sports Bay Area', 'tvg-name': 'NBC Sports Bay Area', 'tvg-id': 'NBC.Sports.Bay.Area.HD.us2'},
    'NBC Sports Boston': {'name': 'NBC Sports Boston', 'tvg-name': 'NBC Sports Boston', 'tvg-id': 'NBC.Sports.Boston.HD.us2'},
    'NFL Network': {'name': 'NFL Network', 'tvg-name': 'NFL Network', 'tvg-id': 'NFL.Network.HD.us2'},
    'NFL Redzone': {'name': 'NFL Redzone', 'tvg-name': 'NFL Redzone', 'tvg-id': 'NFL.RedZone.HD.us2'},
    'Nicktoons': {'name': 'Nicktoons', 'tvg-name': 'Nicktoons', 'tvg-id': 'Nicktoons.us2'},
    'Rally TV': {'name': 'Rally TV', 'tvg-name': 'Rally TV', 'tvg-id': 'Racing.Dummy.us'},
    'Sec Network': {'name': 'Sec Network', 'tvg-name': 'Sec Network', 'tvg-id': 'SEC.Network.HD.us2'},
    'Sky Sport 1 NZ': {'name': 'Sky Sport 1 NZ', 'tvg-name': 'Sky Sport 1 NZ', 'tvg-id': 'Sky.Sport.1.nz'},
    'Sky Sport 2 NZ': {'name': 'Sky Sport 2 NZ', 'tvg-name': 'Sky Sport 2 NZ', 'tvg-id': 'Sky.Sport.2.nz'},
    'Sky Sport 3 NZ': {'name': 'Sky Sport 3 NZ', 'tvg-name': 'Sky Sport 3 NZ', 'tvg-id': 'Sky.Sport.3.nz'},
    'Sky Sport 4 NZ': {'name': 'Sky Sport 4 NZ', 'tvg-name': 'Sky Sport 4 NZ', 'tvg-id': 'Sky.Sport.4.nz'},
    'Sky Sport 5 NZ': {'name': 'Sky Sport 5 NZ', 'tvg-name': 'Sky Sport 5 NZ', 'tvg-id': 'Sky.Sport.5.nz'},
    'Sky Sport 6 NZ': {'name': 'Sky Sport 6 NZ', 'tvg-name': 'Sky Sport 6 NZ', 'tvg-id': 'Sky.Sport.6.nz'},
    'Sky Sport 7 NZ': {'name': 'Sky Sport 7 NZ', 'tvg-name': 'Sky Sport 7 NZ', 'tvg-id': 'Sky.Sport.7.nz'},
    'Sky Sport 8 NZ': {'name': 'Sky Sport 8 NZ', 'tvg-name': 'Sky Sport 8 NZ', 'tvg-id': 'Sky.Sport.8.nz'},
    'Sky Sport 9 NZ': {'name': 'Sky Sport 9 NZ', 'tvg-name': 'Sky Sport 9 NZ', 'tvg-id': 'Sky.Sport.9.nz'},
    'Sky Sports Action': {'name': 'Sky Sports Action', 'tvg-name': 'Sky Sports Action', 'tvg-id': 'SkySp.ActionHD.uk'},
    'Sky Sports Cricket': {'name': 'Sky Sports Cricket', 'tvg-name': 'Sky Sports Cricket', 'tvg-id': 'SkySp.Cricket.uk'},
    'Sky Sports Football': {'name': 'Sky Sports Football', 'tvg-name': 'Sky Sports Football', 'tvg-id': 'SkySp.Fball.uk'},
    'Sky Sports F1': {'name': 'Sky Sports F1', 'tvg-name': 'Sky Sports F1', 'tvg-id': 'SkySp.F1.uk'},
    'Sky Sports Golf': {'name': 'Sky Sports Golf', 'tvg-name': 'Sky Sports Golf', 'tvg-id': 'SkySp.Golf.uk'},
    'Sky Sports Main Event': {'name': 'Sky Sports Main Event', 'tvg-name': 'Sky Sports Main Event', 'tvg-id': 'SkySpMainEvHD.uk'},
    'Sky Sports Premier League': {'name': 'Sky Sports Premier League', 'tvg-name': 'Sky Sports Premier League', 'tvg-id': 'SkySp.PL.HD.uk'},
    'Sky Sports Racing': {'name': 'Sky Sports Racing', 'tvg-name': 'Sky Sports Racing', 'tvg-id': 'SkySp.Racing.uk'},
    'Tennis Channel': {'name': 'Tennis Channel', 'tvg-name': 'Tennis Channel', 'tvg-id': 'Tennis.Channel.HD.us2'},
    'TBS': {'name': 'TBS', 'tvg-name': 'TBS', 'tvg-id': 'TBS.HD.us2'},
    'TNT': {'name': 'TNT', 'tvg-name': 'TNT', 'tvg-id': 'TNT.HD.us2'},
    'TNT Sports 1': {'name': 'TNT Sports 1', 'tvg-name': 'TNT Sports 1', 'tvg-id': 'TNT.Sports.1.HD.uk'},
    'TNT Sports 2': {'name': 'TNT Sports 2', 'tvg-name': 'TNT Sports 2', 'tvg-id': 'TNT.Sports.2.HD.uk'},
    'TNT Sports 3': {'name': 'TNT Sports 3', 'tvg-name': 'TNT Sports 3', 'tvg-id': 'TNT.Sports.3.HD.uk'},
    'TNT Sports 4': {'name': 'TNT Sports 4', 'tvg-name': 'TNT Sports 4', 'tvg-id': 'TNT.Sports.4.HD.uk'},
    'TruTV': {'name': 'TruTV', 'tvg-name': 'TruTV', 'tvg-id': 'truTV.HD.us2'},
    'TSN 1': {'name': 'TSN 1', 'tvg-name': 'TSN 1', 'tvg-id': 'TSN.1.ca2'},
    'TSN 2': {'name': 'TSN 2', 'tvg-name': 'TSN 2', 'tvg-id': 'TSN.2.ca2'},
    'TSN 3': {'name': 'TSN 3', 'tvg-name': 'TSN 3', 'tvg-id': 'TSN.3.ca2'},
    'TSN 4': {'name': 'TSN 4', 'tvg-name': 'TSN 4', 'tvg-id': 'TSN.4.ca2'},
    'TSN 5': {'name': 'TSN 5', 'tvg-name': 'TSN 5', 'tvg-id': 'TSN.5.ca2'},
}

def get_obfuscated_name(clean_name: str, index: int) -> str:
    safe_name = re.sub(r'[\\/*?:"<>|]', "", clean_name)
    words = safe_name.split()
    initials = "".join([word[0].lower() for word in words if word])
    return f"{initials}{index}.m3u8"

async def process_stream(page_id, browser, stream_info, semaphore):
    async with semaphore:
        name = stream_info['channel_name']
        watch_id = stream_info['watch_id']
        watch_page_url = f"{BASE_SITE}/watch.html?id={watch_id}"
        
        found_event = asyncio.Event()
        captured_data = {"url": None}

        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        
        try:
            page = await context.new_page()

            async def block_aggressively(route):
                if route.request.resource_type in ["image", "stylesheet", "font", "media"] and ".m3u8" not in route.request.url:
                    await route.abort()
                elif any(x in route.request.url for x in ["google-analytics", "doubleclick", "ads"]):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_aggressively)

            async def on_response(response):
                url = response.url.lower()
                if ".m3u8" in url and response.status == 200:
                    if any(p in url for p in ["mono.ts.m3u8", "tracks-v1a1", "video.m3u8"]):
                        captured_data["url"] = response.url
                        found_event.set()
                    elif not captured_data["url"]: 
                        captured_data["url"] = response.url

            page.on("response", on_response)
            
            print(f"[{page_id}] 🌐 Navigating: {name}", flush=True)
            try:
                await page.goto(watch_page_url, wait_until="domcontentloaded", timeout=12000)
            except:
                pass 

            await page.mouse.click(640, 360)
            
            try:
                await asyncio.wait_for(found_event.wait(), timeout=12.0)
            except asyncio.TimeoutError:
                pass

            if captured_data["url"]:
                print(f"[{page_id}] ✅ CAPTURED: {name}", flush=True)
                
                mapping = CHANNEL_MAPPINGS.get(name, {})
                tvg_id = mapping.get('tvg-id', "")
                tvg_name = mapping.get('tvg-name', name)
                
                is_live_event = stream_info.get('is_event')
                group_orig = "Tims Live" if is_live_event else "Tims 24/7"
                group_git = "Tims Live ✦ Git" if is_live_event else "Tims 24/7 ✦ Git"

                parsed = urlparse(captured_data["url"])
                stream_origin = f"{parsed.scheme}://{parsed.netloc}"
                
                # --- GitHub File Creation ---
                obfuscated_filename = get_obfuscated_name(name, page_id)
                github_url = f"{GITHUB_RAW_BASE}/{obfuscated_filename}"
                
                try:
                    with open(f"TMS/{obfuscated_filename}", "w", encoding="utf-8") as sub_f:
                        sub_f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=2700000,RESOLUTION=1920x1080\n")
                        sub_f.write(f"{captured_data['url']}\n")
                except Exception as e:
                    print(f"!! Error saving {obfuscated_filename}: {e}", flush=True)

                # Entry 1: Direct
                entry_orig = [
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{stream_info["logo"]}" group-title="{group_orig}", {name}',
                    f'#EXTVLCOPT:http-user-agent={USER_AGENT}',
                    f'#EXTVLCOPT:http-origin={stream_origin}',
                    f'#EXTVLCOPT:http-referrer={BASE_SITE}/',
                    captured_data["url"]
                ]
                
                # Entry 2: Git Proxy
                entry_git = [
                    f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{stream_info["logo"]}" group-title="{group_git}", {name}',
                    f'#EXTVLCOPT:http-user-agent={USER_AGENT}',
                    f'#EXTVLCOPT:http-origin={stream_origin}',
                    f'#EXTVLCOPT:http-referrer={BASE_SITE}/',
                    github_url
                ]
                
                return {"direct": entry_orig, "git": entry_git}
            else:
                print(f"[{page_id}] ❌ FAILED: {name}", flush=True)

        except Exception as e:
            print(f"[{page_id}] ⚠️ ERROR: {name} -> {str(e)[:50]}", flush=True)
        finally:
            await context.close()
        return None

async def main():
    if not os.path.exists("TMS"): os.makedirs("TMS")

    async with async_playwright() as p:
        # Browser set to Firefox per your preference
        browser = await p.firefox.launch(headless=True)
        
        print("[*] Fetching API...", flush=True)
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.get(API_ENDPOINT)
                data = resp.json()
            except Exception as e:
                print(f"Critical API Error: {e}", flush=True)
                await browser.close()
                return

        tasks_data = []
        for category in data:
            items = category.get('events', []) if isinstance(category, dict) else []
            for item in items:
                name = item.get('name', '')
                watch_id = item.get('URL')
                is_event = item.get('isevent', False)

                if is_event or any(k in name.lower() for k in KEYWORDS):
                    if watch_id:
                        tasks_data.append({
                            'channel_name': name,
                            'logo': item.get('logo'),
                            'watch_id': watch_id,
                            'is_event': is_event
                        })

        print(f"🚀 Processing {len(tasks_data)} channels...", flush=True)
        
        sem = asyncio.Semaphore(15) 
        tasks = [process_stream(i+1, browser, info, sem) for i, info in enumerate(tasks_data)]
        results = await asyncio.gather(*tasks)

        playlist_direct = ["#EXTM3U"]
        playlist_git = ["#EXTM3U"]

        for res in results:
            if res:
                playlist_direct.extend(res["direct"])
                playlist_git.extend(res["git"])
        
        # Save Direct Playlist
        with open('S4.m3u8', 'w', encoding='utf-8') as f:
            f.write("\n".join(playlist_direct))

        # Save Git Proxy Playlist
        with open('S4_Git.m3u8', 'w', encoding='utf-8') as f:
            f.write("\n".join(playlist_git))
            
        await browser.close()
        print(f"\n✨ Done! Saved S4.m3u8 (Direct) and S4_Git.m3u8 (Git Proxy)", flush=True)

if __name__ == '__main__':
    # Fixed the syntax error here
    asyncio.run(main())