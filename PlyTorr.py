import asyncio
import httpx
import re
from playwright.async_api import async_playwright

# --- Configuration ---
CHANNELS_API = "https://api.cdn-live.tv/api/v1/channels/?user=cdnlivetv&plan=free"
MAPPING_URL = "https://www.dropbox.com/scl/fi/ow8s16pbppb2dnu3ernmp/channel_mappings.txt?rlkey=zu3a1voqbh3f17etup39h5svx&st=th57uic2&dl=1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
BATCH_SIZE = 4 

COUNTRY_MAP = {
    "us": "United States", "gb": "United Kingdom", "gr": "Greece", "cy": "Cyprus", 
    "es": "Spain", "it": "Italy", "fr": "France", "de": "Germany", "pt": "Portugal", 
    "br": "Brazil", "ar": "Argentina", "mx": "Mexico", "ca": "Canada", "au": "Australia",
    "tr": "Turkey", "nl": "Netherlands"
}

async def fetch_mappings():
    """Retrieves channel mappings for tvg-id assignment."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(MAPPING_URL)
            matches = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', resp.text)
            return {v.lower().strip(): k for k, v in matches}
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch mappings ({e})")
        return {}

async def get_stream_via_network(browser, channel_data, mappings):
    """Opens a page and intercepts the m3u8 network request."""
    name = channel_data.get('name', 'Unknown')
    player_url = channel_data.get('url')
    logo = channel_data.get('image', '')
    code = channel_data.get('code', '').lower()
    group = COUNTRY_MAP.get(code, code.upper())
    
    # Map tvg-id
    tvg_id = mappings.get(name.lower().strip(), "")
    
    found_url = None

    print(f"🔍 Searching: {name}...")

    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    
    def handle_request(request):
        nonlocal found_url
        url = request.url
        if ".m3u8?token=" in url and "cdn-live-tv.ru" in url:
            found_url = url
            print(f"  ✅ Found: {name} -> {url[:60]}...")

    page.on("request", handle_request)

    try:
        await page.goto(player_url, wait_until="commit", timeout=20000)
        for _ in range(8):
            if found_url: break
            await asyncio.sleep(1)
    except Exception as e:
        print(f"  ⚠️ Error: {name} ({e})")
    finally:
        await page.close()
        await context.close()

    if found_url:
        return {
            "name": name, 
            "link": found_url, 
            "logo": logo, 
            "group": group,
            "tvg_id": tvg_id
        }
    else:
        print(f"  ❌ Failed: {name} (No stream found)")
    return None

async def main():
    async with async_playwright() as p:
        # 1. Setup Data
        mappings = await fetch_mappings()
        
        async with httpx.AsyncClient() as client:
            print("📡 Fetching channel list from API...")
            try:
                resp = await client.get(CHANNELS_API)
                channels = resp.json().get('channels', [])
            except Exception as e:
                print(f"❌ Could not fetch API: {e}")
                return
        
        if not channels:
            print("❌ No channels found in API.")
            return

        print(f"🚀 Starting Playwright (Firefox) for {len(channels)} channels...")
        
        browser = await p.firefox.launch(headless=True)
        results = []
        
        # 2. Batch Processing
        for i in range(0, len(channels), BATCH_SIZE):
            batch = channels[i:i + BATCH_SIZE]
            batch_tasks = [get_stream_via_network(browser, item, mappings) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend([r for r in batch_results if r])
            await asyncio.sleep(0.5)
            
        await browser.close()

        # 3. Save to PlyTorr.m3u
        if results:
            with open('PlyTorr.m3u', 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for item in results:
                    tvg_attr = f' tvg-id="{item["tvg_id"]}"' if item["tvg_id"] else ""
                    f.write(f'#EXTINF:-1{tvg_attr} tvg-logo="{item["logo"]}" group-title="{item["group"]}", {item["name"]}\n')
                    f.write(f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n')
                    f.write(f'{item["link"]}\n')
            print(f"\n✨ DONE! Generated PlyTorr.m3u with {len(results)} fresh links.")
        else:
            print("\n❌ No links were captured.")

if __name__ == "__main__":
    asyncio.run(main())