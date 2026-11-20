"""Random fill values for the document-type generator (gen.py). Everything is synthetic.

Kept separate from the templates so the same fill can serve another language pack later.
None of these values are spans or labels: the classifier learns the document's *type*,
so names, numbers and places are noise it must learn to ignore.
"""
from __future__ import annotations

import random

FIRST = ("Mehmet Mustafa Ahmet Ali Hüseyin Hasan İbrahim İsmail Osman Yusuf Murat Ömer Ramazan Halil Süleyman Abdullah "
         "Mahmut Recep Salih Fatih Kemal Hakan Emre Burak Serkan Fatma Ayşe Emine Hatice Zeynep Elif Meryem Şerife Zehra "
         "Sultan Merve Havva Esra Özlem Hacer Melek Yasemin Hülya Leyla Derya Sevim Ebru Can Deniz Ece Mert Selin Kaan "
         "Arda Bora Cem Derin Efe Gizem Tuğba Volkan Sinan Tolga Gökhan Nuray Sibel Aslı Pınar Oya Nermin Cengiz Levent").split()
LAST = ("Yılmaz Kaya Demir Şahin Çelik Yıldız Yıldırım Öztürk Aydın Özdemir Arslan Doğan Kılıç Aslan Çetin Kara Koç Kurt "
        "Özkan Şimşek Polat Özcan Korkmaz Çakır Erdoğan Yavuz Can Acar Şen Aktaş Güler Yalçın Güneş Bozkurt Bulut Keskin "
        "Ünal Turan Gül Özer Işık Kaplan Avcı Sarı Tekin Taş Köse Yüksel Ateş Aksoy Karaca Uçar Erdem Sezer Tuna Ilgaz "
        "Karakaya Bayram Tunç Altun Soylu Duman Akın Coşkun Ekinci Uysal Önal Bilgin Kocabaş Tatlı Durmaz").split()
CITIES = ("İstanbul Ankara İzmir Bursa Antalya Adana Konya Gaziantep Kocaeli Mersin Kayseri Eskişehir Samsun Trabzon "
          "Denizli Sakarya Manisa Diyarbakır Muğla Tekirdağ Aydın Malatya Erzurum Hatay Balıkesir").split()
DISTRICTS = ("Kadıköy Çankaya Konak Nilüfer Muratpaşa Seyhan Selçuklu Şahinbey İzmit Yenişehir Melikgazi Tepebaşı Atakum "
             "Ortahisar Pamukkale Adapazarı Yunusemre Bağlar Bodrum Süleymanpaşa Efeler Battalgazi Yakutiye Antakya "
             "Karesi Beşiktaş Şişli Bornova Keçiören Üsküdar").split()
STREETS = ("Atatürk Cumhuriyet İstiklal Gazi Mimar Sinan Fevzi Çakmak Kazım Karabekir İnönü Barış Lale Çınar Menekşe "
           "Papatya Akasya Bağdat Halaskargazi Necatibey Ziya Gökalp Talatpaşa").split()
COMPANY_W = ("Anadolu Marmara Ege Akdeniz Karadeniz Doğu Yıldız Güneş Kuzey Birlik Atlas Zirve Ufuk Delta Mavi Yeşil "
             "Başak Pınar Kartal Toros Ilgaz Sarp Doruk").split()
SECTOR = ("Gıda İnşaat Lojistik Tekstil Enerji Yazılım Otomotiv Turizm Sağlık Kimya Plastik Mobilya Tarım Madencilik "
          "Danışmanlık Elektronik Ambalaj Medikal").split()
FORM = ["A.Ş.", "Ltd. Şti.", "Sanayi ve Ticaret A.Ş.", "Sanayi ve Ticaret Ltd. Şti.", "Tic. A.Ş."]
BANKS = ["Ziraat", "Halk", "Vakıf", "İş", "Garanti", "Yapı Kredi", "Akbank", "QNB", "Deniz", "TEB"]
COURT_KIND = ["Asliye Hukuk", "Asliye Ticaret", "Sulh Hukuk", "İş", "Aile", "Tüketici", "İcra Hukuk", "Asliye Ceza",
              "Ağır Ceza", "Sulh Ceza", "Kadastro", "Fikri ve Sınai Haklar Hukuk"]
