import requests
import json
import gzip
from io import BytesIO

DATA_URL = "https://i.mjh.nz/PlutoTV/.channels.json.gz"
OUTPUT_FILE = "pluto_tv.m3u"

def fetch_and_generate_m3u():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Pluto TV verileri çekiliyor: {DATA_URL}")
    response = requests.get(DATA_URL, headers=headers, timeout=(10, 30))
    response.raise_for_status()

    # Gzip sıkıştırmasını aç
    json_bytes = gzip.GzipFile(fileobj=BytesIO(response.content)).read()
    data = json.loads(json_bytes)

    regions_data = data.get("regions", {})
    slug_template = data.get("slug", "{id}")

    valid_channels = []

    # Bütün bölgelerdeki kanalları tara
    for region_key, region_val in regions_data.items():
        channels = region_val.get("channels", {})
        for ch_id, ch in channels.items():
            # Lisanslı/DRM korumalı kanalları atla
            if ch.get("license_url"):
                continue

            # Şablon üzerinden slug üret
            slug = slug_template.format(id=ch_id)
            
            # Doğrudan jmp2 akış adresi (oynatıcı seviyesinde çözülecek)
            stream_url = f"https://jmp2.uk/{slug}"
            
            valid_channels.append((ch_id, ch, stream_url))

    print(f"İşlem Tamamlandı! Toplam {len(valid_channels)} kanal M3U listesine aktarılıyor...")

    # M3U Dosyasını Oluştur
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

    print(f"Başarılı! '{OUTPUT_FILE}' dosyasına {len(valid_channels)} kanal yazıldı.")

if __name__ == "__main__":
    fetch_and_generate_m3u()
