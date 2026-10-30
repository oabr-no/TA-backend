from pathlib import Path

import pytest

from src.parsers.kamp import ParseFeil, parse_kamphendelser_html

FIXTURES = Path(__file__).parent / "fixtures"
HJEMMELAG = "LA-HJEMME"
BORTELAG = "LA-BORTE"


@pytest.fixture
def hendelser_html() -> str:
    return (FIXTURES / "kamphendelser.html").read_text(encoding="utf-8")


def test_hendelser_leses_med_aktor_og_lag(hendelser_html: str) -> None:
    hendelser = parse_kamphendelser_html(hendelser_html, HJEMMELAG, BORTELAG)

    assert list(hendelser["Hendelse"]) == ["Mål", "Mål", "2M utvisning"]
    assert list(hendelser["Type"]) == ["Målscorer", "Målvakt", "Bestraffet spiller"]
    assert list(hendelser["Nr"]) == ["7", "1", "9"]
    assert list(hendelser["Navn"]) == ["Ola Testesen", "Kari Prøvesen", "Nils Fiktivsen"]
    assert list(hendelser["Lag"]) == [HJEMMELAG, BORTELAG, BORTELAG]


def test_tom_tabell_gir_tom_dataframe(hendelser_html: str) -> None:
    start = hendelser_html.index("<tbody>") + len("<tbody>")
    slutt = hendelser_html.index("</tbody>")
    html = hendelser_html[:start] + hendelser_html[slutt:]

    hendelser = parse_kamphendelser_html(html, HJEMMELAG, BORTELAG)

    assert hendelser.empty
    assert "Navn" in hendelser.columns


def test_aktor_uten_skilletegn_gir_ikke_feil(hendelser_html: str) -> None:
    html = hendelser_html.replace(" - ", " ")

    hendelser = parse_kamphendelser_html(html, HJEMMELAG, BORTELAG)

    assert len(hendelser) == 3
    assert hendelser["Navn"].isna().all()


def test_mangler_tabellinnhold_gir_feil() -> None:
    with pytest.raises(ParseFeil, match="tbody"):
        parse_kamphendelser_html("<thead></thead>", HJEMMELAG, BORTELAG)
