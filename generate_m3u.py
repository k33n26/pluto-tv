import requests
import json
import gzip
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

# Pluto TV Güncel Veri Adresi
DATA_URL = "https://i.mjh.nz/PlutoTV/.channels.json.gz"
PLAYBACK_URL = "https://jmp2.uk/{slug}"
OUTPUT_FILE = "pluto_tv.m3u"

# İçerik kalitesi yüksek ve yayınları rahat açılan ana bölgeler
TARGET_REGIONS = ["us", "gb", "de", "ca"]

# Hızlı tarama parametreleri (30 eşzamanlı istek, 1.2 sn timeout)
MAX_WORKERS = 30
TIMEOUT_SECONDS = 1.2

def check_stream(channel_data):
    ch_id, ch, slug_template = channel_data
    
    # DRM / Lisans koruması olan kanalları ele
    if ch.get("license_url"):
        return None

    slug = slug_template.format(id=ch_id)
    stream_url = PLAYBACK_URL.format(slug=slug)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Yayın adresine hızlı HEAD kontrolü at
        res = requests.head(stream_url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        if res.status_code == 200:
            return (ch_id, ch, stream_url)
    except Exception:
        pass

    return None

def fetch_and_generate_m3u():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print(f"Pluto TV verileri indiriliyor: {DATA_URL}")
    response = requests.get(DATA_URL, headers=headers, timeout=(5, 15))
    response.raise_for_status()

    json_bytes = gzip.GzipFile(fileobj=BytesIO(response.content)).read()
    data = json.loads(json_bytes)

    regions_data = data.get("regions", {})
    slug_template = data.get("slug", "{id}")

    candidate_channels = []

    for region_key, region_val in regions_data.items():
        if region_key.lower() in TARGET_REGIONS:
            channels = region_val.get("channels", {})
            for ch_id, ch in channels.items():
                candidate_channels.append((ch_id, ch, slug_template))

    print(f"Toplam {len(candidate_channels)} aday Pluto TV kanalı bulundu. Bağlantılar test ediliyor...")

    valid_channels = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_stream, item) for item in candidate_channels]
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_channels.append(result)

    print(f"Test Tamamlandı! {len(valid_channels)} aktif kanal listeye alınıyor...")

    # M3U Formatında Yapılandır
    m3u_lines = ["#EXTM3U\n"]
    for ch_id, ch, stream_url in valid_channels:
        name = ch.get("name", "Unknown Channel")
        logo = ch.get("logo", "")
        group = ch.get("group", "Pluto TV")
        chno = ch.get("chno", "")
        tvg_chno = f' tvg-chno="{chno}"' if chno else ""

        m3u_lines.append(
            f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}"{tvg_chno},{name}\n'
        )
        m3u_lines.append(f"{stream_url}\n\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(m3u_lines)

    print(f"Başarılı! '{OUTPUT_FILE}' dosyası oluşturuldu.")

if __name__ == "__main__":
    fetch_and_generate_m3u()
