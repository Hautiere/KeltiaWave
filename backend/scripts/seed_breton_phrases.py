from app.db import Base, SessionLocal, engine
from app.models import Phrase


AUTHOR = "jeu-test-codex"

PHRASES = [
    ("Demat deoc'h !", "vie-quotidienne", "A1"),
    ("Mont a ran d'ar skol bemdez.", "ecole-formation", "A1"),
    ("Brav eo an amzer hiziv.", "nature-environnement", "A1"),
    ("Kafe tomm a blij din diouzh ar mintin.", "vie-quotidienne", "A1"),
    ("Chom a ran er gêr fenoz.", "vie-quotidienne", "A1"),
    ("Debriñ a ran bara gant amann.", "vie-quotidienne", "A1"),
    ("Ur banne dour a fell din.", "sante", "A1"),
    ("Setu ma levr nevez.", "ecole-formation", "A1"),
    ("Skuizh on goude al labour.", "travail", "A2"),
    ("Laouen on da welet ac'hanout.", "famille", "A2"),
    ("Pelec'h emañ ar porzh-houarn ?", "transports", "A1"),
    ("Pegoulz e loc'h ar bus ?", "transports", "A1"),
    ("Ret eo din prenañ ur bilhed.", "transports", "A2"),
    ("Mont a reomp war varc'h-houarn betek Kemper.", "transports", "A2"),
    ("Gortoz a ran ar c'harr-boutin dirak an ti-kêr.", "transports", "A2"),
    ("An hent-mañ zo serret hiziv.", "transports", "A2"),
    ("N'eo ket pell ar mor diouzh amañ.", "nature-environnement", "A2"),
    ("Klevet a ran an avel er gwez.", "nature-environnement", "A2"),
    ("Glav a ra abaoe ar mintin.", "nature-environnement", "A1"),
    ("Ar ster zo uhel goude ar glav.", "nature-environnement", "B1"),
    ("Plijout a ra din bale war an aod.", "nature-environnement", "A2"),
    ("Gwelet hon eus evned er jardin.", "nature-environnement", "A2"),
    ("Ar vugale a c'hoari er porzh.", "famille", "A1"),
    ("Ma zad-kozh a gomz brezhoneg mat.", "famille", "A2"),
    ("Ouzh taol emañ ar familh fenoz.", "famille", "A2"),
    ("Sikour a ran ma mamm d'ar Sadorn.", "famille", "A2"),
    ("Ur goulenn am eus evit ar c'helenner.", "ecole-formation", "A2"),
    ("Deskiñ a reomp gerioù nevez bep sizhun.", "ecole-formation", "A2"),
    ("Skrivañ a ran ur frazenn war ar c'haier.", "ecole-formation", "A2"),
    ("Lenn a raio ar skolidi ur pennad berr.", "ecole-formation", "B1"),
    ("An abadenn a grogo da eizh eur.", "culture", "A2"),
    ("Kanañ a ra ar strollad e brezhoneg.", "culture", "A2"),
    ("Plijout a ra din sonerezh Breizh.", "culture", "A1"),
    ("Gwelet hon eus ur pezh-c'hoari dec'h.", "culture", "B1"),
    ("Ar festival a sach kalz tud bep bloaz.", "culture", "B1"),
    ("Ret eo leuniañ ar furmskrid-mañ.", "administration", "B1"),
    ("Ma chomlec'h nevez zo bet enrollet.", "administration", "B1"),
    ("Digor eo an ti-kêr betek pemp eur.", "administration", "A2"),
    ("Kaset em eus ur postel d'ar servij.", "administration", "B1"),
    ("Goulenn a ran un testeni chomlec'h.", "administration", "B1"),
    ("Labourat a ran er burev hiziv.", "travail", "A1"),
    ("Ur vodadeg a vo goude merenn.", "travail", "A2"),
    ("Echuiñ a rin ar restr a-benn arc'hoazh.", "travail", "B1"),
    ("Klask a reomp un diskoulm aesoc'h.", "travail", "B1"),
    ("Komz a raio ar skipailh diwar-benn ar raktres.", "travail", "B1"),
    ("Poan am eus em fenn abaoe dec'h.", "sante", "A2"),
    ("Ret eo din mont da welet ar medisin.", "sante", "A2"),
    ("Kousket mat am eus en noz tremenet.", "sante", "A2"),
    ("Debriñ frouezh a zo mat evit ar yec'hed.", "sante", "B1"),
    ("Ar yec'hedour a roio ali d'ar familh.", "sante", "B1"),
    ("Pellgargañ a ran ur restr war ma urzhiataer.", "technologie-medias", "B1"),
    ("Gwelet a ran ar video war ma fellgomzer.", "technologie-medias", "A2"),
    ("An arload-mañ a labour mat-tre.", "technologie-medias", "B1"),
    ("Ret eo mirout ar ger-tremen en un doare sur.", "technologie-medias", "B1"),
    ("Kaset eo bet ar gemennadenn dre bostel.", "technologie-medias", "B1"),
    ("Kemer a ran ma lein da seizh eur.", "vie-quotidienne", "A1"),
    ("Prenañ a ran avaloù er marc'had.", "vie-quotidienne", "A1"),
    ("Naetaat a reomp ar gegin goude koan.", "vie-quotidienne", "A2"),
    ("An nor zo digor, met ar prenestr zo serret.", "vie-quotidienne", "A1"),
    ("Gortoz a ran ma mignoned dirak ar stal.", "vie-quotidienne", "A2"),
    ("N'eus ket kalz amzer ganeomp.", "vie-quotidienne", "A2"),
    ("Bez' ez eus kalz tud er marc'had hiziv.", "vie-quotidienne", "B1"),
    ("Goulenn a ran an hent d'ar greizenn.", "transports", "A2"),
    ("Ar vag a dreuzo ar porzh da nav eur.", "transports", "B1"),
    ("Ar marc'h-houarn a zo leun e-pad ar vakañsoù.", "transports", "B1"),
    ("An dud deuet da weladenniñ a wel ar c'hastell.", "culture", "B1"),
    ("Kontañ a ra ar plac'h ur vojenn gozh.", "culture", "B1"),
    ("Ober a reomp ur fest-noz er gumun.", "culture", "A2"),
    ("An dañserien a zesko pazennoù nevez.", "culture", "B1"),
    ("Ar c'helenn brezhoneg a zo pouezus evidomp.", "ecole-formation", "B1"),
    ("Ar skolidi a labour gant un daolenn nevez.", "ecole-formation", "B1"),
    ("Klevet a ran ar c'helenner er sal.", "ecole-formation", "A2"),
    ("Ret eo adlenn ar gentel a-raok an arnod.", "ecole-formation", "B1"),
    ("Ar bugel a lavar ur ger nevez.", "famille", "A1"),
    ("Ma breur a ra sport bep Merc'her.", "famille", "A2"),
    ("Ma c'hoar a blij dezhi livañ tresadennoù.", "famille", "A2"),
    ("Ouzhpenn dek den a vo d'ar pred.", "famille", "B1"),
    ("Kreskiñ a ra ar plant gant an heol.", "nature-environnement", "A2"),
    ("Er goañv e vez yen an nozioù.", "nature-environnement", "A2"),
    ("An douar a rank bezañ gwarezet.", "nature-environnement", "B1"),
    ("Ne daolomp ket lastez war an hent.", "nature-environnement", "B1"),
    ("Ma c'hendiviz labour a vo berr hiziv.", "travail", "B1"),
    ("An implijidi a eskemm mennozhioù nevez.", "travail", "B1"),
    ("Kavet hon eus un doare simploc'h da labourat.", "travail", "B1"),
    ("Ar raktres a vo kaset d'ar skipailh warc'hoazh.", "travail", "B2"),
    ("Gwelloc'h eo mont da gousket abred.", "sante", "A2"),
    ("An dour tomm a sikour pa vez yen an amzer.", "sante", "A2"),
    ("Dizoursi eo ar paotr goude ar c'hontroll.", "sante", "B1"),
    ("Ur pred skañv a zo mat goude ar sport.", "sante", "B1"),
    ("Ober a ran un enklask war ar rouedad.", "technologie-medias", "B1"),
    ("Ar c'helaouenn a embann ur pennad e brezhoneg.", "technologie-medias", "B1"),
    ("Ma fellgomzer a zo karget mat.", "technologie-medias", "A2"),
    ("Evit selaou an audio, pouezit war ar bouton.", "technologie-medias", "A2"),
    ("Ar gartenn-mañ a ziskouez ar broioù brezhonek.", "administration", "B1"),
    ("An ti-post a serr da c'hwec'h eur.", "administration", "A2"),
    ("Ur respont a vo kaset deoc'h dre bostel.", "administration", "B1"),
    ("Gallout a rit pellgargañ ar restr goude an emgav.", "administration", "B2"),
    ("Dont a raio ma amezeg da sikour ac'hanon.", "vie-quotidienne", "B1"),
    ("N'ouzon ket c'hoazh petra a rin disadorn.", "vie-quotidienne", "B1"),
    ("Ur banne te tomm a garfen bremañ.", "vie-quotidienne", "A2"),
    ("Noz vat ha kenavo d'an holl.", "vie-quotidienne", "A1"),
]


def main() -> None:
    if len(PHRASES) < 100:
        raise SystemExit(f"Expected at least 100 phrases, got {len(PHRASES)}")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = {row[0] for row in db.query(Phrase.texte).all()}
        created = 0
        for texte, theme, niveau in PHRASES:
            if texte in existing:
                continue
            db.add(
                Phrase(
                    texte=texte,
                    theme=theme,
                    niveau=niveau,
                    source="jeu-test",
                    langue="br",
                    auteur=AUTHOR,
                )
            )
            created += 1
        db.commit()
        total = db.query(Phrase).filter(Phrase.auteur == AUTHOR).count()
        print(f"Phrases ajoutees: {created}")
        print(f"Total phrases {AUTHOR}: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
