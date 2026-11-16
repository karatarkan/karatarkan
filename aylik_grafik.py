"""Aylık katkı grafiği: son 12 ayın katkılarını GitHub GraphQL'den okur, iki SVG yazar.

Kullanım: GITHUB_TOKEN=... python3 aylik_grafik.py <kullanici> <cikis_dizini>
Yalnız standart kütüphane.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

AYLAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def sorgula(kullanici, bas, son, belirtec):
    sorgu = (
        'query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){'
        'contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{'
        'contributionDays{date contributionCount}}}}}}'
    )
    govde = json.dumps({"query": sorgu, "variables": {"u": kullanici, "f": bas, "t": son}}).encode()
    istek = urllib.request.Request(
        "https://api.github.com/graphql",
        data=govde,
        headers={"Authorization": f"bearer {belirtec}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        veri = json.load(yanit)
    if "errors" in veri:
        raise SystemExit(json.dumps(veri["errors"]))
    hafta = veri["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [g for h in hafta for g in h["contributionDays"]]


def aylik(kullanici, belirtec, bugun):
    ilk = dt.date(bugun.year - 1, bugun.month, 1) + dt.timedelta(days=32)
    ilk = ilk.replace(day=1)  # 11 ay önceki ayın başı: toplam 12 ay
    gunler = sorgula(kullanici, f"{ilk}T00:00:00Z", f"{bugun}T23:59:59Z", belirtec)
    toplam = {}
    for g in gunler:
        anahtar = g["date"][:7]
        toplam[anahtar] = toplam.get(anahtar, 0) + g["contributionCount"]
    aylar = []
    y, a = ilk.year, ilk.month
    for _ in range(12):
        anahtar = f"{y:04d}-{a:02d}"
        aylar.append((anahtar, toplam.get(anahtar, 0)))
        a += 1
        if a == 13:
            y, a = y + 1, 1
    return aylar


def svg(aylar, renk):
    g, y_ust, y_alt, sol, sag = 820, 70, 250, 24, 24
    en_cok = max(1, max(s for _, s in aylar))
    toplam = sum(s for _, s in aylar)
    # yoğunluğun başladığı ay: toplamın %95'ini taşıyan son kesintisiz aralığın başı
    kalan, bas = 0, aylar[-1][0]
    for anahtar, sayi in reversed(aylar):
        kalan += sayi
        bas = anahtar
        if kalan >= 0.95 * toplam:
            break
    pay = round(100 * kalan / toplam) if toplam else 0
    bas_y, bas_a = int(bas[:4]), int(bas[5:])
    alt_baslik = f"{toplam:,} contributions in the last 12 months · {pay}% of them since {AYLAR[bas_a - 1]} {bas_y}"
    genislik = (g - sol - sag) / len(aylar)
    cubuk = genislik * 0.62
    parcalar = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{g}" height="290" viewBox="0 0 {g} 290" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{g}" height="290" rx="10" fill="{renk["zemin"]}"/>',
        f'<text x="{sol}" y="34" font-size="17" font-weight="600" fill="{renk["baslik"]}">Contributions per month</text>',
        f'<text x="{sol}" y="56" font-size="12.5" fill="{renk["soluk"]}">{alt_baslik}</text>',
    ]
    for i, (anahtar, sayi) in enumerate(aylar):
        x = sol + i * genislik + (genislik - cubuk) / 2
        yuk = (y_alt - y_ust - 18) * sayi / en_cok
        ust = y_alt - yuk
        dolgu = renk["cubuk"] if sayi else renk["bos"]
        parcalar.append(
            f'<rect x="{x:.1f}" y="{ust - (0 if sayi else 2):.1f}" width="{cubuk:.1f}" '
            f'height="{max(yuk, 2):.1f}" rx="3" fill="{dolgu}"/>'
        )
        if sayi:
            parcalar.append(
                f'<text x="{x + cubuk / 2:.1f}" y="{ust - 6:.1f}" font-size="11" text-anchor="middle" '
                f'fill="{renk["baslik"]}">{sayi:,}</text>'
            )
        ay = AYLAR[int(anahtar[5:]) - 1]
        etiket = f"{ay} '{anahtar[2:4]}" if anahtar[5:] == "01" or i == 0 else ay
        if i == len(aylar) - 1:
            etiket = f"{ay} so far"
        parcalar.append(
            f'<text x="{x + cubuk / 2:.1f}" y="{y_alt + 20}" font-size="11" text-anchor="middle" '
            f'fill="{renk["soluk"]}">{etiket}</text>'
        )
    parcalar.append("</svg>")
    return "\n".join(parcalar) + "\n"


KOYU = {"zemin": "#161b22", "baslik": "#e6edf3", "soluk": "#9198a1", "cubuk": "#39d353", "bos": "#2a313c"}
ACIK = {"zemin": "#f6f8fa", "baslik": "#1f2328", "soluk": "#59636e", "cubuk": "#1a7f37", "bos": "#d1d9e0"}

if __name__ == "__main__":
    kullanici, cikis = sys.argv[1], sys.argv[2]
    aylar = aylik(kullanici, os.environ["GITHUB_TOKEN"], dt.date.today())
    os.makedirs(cikis, exist_ok=True)
    for ad, renk in (("aylik-katki-koyu.svg", KOYU), ("aylik-katki-acik.svg", ACIK)):
        with open(os.path.join(cikis, ad), "w", encoding="utf-8") as f:
            f.write(svg(aylar, renk))
    print(aylar)
