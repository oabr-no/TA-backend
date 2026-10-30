import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class KjonnEnum(str, Enum):
    mann = "m"
    kvinne = "k"
    ukjent = "u"


class Sesonger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    navn: str = Field(unique=True)
    base_aar: int
    kamper: list[Kamper] = Relationship(back_populates="sesong")


class Klasser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    navn: str
    kjonn: KjonnEnum
    alder: int | None
    kamper: list[Kamper] = Relationship(back_populates="klasse")


class Klubber(SQLModel, table=True):
    id: str = Field(primary_key=True)
    navn: str = Field(unique=True)
    lag: list[Lag] = Relationship(back_populates="klubb")


class Lag(SQLModel, table=True):
    id: str = Field(primary_key=True)
    navn: str
    klubb_id: str = Field(foreign_key="klubber.id")
    klubb: Optional[Klubber] = Relationship(back_populates="lag")
    kamper: list[Kamper] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "or_(Lag.id==Kamper.hjemmelag_id, Lag.id==Kamper.bortelag_id)",
            "viewonly": True,  # Viktig! Siden den er sammensatt, må den være skrivebeskyttet.
        }
    )
    kampforekomster: list[Kampforekomster] = Relationship(back_populates="lag")


class Spillere(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("navn", "fdato", name="unique_navn_fdato"),)

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True
    )
    navn: str
    fdato: date
    kampforekomster: list[Kampforekomster] = Relationship(back_populates="spiller")


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
    tidspunkt: Optional[datetime] = Field(default=None)
    sesong_id: int = Field(foreign_key="sesonger.id")
    sesong: Optional[Sesonger] = Relationship(back_populates="kamper")
    kampforekomster: list[Kampforekomster] = Relationship(back_populates="kamp")
    ant_maal_hjemmelag: int
    ant_maal_bortelag: int


class Kampforekomster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spiller_id: int = Field(foreign_key="spillere.id")
    spiller: Optional[Spillere] = Relationship(back_populates="kampforekomster")
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
