import requests
import sys
from pathlib import Path
from urllib.parse import urljoin

TIMEOUT = 10

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_text(url, headers):
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    if r.status_code >= 400:
        return None
    if "#EXTM3U" not in r.text:
        return None
    return r.text


def extract_uris(playlist_text):
    return [
        line.strip()
        for line in playlist_text.splitlines()
        if line and not line.startswith("#")
    ]


def is_hls_playable(url, headers=None):
    headers = {**DEFAULT_HEADERS, **(headers or {})}

    # 1️⃣ Load initial playlist
    playlist = fetch_text(url, headers)
    if not playlist:
        return False

    uris = extract_uris(playlist)
    if not uris:
        return False

    # 2️⃣ If master playlist → load first variant
    if any("#EXT-X-STREAM-INF" in line for line in playlist.splitlines()):
        variant_url = urljoin(url, uris[0])
        playlist = fetch_text(variant_url, headers)
        if not playlist:
            return False
        uris = extract_uris(playlist)
        if not uris:
            return False
        base_url = variant_url
    else:
        base_url = url

    # 3️⃣ Try up to 3 segments
    for seg in uris[:3]:
        seg_url = urljoin(base_url, seg)
        try:
            r = requests.get(seg_url, headers=headers, timeout=TIMEOUT, stream=True)
            if r.status_code < 400:
                chunk = next(r.iter_content(4096), None)
                if chunk:
                    return True
        except requests.RequestException:
            continue

    return False


def filter_m3u_playlist(input_path, output_path):
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip() for line in f]

    output = ["#EXTM3U"]
    tags, vlcopts = [], []

    for line in lines:
        if line.startswith("#EXTINF"):
            tags.append(line)

        elif line.startswith("#EXTVLCOPT"):
            vlcopts.append(line)

        elif line.strip():
            url = line.strip()

            headers = {}
            for opt in vlcopts:
                key, _, value = opt[len("#EXTVLCOPT:"):].partition("=")
                key = key.lower()
                if key == "http-referrer":
                    headers["Referer"] = value
                elif key == "http-origin":
                    headers["Origin"] = value
                elif key == "http-user-agent":
                    headers["User-Agent"] = value

            print(f"Checking: {url}")
            if is_hls_playable(url, headers):
                print("  ✓ Playable")
                output.extend(tags)
                output.extend(vlcopts)
                output.append(url)
            else:
                print("  ✗ Not playable")

            tags.clear()
            vlcopts.clear()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output) + "\n")

    print(f"\nSaved filtered playlist to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_m3u_playlist.py input.m3u output.m3u")
        sys.exit(1)

    if not Path(sys.argv[1]).exists():
        print("Input file does not exist.")
        sys.exit(1)

    filter_m3u_playlist(sys.argv[1], sys.argv[2])
