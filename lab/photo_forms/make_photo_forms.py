"""Synthetic photographed, hand-filled Turkish lease forms (kira sözleşmesi) for testing masking.

Why: lawyers submit phone photos of hand-filled lease contracts as evidence (sulh hukuk), and the
first real one we saw leaked both TC kimlik numbers and both names. Real ones cannot be shared, so
this script draws look-alikes: a printed form with our own layout, values in handwriting fonts and
ballpoint-blue ink, then a phone-photo look (wood floor, perspective, shading, show-through from the
back of the sheet, blur, JPEG), saved as a PDF page the way an iPhone saves a photo (1152x2048 pt).

Every value's position on the final page is known, so scoring needs no OCR: a value is leaked when the
masks cover less than 70% of its box, and a street name that must stay readable is over-masked when
masks cover more than 30% of it.

  python make_photo_forms.py OUT_DIR [--n 20] [--seed 1311] [--fonts DIR]

Fonts: five OFL handwriting fonts from github.com/google/fonts (Caveat, Kalam, Indie Flower,
Shadows Into Light, Patrick Hand), downloaded into --fonts on first use. All names, ID numbers and
addresses are made up; TC kimlik numbers have a valid checksum.
"""
import argparse, json, math, random, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {"Caveat.ttf": "ofl/caveat/Caveat%5Bwght%5D.ttf", "Kalam.ttf": "ofl/kalam/Kalam-Regular.ttf",
         "IndieFlower.ttf": "ofl/indieflower/IndieFlower-Regular.ttf",
         "ShadowsIntoLight.ttf": "ofl/shadowsintolight/ShadowsIntoLight.ttf",
         "PatrickHand.ttf": "ofl/patrickhand/PatrickHand-Regular.ttf"}
PRINT = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"]
PRINT_BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

FIRST = ["Mustafa", "Ayşe", "Mehmet", "Fatma", "Hüseyin", "Zeynep", "İbrahim", "Elif", "Çağrı", "Gülşen", "Şükrü", "Özlem",
         "Ömer", "Büşra", "Yiğit", "Ebru", "Tuğba", "Ilgaz", "Nurcan", "Doğan", "Sevgi", "Kadir", "Hülya", "Erdem", "Gökhan"]
LAST = ["YAVAŞ", "GÖKER", "YILMAZ", "KAYA", "DEMİR", "ŞAHİN", "ÇELİK", "YILDIZ", "ÖZTÜRK", "AYDIN", "ÖZDEMİR", "ARSLAN",
        "DOĞAN", "KILIÇ", "ÇETİN", "KARA", "KOÇ", "KURT", "ÖZKAN", "ŞİMŞEK", "POLAT", "ERDOĞAN", "GÜNEŞ", "TEKİN", "UYSAL"]
# streets named after people: they must stay readable (the lawyer's example)
PERSON_STREETS = ["Alparslan Türkeş", "Atatürk", "Fevzi Çakmak", "Mimar Sinan", "Necip Fazıl", "İsmet İnönü",
                  "Adnan Menderes", "Turgut Özal", "Kazım Karabekir", "Yunus Emre", "Mehmet Akif Ersoy", "Barış Manço"]
MAHALLE = ["Ege", "Cumhuriyet", "Yenişehir", "Kazım Dirik", "Bahçelievler", "Güzelyalı", "Hürriyet", "Esentepe", "Karşıyaka"]
DISTRICT = [("Kuşadası", "AYDIN"), ("Bornova", "İZMİR"), ("Çankaya", "ANKARA"), ("Kadıköy", "İSTANBUL"), ("Nilüfer", "BURSA"),
            ("Muratpaşa", "ANTALYA"), ("Atakum", "SAMSUN"), ("Tepebaşı", "ESKİŞEHİR"), ("Merkezefendi", "DENİZLİ")]
