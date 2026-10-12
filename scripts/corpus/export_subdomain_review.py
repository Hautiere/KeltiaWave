"""Export approved Library phrases for editorial subdomain review.

This script is read-only. It does not infer or write subdomains.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.request import urlopen


def fetch_json(url: str) -> list[dict]:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4200")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phrases-json", type=Path, help="Saved response from /api/phrases/")
    parser.add_argument("--audios-json", type=Path, help="Saved response from /api/audios/?status=approved")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    phrases = json.loads(args.phrases_json.read_text()) if args.phrases_json else fetch_json(f"{base}/api/phrases/")
    approved = json.loads(args.audios_json.read_text()) if args.audios_json else fetch_json(f"{base}/api/audios/?status=approved")
    counts = Counter(audio["phrase_id"] for audio in approved)
    rows = [phrase for phrase in phrases if phrase["id"] in counts and phrase.get("langue") == "br"]
    rows.sort(key=lambda phrase: ((phrase.get("theme") or ""), phrase["id"]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["phrase_id", "theme", "subdomain_actuel", "subdomain_propose", "niveau", "texte_breton", "traduction_fr", "audios_approuves"])
        for phrase in rows:
            writer.writerow([
                phrase["id"], phrase.get("theme") or "", phrase.get("subdomain") or "", "",
                phrase.get("niveau") or "", phrase["texte"], phrase.get("traduction_fr") or "", counts[phrase["id"]],
            ])
    print(f"{len(rows)} phrases exportées vers {args.output}")


if __name__ == "__main__":
    main()
