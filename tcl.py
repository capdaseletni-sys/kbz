import requests
import sys
from pathlib import Path
from urllib.parse import urljoin

TIMEOUT = 10

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def is_stream_playable(url, headers=None):
    headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
        if r.status_code >= 400:
            return False
    except requests.RequestException:
        return False

    content_type = r.headers.get("Content-Type", "").lower()

    # ---------- HLS STREAM ----------
    if ".m3u8" in url or "mpegurl" in content_type:
        try:
            text = r.text
        except Exception:
            return False

        if not text.lstrip().startswith("#EXTM3U"):
            return False

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Master playlist
        if any(line.startswith("#EXT-X-STREAM-INF") for line in lines):
            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                    variant = lines[i + 1]
                    if not variant.startswith("#"):
                        return is_stream_playable(
                            urljoin(url, variant),
                            headers
                        )
            return False

        # Media playlist
        segments = [line for line in lines if not line.startswith("#")]
        if not segments:
            return False

        seg_url = urljoin(url, segments[0])
        try:
            seg = requests.get(seg_url, headers=headers, timeout=TIMEOUT, stream=True)
            if seg.status_code < 400:
                chunk = next(seg.iter_content(4096), None)
                return bool(chunk)
        except requests.RequestException:
            return False

    # ---------- NON-HLS STREAM ----------
    else:
        try:
            chunk = next(r.iter_content(4096), None)
            return bool(chunk)
        except Exception:
            return False


def filter_m3u_playlist(input_path, output_path):
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
                print("  ✗ Not playable")

            extinf, vlcopts = [], []

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
