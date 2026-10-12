"""Add reviewed English translations for the meeting and daily-life phrases.

Run from backend with PYTHONPATH=. python scripts/seed_english_translations.py --apply.
The default mode only reports the matching rows. Existing English translations
are preserved unless --replace is also supplied.
"""

from __future__ import annotations

import argparse

from app.db import SessionLocal
from app.models import Phrase


TRANSLATIONS = {
    100: "My neighbour will come and help me.",
    101: "I don't yet know what I'll do on Saturday.",
    105: "It's going well.",
    108: "Hello.",
    109: "Hello, I'm Yann. Who are you?",
    110: "Goodbye!",
    111: "See you tomorrow.",
    112: "Thank you!",
    113: "Thank you.",
    114: "How are you?",
    115: "I'm fine, thank you!",
    116: "What's new?",
    117: "How's it going?",
    118: "What's your name?",
    119: "Where are you from?",
    120: "Who are you?",
    121: "Where are you?",
    122: "Do you agree?",
    123: "Yes, please!",
    124: "No, thank you for your help; I'm nearly there.",
    125: "Please.",
    126: "What time is it?",
    127: "It's ten o'clock.",
    128: "What time does it start?",
    129: "What time is he or she coming?",
    130: "See you tonight.",
    131: "Tonight at eight o'clock.",
    132: "What time does the shop open?",
    133: "Where do you live?",
    143: "I'm going to bed.",
    144: "It's time to go to bed.",
    145: "I'm going to bed early.",
    146: "I have to go to bed early tonight.",
    152: "What's happening?",
    153: "What needs to be done?",
    154: "What do you need?",
    155: "Will you come?",
    156: "I'll call you tomorrow.",
    157: "I'll go.",
    709: "Hi!",
    710: "Good night!",
    711: "Good night to you.",
    712: "Goodbye.",
    713: "Thank you very much.",
    714: "Thank you.",
    715: "Please sit down.",
    716: "Welcome.",
    717: "I'm fine, and you?",
    718: "How's it going?",
    719: "How are things?",
    720: "Who are you?",
    721: "Who are you?",
    722: "What's your name?",
    723: "What's your name?",
    724: "What is your name?",
    725: "My name is Raja.",
    726: "My name is Enora.",
    727: "Where are you from?",
    728: "How old are you?",
    729: "How old are you?",
    730: "Do you have children?",
    731: "Are you married?",
    732: "Have you been here long?",
    733: "Who is that man?",
    734: "Who speaks Breton?",
    735: "How do you pronounce that?",
    736: "Who is that person over there?",
    737: "Who came with you?",
    738: "What time shall we meet?",
    739: "I came to see you.",
    740: "When will you move into the new house?",
    741: "Sometimes I dance alone at home.",
    742: "I found my grandparents' house again.",
    743: "I have a new house.",
    744: "The house is big.",
    745: "This house is very big.",
    746: "The house is beautiful.",
    747: "There are six of us at home.",
    748: "I had stayed at home.",
    749: "I'm at home at noon.",
    750: "We're at home.",
    751: "Is your father at home?",
    752: "He stayed at home alone.",
    753: "What is the new house like?",
    754: "Have you bought a new house?",
    755: "I stay in bed until noon every Monday morning.",
    756: "What time do you wake up?",
    757: "Every morning, we used to have breakfast at the table.",
    758: "We used to drink hot chocolate every morning.",
    759: "He had slept well during the night.",
    760: "I usually drink coffee for breakfast.",
    761: "Do you drink coffee in the morning? I don't.",
    762: "What do you have in the morning, coffee or tea?",
    763: "The phone rang at ten past eight.",
    764: "The door opens.",
    765: "I open the door.",
    766: "Do you open the door?",
    767: "Please lock the door behind you.",
    768: "Do you mind if I open the window?",
    769: "Please close the window!",
    770: "She really likes tidying the house.",
    771: "I have to tidy the house.",
    772: "People wash their hands before sitting down to eat.",
    773: "I still need to brush my teeth and take a shower.",
    774: "Please boil the water.",
    775: "I open the gate every morning.",
    776: "I don't open the gate every morning.",
    777: "Who turned off the light?",
    778: "I'm not sure I turned off the light before going out.",
    779: "As long as there is daylight, we stay and read.",
    780: "Make sure no water gets into the house.",
    781: "Where is the bathroom?",
    782: "Go through the room to get out.",
    783: "Where is the book? It's on the floor.",
    784: "Where is the school bag? It's on the table.",
    785: "What is that? It's a table.",
    786: "What is there on the table?",
    787: "Where did you put the book?",
    788: "Which bag is yours?",
    789: "Is the floor of the room made of real wood?",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        phrases = db.query(Phrase).filter(Phrase.id.in_(TRANSLATIONS)).all()
        matched = [phrase for phrase in phrases if phrase.langue == "br" and phrase.theme in {"rencontres", "maison-quotidien", "vie-quotidienne"}]
        if len(matched) != len(TRANSLATIONS):
            raise SystemExit(f"Expected {len(TRANSLATIONS)} matching Breton phrases, found {len(matched)}; database differs from the reviewed corpus")
        changes = [phrase for phrase in matched if args.replace or not phrase.traduction_en]
        print(f"Matched: {len(matched)}; to update: {len(changes)}; apply: {args.apply}")
        if args.apply:
            for phrase in changes:
                phrase.traduction_en = TRANSLATIONS[phrase.id]
            db.commit()


if __name__ == "__main__":
    main()
