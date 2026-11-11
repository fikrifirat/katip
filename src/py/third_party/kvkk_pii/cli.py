"""
kvkk-pii CLI

Kullanim:
    kvkk-pii scan "Ali Veli TC: 10000000146"
    kvkk-pii scan dosya.txt
    echo "metin" | kvkk-pii scan
    kvkk-pii scan --layer ner --format json "metin"
    kvkk-pii anonymize "Ali Veli TC: 10000000146"
    kvkk-pii version
"""
import argparse
import json
import sys


def cmd_scan(args) -> None:
    from .detector import PiiDetector
    from .layers.regex_layer import DEFAULT_RECOGNIZERS

    # Metin kaynagi: arguman, dosya veya stdin
    if args.text and args.text != "-":
        import os
        if os.path.isfile(args.text):
            with open(args.text, encoding="utf-8") as f:
                text = f.read()
        else:
            text = args.text
    else:
        text = sys.stdin.read()

    # Katmanlari belirle
    layers = ["regex"]
    if args.layer in ("ner", "full"):
        layers.append("ner")
    if args.layer == "full":
        layers.append("gliner")

    detector = PiiDetector(layers=layers, download_policy="auto")
    result = detector.analyze(text)

    if args.format == "json":
        output = [
            {
                "type": e.entity_type,
                "text": e.text,
                "start": e.start,
                "end": e.end,
                "score": round(e.score, 3),
                "layer": e.layer,
            }
            for e in result.entities
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if not result.entities:
            print("PII bulunamadi.")
            return
        for e in result.entities:
            print(f"  [{e.entity_type}] {e.text!r}  (score={e.score:.2f}, layer={e.layer})")


def cmd_anonymize(args) -> None:
    from .detector import PiiDetector
    import os

    if args.text and args.text != "-":
        if os.path.isfile(args.text):
            with open(args.text, encoding="utf-8") as f:
                text = f.read()
        else:
            text = args.text
    else:
        text = sys.stdin.read()

    layers = ["regex"]
    if args.layer in ("ner", "full"):
        layers.append("ner")
    if args.layer == "full":
        layers.append("gliner")

    detector = PiiDetector(layers=layers, download_policy="auto")
    print(detector.anonymize(text))


def cmd_version(args) -> None:
    from . import __version__
    print(f"kvkk-pii {__version__}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kvkk-pii",
        description="KVKK uyumlu Turkce PII detection",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="PII tespiti yap")
    p_scan.add_argument("text", nargs="?", default="-", help="Metin veya dosya yolu (- icin stdin)")
    p_scan.add_argument("--layer", choices=["regex", "ner", "full"], default="regex")
    p_scan.add_argument("--format", choices=["text", "json"], default="text")

    # anonymize
    p_anon = sub.add_parser("anonymize", help="PII'i maskele")
    p_anon.add_argument("text", nargs="?", default="-")
    p_anon.add_argument("--layer", choices=["regex", "ner", "full"], default="regex")

    # version
    sub.add_parser("version", help="Versiyon goster")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "anonymize":
        cmd_anonymize(args)
    elif args.command == "version":
        cmd_version(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
