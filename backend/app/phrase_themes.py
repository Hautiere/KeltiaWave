import re
import unicodedata


DEFAULT_THEME = "maison-quotidien"

THEME_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rencontres", ("demat", "kenavo", "trugarez", "piv out", "piv oc'h", "da anv", "ho anv", "en em gav")),
    ("alimentation-achats", ("bara", "kafe", "debri", "kegin", "preti", "stal", "prena", "dour mar plij")),
    ("deplacements", ("bus", "karr-boutin", "marc'h-houarn", "porzh-houarn", "bilhed", "hent", "vag", "porzh")),
    ("nature-meteo", ("amzer", "avel", "gwez", "glav", "ster", "aod", "mor", "evned", "jardin", "plant", "heol", "douar", "lastez", "gouanv")),
    ("travail-etudes", ("skol", "skolidi", "kelenner", "deskin", "gentel", "arnod", "kaier", "levr", "labour", "burev", "vodadeg", "skipailh", "raktres", "implijidi")),
    ("famille-relations", ("familh", "mamm", "tad", "breur", "c'hoar", "bugel", "bugale", "tad-kozh")),
    ("sante-bien-etre", ("yec'hed", "medisin", "poan", "kousket", "dizoursi")),
    ("loisirs-sport", ("sport", "c'hoari", "bourmen")),
    ("numerique-technologies", ("urzhiataer", "video", "fellgomzer", "arload", "ger-tremen", "rouedad", "audio", "bouton")),
    ("demarches-services", ("furmskrid", "chomlec'h", "ti-ker", "servij", "testeni", "ti-post", "emgav")),
    ("culture-fetes", ("abadenn", "kanan", "sonerezh", "pezh-c'hoari", "festival", "fest-noz", "danserien")),
    ("histoire-patrimoine", ("kastell", "mojenn", "istor", "glad")),
)


def classify_phrase_theme(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"\s+", " ", normalized)
    for theme, keywords in THEME_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return theme
    return DEFAULT_THEME
