import re
from datetime import date, datetime

import backend.src.models as model
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.sql._expression_select_cls import SelectOfScalar

KVINNER: set[str] = {
    "jenter",
    "kvinner",
    "girls",
}
MENN: set[str] = {
    "gutter",
    "menn",
    "boys",
    "veteran",
}
ALDER: dict[str, int] = {
    "12": 12,
    "13": 13,
    "14": 14,
    "15": 15,
    "16": 16,
    "17": 17,
    "18-23": 23,
    "18": 18,
    "19": 19,
    "senior": 28,
    "old girls": 33,
    "old boys": 35,
    "veteran": 40,
}


sqlite_file_name = "innebandy.db"
sqlite_url = f"sqlite:///./data/{sqlite_file_name}"
engine = create_engine(
    sqlite_url, echo=False
)  # Sett echo=True for å se SQL-spørringene i terminalen

SQLModel.metadata.create_all(engine)


def hent_eller_lagre_sesong(sesong_navn: str) -> int:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Sesonger] = select(model.Sesonger).where(
            model.Sesonger.navn == sesong_navn
        )
        sesong: model.Sesonger | None = session.exec(statement).first()

        if not sesong:
            aarstall: str = re.search(r"\d{4}", sesong_navn).group()
            aarstall_int: int = int(aarstall)
            sesongen = model.Sesonger(navn=sesong_navn, base_aar=aarstall_int)
            session.add(sesongen)
            session.commit()
            session.refresh(sesongen)
            return sesongen.id

        return sesong.id


def hent_eller_lagre_klasse(klasse_navn: str) -> int:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Klasser] = select(model.Klasser).where(
            model.Klasser.navn == klasse_navn
        )
        klasse: model.Klasser | None = session.exec(statement).first()

        if not klasse:
            klasse_navn_low: str = klasse_navn.lower()
            kjonn = model.KjonnEnum("u")
            if any(klasse.lower() in klasse_navn_low for klasse in KVINNER):
                kjonn = model.KjonnEnum("k")
            if any(klasse.lower() in klasse_navn_low for klasse in MENN):
                kjonn = model.KjonnEnum("m")

            sortert_alder: list[str] = sorted(ALDER.keys(), key=len, reverse=True)

            alder: int | None = None
            for nokkel in sortert_alder:
                if nokkel.lower() in klasse_navn_low:
                    alder = ALDER[nokkel]

            klassen = model.Klasser(navn=klasse_navn, kjonn=kjonn, alder=alder)
            session.add(klassen)
            session.commit()
            session.refresh(klassen)
            return klassen.id

        return klasse.id


def hent_eller_lagre_klubb_og_lag(
    klubb_id: str, klubb_navn: str, lag_id: str, lag_navn: str
) -> str:
    with Session(engine) as session:
        statement_klubb: SelectOfScalar[model.Klubber] = select(model.Klubber).where(
            model.Klubber.id == klubb_id
        )
        klubb: model.Klubber | None = session.exec(statement_klubb).first()

        if klubb:
            klubb_id_ut: str = klubb.id
        else:
            klubben = model.Klubber(id=klubb_id, navn=klubb_navn)
            session.add(klubben)
            session.commit()
            session.refresh(klubben)
            klubb_id_ut = klubben.id

        statement_lag: SelectOfScalar[model.Lag] = select(model.Lag).where(
            model.Lag.id == lag_id
        )
        lag: model.Lag | None = session.exec(statement_lag).first()

        if lag:
            lag_id_ut: str = lag.id
        else:
            laget = model.Lag(id=lag_id, navn=lag_navn, klubb_id=klubb_id)
            session.add(laget)
            session.commit()
            session.refresh(laget)
            lag_id_ut = laget.id

        return lag_id_ut


def hent_eller_lagre_kamp(
    kampnr: int,
    klasse_id: int,
    hjemmelag_id: str,
    bortelag_id: str,
    tidspunkt: datetime,
    sesong_id: int,
    maal_h: int,
    maal_b: int,
) -> int:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Kamper] = select(model.Kamper).where(
            model.Kamper.kampnr == kampnr
        )
        kamp: model.Kamper | None = session.exec(statement).first()

        if not kamp:
            kampen = model.Kamper(
                kampnr=kampnr,
                klasse_id=klasse_id,
                hjemmelag_id=hjemmelag_id,
                bortelag_id=bortelag_id,
                tidspunkt=tidspunkt,
                sesong_id=sesong_id,
                ant_maal_hjemmelag=maal_h,
                ant_maal_bortelag=maal_b,
            )
            session.add(kampen)
            session.commit()
            session.refresh(kampen)
            return kampen.kampnr

        return kamp.kampnr


def hent_eller_lagre_spiller(spiller_navn: str, spiller_fdato: date) -> int:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Spillere] = select(model.Spillere).where(
            model.Spillere.navn == spiller_navn,
            model.Spillere.fdato == spiller_fdato,
        )
        spiller: model.Spillere | None = session.exec(statement).first()

        if not spiller:
            spilleren = model.Spillere(
                navn=spiller_navn,
                fdato=spiller_fdato,
            )
            session.add(spilleren)
            session.commit()
            session.refresh(spilleren)
            return spilleren.id

        return spiller.id


def hent_eller_lagre_kampforekomst(kamphendelse) -> int:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Kampforekomster] = select(
            model.Kampforekomster
        ).where(
            model.Kampforekomster.spiller_id == kamphendelse["spiller_id"],
            model.Kampforekomster.kamp_id == kamphendelse["kamp_id"],
        )
        kampforekomst: model.Kampforekomster | None = session.exec(statement).first()

        if not kampforekomst:
            kampforekomsten = model.Kampforekomster(
                spiller_id=kamphendelse["spiller_id"],
                kamp_id=kamphendelse["kamp_id"],
                lag_id=kamphendelse["lag_id"],
                ant_maal=kamphendelse["Mål"],
                ant_assist=kamphendelse["Assist"],
                ant_to_min=kamphendelse["2M utvisning"],
                ant_to_p_ti_min=kamphendelse["2+10M utvisning"],
                ant_kampstraff=kamphendelse["Kampstraff"],
                redninger=kamphendelse["Redninger"],
                ant_maal_mot=kamphendelse["Innsluppet"],
                maalvakt=kamphendelse["Målvakt"],
            )
            session.add(kampforekomsten)
            session.commit()
            session.refresh(kampforekomsten)
            return kampforekomsten.id

        return kampforekomst.id


def sjekk_om_kamp_finnes(kampnr) -> bool:
    with Session(engine) as session:
        statement: SelectOfScalar[model.Kamper] = select(model.Kamper).where(
            model.Kamper.kampnr == kampnr
        )
        kamp: model.Kamper | None = session.exec(statement).first()

        return bool(kamp)


def hent_tidspunkt_siste_kamp_spiller(spiller) -> datetime:
    pass
