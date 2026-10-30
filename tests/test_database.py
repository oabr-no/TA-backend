from datetime import date, datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, func, select

import src.models as model
from src import database


@pytest.fixture(autouse=True)
def database_i_minnet(monkeypatch: pytest.MonkeyPatch):
    """Bytter ut den ekte databasen med en tom database i minnet."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(database, "_engine", engine)
    return engine


def antall(engine, tabell) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(tabell)).one()


def lagre_kamp(session: Session, kampnr: int = 1001) -> None:
    """Lagrer en fiktiv kamp med to spillere, slik run_scraper gjør det."""
    sesong_id = database.hent_eller_lagre_sesong(session, "2026/2027")
    klasse_id = database.hent_eller_lagre_klasse(session, "G15")
    hjemmelag = database.hent_eller_lagre_klubb_og_lag(
        session, "KL01", "Fiktiv IBK", "LA01", "Fiktiv IBK 1"
    )
    bortelag = database.hent_eller_lagre_klubb_og_lag(
        session, "KL02", "Oppdiktet IL", "LA02", "Oppdiktet IL 1"
    )
    database.hent_eller_lagre_kamp(
        session, kampnr, klasse_id, hjemmelag, bortelag,
        datetime(2026, 10, 1, 18, 0), sesong_id, 3, 2,
    )
    for navn, lag in (("Ola Testesen", hjemmelag), ("Kari Prøvesen", bortelag)):
        spiller_id = database.hent_eller_lagre_spiller(session, navn, date(2011, 5, 5))
        database.hent_eller_lagre_kampforekomst(
            session,
            {
                "spiller_id": spiller_id, "kamp_id": kampnr, "lag_id": lag,
                "Mål": 0, "Assist": 0, "2M utvisning": 0, "2+10M utvisning": 0,
                "Kampstraff": 0, "Redninger": 0, "Innsluppet": 0,
                "Målvakt": False, "Spilt": True, "Klubbtilhørighet": "Fiktiv IBK",
            },
        )


def test_hele_kampen_lagres_ved_commit(database_i_minnet) -> None:
    with database.transaksjon() as session:
        lagre_kamp(session)

    assert database.sjekk_om_kamp_finnes(1001)
    assert antall(database_i_minnet, model.Kampforekomster) == 2
    assert antall(database_i_minnet, model.Spillere) == 2
    with Session(database_i_minnet) as session:
        tilhorighet = session.exec(select(model.Kampforekomster.klubbtilhorighet)).all()
    assert tilhorighet == ["Fiktiv IBK", "Fiktiv IBK"]


def test_feil_underveis_ruller_tilbake_alt(database_i_minnet) -> None:
    with pytest.raises(RuntimeError):
        with database.transaksjon() as session:
            lagre_kamp(session)
            raise RuntimeError("feil etter at kampen er lagt til")

    assert not database.sjekk_om_kamp_finnes(1001)
    for tabell in (
        model.Kamper, model.Kampforekomster, model.Spillere,
        model.Lag, model.Klubber, model.Klasser, model.Sesonger,
    ):
        assert antall(database_i_minnet, tabell) == 0, tabell.__name__


def test_avbrudd_med_ctrl_c_ruller_ogsa_tilbake(database_i_minnet) -> None:
    with pytest.raises(KeyboardInterrupt):
        with database.transaksjon() as session:
            lagre_kamp(session)
            raise KeyboardInterrupt

    assert not database.sjekk_om_kamp_finnes(1001)


def test_nye_rader_finnes_igjen_i_samme_transaksjon(database_i_minnet) -> None:
    # Samme klubb og spiller to ganger før commit skal ikke gi duplikater
    with database.transaksjon() as session:
        lag_a = database.hent_eller_lagre_klubb_og_lag(session, "KL01", "Fiktiv IBK", "LA01", "Fiktiv IBK 1")
        lag_b = database.hent_eller_lagre_klubb_og_lag(session, "KL01", "Fiktiv IBK", "LA03", "Fiktiv IBK 2")
        id_1 = database.hent_eller_lagre_spiller(session, "Ola Testesen", date(2011, 5, 5))
        id_2 = database.hent_eller_lagre_spiller(session, "Ola Testesen", date(2011, 5, 5))

    assert (lag_a, lag_b) == ("LA01", "LA03")
    assert id_1 == id_2
    assert antall(database_i_minnet, model.Klubber) == 1
    assert antall(database_i_minnet, model.Spillere) == 1


def test_ny_spiller_lagres_med_fornavn_og_etternavn(database_i_minnet) -> None:
    with database.transaksjon() as session:
        database.hent_eller_lagre_spiller(
            session, "Ola Nordmann Testesen", date(2011, 5, 5), "Ola Nordmann", "Testesen"
        )

    with Session(database_i_minnet) as session:
        spiller = session.exec(select(model.Spillere)).one()
    assert (spiller.fornavn, spiller.etternavn) == ("Ola Nordmann", "Testesen")


def test_gammel_spiller_uten_fornavn_fylles_ut(database_i_minnet) -> None:
    with database.transaksjon() as session:
        gammel_id = database.hent_eller_lagre_spiller(session, "Ola Testesen", date(2011, 5, 5))
    with database.transaksjon() as session:
        ny_id = database.hent_eller_lagre_spiller(
            session, "Ola Testesen", date(2011, 5, 5), "Ola", "Testesen"
        )

    with Session(database_i_minnet) as session:
        spiller = session.exec(select(model.Spillere)).one()
    assert gammel_id == ny_id
    assert (spiller.fornavn, spiller.etternavn) == ("Ola", "Testesen")


def test_lagret_fornavn_overskrives_ikke(database_i_minnet) -> None:
    # Samme fulle navn kan deles på to måter. Den første lagrede verdien beholdes.
    with database.transaksjon() as session:
        database.hent_eller_lagre_spiller(
            session, "Ola Nordmann Testesen", date(2011, 5, 5), "Ola", "Nordmann Testesen"
        )
    with database.transaksjon() as session:
        database.hent_eller_lagre_spiller(
            session, "Ola Nordmann Testesen", date(2011, 5, 5), "Ola Nordmann", "Testesen"
        )

    with Session(database_i_minnet) as session:
        spiller = session.exec(select(model.Spillere)).one()
    assert (spiller.fornavn, spiller.etternavn) == ("Ola", "Nordmann Testesen")


def test_lagret_kamp_blir_ikke_dobbelt_lagret(database_i_minnet) -> None:
    with database.transaksjon() as session:
        lagre_kamp(session)
    with database.transaksjon() as session:
        lagre_kamp(session)

    assert antall(database_i_minnet, model.Kamper) == 1
    assert antall(database_i_minnet, model.Kampforekomster) == 2
