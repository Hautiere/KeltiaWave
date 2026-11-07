"""Correct common Welsh phrases after importing the machine draft.

Use --apply to save the corrections. The default mode is read-only.
"""

from __future__ import annotations

import argparse

from app.db import SessionLocal
from app.models import Phrase


CORRECTIONS = {
    100: "Bydd fy nghymydog yn dod i’m helpu.",
    109: "Helo, Yann ydw i. Pwy wyt ti?",
    111: "Welwn ni yfory.",
    112: "Diolch!",
    113: "Diolch i ti.",
    119: "O ble wyt ti’n dod?",
    121: "Ble ydych chi?",
    125: "Os gweli di’n dda.",
    129: "Faint o’r gloch y daw ef neu hi?",
    130: "Welwn ni heno.",
    136: "Wyddoch chi sut i gyrraedd Gwesty Marriott?",
    137: "Gaf i wydraid o ddŵr, os gwelwch yn dda?",
    141: "Dewch â rhagor o fara i ni, os gwelwch yn dda.",
    155: "Wnei di ddod?",
    711: "Nos da i chi.",
    714: "Diolch i chi.",
    717: "Rwy’n iawn, a chi?",
    720: "Pwy wyt ti?",
    722: "Beth yw dy enw?",
    725: "Fy enw i yw Raja.",
    727: "O ble ydych chi’n dod?",
    728: "Pa mor hen wyt ti?",
    733: "Pwy yw hwnnw?",
    734: "Pwy sy’n siarad Llydaweg?",
    735: "Sut mae ynganu hynny?",
    737: "Pwy ddaeth gyda thi?",
    739: "Des i i’ch gweld chi.",
    742: "Des i o hyd i dŷ fy neiniau a theidiau eto.",
    752: "Arhosodd gartref ar ei ben ei hun.",
    753: "Sut mae’r tŷ newydd?",
    755: "Rwy’n aros yn y gwely tan hanner dydd bob bore Llun.",
    757: "Bob bore, roedden ni’n bwyta brecwast wrth y bwrdd.",
    758: "Roedden ni’n yfed siocled poeth bob bore.",
    761: "Wyt ti’n yfed coffi yn y bore? Dydw i ddim.",
    763: "Canodd y ffôn am ddeg munud wedi wyth.",
    767: "Clowch y drws ar eich ôl, os gwelwch yn dda.",
    768: "Oes ots gennych chi os agoraf y ffenestr?",
    770: "Mae hi’n hoff iawn o dacluso’r tŷ.",
    771: "Rhaid i mi dacluso’r tŷ.",
    775: "Rwy’n agor y giât bob bore.",
    776: "Dydw i ddim yn agor y giât bob bore.",
    777: "Pwy ddiffoddodd y golau?",
    779: "Cyhyd ag y bydd golau, rydyn ni’n aros i ddarllen.",
    783: "Ble mae’r llyfr? Mae ar y llawr.",
    788: "Pa fag yw eich un chi?",
    789: "A yw llawr yr ystafell wedi’i wneud o bren go iawn?",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        phrases = {phrase.id: phrase for phrase in db.query(Phrase).filter(Phrase.id.in_(CORRECTIONS)).all()}
        if len(phrases) != len(CORRECTIONS) or any(phrase.langue != "br" for phrase in phrases.values()):
            raise SystemExit("Expected Breton phrases are missing")
        changes = [phrase for phrase in phrases.values() if phrase.traduction_cy != CORRECTIONS[phrase.id]]
        print(f"Matched: {len(phrases)}; to correct: {len(changes)}; apply: {args.apply}")
        if args.apply:
            for phrase in changes:
                phrase.traduction_cy = CORRECTIONS[phrase.id]
            db.commit()


if __name__ == "__main__":
    main()
