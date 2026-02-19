# ... (imports and TEAM_MAP remain the same)

# Updated Mirror configuration with the new URL
MIRRORS = [
    {"base": "https://live3.totalsportek777.com/", "hex_decode": True},
    {"base": "https://live.totalsportek777.com/", "hex_decode": True},
    {"base": "https://live2.totalsportek777.com/", "hex_decode": False},
]

# ... (fix_txt, shorten_nba_teams, load_cache, etc., remain the same)

async def scrape() -> None:
    cached_data = load_cache()
    current_time = time.time()
    
    # 8-hour cache window (28,800 seconds)
    active_cache = {k: v for k, v in cached_data.items() if current_time - v.get("timestamp", 0) < 28800}
    urls.update({k: v for k, v in active_cache.items() if v.get("url")})

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        base_url = None
        # This loop now checks live3 first
        for mirror in MIRRORS:
            try:
                r = await client.get(mirror["base"], timeout=5.0)
                if r.status_code == 200:
                    base_url = str(r.url)
                    log.info(f"Connected to mirror: {base_url}")
                    break
            except Exception as e:
                log.warning(f"Mirror {mirror['base']} failed: {e}")
                continue

        if not base_url:
            log.error("All mirrors are unreachable.")
            return

        new_events = await get_events(client, base_url, list(active_cache.keys()))

        for i, ev in enumerate(new_events, start=1):
            # Pass the mirror config to handle different decoding needs
            m3u8, iframe = await process_event(client, ev["href"], i)
            if m3u8:
                entry = {"url": m3u8, "base": iframe, "timestamp": time.time(), "href": ev["href"]}
                active_cache[ev["key"]] = entry
                urls[ev["key"]] = entry
                log.info(f"Added: {ev['key']}")

    # Generate M3U
    m3u_lines = ["#EXTM3U"]
    for title, data in urls.items():
        if stream_url := data.get("url"):
            m3u_lines.append(f'#EXTINF:-1 group-title="Totalsports", {title}')
            m3u_lines.append(stream_url)

    with open(M3U_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    save_cache(active_cache)
    log.info(f"Updated {M3U_FILENAME} with {len(urls)} active streams.")

if __name__ == "__main__":
    asyncio.run(scrape())
