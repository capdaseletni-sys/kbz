import requests
import sys
from pathlib import Path
from urllib.parse import urljoin

TIMEOUT = 10

# Default headers to mimic a browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def is_stream_playable(url, headers=None):
    """
    Relaxed playable check:
    - Returns True if URL is reachable (<400)
    - If HLS (.m3u8), checks master/variant playlists and first segment
    - Does NOT inspect payload (to avoid rejecting Amagi / CloudFront)
    """
    headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code >= 400:
            return False
    except requests.RequestException:
        return False

    content_type = r.headers.get("Content-Type", "").lower()

    # ---------- HLS playlist ----------
    if ".m3u8" in url or "mpegurl" in content_type:
        text = r.text
        if not text.lstrip().startswith("#EXTM3U"):
            return False

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Master playlist → check first variant recursively
        if any(l.startswith("#EXT-X-STREAM-INF") for l in lines):
            for i, l in enumerate(lines):
                if l.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                    variant = lines[i + 1]
                    if not variant.startswith("#"):
                        return is_stream_playable(urljoin(url, variant), headers)
            return False

        # Media playlist → check first segment URL only
        segments = [l for l in lines if not l.startswith("#")]
        if not segments:
            return False

        seg_url = urljoin(url, segments[0])
        try:
            seg = requests.get(seg_url, headers=headers, timeout=TIMEOUT, stream=True)
            return seg.status_code < 400
        except requests.RequestException:
            return False

    # ---------- Non-HLS stream ----------
    return True


def filter_m3u_playlist(input_path, output_path):
    """Reads an EXTINF-based M3U playlist and outputs only playable streams."""
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip() for line in f]

    output = ["#EXTM3U"]
    extinf, vlcopts = [], []

    for line in lines:
        if line.startswith("#EXTINF"):
            extinf = [line]

        elif line.startswith("#EXTVLCOPT"):
            vlcopts.append(line)

        elif line.strip().startswith(("http://", "https://")):
            url = line.strip()

            # Convert VLC options to HTTP headers
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
            if is_stream_playable(url, headers):
                print("  ✓ Playable")
                output.extend(extinf)
                output.extend(vlcopts)
                output.append(url)
            else:
                print("  ✗ Not reachable")

            extinf, vlcopts = [], []

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output) + "\n")

    print(f"\nSaved filtered playlist to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_m3u_playlist.py input.m3u output.m3u")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print("Input file does not exist.")
        sys.exit(1)

    filter_m3u_playlist(input_file, output_file)
