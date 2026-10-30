import json
from datetime import datetime
from pathlib import Path

import pytest

from src.manifest import KampStatus, Manifest


def lag_manifest() -> Manifest:
    manifest = Manifest(startet=datetime(2026, 10, 30, 12, 0, 0))
    manifest.klasse_hentet(100, "2026/2027", {3, 1, 2})
    manifest.klasse_feilet(200, "tidsavbrudd")
    return manifest


def test_kamper_uten_status_meldes() -> None:
    manifest = lag_manifest()
    manifest.sett_status(100, 1, KampStatus.LAGRET)

    mangler = manifest.kontroller()

    assert mangler == [
        "Kamp 2 i klasse 100 ble ikke behandlet",
        "Kamp 3 i klasse 100 ble ikke behandlet",
    ]


def test_alle_kamper_med_status_gir_ingen_mangler() -> None:
    manifest = lag_manifest()
    manifest.sett_status(100, 1, KampStatus.LAGRET)
    manifest.sett_status(100, 2, KampStatus.INGEN_HENDELSER)
    manifest.sett_status(100, 3, KampStatus.FEILET, "fant ikke tabellen")

    assert manifest.kontroller() == []


def test_status_for_kamp_utenfor_kamplisten_gir_feil() -> None:
    manifest = lag_manifest()

    with pytest.raises(KeyError):
        manifest.sett_status(100, 99, KampStatus.LAGRET)


def test_oppsummering_teller_per_status_og_feilede_klasser() -> None:
    manifest = lag_manifest()
    manifest.sett_status(100, 1, KampStatus.LAGRET)
    manifest.sett_status(100, 2, KampStatus.LAGRET)

    linjer = manifest.oppsummering()

    assert linjer[0] == "3 kamper i kamplistene for 2 klasser"
    assert "  lagret: 2" in linjer
    assert "  IKKE BEHANDLET: 1" in linjer
    assert "1 klasser kunne ikke leses: [200]" in linjer


def test_lagre_skriver_json_med_status_og_aarsak(tmp_path: Path) -> None:
    manifest = lag_manifest()
    manifest.sett_status(100, 1, KampStatus.FEILET, "fant ikke tabellen")

    fil = manifest.lagre(tmp_path / "manifest")

    assert fil.name == "2026-10-30T12-00-00.json"
    data = json.loads(fil.read_text(encoding="utf-8"))
    assert data["klasser"]["100"]["kamper"]["1"] == {
        "status": "feilet",
        "aarsak": "fant ikke tabellen",
    }
    assert data["klasser"]["100"]["kamper"]["2"]["status"] is None
    assert data["klasser"]["200"]["feilet"] == "tidsavbrudd"
    assert len(data["mangler_status"]) == 2
