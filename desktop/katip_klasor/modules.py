"""The tools the app holds. v0.1 ships one, masking; the others are planned Katip tools that would work on the
same case folders, case keys and audit log, downloaded on request and run on this computer.

A module is: an id, a name, what it does, and (once built) a Python entry point the window can call. Keeping
the list here, not spread through the UI, is what lets a later version add a tool without reworking the app."""
from __future__ import annotations

MODULES = [
    {"id": "maske", "name": "Maskeleme", "status": "installed",
     "about": "Gelen klasöründeki belgeleri maskeler, kontrol edilecek yerleri gösterir, yapay zekâ cevabına adları geri koyar."},
    {"id": "emsal", "name": "Katip Emsal", "status": "planned",
     "about": "Yargıtay emsal kararlarını bu bilgisayarda arar ve dava dosyasına göre önerir."},
    {"id": "cite", "name": "Katip Cite", "status": "planned",
     "about": "Dilekçedeki kanun ve madde atıflarını çevrimdışı kontrol eder."},
    {"id": "taslak", "name": "Katip Taslak", "status": "planned",
     "about": "Maskeli belgelerden yerel bir modelle dilekçe taslağı hazırlar."},
]


def catalogue() -> list[dict]:
    return [dict(m) for m in MODULES]
