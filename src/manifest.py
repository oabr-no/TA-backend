"""Oversikt over hva en skrapekjøring gjorde med hver klasse og kamp.

Hver kamp i kamplistene skal ende med nøyaktig én status. Kamper som står uten
status når kjøringen er ferdig, ble aldri behandlet (f.eks. fordi kjøringen
stoppet), og meldes av kontroller().

Manifestet inneholder bare klasse- og kampnumre, ingen personopplysninger.
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class KampStatus(StrEnum):
    LAGRET = "lagret"
    ALLEREDE_LAGRET = "allerede lagret"
    IKKE_SPILT_ENNA = "kamptidspunktet er ikke passert"
    INGEN_HENDELSER = "ingen kamphendelser (regnes som ikke spilt)"
    INGEN_SPILT = "ingen spillere huket av for «Spilt»"
    FEILET = "feilet"


@dataclass
class KampResultat:
    status: KampStatus | None = None
    aarsak: str | None = None


@dataclass
class KlasseResultat:
    feilet: str | None = None
    sesong: str | None = None
    kamper: dict[int, KampResultat] = field(default_factory=dict)


@dataclass
class Manifest:
    startet: datetime = field(default_factory=datetime.now)
    klasser: dict[int, KlasseResultat] = field(default_factory=dict)

    def klasse_feilet(self, klassenr: int, aarsak: str) -> None:
        self.klasser[klassenr] = KlasseResultat(feilet=aarsak)

    def klasse_hentet(self, klassenr: int, sesong: str, kampnr: set[int]) -> None:
        """Registrerer alle kampene i klassen. De står uten status til de er behandlet."""
        self.klasser[klassenr] = KlasseResultat(
            sesong=sesong, kamper={nr: KampResultat() for nr in sorted(kampnr)}
        )

    def sett_status(
        self, klassenr: int, kampnr: int, status: KampStatus, aarsak: str | None = None
    ) -> None:
        kamper = self.klasser[klassenr].kamper
        if kampnr not in kamper:
            raise KeyError(f"Kamp {kampnr} står ikke i kamplisten for klasse {klassenr}")
        kamper[kampnr] = KampResultat(status=status, aarsak=aarsak)

    def kontroller(self) -> list[str]:
        """Returnerer en melding for hver kamp som står uten status."""
        return [
            f"Kamp {kampnr} i klasse {klassenr} ble ikke behandlet"
            for klassenr, klasse in self.klasser.items()
            for kampnr, kamp in klasse.kamper.items()
            if kamp.status is None
        ]

    def oppsummering(self) -> list[str]:
        """Linjer som viser hvor mye av kamplistene som er dekket."""
        kamper = [k for klasse in self.klasser.values() for k in klasse.kamper.values()]
        antall = Counter(k.status for k in kamper)
        feilede_klasser = [nr for nr, k in self.klasser.items() if k.feilet]

        linjer = [f"{len(kamper)} kamper i kamplistene for {len(self.klasser)} klasser"]
        linjer += [f"  {status}: {antall[status]}" for status in KampStatus if antall[status]]
        if antall[None]:
            linjer.append(f"  IKKE BEHANDLET: {antall[None]}")
        if feilede_klasser:
            linjer.append(
                f"{len(feilede_klasser)} klasser kunne ikke leses: {feilede_klasser}"
            )
        return linjer

    def lagre(self, mappe: Path) -> Path:
        """Lagrer manifestet som JSON i `mappe` med tidsstempel i filnavnet."""
        mappe.mkdir(parents=True, exist_ok=True)
        fil = mappe / f"{self.startet.strftime('%Y-%m-%dT%H-%M-%S')}.json"

        data = {
            "startet": self.startet.isoformat(timespec="seconds"),
            "avsluttet": datetime.now().isoformat(timespec="seconds"),
            "mangler_status": self.kontroller(),
            "klasser": {
                str(klassenr): {
                    "sesong": klasse.sesong,
                    "feilet": klasse.feilet,
                    "kamper": {
                        str(kampnr): {
                            "status": kamp.status.value if kamp.status else None,
                            "aarsak": kamp.aarsak,
                        }
                        for kampnr, kamp in klasse.kamper.items()
                    },
                }
                for klassenr, klasse in self.klasser.items()
            },
        }

        fil.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return fil
