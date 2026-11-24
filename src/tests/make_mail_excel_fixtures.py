"""Writes the synthetic e-mail and Excel test files in src/tests/fixtures/mail_excel/ and their answer key.

Every person, number and address here is made up (TC kimlik and IBAN numbers only pass their checksums).
Needs openpyxl (for the .xlsx); the .msg is written with a small compound-file writer below (stdlib only).

  python src/tests/make_mail_excel_fixtures.py
"""
import json
import struct
import sys
from email.message import EmailMessage
from pathlib import Path

OUT = Path(__file__).parent / "fixtures" / "mail_excel"
sys.path.insert(0, str(Path(__file__).parents[1]))
from mail_samples import cfb  # noqa: E402


def tckn(nine):
    d = [int(c) for c in nine]
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    d11 = (sum(d) + d10) % 10
    return nine + str(d10) + str(d11)


def iban(bank, acct):
    bban = bank + "0" + acct  # 5 bank + 1 reserve + 16 account
    n = int("".join(str(int(c, 36)) for c in bban + "TR00"))
    return f"TR{98 - n % 97:02d}{bban}"


PEOPLE = [  # name, tckn, phone, e-mail, address
    ("Ayşe Kaya Demirtaş", tckn("318452907"), "0532 418 27 63", "ayse.demirtas@ornekposta.com.tr",
     "Bağdat Caddesi No: 214 Daire: 7 Kadıköy/İstanbul"),
    ("Mehmet Ali Karakoç", tckn("427109385"), "0544 730 15 92", "makarakoc@ornekposta.net",
     "Atatürk Bulvarı No: 88/12 Çankaya/Ankara"),
    ("Zeynep Özgür", tckn("536218470"), "0505 962 40 18", "zeynep.ozgur@ornekfirma.com.tr",
     "Kıbrıs Şehitleri Caddesi No: 41 Daire: 3 Alsancak/İzmir"),
    ("Hüseyin Çelikkaya", tckn("645327019"), "0533 281 77 06", "h.celikkaya@ornekposta.com",
     "Mimar Sinan Mahallesi 1203. Sokak No: 9 Nilüfer/Bursa"),
    ("Elif Şahinoğlu", tckn("754436128"), "0542 105 63 39", "elif.sahinoglu@ornekfirma.com.tr",
     "Cumhuriyet Caddesi No: 17 Kat: 4 Muratpaşa/Antalya"),
]
IBANS = [iban("00062", "0000123456789012"), iban("00010", "0000987654321098")]


def gold(*items):
    return [x for x in items if x]


# ---------------------------------------------------------------- .eml
def eml_reply():
    a, b, c = PEOPLE[0], PEOPLE[1], PEOPLE[2]
    m = EmailMessage()
    m["From"] = f"{a[0]} <{a[3]}>"
    m["To"] = f"Av. {b[0]} <{b[3]}>"
    m["Cc"] = f"{c[0]} <{c[3]}>"
    m["Subject"] = f"Kira alacağı - {a[0]} / ödeme planı"
    m["Date"] = "Mon, 23 Nov 2026 09:41:00 +0300"
    m["Message-ID"] = "<20261123094100.4821@ornekposta.com.tr>"
    m["Received"] = "from mail.ornekposta.com.tr (88.247.112.34) by mx.ornekfirma.com.tr"
    body = (f"Sayın Av. {b[0]},\n\n"
            f"Müvekkiliniz adına yazdığınız ihtarnameyi aldım. Kira borcunu {IBANS[0]} numaralı hesaba "
            f"üç taksitte ödemek istiyorum. T.C. kimlik numaram {a[1]}, adresim {a[4]}.\n"
            f"Bana {a[2]} numaralı telefondan ulaşabilirsiniz.\n\nSaygılarımla,\n{a[0]}\n\n"
            f"-----Original Message-----\nFrom: {b[0]} <{b[3]}>\nSent: 20 Kasım 2026 16:02\n"
            f"Subject: İhtarname\n\nSayın {a[0]}, müvekkilim {c[0]} adına ekteki ihtarnameyi iletiyorum.\n")
    m.set_content(body)
    m.add_alternative("<html><body><p>" + body.replace("\n", "<br>") + "</p></body></html>", subtype="html")
    m.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename=f"ihtarname-{a[0]}.pdf")
    return m.as_bytes(), gold(a[0], a[3], b[0], b[3], c[0], c[3], a[1], a[2], IBANS[0], a[4])


