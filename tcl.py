def is_hls_playable(url, headers=None):
    headers = {**DEFAULT_HEADERS, **(headers or {})}

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code >= 400:
            return False
        text = r.text
        if not text.lstrip().startswith("#EXTM3U"):
            return False
    except requests.RequestException:
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # ---------- MASTER PLAYLIST ----------
    if any(line.startswith("#EXT-X-STREAM-INF") for line in lines):
        variants = []
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines):
                uri = lines[i + 1]
                if not uri.startswith("#"):
                    variants.append(uri)

        if not variants:
            return False

        # Try first variant
        variant_url = urljoin(url, variants[0])

        try:
            r = requests.get(variant_url, headers=headers, timeout=TIMEOUT)
            if r.status_code >= 400:
                return False
            text = r.text
            if not text.lstrip().startswith("#EXTM3U"):
                return False
        except requests.RequestException:
            return False

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        base_url = variant_url

    # ---------- MEDIA PLAYLIST ----------
    else:
        base_url = url

    segments = [
        line for line in lines
        if not line.startswith("#")
    ]

    if not segments:
        return False

    # Try up to 3 segments
    for seg in segments[:3]:
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
