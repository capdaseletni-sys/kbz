import requests
import time

INPUT_M3U8 = "baniknik.m3u8"
OUTPUT_M3U8 = "globe.m3u8"

TIMEOUT = 7  # seconds
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def is_stream_online(url):
    """
    Check if a stream URL is reachable.
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            stream=True
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def process_m3u8(input_file, output_file):
    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    output_lines = ["#EXTM3U\n"]
    total = 0
    working = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                total += 1
                print(f"Checking ({total}): {url}")

                if is_stream_online(url):
                    output_lines.append(lines[i])
                    output_lines.append(lines[i + 1])
                    working += 1
                    print("  ✔ Online")
                else:
                    print("  ✖ Offline")

                i += 2
                time.sleep(0.3)  # avoid spamming servers
            else:
                i += 1
        else:
            i += 1

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print("\nDone!")
    print(f"Total streams checked: {total}")
    print(f"Working streams saved: {working}")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    process_m3u8(INPUT_M3U8, OUTPUT_M3U8)
