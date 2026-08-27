import re
import unicodedata


DEFAULT_THEME = "vie-quotidienne"

THEME_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("transports", ("bus", "karr-boutin", "marc'h-houarn", "porzh-houarn", "bilhed", "hent", "vag", "porzh")),
    ("nature-environnement", ("amzer", "avel", "gwez", "glav", "ster", "aod", "mor", "evned", "jardin", "plant", "heol", "douar", "lastez", "gouanv")),
    ("ecole-formation", ("skol", "skolidi", "kelenner", "deskin", "gentel", "arnod", "kaier", "levr")),
    ("famille", ("familh", "mamm", "tad", "breur", "c'hoar", "bugel", "bugale", "tad-kozh")),
    ("sante", ("yec'hed", "medisin", "poan", "kousket", "dizoursi", "sport", "frouezh")),
    ("travail", ("labour", "burev", "vodadeg", "skipailh", "raktres", "implijidi", "restr")),
    ("technologie-medias", ("urzhiataer", "video", "fellgomzer", "arload", "ger-tremen", "rouedad", "audio", "bouton")),
    ("administration", ("furmskrid", "chomlec'h", "ti-ker", "servij", "testeni", "ti-post", "emgav")),
    ("culture", ("abadenn", "kanan", "sonerezh", "pezh-c'hoari", "festival", "kastell", "mojenn", "fest-noz", "danserien")),
)


def classify_phrase_theme(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"\s+", " ", normalized)
    for theme, keywords in THEME_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return theme
    return DEFAULT_THEME