DAVA = ["Alacak", "Tazminat", "İtirazın İptali", "Tahliye", "İşçilik Alacağı", "Boşanma", "Tapu İptali ve Tescil",
        "Menfi Tespit", "Kira Bedelinin Tespiti", "İşe İade", "Ortaklığın Giderilmesi", "Maddi ve Manevi Tazminat",
        "Ecrimisil", "Kıdem ve İhbar Tazminatı", "Rücuen Tazminat", "Haksız Rekabetin Tespiti"]
GOODS = ["Danışmanlık hizmeti", "Yazılım lisansı", "Nakliye bedeli", "Kira bedeli", "Bakım onarım hizmeti", "Ofis malzemesi",
         "Çelik profil", "Ambalaj kolisi", "Avukatlık ücreti", "Temizlik hizmeti", "Elektrik malzemesi", "Kumaş"]


def upper_tr(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


class Fill:
    def __init__(self, rng: random.Random):
        self.r = rng

    def pick(self, s, *more):
        """'a|b|c', a list, or several arguments -> one item."""
        if more:
            return self.r.choice([s, *more])
        return self.r.choice(s.split("|") if isinstance(s, str) else s)

    def name(self):
        f, l = self.r.choice(FIRST), self.r.choice(LAST)
        if self.r.random() < .12:
            f += " " + self.r.choice(FIRST)
        k = self.r.random()
        return f"{f} {l}" if k < .45 else f"{f} {upper_tr(l)}" if k < .8 else upper_tr(f"{f} {l}")

    def lawyer(self):
        return f"Av. {self.name()}"

    def company(self):
        return f"{self.pick(COMPANY_W)} {self.pick(SECTOR)} {self.pick(FORM)}"

    def city(self):
        return self.pick(CITIES)

    def address(self):
        r = self.r
        return (f"{self.pick(STREETS)} {self.pick('Mah.|Mahallesi|Mh.')} {self.pick(STREETS)} {self.pick('Cad.|Caddesi|Sok.|Sokak')} "
                f"No: {r.randint(1, 200)}{self.pick(['/', ' D:', ' Daire: '])}{r.randint(1, 40)} {self.pick(DISTRICTS)}/{upper_tr(self.city())}")

    def tckn(self):
        return str(self.r.randint(1, 9)) + "".join(str(self.r.randint(0, 9)) for _ in range(10))

    def vkn(self):
        return "".join(str(self.r.randint(0, 9)) for _ in range(10))

    def phone(self):
        return self.pick(["0532", "0542", "0555", "0505", "0216", "0312", "0232"]) + f" {self.r.randint(100, 999)} {self.r.randint(10, 99)} {self.r.randint(10, 99)}"

    def email(self):
        return f"{self.pick(FIRST).lower()}.{self.pick(LAST).lower()}@{self.pick('gmail.com|hotmail.com|outlook.com|yandex.com.tr|firma.com.tr')}".translate(
            str.maketrans("çğıöşüİ", "cgiosui"))

    def iban(self):
        d = "".join(str(self.r.randint(0, 9)) for _ in range(24))
        return "TR" + d[:2] + " " + " ".join(d[i:i + 4] for i in range(2, 22, 4)) + " " + d[22:]

    def date(self, y0=2015, y1=2026):
        return f"{self.r.randint(1, 28):02d}.{self.r.randint(1, 12):02d}.{self.r.randint(y0, y1)}"

    def year(self):
        return self.r.randint(2015, 2026)

    def esas(self):
        return f"{self.year()}/{self.r.randint(1, 2500)}"

    def money(self):
        v = self.r.choice([self.r.randint(1, 99) * 1000, self.r.randint(1000, 2_000_000)])
        s = f"{v:,}".replace(",", ".")
        return f"{s},{self.r.randint(0, 99):02d} TL" if self.r.random() < .6 else f"{s} TL"

    def court(self, kind=None):
        n = self.r.choice(["", f"{self.r.randint(1, 30)}. "])
        return f"{upper_tr(self.city())} {n}{upper_tr(kind or self.pick(COURT_KIND))} MAHKEMESİ"

    def icra_office(self):
        return f"{upper_tr(self.city())} {self.r.randint(1, 40)}. İCRA DAİRESİ"

    def plate(self):
        return f"{self.r.randint(1, 81):02d} {''.join(self.r.choice('ABCDEFGHJKLMNPRSTUVYZ') for _ in range(self.r.randint(1, 3)))} {self.r.randint(10, 9999)}"

    def dava(self):
        return self.pick(DAVA)

    def bank(self):
        return self.pick(BANKS)

    def goods(self):
        return self.pick(GOODS)
