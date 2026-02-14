import requests
import json
import base64
import urllib.parse
from Crypto.Cipher import AES
from typing import List, Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SportzxClient:
    APP_PASSWORD = "oAR80SGuX3EEjUGFRwLFKBTiris="
    CHARSET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+!@#$%&="

    def __init__(self, timeout: int = 30): # Increased default timeout to 30s
        self.timeout = timeout
        self.raw_log = []
        # Create a session with a retry strategy
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _u32(self, x: int) -> int: 
        return x & 0xFFFFFFFF

    def _imul(self, a: int, b: int) -> int:
        res = (a * b) & 0xFFFFFFFF
        return res - 0x100000000 if res & 0x80000000 else res

    def generate_aes_key_iv(self, s: str):
        data = s.encode('utf-8')
        n = len(data)
        u = 0x811c9dc5
        for b in data: u = self._u32(self._imul(u ^ b, 0x1000193))
        key = bytearray(16)
        for i in range(16):
            b = data[i % n]
            u = self._u32(self._imul(u, 0x1f) + (i ^ b))
            key[i] = self.CHARSET[u % len(self.CHARSET)]
        u = 0x811c832a
        for b in data: u = self._u32(self._imul(u ^ b, 0x1000193))
        iv = bytearray(16)
        idx, acc = 0, 0
        while idx != 0x30:
            b = data[idx % n]
            u = self._u32(self._imul(u, 0x1d) + (acc ^ b))
            iv[idx // 3] = self.CHARSET[u % len(self.CHARSET)]
            idx += 3
            acc = self._u32(acc + 7)
        return bytes(key), bytes(iv)

    def decrypt_data(self, b64_data: str) -> str:
        try:
            ct = base64.b64decode(b64_data)
            key, iv = self.generate_aes_key_iv(self.APP_PASSWORD)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            pt = cipher.decrypt(ct)
            pad = pt[-1]
            if 0 < pad <= 16:
                pt = pt[:-pad]
            return pt.decode('utf-8')
        except Exception as e:
            print(f"Decryption Error: {e}", flush=True)
            return ""

    def fetch_decrypted(self, url: str):
        # Use session instead of direct requests for better pooling
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        raw_payload = resp.json().get('data', '')
        decrypted_json = self.decrypt_data(raw_payload)
        return json.loads(decrypted_json)

    def get_api_url(self) -> Optional[str]:
        print("Bypassing Firebase Authentication...", flush=True)
        base_headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 13)",
            "X-Android-Package": "com.sportzx.live",
            "X-Android-Cert": "A0047CD121AE5F71048D41854702C52814E2AE2B",
            "Content-Type": "application/json"
        }
        i_url = "https://firebaseinstallations.googleapis.com/v1/projects/sportzx-7cc3f/installations"
        i_headers = {**base_headers, "x-goog-api-key": "AIzaSyBa5qiq95T97xe4uSYlKo0Wosmye_UEf6w"}
        i_body = {"fid": "eOaLWBo8S7S1oN-vb23mkf", "appId": "1:446339309956:android:b26582b5d2ad841861bdd1", "authVersion": "FIS_v2", "sdkVersion": "a:18.0.0"}

        try:
            r_inst = self.session.post(i_url, json=i_body, headers=i_headers, timeout=self.timeout)
            token = r_inst.json().get('authToken', {}).get('token')
            if not token: return None

            print("Fetching Remote Config...", flush=True)
            c_url = "https://firebaseremoteconfig.googleapis.com/v1/projects/446339309956/namespaces/firebase:fetch"
            c_headers = {**base_headers, "X-Goog-Api-Key": "AIzaSyBa5qiq95T97xe4uSYlKo0Wosmye_UEf6w", "X-Goog-Firebase-Installations-Auth": token, "X-Firebase-RC-Fetch-Type": "BASE/1"}
            c_body = {"appId": "1:446339309956:android:b26582b5d2ad841861bdd1", "appInstanceId": "eOaLWBo8S7S1oN-vb23mkf", "appInstanceIdToken": token, "packageName": "com.sportzx.live", "appVersion": "2.1", "sdkVersion": "22.1.2"}

            r_conf = self.session.post(c_url, json=c_body, headers=c_headers, timeout=self.timeout)
            return r_conf.json().get('entries', {}).get('api_url')
        except Exception as e:
            print(f"Firebase Discovery Exception: {e}", flush=True)
            return None

    def build_playlist(self):
        api_url = self.get_api_url()
        if not api_url: return

        m3u_output = ["#EXTM3U"]
        total_streams = 0
        
        try:
            events = self.fetch_decrypted(f"{api_url}/events.json")
            
            for event in events:
                ev_id = event.get('id')
                ev_title = event.get('title', 'No Title')
                ev_cat = event.get('cat', 'Sports')
                
                print(f"\n[EVENT] {ev_title}", flush=True)
                
                try:
                    channels = self.fetch_decrypted(f"{api_url}/channels/{ev_id}.json")
                    self.raw_log.append({"event": event, "decrypted_channels": channels})

                    if not channels:
                        print("  └── No streams found for this event.", flush=True)
                        continue

                    for ch in channels:
                        ch_title = ch.get('title', 'Server')
                        print(f"  └── Found: {ch_title}", flush=True)
                        total_streams += 1

                        display_name = f"{ev_title} ★ {ch_title}"
                        link_parts = ch.get('link', '').split('|')
                        stream_url = link_parts[0].strip()
                        keys = ch.get('api', '') 
                        logo = event.get('eventInfo', {}).get('teamAFlag', '')

                        if ".mpd" in stream_url.lower():
                            m3u_output.append(f"\n#KODIPROP:inputstreamaddon=inputstream.adaptive")
                            m3u_output.append(f"#KODIPROP:inputstream.adaptive.manifest_type=dash")
                            if ":" in keys:
                                m3u_output.append(f"#KODIPROP:inputstream.adaptive.license_type=org.w3.clearkey")
                                m3u_output.append(f"#KODIPROP:inputstream.adaptive.license_key={keys}")
                            m3u_output.append(f'#EXTINF:-1 tvg-id="Live.Event.us" group-title="SP✦{ev_cat}" tvg-logo="{logo}",{display_name}')
                            m3u_output.append(stream_url)
                        
                        elif ".m3u8" in stream_url.lower():
                            m3u_output.append(f'\n#EXTINF:-1 tvg-id="Live.Event.us" group-title="SP✦{ev_cat}" tvg-logo="{logo}",{display_name}')
                            
                            if len(link_parts) > 1:
                                header_str = link_parts[1]
                                headers = dict(urllib.parse.parse_qsl(header_str))
                                
                                origin = headers.get('Origin') or headers.get('origin')
                                referer = headers.get('Referer') or headers.get('referer')
                                
                                if origin: m3u_output.append(f"#EXTVLCOPT:http-origin={origin}")
                                if referer: m3u_output.append(f"#EXTVLCOPT:http-referrer={referer}")
                                m3u_output.append(f"#EXTVLCOPT:http-user-agent=Mozilla/50 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0")
                            
                            m3u_output.append(stream_url)
                            
                except Exception as e:
                    print(f"  └── Error fetching channels: {e}", flush=True)

            with open("spx.m3u", "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_output))
            
            with open("raw_data_dump.json", "w", encoding="utf-8") as jf:
                json.dump(self.raw_log, jf, indent=4, ensure_ascii=False)

            print("\n" + "="*30)
            print(f"[COMPLETE] Total Streams Discovered: {total_streams}")
            print(f"- Playlist saved to: spx.m3u")
            print("="*30, flush=True)

        except Exception as e:
            print(f"Main Loop Error: {e}", flush=True)

if __name__ == "__main__":
    client = SportzxClient()
    client.build_playlist()