def eml_html_only():
    d, e = PEOPLE[3], PEOPLE[4]
    m = EmailMessage()
    m["From"] = f'"{d[0]}" <{d[3]}>'
    m["To"] = e[3]
    m["Subject"] = "=?utf-8?b?" + __import__("base64").b64encode("İşe iade davası – tanık listesi".encode()).decode() + "?="
    m["Date"] = "Tue, 24 Nov 2026 11:05:00 +0300"
    html = (f"<html><head><style>p{{color:#333}}</style></head><body><p>Elif Hanım merhaba,</p>"
            f"<p>Tanık olarak <b>{e[0]}</b> (TCKN {e[1]}, tel. {e[2]}) ve ben, {d[0]} "
            f"(TCKN {d[1]}) dinlenmek istiyoruz.</p><table><tr><td>Adres</td><td>{d[4]}</td></tr></table>"
            f"<p>Maaş ödemeleri {IBANS[1]} hesabına yapılıyordu.</p></body></html>")
    m.set_content(html, subtype="html")
    return m.as_bytes(), gold(d[0], d[3], e[3], e[0], e[1], e[2], d[1], d[4], IBANS[1])


def msg_file():
    a, b, c = PEOPLE[1], PEOPLE[3], PEOPLE[4]
    u = lambda s: s.encode("utf-16-le")
    st = {
        "__substg1.0_0037001F": u(f"Tapu iptal davası - {a[0]} vekâlet"),
        "__substg1.0_0C1A001F": u(a[0]),
        "__substg1.0_5D01001F": u(a[3]),
        "__substg1.0_0E04001F": u(b[0]),
        "__substg1.0_0E03001F": u(c[0]),
        "__substg1.0_1000001F": u(
            f"Sayın {b[0]},\r\n\r\nVekâletnameyi imzalayıp gönderiyorum. T.C. kimlik no: {a[1]}. "
            f"Tebligat adresim: {a[4]}. Cep telefonum {a[2]}.\r\nTaşınmazın eski maliki {c[0]} "
            f"(TCKN {c[1]}) ile görüşmedim.\r\n\r\nİyi çalışmalar,\r\n{a[0]}"),
        "__properties_version1.0": b"\0" * 32,
    }
    for k, (who, rtype) in enumerate(((b, 1), (c, 2))):
        base = f"__recip_version1.0_#{k:08X}/"
        st[base + "__substg1.0_3001001F"] = u(who[0])
        st[base + "__substg1.0_39FE001F"] = u(who[3])
        st[base + "__properties_version1.0"] = b"\0" * 8 + struct.pack("<IIII", 0x0C150003, 6, rtype, 0)
    st["__attach_version1.0_#00000000/__substg1.0_3707001F"] = u(f"vekaletname-{a[0]}.pdf")
    st["__attach_version1.0_#00000000/__substg1.0_37010102"] = b"%PDF-1.4 fake" * 400  # a regular-sector stream
    st["__attach_version1.0_#00000000/__properties_version1.0"] = b"\0" * 8
    return cfb(st), gold(a[0], a[3], b[0], b[3], c[0], c[3], a[1], a[4], a[2], c[1])


# ---------------------------------------------------------------- .xlsx
def xlsx_file(path):
    import openpyxl
    from openpyxl.comments import Comment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Personel"
    ws.append(["Ad Soyad", "T.C. Kimlik No", "Telefon", "E-posta", "Adres", "IBAN", "Brüt maaş"])
    for i, p in enumerate(PEOPLE):
        ws.append([p[0], int(p[1]), p[2], p[3], p[4], IBANS[i % 2], 41000 + 2500 * i])
    ws["H1"] = "Toplam"
    ws["H2"] = "=SUM(G2:G6)"
    ws["I1"] = "Not"
    ws["I2"] = f"Sorumlu: {PEOPLE[2][0]} (İK)"
    ws["I3"] = f"='{PEOPLE[2][0]} izin'!A2"  # a formula that names the sheet called after a person
    ws["B3"].comment = Comment(f"{PEOPLE[1][0]} kimliğini 12.10.2026'da yeniledi; eski no {tckn('427109300')}", "İK Uzmanı Derya Aksoy")
    s2 = wb.create_sheet(f"{PEOPLE[2][0]} izin")
    s2.append(["Tarih", "Açıklama"])
    s2.append(["03.11.2026", f"{PEOPLE[2][0]} yıllık izin, vekil {PEOPLE[4][0]}"])
    s2.append(["10.11.2026", f"Rapor: {PEOPLE[2][0]}, {PEOPLE[2][2]}"])
    wb.properties.creator = "Derya Aksoy"
    wb.properties.lastModifiedBy = "Derya Aksoy"
    wb.save(path)
    g = [x for p in PEOPLE for x in (p[0], p[1], p[2], p[3], p[4])] + IBANS + [tckn("427109300"), "Derya Aksoy"]
    return g


