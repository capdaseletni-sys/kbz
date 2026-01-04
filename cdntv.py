import requests

PLAYLIST_URL = "https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/events.m3u8"
OUTPUT_FILE = "cdntv.m3u8"

KEYWORDS = ["(CDNTV)", "(SHARK)","(ROXIE)"]


def download_m3u(url: str) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def filter_m3u(content: str) -> str:
    lines = content.splitlines()
    filtered_lines = ["#EXTM3U"]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):
            lower_line = line.lower()

            if any(keyword.lower() in lower_line for keyword in KEYWORDS):
                # Keep EXTINF line
                filtered_lines.append(lines[i])

                # Keep stream URL if present
                if i + 1 < len(lines):
                    filtered_lines.append(lines[i + 1])

                i += 2
                continue

        i += 1

    return "\n".join(filtered_lines) + "\n"


def main():
    try:
        m3u_content = download_m3u(PLAYLIST_URL)
        filtered_m3u = filter_m3u(m3u_content)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(filtered_m3u)

        print(f"Filtered playlist saved to: {OUTPUT_FILE}")

    except requests.RequestException as e:
        print(f"Download error: {e}")
    except OSError as e:
        print(f"File error: {e}")


if __name__ == "__main__":
    main()
