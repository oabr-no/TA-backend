from datetime import date
from pathlib import Path

import pytest

from src.parsers.kamp import (
    ParseFeil,
    har_registrert_deltakelse,
    parse_spilletropp_html,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tropp_html() -> str:
    return (FIXTURES / "tropp.html").read_text(encoding="utf-8")


def test_hele_troppen_tas_med_med_spilt_per_spiller(tropp_html: str) -> None:
    tropp = parse_spilletropp_html(tropp_html)

    assert list(tropp["Navn"]) == ["Ola Testesen", "Kari Prøvesen"]
    assert list(tropp["Fornavn"]) == ["Ola", "Kari"]
    assert list(tropp["Etternavn"]) == ["Testesen", "Prøvesen"]
    assert list(tropp["Spilt"]) == [True, False]
    assert tropp["Spilt"].dtype == bool


def test_stotteapparat_og_lisensrader_tas_ikke_med(tropp_html: str) -> None:
    tropp = parse_spilletropp_html(tropp_html)

    assert "Per Lagleder" not in list(tropp["Navn"])
    assert len(tropp) == 2


def test_ovrige_felter_leses(tropp_html: str) -> None:
    ola = parse_spilletropp_html(tropp_html).iloc[0]

    assert ola["Fødselsdato"] == date(2012, 1, 1)
    assert ola["Kaptein"]
    assert ola["Klubbtilhørighet"] == "Fiktiv IBK"
    assert ola["Betalt Lisens"] == "Ja"


def test_spilt_finnes_via_overskriften_ogsa_med_colspan(tropp_html: str) -> None:
    # To tomme overskrifter slått sammen til én med colspan skal ikke forskyve
    # posisjonen til «Spilt».
    html = tropp_html.replace(
        "<th>Ukjent A</th>\n    <th>Kaptein</th>",
        '<th colspan="2">Ukjent A og Kaptein</th>',
    )

    tropp = parse_spilletropp_html(html)

    assert list(tropp["Spilt"]) == [True, False]


def test_mangler_spilt_kolonnen_gir_feil(tropp_html: str) -> None:
    html = tropp_html.replace("<th>Spilt</th>", "<th>Noe annet</th>")

    with pytest.raises(ParseFeil, match="Spilt"):
        parse_spilletropp_html(html)


def test_to_spilt_kolonner_gir_feil(tropp_html: str) -> None:
    html = tropp_html.replace("<th>Ukjent B</th>", "<th>Spilt</th>")

    with pytest.raises(ParseFeil, match="Spilt"):
        parse_spilletropp_html(html)


def test_mangler_overskriftsrad_gir_feil(tropp_html: str) -> None:
    start = tropp_html.index("<thead>")
    slutt = tropp_html.index("</thead>") + len("</thead>")
    html = tropp_html[:start] + tropp_html[slutt:]

    with pytest.raises(ParseFeil, match="overskriftsraden"):
        parse_spilletropp_html(html)


def test_deltakelse_registrert_nar_minst_en_er_huket_av(tropp_html: str) -> None:
    assert har_registrert_deltakelse(parse_spilletropp_html(tropp_html))


def test_ingen_huket_av_gir_ikke_registrert_deltakelse(tropp_html: str) -> None:
    html = tropp_html.replace("glyphicon-ok", "")

    tropp = parse_spilletropp_html(html)

    assert len(tropp) == 2
    assert not har_registrert_deltakelse(tropp)


def test_tom_tropp_gir_ikke_registrert_deltakelse(tropp_html: str) -> None:
    start = tropp_html.index("<tbody>") + len("<tbody>")
    slutt = tropp_html.index("</tbody>")
    html = tropp_html[:start] + tropp_html[slutt:]

    tropp = parse_spilletropp_html(html)

    assert tropp.empty
    assert not har_registrert_deltakelse(tropp)
