"""
Türkçe karakter normalizasyonu — regex recognizer'lar için yardımcı.

Kullanıcılar sıklıkla Türkçe karakter olmadan yazar:
  "Ahmet Yilmaz" → "Ahmet Yılmaz"
  "Istanbulda"   → "İstanbul'da"

Recognizer'lar normalize edilmiş metin üzerinde çalışır,
ancak bulunan span'ler orijinal metne geri map'lenir.
"""

_TR_MAP = str.maketrans(
    "iIcCgGsSOoUu",
    "ıİçÇğĞşŞÖöÜü",
)

# Türkçe karakter olmayan versiyondan Türkçe versiyona
_ASCII_TO_TR = {
    "i": "ı",  # küçük i → ı (ama İ değil — dikkatli)
    "I": "İ",
    "c": "ç",
    "C": "Ç",
    "g": "ğ",
    "G": "Ğ",
    "s": "ş",
    "S": "Ş",
    "o": "ö",  # bu agresif — sadece belirli bağlamlarda kullan
    "u": "ü",
}


def normalize_turkish(text: str) -> str:
    """
    ASCII Türkçe → gerçek Türkçe karakter dönüşümü.
    Dikkat: Bu dönüşüm kayıplıdır — sadece span tespiti için kullan,
    orijinal metni değiştirme.
    """
    # Yaygın kısmi dönüşüm — tüm harfleri değil, yaygın hataları düzelt
    replacements = [
        ("Ii", "İ"),   # "Istanbul" → "İstanbul"
        ("ii", "ı"),   # "kişii" değil ama "kimlik" gibi
    ]
    result = text
    # Basit: sadece kelime başı I → İ
    import re
    result = re.sub(r'\bI([a-zçğışöşü])', lambda m: 'İ' + m.group(1), result)
    return result
