def is_stream_playable(url, headers=None):
    headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code >= 400:
            return False
    except requests.RequestException:
        return False

    content_type = r.headers.get("Content-Type", "").lower()

    # ---------- HLS ----------
    if ".m3u8" in url or "mpegurl" in content_type:
        text = r.text
        if not text.lstrip().startswith("#EXTM3U"):
            return False

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # Master playlist
        if any(l.startswith("#EXT-X-STREAM-INF") for l in lines):
            for i, l in enumerate(lines):
                if l.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                    variant = lines[i + 1]
                    if not variant.startswith("#"):
                        return is_stream_playable(urljoin(url, variant), headers)
            return False

        # Media playlist
        segments = [l for l in lines if not l.startswith("#")]
        if not segments:
            return False

        seg_url = urljoin(url, segments[0])

        try:
            seg = requests.get(seg_url, headers=headers, timeout=TIMEOUT, stream=True)
            if seg.status_code >= 400:
                return False

            data = b""
            for chunk in seg.iter_content(8192):
                data += chunk
                if len(data) >= 32768:  # 32 KB
                    break

            # ❗ Critical FAST filter
            if len(data) < 20000:
                return False

            # MPEG-TS sync byte check
            if b"\x47" not in data[:188*5]:
                return False

            return True

        except requests.RequestException:
            return False

    # ---------- NON-HLS ----------
    else:
        try:
            data = b""
            for chunk in r.iter_content(8192):
                data += chunk
                if len(data) >= 32768:
                    break
            return len(data) >= 20000
        except Exception:
            return False
