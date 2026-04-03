#!/usr/bin/env python3
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright
# Only importing the specific scraper we are interested in
from scrapers import ppv
from scrapers.utils import get_logger, network

log = get_logger(__name__)

# File paths maintained from original logic
BASE_FILE = Path(__file__).parent / "base.m3u8"
EVENTS_FILE = Path(__file__).parent / "events.m3u8"
COMBINED_FILE = Path(__file__).parent / "TV.m3u8"

def load_base() -> tuple[list[str], int]:
    if not BASE_FILE.exists():
        log.warning("base.m3u8 not found, starting with empty base.")
        return ["#EXTM3U"], 0
        
    log.info("Fetching base M3U8")
    data = BASE_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r'tvg-chno="(\d+)"')
    last_chnl_num = max(map(int, pattern.findall(data)), default=0)
    return data.splitlines(), last_chnl_num

async def main() -> None:
    log.info(f"{'=' * 10} PPV Scraper Started {'=' * 10}")

    base_m3u8, tvg_chno = load_base()

    async with async_playwright() as p:
        # Initializing browsers via the network utility
        hdl_brwsr = await network.browser(p)
        xtrnl_brwsr = await network.browser(p, external=True)

        try:
            # We only run the PPV task now
            log.info("Running PPV scrape task...")
            await ppv.scrape(xtrnl_brwsr)

        finally:
            await hdl_brwsr.close()
            await xtrnl_brwsr.close()
            await network.client.aclose()

    # Only process the PPV dictionary
    additions = ppv.urls
    live_events: list[str] = []
    combined_channels: list[str] = []

    for i, (event, info) in enumerate(sorted(additions.items()), start=1):
        # Logic for M3U tags preserved exactly as original
        extinf_all = (
            f'#EXTINF:-1 tvg-chno="{tvg_chno + i}" tvg-id="{info["id"]}" '
            f'tvg-name="{event}" tvg-logo="{info["logo"]}" group-title="Live Events",{event}'
        )

        extinf_live = (
            f'#EXTINF:-1 tvg-chno="{i}" tvg-id="{info["id"]}" '
            f'tvg-name="{event}" tvg-logo="{info["logo"]}" group-title="Live Events",{event}'
        )

        vlc_block = [
            f'#EXTVLCOPT:http-referrer={info["base"]}',
            f'#EXTVLCOPT:http-origin={info["base"]}',
            f"#EXTVLCOPT:http-user-agent={info.get('UA', network.UA)}",
            info["url"],
        ]

        combined_channels.extend(["\n" + extinf_all, *vlc_block])
        live_events.extend(["\n" + extinf_live, *vlc_block])

    # Save outputs
    COMBINED_FILE.write_text("\n".join(base_m3u8 + combined_channels), encoding="utf-8")
    log.info(f"Combined M3U saved to {COMBINED_FILE.resolve()}")

    EVENTS_FILE.write_text(
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/TV.xml"\n'
        + "\n".join(live_events),
        encoding="utf-8",
    )
    log.info(f"Events M3U saved to {EVENTS_FILE.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())

    # Ensuring the flush for console output as requested
    for hndlr in log.handlers:
        hndlr.flush()
        if hasattr(hndlr, 'stream'):
            hndlr.stream.write("\n")
            hndlr.stream.flush()
