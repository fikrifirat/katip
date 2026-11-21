"""MCP tool definitions for Katip DD, shared by the local Kalkan server and the relay."""
from __future__ import annotations

from ..mcp_proto import Tool
from . import service

RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

SCREEN_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Person or company name as the user wrote it; Turkish letters, "
                                                  "casing and legal form (A.Ş., Ltd. Şti.) do not matter."},
        "birth_year": {"type": "string", "description": "Optional. A different year on the list lowers the score."},
        "id_number": {"type": "string", "description": "Optional TCKN/VKN/YKN/passport number. Only an exact match "
                                                       "counts; the number is never echoed back."},
        "sources": {"type": "array", "items": {"type": "string", "enum": list(service.SOURCES)}},
        "lists": {"type": "array", "items": {"type": "string", "enum": service.LISTS},
                  "description": "MASAK lists: 6415 art. 5 (UN), art. 6 (foreign request), art. 7 (domestic), 7262 (WMD)"},
        "date_from": {"type": "string", "description": "YYYY-MM-DD, decision or notice date"},
        "date_to": {"type": "string", "description": "YYYY-MM-DD"},
        "min_band": {"type": "string", "enum": ["match", "review", "weak"], "default": "review"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
    },
    "additionalProperties": False,
}

SCREEN_DESC = ("Kişi ya da şirketi kamu listelerinde tarar (MASAK malvarlığı dondurma 6415 m.5/6/7 ve 7262, ilan.gov.tr, "
               "Ticaret Sicili Gazetesi) · Screen a person or company against Turkish public lists. Deterministic: "
               "returns stored source records with official links, match score and band, and the date of each "
               "source's data. Quote hits as returned with source_url; a 'review' hit needs checking; no hit is not "
               "a clearance. Third parties' ID numbers and parents' names are removed before results reach you.")


def screen_tool(redact: bool = True) -> Tool:
    return Tool("dd_screen", "DD taraması · Screen a name", SCREEN_DESC, SCREEN_SCHEMA,
                lambda **kw: service.screen(**kw, verbatim=True, redact=redact), RO)


def sources_tool() -> Tool:
    return Tool("dd_sources", "DD kaynakları · DD source freshness",
                "What each DD source holds, the date of its data and its last failure · Her kaynağın kaydı, tarihi, "
                "son hatası.", {"type": "object", "properties": {}, "additionalProperties": False},
                lambda: service.sources_status(), RO)


def local_tools() -> list[Tool]:
    return [
        screen_tool(),
        Tool("dd_record", "DD kaydı · One DD record",
             "Return one stored record by record_id from dd_screen, with third parties' ID numbers removed.",
             {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"],
              "additionalProperties": False},
             lambda record_id: service.record(record_id, redact=True), RO),
        sources_tool(),
        Tool("dd_update", "MASAK listelerini güncelle · Refresh MASAK lists",
             "Fetch the four MASAK asset-freeze lists from masak.hmb.gov.tr into the local index (about 10 requests, "
             "2 s apart). Call it when dd_sources shows MASAK data older than a week or missing.",
             {"type": "object", "properties": {}, "additionalProperties": False},
             lambda: service.update("masak"),
             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}),
        Tool("dd_ilan_lookup", "ilan.gov.tr'de ara · Look up one name on ilan.gov.tr",
             "Search ilan.gov.tr for ONE named DD target in a real browser on this computer (the site's own search "
             "box, a few seconds per page, at most 20 notices, tebligat notices skipped). Takes 1-3 minutes. Then "
             "call dd_screen with the same name. Needs Playwright on this computer.",
             {"type": "object", "properties": {
                 "target": {"type": "string", "description": "The person or company name to look up"},
                 "max_ads": {"type": "integer", "minimum": 1, "maximum": 20, "default": 20}},
              "required": ["target"], "additionalProperties": False},
             lambda target, max_ads=20: service.ilan_lookup(target, max_ads),
             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}),
        Tool("dd_gazette_lookup", "Ticaret Sicili Gazetesi'nde ara · Look up one name in the Trade Registry Gazette",
             "Search the Türkiye Ticaret Sicili Gazetesi for ONE named DD target. Opens Chrome on this computer; the "
             "lawyer logs in with e-Devlet themselves (Katip never types credentials). Katip searches the site's own "
             "form (registry office + at least the first 5 letters of the name), saves up to 3 free gazette pages, "
             "logs out and deletes the browser profile, then reads the pages with OCR. Takes a few minutes. Then call "
             "dd_screen. Needs Playwright and OCR on this computer.",
             {"type": "object", "properties": {
                 "target": {"type": "string", "description": "Company name (at least 5 letters) as registered"},
                 "office": {"type": "string", "description": "Ticaret sicili müdürlüğü, e.g. BURSA, İSTANBUL, ANKARA"},
                 "max_pages": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                 "court": {"type": "boolean", "default": False,
                           "description": "Search court and bankruptcy-office notices (konkordato, iflas) instead"}},
              "required": ["target", "office"], "additionalProperties": False},
             lambda target, office, max_pages=3, court=False: service.gazette_lookup(target, office, max_pages, court),
             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}),
    ]


def relay_tools() -> list[Tool]:
    """Read-only, redacted. The relay operator refreshes the index with the CLI; callers cannot fetch."""
    return [screen_tool(redact=True), sources_tool()]