def eml_outlook_forward():
    """Outlook-style: quoted-printable HTML with an inline logo, and the earlier mail forwarded as an attachment."""
    from email.mime.image import MIMEImage
    from email.mime.message import MIMEMessage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    a, b, e = PEOPLE[4], PEOPLE[0], PEOPLE[3]
    inner = EmailMessage()
    inner["From"] = f"{e[0]} <{e[3]}>"
    inner["To"] = a[3]
    inner["Subject"] = "Bilirkişi raporuna itiraz"
    inner.set_content(f"Elif Hanım, raporu {e[2]} numaralı telefondan konuşalım. TCKN {e[1]}.")
    rel = MIMEMultipart("related")
    html = (f'<html><body><div class="WordSection1"><p class="MsoNormal">Sayın {b[0]},<o:p></o:p></p>'
            f'<p class="MsoNormal">{e[0]} Bey&#39;in iletisini ekte gönderiyorum. Kendisinin adresi: {e[4]}.</p>'
            f'<p class="MsoNormal">Saygılarımla,<br>Av. {a[0]}<br>{a[2]}</p><img src="cid:logo001"></div></body></html>')
    rel.attach(MIMEText(html, "html", "utf-8"))
    rel["Content-Type"] = rel["Content-Type"]
    img = MIMEImage(b"\x89PNG\r\n\x1a\n" + b"\0" * 64, "png")
    img.add_header("Content-ID", "<logo001>")
    img.add_header("Content-Disposition", "inline", filename="image001.png")
    rel.attach(img)
    top = MIMEMultipart("mixed")
    top["From"] = f"Av. {a[0]} <{a[3]}>"
    top["To"] = f"{b[0]} <{b[3]}>"
    top["Subject"] = f"FW: Bilirkişi raporuna itiraz - {e[0]}"
    top["Date"] = "Wed, 18 Nov 2026 17:20:00 +0300"
    top["Reply-To"] = a[3]
    top.attach(rel)
    fwd = MIMEMessage(inner)
    fwd.add_header("Content-Disposition", "attachment", filename="Bilirkişi raporuna itiraz.eml")
    top.attach(fwd)
    for part in top.walk():  # Outlook sends HTML as quoted-printable
        if part.get_content_type() == "text/html":
            from email import encoders
            payload = part.get_payload(decode=True)
            del part["Content-Transfer-Encoding"]
            part.set_payload(payload)
            encoders.encode_quopri(part)
    # the forwarded mail is an attachment: not carried over, so only the outer mail's values are in the key
    return top.as_bytes(), gold(a[0], a[3], b[0], b[3], e[0], e[4], a[2])


# text that must still be readable in the masked copy: the content around the personal data is not lost
KEEP = {
    "yanit-zinciri.eml": ["Kira alacağı", "ödeme planı", "üç taksitte ödemek istiyorum", "ihtarnameyi iletiyorum"],
    "yalniz-html.eml": ["İşe iade davası", "dinlenmek istiyoruz", "hesabına yapılıyordu"],
    "vekalet.msg": ["Tapu iptal davası", "Vekâletnameyi imzalayıp gönderiyorum", "ile görüşmedim"],
    "outlook-iletme.eml": ["Bilirkişi raporuna itiraz", "iletisini ekte gönderiyorum", "Saygılarımla"],
    "personel.xlsx": ["Brüt maaş", "41000", "yıllık izin", "Sorumlu:"],
    "personel-libreoffice.xlsx": ["Brüt maaş", "41000", "yıllık izin", "Sorumlu:"],
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = {}
    for name, fn in (("yanit-zinciri.eml", eml_reply), ("yalniz-html.eml", eml_html_only), ("vekalet.msg", msg_file),
                     ("outlook-iletme.eml", eml_outlook_forward)):
        data, g = fn()
        (OUT / name).write_bytes(data)
        key[name] = g
    key["personel.xlsx"] = xlsx_file(OUT / "personel.xlsx")
    # the same workbook as LibreOffice saves it (shared strings, cached formula results), when LibreOffice is here
    import shutil, subprocess, tempfile
    if shutil.which("soffice"):
        with tempfile.TemporaryDirectory() as t:
            subprocess.run(["soffice", "--headless", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", t,
                            str(OUT / "personel.xlsx")], check=True, capture_output=True, timeout=120)
            shutil.copyfile(Path(t) / "personel.xlsx", OUT / "personel-libreoffice.xlsx")
        key["personel-libreoffice.xlsx"] = [g for g in key["personel.xlsx"] if g != "Derya Aksoy"] + ["Derya Aksoy"]
    key = {n: {"mask": g, "keep": KEEP[n]} for n, g in key.items()}
    (OUT / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", ", ".join(sorted(key)))


if __name__ == "__main__":
    main()