BUILDING = ["Trend Royal-1", "Gül Apt.", "Yıldız Sitesi", "Park Evleri", "Deniz Apt.", "Lale Konutları", "Mavi Sitesi"]


def tckn(rng):
    d = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(8)]
    d.append((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10)
    d.append(sum(d) % 10)
    return "".join(map(str, d))


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def get_fonts(d):
    d.mkdir(parents=True, exist_ok=True)
    for name, path in FONTS.items():
        if not (d / name).exists():
            urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/" + path, d / name)
    return [d / n for n in FONTS]


def person(rng):
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def address(rng):
    mah, street = rng.choice(MAHALLE), rng.choice(PERSON_STREETS)
    num = rng.randint(100, 2999)
    bld, blk, door = rng.choice(BUILDING), rng.choice("ABCD"), rng.randint(1, 40)
    ilce, il = rng.choice(DISTRICT)
    return {"line1": f"{mah} Mah. {street} Cad. {num} Sk.", "line2": f"{bld} {blk} Blok D:{door} {ilce}/{il}",
            "visible": [f"{mah} Mah.", f"{street} Cad.", f"{ilce}/{il}"], "house": f"{bld} {blk} Blok D:{door}", "town": f"{ilce}/{il}",
            "mah": mah, "street": street, "num": num}


class Hand:
    """Writes one value in a handwriting font, ballpoint blue, slightly rotated; returns its box."""
    def __init__(self, rng, fonts):
        self.rng, self.font = rng, ImageFont.truetype(str(rng.choice(fonts)), rng.randint(34, 46))
        b = rng.randint(70, 170)
        self.ink = (rng.randint(15, 45), rng.randint(25, 60), b)

    def write(self, img, xy, text):
        rng = self.rng
        tw = int(self.font.getlength(text)) + 20
        layer = Image.new("RGBA", (tw, 70), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((10, 8), text, font=self.font, fill=self.ink + (235,))
        layer = layer.rotate(rng.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=False)
        x, y = xy[0] + rng.randint(-4, 8), xy[1] + rng.randint(-6, 3)
        img.alpha_composite(layer, (x, y))
        bb = layer.getbbox() or (0, 0, tw, 70)
        return [x + bb[0], y + bb[1], x + bb[2], y + bb[3]]


def draw_form(rng, fonts):
    W, H = 1240, 1754  # A4 at 150 dpi
    img = Image.new("RGBA", (W, H), (250, 249, 246, 255))
    d = ImageDraw.Draw(img)
    f, fb, ft = font(PRINT, 19), font(PRINT_BOLD, 19), font(PRINT_BOLD, 46)
    d.rectangle([60, 50, W - 60, H - 50], outline=(20, 20, 20), width=4)
    d.text((W // 2, 120), "KİRA SÖZLEŞMESİ", font=ft, fill=(15, 15, 15), anchor="mm")
    landlord, tenant = person(rng), person(rng)
    a_land, a_ten, a_prop = address(rng), address(rng), address(rng)
    t1, t2 = tckn(rng), tckn(rng)
    rent = rng.choice([15000, 22500, 30000, 50000])
    rows = [("Dairesi", f"{rng.choice('ABCD')}-{rng.randint(1, 30)}", None),
            ("Mahallesi", f"{a_prop['mah']} Mah.", "visible"),
            ("Sokağı, Numarası", f"{a_prop['num']} Sk. {a_prop['street']} Cad.", "visible"),
            ("Kiralanan yerin cinsi", rng.choice(["Mesken", "Dükkan", "Ofis"]), None),
            ("Kiraya verenin\nAdı soyadı", landlord, "PERSON"),
            ("Kiraya verenin\nT.C. Kimlik No.", t1, "TCKN"),
            ("Kiraya verenin\nİkametgahı", a_land, "ADDRESS"),
            ("Kiracının\nAdı soyadı", tenant, "PERSON"),
            ("Kiracının\nT.C. Kimlik No.", t2, "TCKN"),
            ("Kiracının\nİkametgahı", a_ten, "ADDRESS"),
            ("Bir Aylık Kira Karşılığı", f"{rent:,} TL".replace(",", "."), None),
            ("Kira Karşılığının\nNe Şekilde Ödeneceği", rng.choice(["Eft, Havale", "Elden", "Banka"]), None),
            ("Kira Müddeti", rng.choice(["1 Yıl", "2 Yıl"]), None),
            ("Kiranın Başlangıcı", f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.2025", None),
            ("Kiralanan Yerin\nNe İçin Kullanılacağı", rng.choice(["Konaklama", "İkamet", "İşyeri"]), None)]
    hand = Hand(rng, fonts)
    gold, visible = [], []
    x0, x1, xm, y = 110, W - 110, 400, 190
    for label, value, kind in rows:
        h = 92 if kind == "ADDRESS" else 66
        d.rectangle([x0, y, x1, y + h], outline=(30, 30, 30), width=2)
        d.line([xm, y, xm, y + h], fill=(30, 30, 30), width=2)
        d.multiline_text((x0 + 12, y + 10 if "\n" in label else y + 22), label, font=f, fill=(20, 20, 20), spacing=2)
        if label.endswith("No."):
            d.rectangle([x1 - 230, y, x1, y + h], outline=(30, 30, 30), width=2)
            d.text((x1 - 215, y + 22), "Vergi Nosu", font=f, fill=(20, 20, 20))
        if kind == "ADDRESS":
            b1 = hand.write(img, (xm + 14, y + 2), value["line1"])
            b2 = hand.write(img, (xm + 14, y + 44), value["house"])
            b3 = hand.write(img, (b2[2] + 24, y + 44), value["town"])
            visible += [{"text": value["line1"], "box": b1, "why": "mahalle and street of a person's address"},
                        {"text": value["town"], "box": b3, "why": "district and province"}]
            gold.append({"entity_type": "ADDRESS", "text": value["house"], "box": b2, "part": "building, block, door"})
        else:
            b = hand.write(img, (xm + 14, y + 10), value)
            if kind in ("PERSON", "TCKN"):
                gold.append({"entity_type": kind, "text": value, "box": b})
            elif kind == "visible":
                visible.append({"text": value, "box": b, "why": "address of the leased property, named after a person"})
        y += h
    # signature block: printed role, handwritten name, scribble
    y += 70
    for i, (role, name) in enumerate((("Kiracı", tenant), ("Kiraya Veren", landlord))):
        cx = 330 + i * 560
        d.text((cx, y), role, font=fb, fill=(15, 15, 15), anchor="mm")
        b = hand.write(img, (cx - 120, y + 20), name)
        gold.append({"entity_type": "PERSON", "text": name, "box": b, "part": "signature block"})
        sig = ImageDraw.Draw(img)
        pts = [(cx - 90 + k * 12, y + 110 + int(25 * math.sin(k * rng.uniform(0.8, 1.6)))) for k in range(16)]
        sig.line(pts, fill=hand.ink + (255,), width=3)
    d.text((110, H - 120), "Gelir vergisi kanununa göre stopaj kiracı tarafından yatırılır.", font=font(PRINT, 16), fill=(30, 30, 30))
    return img, gold, visible


def wood(W, H, rng):
    x = np.linspace(0, 1, W)[None, :]
    yy = np.linspace(0, 1, H)[:, None]
    base = np.array([196, 186, 168]) + rng.randint(-15, 15)
    grain = 10 * np.sin(2 * np.pi * (x * rng.uniform(25, 40) + 3 * np.sin(yy * 9)))
    planks = ((x * rng.uniform(3, 5)) % 1 < 0.015) * -70
    noise = np.random.default_rng(rng.randint(0, 2 ** 31)).normal(0, 6, (H, W))
    v = (grain + planks + noise)[..., None]
    return Image.fromarray(np.clip(base[None, None, :] + v, 0, 255).astype("uint8"), "RGB")


def find_coeffs(src, dst):
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(m, float), np.array(src, float).reshape(8)).tolist()


def photograph(form, rng):
    """Phone photo of the sheet on a wooden floor; returns the image and a point mapper form->photo."""
    W, H = 1152, 2048
    fw, fh = form.size
    # back side shows through: mirrored faint copy of the same layout
    back = form.convert("L").transpose(Image.FLIP_LEFT_RIGHT).point(lambda v: 255 - (255 - v) * 0.12)
    sheet = Image.fromarray(np.minimum(np.asarray(form.convert("RGB")), np.asarray(Image.merge("RGB", [back] * 3))))
    s = rng.uniform(0.80, 0.88) * W / fw
    cx, cy = W / 2 + rng.uniform(-30, 30), H / 2 + rng.uniform(-60, 60)
    jit = lambda: (rng.uniform(-35, 35), rng.uniform(-35, 35))
    corners = [(cx - fw * s / 2, cy - fh * s / 2), (cx + fw * s / 2, cy - fh * s / 2), (cx + fw * s / 2, cy + fh * s / 2), (cx - fw * s / 2, cy + fh * s / 2)]
    dst = [(x + jit()[0], y + jit()[1]) for x, y in corners]
    src = [(0, 0), (fw, 0), (fw, fh), (0, fh)]
    coeffs = find_coeffs(src, dst)
    warped = sheet.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(0, 0, 0))
    mask = Image.new("L", form.size, 255).transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=0)
    photo = wood(W, H, rng)
    photo.paste(warped, (0, 0), mask)
    # uneven light and a soft shadow
    g = np.linspace(rng.uniform(0.78, 0.9), rng.uniform(1.0, 1.05), W)[None, :, None] * np.linspace(1.02, rng.uniform(0.85, 0.95), H)[:, None, None]
    photo = Image.fromarray(np.clip(np.asarray(photo) * g, 0, 255).astype("uint8"))
    photo = photo.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 1.1)))
    # forward map for gold boxes: solve the inverse homography
    Hm = np.array(find_coeffs(dst, src) + [1.0]).reshape(3, 3)

    def fwd(x, y):
        p = Hm @ np.array([x, y, 1.0])
        return p[0] / p[2], p[1] / p[2]

    def box(b):
        pts = [fwd(b[0], b[1]), fwd(b[2], b[1]), fwd(b[2], b[3]), fwd(b[0], b[3])]
        return [round(min(p[0] for p in pts), 1), round(min(p[1] for p in pts), 1), round(max(p[0] for p in pts), 1), round(max(p[1] for p in pts), 1)]
    return photo, box


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=1311)
    ap.add_argument("--fonts", default=str(Path(__file__).parent / "fonts"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fonts = get_fonts(Path(a.fonts))
    manifest = []
    for i in range(a.n):
        rng = random.Random(a.seed * 1000 + i)
        form, gold, visible = draw_form(rng, fonts)
        photo, box = photograph(form, rng)
        name = f"kira_foto_{i + 1:02d}"
        q = rng.randint(55, 80)
        photo.save(out / f"{name}.jpg", quality=q)
        Image.open(out / f"{name}.jpg").save(out / f"{name}.pdf", resolution=72.0)  # 1152x2048 pt page
        for g in gold + visible:
            g["box"] = box(g["box"])
        (out / f"{name}.gold.json").write_text(json.dumps({"entities": gold, "visible": visible, "jpeg_quality": q}, ensure_ascii=False, indent=1))
        manifest.append(name)
    (out / "manifest.json").write_text(json.dumps({"seed": a.seed, "docs": manifest, "generator": "lab/photo_forms/make_photo_forms.py"}, indent=1))
    print(f"{len(manifest)} photographed forms in {out}")


if __name__ == "__main__":
    main()
