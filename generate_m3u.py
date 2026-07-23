import requests
import json
import gzip
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_URL = "https://i.mjh.nz/PlutoTV/.channels.json.gz"
PLAYBACK_URL = "https://jmp2.uk/{slug}"
OUTPUT_FILE = "pluto_tv.m3u"

# Paralel test ayarları
MAX_WORKERS = 20
TIMEOUT_SECONDS = 2.0

def check_stream(channel_data):
    ch_id, ch, slug_template = channel_data
    
    # DRM veya Lisanslı kanalları atla
    if ch.get("license_url"):
        return None

    slug = slug_template.format(id=ch_id)
    stream_url = PLAYBACK_URL.format(slug=slug)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Yayın bağlantısına istek atıp canlılık kontrolü yap
        res = requests.head(stream_url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        if res.status_code == 200:
            return (ch_id, ch, stream_url)
        
        # HEAD yanıt vermezse GET dene
        res = requests.get(stream_url, headers=headers, timeout=TIMEOUT_SECONDS, stream=True)
        if res.status_code == 200:
            return (ch_id, ch, stream_url)
    except Exception:
        pass

    return None

def fetch_and_generate_m3u():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print(f"Pluto TV verileri çekiliyor: {DATA_URL}")
    response = requests.get(DATA_URL, headers=headers, timeout=(10, 30))
    response.raise_for_status()

    json_bytes = gzip.GzipFile(fileobj=BytesIO(response.content)).read()
    data = json.loads(json_bytes)

    regions_data = data.get("regions", {})
    slug_template = data.get("slug", "{id}")

    candidate_channels = []

    # Bütün bölgelerdeki kanalları çek
    for region_key, region_val in regions_data.items():
        channels = region_val.get("channels", {})
        for ch_id, ch in channels.items():
            candidate_channels.append((ch_id, ch, slug_template))

    print(f"Toplam {len(candidate_channels)} kanal bulundu. Canlılık testi başlatılıyor...")

    valid_channels = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_stream, item) for item in candidate_channels]
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_channels.append(result)

    print(f"Test Bitti! {len(valid_channels)} çalışan kanal bulundu.")

    # M3U Oluştur
    m3u_lines = ["#EXTM3U\n"]
    for ch_id, ch, stream_url in valid_channels:
        name = ch.get("name", "Pluto Channel")
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

    print(f"İşlem Tamamlandı! '{OUTPUT_FILE}' dosyasına yazıldı.")

if __name__ == "__main__":
    fetch_and_generate_m3u()
