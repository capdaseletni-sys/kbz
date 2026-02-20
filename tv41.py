from curl_cffi import requests
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
PLAYLIST_URL = "http://1tv41.icu:8080/get.php?username=Y06DNq&password=295733&type=m3u_plus"
FILE_NAME = "tv41.m3u8"
MAX_WORKERS = 20  # How many channels to check at the same time

TARGET_GROUPS = [
    'group-title="USA "',
    'group-title="CANADA"',
    'group-title="UK UNITED KINGDOM"',
    'group-title="USA | NEWS | REGIONALS "',
    'group-title="MOVIE NETWORKS"',
    'group-title="Sports Fanatic\'s "',
    'group-title="24/7 CHANNELS "'
]

def get_best_save_path():
    user_home = os.path.expanduser("~")
    possible_paths = [
        os.path.join(user_home, "Desktop", FILE_NAME),
        os.path.join(user_home, "OneDrive", "Desktop", FILE_NAME),
        FILE_NAME
    ]
    for path in possible_paths:
        if os.path.exists(os.path.dirname(path)) or os.path.dirname(path) == "":
            return path
    return FILE_NAME

def check_link(name, info_line, url):
    """Checks if a single stream URL is reachable."""
    headers = {"User-Agent": "IPTVSmartersPro"}
    try:
        # We use a HEAD request or a short timeout to speed things up
        # impersonate="chrome110" ensures the provider doesn't block the check
        response = requests.get(url, headers=headers, impersonate="chrome110", timeout=5, stream=True)
        if response.status_code == 200:
            return (info_line, url)
    except:
        pass
    return None

def download_filter_verify():
    save_path = get_best_save_path()
    headers = {"User-Agent": "IPTVSmartersPro"}

    try:
        print(f"1. Downloading main playlist...")
        res = requests.get(PLAYLIST_URL, headers=headers, impersonate="chrome110", timeout=60)
        if res.status_code != 200:
            print(f"❌ Failed to download source.")
            return

        lines = res.text.splitlines()
        candidate_channels = []
        group_regex = r'group-title="[^"]*"'

        print(f"2. Filtering by group and preparing for verification...")
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                if any(group in lines[i] for group in TARGET_GROUPS):
                    # Rename the group to Direct TV
                    modified_info = re.sub(group_regex, 'group-title="Direct TV"', lines[i])
                    if i + 1 < len(lines):
                        url = lines[i+1]
                        name = modified_info.split(",")[-1]
                        candidate_channels.append((name, modified_info, url))

        print(f"3. Verifying {len(candidate_channels)} channels (Live Check)...")
        verified_content = ["#EXTM3U"]
        
        # Use ThreadPoolExecutor to check channels in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_chan = {executor.submit(check_link, c[0], c[1], c[2]): c for c in candidate_channels}
            
            count = 0
            for future in as_completed(future_to_chan):
                result = future.result()
                if result:
                    verified_content.append(result[0])
                    verified_content.append(result[1])
                    count += 1
                
                # Print progress every 10 channels
                if (len(verified_content) // 2) % 10 == 0:
                    print(f"   Checked {len(verified_content)//2} working channels...", end="\r")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(verified_content))
            
        print(f"\n✅ SUCCESS! File saved to: {os.path.abspath(save_path)}")
        print(f"Total Found: {len(candidate_channels)} | Alive & Saved: {count}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    download_filter_verify()
