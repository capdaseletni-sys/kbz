from curl_cffi import requests
import os

# --- CONFIGURATION ---
PLAYLIST_URL = "http://1tv41.icu:8080/get.php?username=Y06DNq&password=295733&type=m3u_plus"
FILE_NAME = "tv41.m3u8"

def get_best_save_path():
    # Try common Windows Desktop locations for the new filename
    user_home = os.path.expanduser("~")
    possible_paths = [
        os.path.join(user_home, "Desktop", FILE_NAME),
        os.path.join(user_home, "OneDrive", "Desktop", FILE_NAME),
        FILE_NAME # Fallback: Current folder
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.dirname(path)) or os.path.dirname(path) == "":
            return path
    return FILE_NAME

def download_playlist():
    save_path = get_best_save_path()
    # Keeping the User-Agent as a common IPTV player to avoid being blocked
    headers = {"User-Agent": "IPTVSmartersPro"}

    try:
        print(f"Connecting to server... downloading {FILE_NAME}")
        
        # Fetching the direct m3u_plus content
        response = requests.get(PLAYLIST_URL, headers=headers, impersonate="chrome110", timeout=60)
        
        if response.status_code == 200:
            # Save the raw text response directly to the file
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"✅ SUCCESS! File saved to: {os.path.abspath(save_path)}")
        else:
            print(f"❌ SERVER ERROR: Status Code {response.status_code}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    download_playlist()
