"""Propose conservative subdomains from Breton/French keywords for local review.

Only rows with one matching category receive a proposal. Existing values are kept.
"""

import argparse
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


# Keys match the central taxonomy in apps/corpus/src/app/core/subdomains.ts.
RULES: dict[str, dict[str, str]] = {
    "rencontres": {
        "saluer-et-prendre-conge": r"\b(demat|bonjour|bonsoir|kenavo|au revoir|salut|trugarez|merci)\b",
        "se-presenter": r"\b(m'appelle|je suis|mon nom|anv|appelle|piv oc'h|qui etes)\b",
        "origine-et-lieu-de-vie": r"\b(viens de|viens-tu|d'ou|pelec'h|habite|j'habite|chom|origine)\b",
        "parler-de-soi": r"\b(j'ai|j'aime|je veux|me plait|je peux)\b",
        "gouts-et-preferences": r"\b(prefere|aime|plij|karout|gout)\b",
        "poser-des-questions": r"\b(comment|pourquoi|quand|ou|qui|quoi|petra|perak|pegoulz|penaos)\b",
    },
    "maison-quotidien": {
        "maison": r"\b(maison|ti|chez moi|chez nous)\b",
        "pieces-et-mobilier": r"\b(chambre|cuisine|salon|lit|table|chaise|meuble|dor|fenetre)\b",
        "taches-quotidiennes": r"\b(nettoie|menage|vaisselle|laver|ranger|nettoyer|faire la cuisine)\b",
        "matin-et-soir": r"\b(matin|soir|nuit|reveil|coucher|dormir|kousk|noz|mintin)\b",
        "objets-du-quotidien": r"\b(cle|sac|lampe|telephone|objet|livre|bouteille)\b",
        "voisinage": r"\b(voisin|voisine|amezeg|quartier)\b",
    },
    "famille-relations": {
        "famille": r"\b(famill|familh|mamm|mere|papa|pere|tad|breur|frere|soeur|c'hoar|grand-mere|grand-pere|mamm-gozh|tad-kozh)\b",
        "couple-et-proches": r"\b(mari|femme|epoux|epouse|conjoint|pried|gwaz|fiance)\b",
        "amis": r"\b(ami|amie|mignon|copain|copine)\b",
        "enfants-et-generations": r"\b(enfant|enfants|bugel|bugale|bebe|merc'h|fils|fille|generations)\b",
        "relations-humaines": r"\b(rencontr|ensemble|asambles|se connaitre|discut|relations|conflit)\b",
        "emotions-et-sentiments": r"\b(aime|amour|karout|joie|peur|colere|triste|heureux|sentiment|mousc'hoarzh)\b",
    },
    "alimentation-achats": {
        "aliments-et-boissons": r"\b(pain|lait|laezh|eau|dour|the|te|cafe|kafe|fruit|frouezh|legume|viande|kig|poisson|pesk|boued)\b",
        "repas": r"\b(repas|dejeuner|diner|petit-dejeuner|pred|manger|debri|faim)\b",
        "cuisine-et-recettes": r"\b(cuisine|cuisiner|recette|cuire|gateau|gwastell|poazh|four)\b",
        "cafe-et-restaurant": r"\b(restaurant|serveur|menu|cafe|kafe|commander)\b",
        "marche-et-commerces": r"\b(marche|boutique|magasin|commerce|stal|supermarche)\b",
        "acheter-et-payer": r"\b(acheter|achat|payer|prix|euro|billet|monnaie|prena|paea)\b",
    },
    "deplacements": {
        "se-deplacer": r"\b(partir|arriver|aller|mont|dont|voyager|deplacer|trajet)\b",
        "train-et-gare": r"\b(train|gare|marc'h-houarn|station ferroviaire)\b",
        "voiture-et-route": r"\b(voiture|auto|route|hent|velo|belohent|condui)\b",
        "bus-et-transports-publics": r"\b(bus|car|metro|tram|carr-boutin|karr-boutin|transport public)\b",
        "hebergement": r"\b(hotel|chambre|hebergement|logement|auberge)\b",
        "demander-son-chemin": r"\b(ou se trouve|comment aller|direction|quel chemin|da belec'h|ou mene)\b",
    },
    "nature-meteo": {
        "mer-et-littoral": r"\b(mer|mor|plage|aod|bateau|vag|baie|ocean|littoral|cote)\b",
        "campagne-et-paysages": r"\b(campagne|paysage|montagne|colline|vallee|foret|koat|parc|champ)\b",
        "animaux": r"\b(animal|loen|oiseau|evn|cheval|kezeg|chien|chat|poisson)\b",
        "plantes-et-jardin": r"\b(plante|plant|jardin|liorzh|fleur|arbre|gwez)\b",
        "meteo-et-saisons": r"\b(pluie|glav|soleil|heol|vent|avel|hiver|goanv|ete|hanv|printemps|automne|froid|chaud|temps)\b",
        "environnement": r"\b(climat|ecolog|environnement|pollution|recycl|biodivers|terre|douar)\b",
    },
    "travail-etudes": {
        "metiers": r"\b(metier|micher|jardinier|enseignant|professeur|infirm|boulanger|employe)\b",
        "lieu-de-travail": r"\b(bureau|burev|entreprise|usine|atelier|lieu de travail)\b",
        "ecole-et-etudes": r"\b(ecole|skol|eleve|skolidi|lycee|universite|cours|kentel|etude|examen)\b",
        "apprendre": r"\b(apprendre|deski|enseigne|kelenn|etudier|lire|lenn|ecrire|skriv)\b",
        "reunions-et-echanges": r"\b(reunion|bodadeg|echanger|discut|kendiviz|rencontre)\b",
        "projets-et-activites": r"\b(projet|raktres|activite|labourat|travailler|travail|labour)\b",
    },
    "sante-bien-etre": {
        "corps-humain": r"\b(corps|bras|jambe|main|tete|dos|epaule|estomac|ventre|gwad|sang)\b",
        "sante-et-symptomes": r"\b(malade|maladie|douleur|mal au|poan|klañv|fievre|blessure|gouli|symptome)\b",
        "medecin-et-pharmacie": r"\b(medecin|medisin|docteur|pharmacie|medicament|hopital)\b",
        "forme-et-fatigue": r"\b(fatigue|skuizh|forme|energie|sport|course|redadeg)\b",
        "sommeil-et-repos": r"\b(dormir|sommeil|repos|kousk|noz|nuit|coucher)\b",
        "bien-etre": r"\b(bien-etre|detente|calme|relax|yec'hed mat|bonne sante)\b",
    },
    "culture-fetes": {
        "heure-et-rendez-vous": r"\b(heure|eur|rendez-vous|emgav|demain|warc'hoazh|aujourd'hui|hiziv)\b",
        "telephone-et-messages": r"\b(telephone|pellgomz|message|kemennadenn|bostel|appel)\b",
        "services": r"\b(service|servij|poste|mairie|ti-ker)\b",
        "problemes-et-imprevus": r"\b(probleme|imprevu|panne|fazi|erreur|diaes)\b",
        "demander-de-l-aide": r"\b(aide|sikour|secours|aider)\b",
        "politesse-et-interactions": r"\b(merci|trugarez|pardon|pardono|s'il vous plait|mar plij)\b",
        "traditions-et-fetes": r"\b(fete|fest|gouel|noel|nedeleg|pask|paques|anniversaire|festival|fest-noz)\b",
    },
    "loisirs-sport": {
        "sports": r"\b(sport|football|match|course|redadeg|entrain|jouer|c'hoari)\b",
        "marche-et-randonnee": r"\b(marche|randonn|bale|promenad)\b",
        "mer-et-activites-nautiques": r"\b(nager|natation|voile|surf|plongee|bateau|vag|kayak)\b",
        "musique": r"\b(musique|sonerezh|chanter|kana|chanson|ganaouenn|concert)\b",
        "lecture-et-medias": r"\b(lire|lenn|livre|levr|film|cinema|television|media)\b",
        "sorties-et-vacances": r"\b(vacances|vakans|sortie|voyage|festival|week-end)\b",
    },
    "histoire-patrimoine": {
        "histoire-et-patrimoine": r"\b(histoire|istor|roi|roue|chateau|kastell|patrimoine|ancien|gozh)\b",
        "traditions-et-fetes": r"\b(tradition|fete|fest|gouel|noel|nedeleg|festival)\b",
        "musique-et-danse": r"\b(musique|sonerezh|danse|dans|fest-noz|chanson)\b",
        "langue-bretonne": r"\b(breton|brezhoneg|langue|yezh|mot breton)\b",
        "arts-et-litterature": r"\b(art|litterature|livre|levr|lire|lenn|poeme|roman|peint|ecriv)\b",
        "societe-et-vie-locale": r"\b(societe|commune|kumun|ville|ker|politique|maire|population)\b",
    },
    "demarches-services": {
        "lieux-et-directions": r"\b(lieu|lec'h|direction|adresse|chomlec'h|ou se trouve|maison|ti-ker)\b",
        "signalisation": r"\b(panneau|signal|carte|kartenn|indication|fleche)\b",
        "horaires-et-dates": r"\b(horaire|heure|eur|date|demain|warc'hoazh|aujourd'hui|hiziv|ouvert|ferme)\b",
        "prix-et-paiement": r"\b(prix|payer|euro|budget|budjed|depense|dispign)\b",
        "administration": r"\b(administration|mairie|ti-ker|commune|kumun|formulaire|document|restr|attestation|testeni)\b",
        "urgences-et-services": r"\b(urgence|police|polis|pompier|hopital|secours|service|servij|poste)\b",
    },
    "numerique-technologies": {
        "internet": r"\b(internet|rouedad|site web|navigateur|en ligne)\b",
        "telephone-et-applications": r"\b(telephone|pellgomz|application|arload|appeler|appel)\b",
        "ordinateur": r"\b(ordinateur|urzhiataer|informatique|urzhataerezh|logiciel|meziant|fichier)\b",
        "messages-et-reseaux": r"\b(message|kemennadenn|bostel|courriel|reseau social|email)\b",
        "services-numeriques": r"\b(donnees|roadennoù|telecharg|pellgarg|programme|brogramm|plateforme)\b",
        "securite-en-ligne": r"\b(mot de passe|ger-tremen|securite|sur|pirat|confidentiel)\b",
    },
}


def normalize(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn")


def propose(theme: str, text: str) -> tuple[str, str]:
    theme = {"vie-quotidienne": "maison-quotidien"}.get(theme, theme)
    matches = [key for key, pattern in RULES.get(theme, {}).items() if re.search(pattern, normalize(text))]
    return (matches[0], "lexical") if len(matches) == 1 else ("", "ambiguous" if matches else "unmatched")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    counts: Counter[str] = Counter()
    with args.input.open(encoding="utf-8-sig", newline="") as source, args.output.open("w", encoding="utf-8-sig", newline="") as target:
        reader = csv.DictReader(source)
        fields = list(reader.fieldnames or []) + ["proposal_status"]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for row in reader:
            if not row["subdomain_actuel"]:
                value, status = propose(row["theme"], row["texte_breton"] + " " + row["traduction_fr"])
                row["subdomain_propose"] = value
            else:
                status = "existing"
            row["proposal_status"] = status
            counts[status] += 1
            writer.writerow(row)
    print(dict(counts))


if __name__ == "__main__":
    main()
