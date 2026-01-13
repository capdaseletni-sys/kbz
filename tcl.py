import requests
import sys
from pathlib import Path
from urllib.parse import urljoin

TIMEOUT = 10
VALID_PLAYLIST_TYPES = {
    "application/vnd.apple.mpegurl",
    "application/x-mpegURL",
}

VALID_SEGMENT_TYPES = {
    "video/mp2t",
    "video/ts",
    "application/octet-stream",
}

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0"
}


def is_hls_stream_playable(url: str, headers=None) -> bool:
    headers = {**HEADERS_DEFAULT, **(headers or {})}

    # 1️⃣ Fetch playlist
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code >= 400:
            return False

        content_type = r.headers.get("Content-Type", "").split(";")[0]
        if content_type not in VALID_PLAYLIST_TYPES:
            return False

        playlist_text = r.text
    except requests.RequestException:
        return False

    # 2️⃣ Extract media segment URLs
    segment_urls = []
    for line in playlist_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and (
            line.endswith(".ts") or ".ts?" in line
        ):
            segment_urls.append(urljoin(url, line))
            if len(segment_urls) >= 3:
                break

    if not segment_urls:
        return False

    # 3️⃣ Validate at least one segment
    for seg_url in segment_urls:
        try:
            seg = requests.get(
                seg_url,
                headers=headers,
                timeout=TIMEOUT,
                stream=True
            )
            if seg.status_code < 400:
                ct = seg.headers.get("Content-Type", "").split(";")[0]
                if ct in VALID_SEGMENT_TYPES or not ct:
                    # Read a small chunk to ensure payload exists
                    chunk = next(seg.iter_content(2048), None)
                    if chunk:
                        return True
        except requests.RequestException:
            continue

    return False


def filter_m3u_playlist(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.rstrip() for line in f]

    output_lines = ["#EXTM3U"]
    buffer_tags = []
    buffer_vlcopt = []

    for line in lines:
        if line.startswith("#EXTINF"):
            buffer_tags.append(line)

        elif line.startswith("#EXTVLCOPT"):
            buffer_vlcopt.append(line)

        elif line.strip():
            url = line.strip()

            # Convert VLC options to HTTP headers
            headers = {}
            for opt in buffer_vlcopt:
                if opt.startswith("#EXTVLCOPT:"):
                    key, _, value = opt[len("#EXTVLCOPT:"):].partition("=")
                    key = key.lower()
                    if key == "http-referrer":
                        headers["Referer"] = value
                    elif key == "http-origin":
                        headers["Origin"] = value
                    elif key == "http-user-agent":
                        headers["User-Agent"] = value

            print(f"Checking: {url}")

            if is_hls_stream_playable(url, headers=headers):
                print("  ✓ Playable")
                output_lines.extend(buffer_tags)
                output_lines.extend(buffer_vlcopt)
                output_lines.append(url)
            else:
                print("  ✗ Not playable")

            buffer_tags.clear()
            buffer_vlcopt.clear()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"\nSaved filtered playlist to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_m3u_playlist.py input.m3u output.m3u")
        sys.exit(1)

    input_m3u = sys.argv[1]
    output_m3u = sys.argv[2]

    if not Path(input_m3u).exists():
        print("Input file does not exist.")
        sys.exit(1)

    filter_m3u_playlist(input_m3u, output_m3u)
