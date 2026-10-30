import uuid
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import NaiveDatetime
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class KjonnEnum(str, Enum):
    mann = "m"
    kvinne = "k"
    ukjent = "u"


class Sesonger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    navn: str = Field(unique=True)
    base_aar: int
    kamper: list["Kamper"] = Relationship(back_populates="sesong")


class Klasser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    navn: str
    kjonn: KjonnEnum
    alder: int | None
    kamper: list["Kamper"] = Relationship(back_populates="klasse")


class Klubber(SQLModel, table=True):
    id: str = Field(primary_key=True)
    navn: str = Field(unique=True)
    lag: list["Lag"] = Relationship(back_populates="klubb")


class Lag(SQLModel, table=True):
    id: str = Field(primary_key=True)
    navn: str
    klubb_id: str = Field(foreign_key="klubber.id")
    klubb: Optional[Klubber] = Relationship(back_populates="lag")
    kamper: list["Kamper"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "or_(Lag.id==Kamper.hjemmelag_id, Lag.id==Kamper.bortelag_id)",
            "viewonly": True,  # Viktig! Siden den er sammensatt, må den være skrivebeskyttet.
        }
    )
    kampforekomster: list["Kampforekomster"] = Relationship(back_populates="lag")


class Spillere(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("navn", "fdato", name="unique_navn_fdato"),)

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True
    )
    navn: str
    fdato: date
    # Fra TA. Tomme for spillere fra tidligere sesonger, der bare det sammenslåtte
    # navnet er lagret. Fylles ut når spilleren dukker opp i en ny kamp.
    fornavn: Optional[str] = Field(default=None)
    etternavn: Optional[str] = Field(default=None)
    kampforekomster: list["Kampforekomster"] = Relationship(back_populates="spiller")


class Kamper(SQLModel, table=True):
    kampnr: int = Field(primary_key=True)
    klasse_id: int = Field(foreign_key="klasser.id")
    klasse: Optional[Klasser] = Relationship(back_populates="kamper")

    hjemmelag_id: str = Field(foreign_key="lag.id")
    hjemmelag: Optional[Lag] = Relationship(
        back_populates="kamper",
        sa_relationship_kwargs={"foreign_keys": "[Kamper.hjemmelag_id]"},
    )

    bortelag_id: str = Field(foreign_key="lag.id")
    bortelag: Optional[Lag] = Relationship(
        back_populates="kamper",
        sa_relationship_kwargs={"foreign_keys": "[Kamper.bortelag_id]"},
    )
    # Norsk lokal tid uten tidssone, slik TA viser den og slik eldre rader er lagret
    tidspunkt: Optional[NaiveDatetime] = Field(default=None)
    sesong_id: int = Field(foreign_key="sesonger.id")
    sesong: Optional[Sesonger] = Relationship(back_populates="kamper")
    kampforekomster: list["Kampforekomster"] = Relationship(back_populates="kamp")
    # None når resultatet ikke er registrert i TA
    ant_maal_hjemmelag: Optional[int] = Field(default=None)
    ant_maal_bortelag: Optional[int] = Field(default=None)


class Kampforekomster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spiller_id: str = Field(foreign_key="spillere.id")
    spiller: Optional[Spillere] = Relationship(back_populates="kampforekomster")
    # Lagret som tekst, mens Kamper.kampnr er int. SQL-spørringer kobler likevel
    # riktig, men i Python/pandas må kamp_id gjøres om til int før sammenligning.
    kamp_id: str = Field(foreign_key="kamper.kampnr")
    kamp: Optional[Kamper] = Relationship(back_populates="kampforekomster")
    lag_id: str = Field(foreign_key="lag.id")
    lag: Optional[Lag] = Relationship(back_populates="kampforekomster")
    ant_maal: int = Field(default=0)
    ant_assist: int = Field(default=0)
    ant_to_min: int = Field(default=0)
    ant_to_p_ti_min: int = Field(default=0)
    ant_kampstraff: int = Field(default=0)
    redninger: int = Field(default=0)
    ant_maal_mot: int = Field(default=0)
    maalvakt: bool = Field(default=False)
    # Huket av for «Spilt» i TA. Data fra tidligere sesonger har ikke dette
    # feltet, og der antas det at alle som står i databasen har spilt.
    spilt: bool = Field(default=True)
    # Klubbnavnet i kolonnen «Klubbtilhørighet» i kamptroppen, slik TA viser det
    # på kampdagen. Samsvarer ikke nødvendigvis med Klubber.navn. NULL for data
    # fra tidligere sesonger, der det ikke ble lagret.
    klubbtilhorighet: Optional[str] = Field(default=None)
