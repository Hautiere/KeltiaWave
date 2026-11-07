#!/usr/bin/env python3
"""Prepare 50 additional Common Voice clips per Komz theme, without DB writes.

Existing Breton texts must be exported from the target database first. Explicit
textual theme choices cover ambiguous categories; neither these choices nor
Common Voice votes claim an individual listening or linguistic validation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from common_voice import DEFAULT_DATASET_DIR, load_common_voice, rank_audios
from prepare_common_voice_1000 import FIELDS, read_durations
from preview_theme_migration import DIRECT

THEMES = set(DIRECT.values()) | {'rencontres', 'maison-quotidien'}

def prepare(existing_path: Path, choices_path: Path, classified: Path, dataset: Path, output: Path):
    existing = {text.strip().casefold() for text in json.loads(existing_path.read_text())}
    with choices_path.open(encoding='utf-8-sig') as handle:
        choices = list(csv.DictReader(handle, delimiter=';'))
    overrides = {}
    for row in choices:
        text, theme = row['phrase_br'].strip(), row['theme_propose'].strip()
        if theme not in THEMES or text.casefold() in existing or text in overrides:
            raise ValueError(f'Choix thématique invalide ou déjà présent : {text}')
        overrides[text] = theme
    with classified.open(encoding='utf-8-sig') as handle:
        source = {row['phrase_br'].strip(): row for row in csv.DictReader(handle, delimiter=';')}
    index = load_common_voice(dataset)
    durations = read_durations(dataset / 'clip_durations.tsv')
    groups = {theme: [] for theme in THEMES}
    for text, audios in index.items():
        if text.casefold() in existing or not 2 <= len(text.split()) <= 20 or not 8 <= len(text) <= 160:
            continue
        old = source.get(text, {})
        theme = overrides.get(text) or DIRECT.get(old.get('theme_keltiawave', ''))
        if not theme:
            continue
        eligible = [a for a in audios if a['audio_exists'] and a['up_votes'] >= 2 and a['down_votes'] == 0
                    and 500 <= durations.get(a['audio_filename'], 0) <= 20000]
        if not eligible:
            continue
        best = rank_audios(eligible)[0]
        groups[theme].append((text, old, best, len(audios)))
    selected = []
    seen_text, seen_audio = set(existing), set()
    for theme in sorted(THEMES):
        candidates = groups[theme]
        if any(value == theme for value in overrides.values()):
            candidates = [item for item in candidates if overrides.get(item[0]) == theme]
        candidates.sort(key=lambda item: (-item[2]['up_votes'], {'élevée':0, 'moyenne':1}.get(item[1].get('confiance_classement'),2), abs(len(item[0].split())-7), item[0]))
        retained = []
        for text, old, audio, count in candidates:
            if text.casefold() in seen_text or audio['audio_filename'] in seen_audio:
                continue
            seen_text.add(text.casefold()); seen_audio.add(audio['audio_filename'])
            path = dataset / 'clips' / audio['audio_filename']
            retained.append(dict(phrase_br=text, theme_source=old.get('theme_keltiawave',''), theme_propose=theme,
                theme_statut='proposition_a_relire', traduction_fr='', traduction_statut='a_traduire',
                niveau='', niveau_statut='a_evaluer', best_audio_filename=path.name, audio_count=count,
                up_votes=audio['up_votes'], down_votes=audio['down_votes'], duration_ms=durations[path.name],
                audio_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sentence_id=audio['source_id'],
                locale=audio['locale'], accent_declare=audio['accents'], variante_declaree=audio['variant'],
                source='common-voice', licence_source='CC0 (déclaration du jeu de données)', validation_komz='non_valide'))
            if len(retained)==50:
                break
        if len(retained)!=50:
            raise ValueError(f'{theme} : {len(retained)} candidats seulement ; aucun manifeste écrit')
        selected.extend(retained)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS,delimiter=';',lineterminator='\n');writer.writeheader()
        for rank,row in enumerate(selected,1):writer.writerow(dict(rang=rank,**row))
    return Counter(row['theme_propose'] for row in selected)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--existing',type=Path,required=True)
    parser.add_argument('--choices',type=Path,required=True)
    parser.add_argument('--classified',type=Path,default=DEFAULT_DATASET_DIR.parent/'keltiawave_commonvoice_phrases_classees.csv')
    parser.add_argument('--dataset',type=Path,default=DEFAULT_DATASET_DIR)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for theme,count in sorted(prepare(args.existing,args.choices,args.classified,args.dataset,args.output).items()):print(f'{theme}: {count}')
