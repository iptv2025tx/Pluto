import requests
import uuid
import time
from datetime import datetime, timedelta, timezone

STITCHER = "https://cfd-v4-service-channel-stitcher-use1-1.prd.pluto.tv"
EPG_URL = "https://github.com/matthuisman/i.mjh.nz/raw/master/PlutoTV/all.xml.gz"
OUTPUT_FILE = "pluto_global.m3u"

REGIONS = {
    "United States": "108.82.206.181",
    "Canada": "192.206.151.131",
    "United Kingdom": "178.238.11.6",
    "Argentina": "168.226.232.228",
    "Brazil": "104.112.149.255",
    "Chile": "200.89.74.146",
    "Denmark": "192.36.27.7",
    "France": "91.160.93.4",
    "Germany": "85.214.132.117",
    "Italy": "80.207.161.250",
    "Mexico": "201.144.119.146",
    "Norway": "160.68.205.231",
    "Spain": "88.26.241.248",
    "Sweden": "192.44.242.19"
}

def format_time(dt):
    return dt.replace(minute=0, second=0, microsecond=0) \
             .isoformat() \
             .replace("+00:00", "Z")

def start_session(region_ip):
    device_id = str(uuid.uuid4())
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Forwarded-For": region_ip,
        "X-Real-IP": region_ip,
        "CF-Connecting-IP": region_ip
    }

    boot_url = (
        "https://boot.pluto.tv/v4/start?"
        "appName=web"
        "&appVersion=8.0.0"
        "&deviceVersion=122.0.0"
        "&deviceModel=web"
        "&deviceMake=chrome"
        "&deviceType=web"
        f"&clientID={device_id}"
        "&clientModelNumber=1.0.0"
        "&serverSideAds=false"
        "&drmCapabilities=widevine:L3"
    )

    r = requests.get(boot_url, headers=headers, timeout=30)
    data = r.json()
    return data.get("sessionToken"), data.get("stitcherParams", ""), headers

def fetch_channels(headers):
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=6)
    start = format_time(now)
    stop = format_time(later)
    url = f"https://api.pluto.tv/v2/channels?start={start}&stop={stop}"
    r = requests.get(url, headers=headers, timeout=30)
    data = r.json()
    return data if isinstance(data, list) else []

def build_playlist():
    playlist = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'

    for country_name, ip in REGIONS.items():
        print(f"Generating {country_name} channels...")

        token, stitcher_params, headers = start_session(ip)
        channels = []

        if token:
            channels = fetch_channels(headers)

        valid_channels = [ch for ch in channels if isinstance(ch, dict) and ch.get("isStitched")]

        # If no channels, insert placeholder
        if not valid_channels:
            playlist += (
                f'#EXTINF:-1 group-title="{country_name}" '
                f'tvg-id="{country_name}-placeholder" '
                f'tvg-name="No Channels Available" '
                f'tvg-logo="",No Channels Available\n'
            )
            playlist += "http://example.com/blank\n\n"
            continue

        for ch in valid_channels:
            name = ch.get("name", "Unknown")
            slug = ch.get("slug", "")
            logo = ch.get("colorLogoPNG", {}).get("path", "")

            stream_url = (
                f"{STITCHER}/v2/stitch/hls/channel/{ch['_id']}/master.m3u8"
                f"?{stitcher_params}&jwt={token}&masterJWTPassthrough=true"
            )

            tvg_id = f"{country_name}-{slug}"

            playlist += (
                f'#EXTINF:-1 group-title="{country_name}" '
                f'tvg-id="{tvg_id}" '
                f'tvg-name="{name}" '
                f'tvg-logo="{logo}",{name}\n'
            )
            playlist += stream_url + "\n\n"

    return playlist

def save_playlist(content):
    content = content.replace("\r\n", "\n")
    with open(OUTPUT_FILE, "wb") as f:
        f.write(content.encode("utf-8"))
    print(f"Playlist updated: {OUTPUT_FILE}")

def main():
    while True:
        print("Starting Pluto TV playlist update...")
        m3u = build_playlist()
        save_playlist(m3u)
        print("Next update in 24 hours...\n")
        time.sleep(86400)

if __name__ == "__main__":
    main()
