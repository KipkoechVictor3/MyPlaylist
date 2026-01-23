import asyncio
from playwright.async_api import async_playwright
import json
import os
import re
import httpx
from urllib.parse import urlparse
import sys

# --- Configuration ---
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

GENRE_MAP = {1: "Soccer", 2: "Motorsport", 3: "MMA", 7: "Basketball", 8: "Am. Football", 10: "Tennis", 13: "Cricket"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
TORR_URL = "https://www.dropbox.com/scl/fi/lib5ho7effzocz1rkw942/PLTorr.m3u?rlkey=nzvd0vbf87sak2ful8a6tpd9f&st=5otkqdhs&dl=1"

stats = {"current": 0, "total": 0}

async def process_stream(context, stream_info, semaphore):
    async with semaphore:
        name = stream_info['channel_name']
        url = stream_info['stream_url']
        detected_urls = []

        try:
            page = await context.new_page()
            # Intercept network traffic for m3u8
            page.on("response", lambda res: detected_urls.append(res.url) if ".m3u8" in res.url.lower() else None)
            
            await page.goto(url, wait_until="load", timeout=60000)
            await page.mouse.click(400, 300) # Bypass potential play overlays
            await asyncio.sleep(12) 

            stats["current"] += 1
            if detected_urls:
                captured_link = detected_urls[-1]
                sys.stdout.write(f"\r🧪 Found [{stats['current']}/{stats['total']}]: {name[:30]}... ")
                sys.stdout.flush()

                group = "24/7" if stream_info['is_247'] else f"Live: {GENRE_MAP.get(stream_info['genre_id'], 'Sports')}"
                logo = stream_info['channel_logo'] or ""
                tid = CHANNEL_MAPPINGS.get(name, {}).get('tvg-id', "")
                tname = CHANNEL_MAPPINGS.get(name, {}).get('tvg-name', name)
                
                parsed = urlparse(url)
                origin = f"{parsed.scheme}://{parsed.netloc}"

                return [
                    f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{tname}" tvg-logo="{logo}" group-title="{group}", {name}',
                    f'#EXTVLCOPT:http-origin={origin}',
                    f'#EXTVLCOPT:http-referrer={origin}/',
                    f'#EXTVLCOPT:http-user-agent={USER_AGENT}',
                    captured_link
                ]
            else:
                sys.stdout.write(f"\r❌ Failed [{stats['current']}/{stats['total']}]: {name[:30]}... ")
                sys.stdout.flush()

        except Exception:
            pass
        finally:
            await page.close()
        return None

async def main():
    print("📡 Initializing Scraper (Direct Mode + PLTorr Integration)...")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 1. Download PLTorr Playlist
            print("📥 Downloading PLTorr contents...")
            try:
                torr_resp = await client.get(TORR_URL)
                torr_lines = torr_resp.text.splitlines()
                # Remove the first #EXTM3U line if it exists
                if torr_lines and "#EXTM3U" in torr_lines[0]:
                    torr_lines = torr_lines[1:]
                torr_content = "\n".join(torr_lines)
            except Exception as e:
                print(f"⚠️ Could not download PLTorr: {e}")
                torr_content = ""

            # 2. Fetch Main Source Data
            r = await client.get("https://dl.dropboxusercontent.com/scl/fi/774dn4reqvnu1yu7e89ug/main.json?rlkey=8p7pm1bx09hgxcpec6kvhdvov&dl=1")
            categories = r.json()

        # 3. Filter Logic
        accepted = []
        ch_keywords = ['sky', 'tnt', 'bbc', 'itv', 'tsn', 'laliga', 'fox', 'nick', 'premier', 'usa']
        
        for cat in categories:
            cat_name = cat.get('category', '').lower()
            is_247_cat = any(x in cat_name for x in ["24", "7", "twenty"])
            
            for ev in cat.get('events', []):
                name_lower = ev.get('name', '').lower()
                
                should_process = False
                if is_247_cat:
                    # Apply keyword filter to 24/7 channels
                    if any(k in name_lower for k in ch_keywords):
                        should_process = True
                elif ev.get('genre') in range(1, 16):
                    # Allow all live sports events
                    should_process = True

                if should_process:
                    for s in ev.get('streams', []):
                        if '/embed/' in s.get('url', ''):
                            accepted.append({
                                'channel_name': ev.get('name'), 
                                'channel_logo': ev.get('logo'), 
                                'stream_url': s.get('url'), 
                                'genre_id': ev.get('genre'), 
                                'is_247': is_247_cat
                            })

        # 4. Process Streams
        stats["total"] = len(accepted)
        sem = asyncio.Semaphore(3) # Use 3 workers for Firefox stability
        tasks = [process_stream(context, info, sem) for info in accepted]
        results = await asyncio.gather(*tasks)

        # 5. Assemble Playlist
        playlist = ["#EXTM3U"]
        
        # Add Torr Content first
        if torr_content:
            playlist.append("\n" + torr_content)
            
        valid_count = 0
        for res in results:
            if res: 
                playlist.extend(res)
                valid_count += 1
        
        # Save output
        with open('TML.m3u', 'w', encoding='utf-8') as f:
            f.write("\n".join(playlist))
            
        print(f"\n✨ DONE: Added PLTorr and {valid_count} direct streams to TML.m3u")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())