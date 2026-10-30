"""Åpner kampsiden i TA med Playwright og henter ut innholdet. Bare lesing.

Selve tolkningen av tabellene ligger i src.parsers.kamp.
"""

import re
from datetime import datetime
from typing import List

import pandas as pd
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api._generated import Locator

from src.parsers.kamp import (
    KOLONNER_KAMPHENDELSER,
    ParseFeil,
    parse_kamphendelser_html,
    parse_spilletropp_html,
)


TIMEOUT = 10000


def parse_kamp_info(page: Page, kampnr: int) -> dict:
    try:
        page.wait_for_selector(
            f"#matchDetailsViewModel_{kampnr} > div.panel.panel-nif > div.panel-body > div.row > div > div.row",
            timeout=TIMEOUT,
        )
        rader: List[Locator] = page.locator(
            f"#matchDetailsViewModel_{kampnr} > div.panel.panel-nif > div.panel-body > div.row > div > div.row"
        ).all()

        kampdetaljer = {}

        for rad in rader:
            nokkel: str = rad.locator("div").nth(0).inner_text().strip()
            verdi: str = rad.locator("div").nth(1).inner_text().strip()

            kampdetaljer[nokkel] = verdi

        lag_pattern = r"(.*?)\*?\s*\((.*?)\)"
        hjemmelag_tekst: str = kampdetaljer.get("Hjemmelag", None)
        hjemmelag_match: re.Match[str] = re.search(lag_pattern, hjemmelag_tekst)
        bortelag_tekst: str = kampdetaljer.get("Bortelag", None)
        bortelag_match: re.Match[str] = re.search(lag_pattern, bortelag_tekst)

        klasse: str = kampdetaljer.get("Turnering", None)
        hjemmelag_id: str = hjemmelag_match.group(2).strip()
        hjemmelag_navn: str = hjemmelag_match.group(1).strip()
        hjemmeklubb_id: str = hjemmelag_id[:10].replace("LA", "KL", 1)
        hjemmeklubb_navn: str = re.sub(r"\s+\d+$", "", hjemmelag_navn).strip()
        bortelag_id: str = bortelag_match.group(2).strip()
        bortelag_navn: str = bortelag_match.group(1).strip()
        borteklubb_id: str = bortelag_id[:10].replace("LA", "KL", 1)
        borteklubb_navn: str = re.sub(r"\s+\d+$", "", bortelag_navn).strip()
        kamptidspunkt: str = kampdetaljer.get("Tid", None)

        kamptidspunkt_datetime: datetime | None = None
        if kamptidspunkt and kamptidspunkt.strip():
            try:
                kamptidspunkt_datetime = datetime.strptime(
                    kamptidspunkt.strip(), "%d.%m.%Y %H:%M"
                )
            except ValueError:
                kamptidspunkt_datetime = None

        if kamptidspunkt_datetime is not None:
            kamp_er_spilt: bool = kamptidspunkt_datetime < datetime.now()
        else:
            kamp_er_spilt = False

        return {
            "kampnr": kampnr,
            "klasse": klasse,
            "hjemmeklubb_id": hjemmeklubb_id,
            "hjemmeklubb_navn": hjemmeklubb_navn,
            "hjemmelag_navn": hjemmelag_navn,
            "hjemmelag_id": hjemmelag_id,
            "borteklubb_id": borteklubb_id,
            "borteklubb_navn": borteklubb_navn,
            "bortelag_navn": bortelag_navn,
            "bortelag_id": bortelag_id,
            "tidspunkt": kamptidspunkt_datetime,
            "kamp_er_spilt": kamp_er_spilt,
        }

    except Exception as e:
        raise ParseFeil(f"Kunne ikke lese kampdetaljene for kamp {kampnr}: {e}") from e


def parse_kamp_resultat(page: Page, kampnr: int) -> dict[str, int | None]:
    """Antall mål for hjemme- og bortelaget. None når resultatet ikke er registrert."""
    try:
        page.wait_for_selector(
            f"#resultRegistrationContainer_{kampnr} > div > div:nth-child(3) > div.panel-heading > h4 > a",
            timeout=TIMEOUT,
        )
        page.locator(
            f"#resultRegistrationContainer_{kampnr} > div > div:nth-child(3) > div.panel-heading > h4 > a",
        ).click()

        page.wait_for_selector(
            "#collapseEndResults > div > div.table-responsive > table",
            timeout=TIMEOUT,
        )
        rad: Locator = page.locator(
            "#collapseEndResults > div > div.table-responsive > table > tbody > tr"
        ).nth(1)

        resultat: dict[str, int | None] = {}

        verdi_h: str = rad.locator("td").nth(1).inner_text().strip()
        resultat["hjemme"] = int(verdi_h) if verdi_h.isdigit() else None

        verdi_b: str = rad.locator("td").nth(2).inner_text().strip()
        resultat["borte"] = int(verdi_b) if verdi_b.isdigit() else None

        return resultat

    except Exception as e:
        raise ParseFeil(f"Kunne ikke lese resultatet for kamp {kampnr}: {e}") from e


def parse_spilletropp_hjemmelag(page: Page) -> pd.DataFrame:
    return _hent_spilletropp(
        page, panel_nr=1, container="#collapseHomeTeamIndividuals", lag="hjemmelaget"
    )


def parse_spilletropp_bortelag(page: Page) -> pd.DataFrame:
    return _hent_spilletropp(
        page, panel_nr=2, container="#collapseAwayTeamIndividuals", lag="bortelaget"
    )


def _hent_spilletropp(page: Page, panel_nr: int, container: str, lag: str) -> pd.DataFrame:
    """Åpner troppen i kampsiden og sender tabellen videre til parse_spilletropp_html."""
    panel_lenke = f"#MatchPlayersBindingContainer > div.panel-body > div:nth-child({panel_nr}) > div.panel-heading > h4 > a"
    tabell_selector = f"{container} > div > div > div.table-responsive > table"

    try:
        page.wait_for_selector(panel_lenke, timeout=TIMEOUT)
        page.locator(panel_lenke).all()[0].click()

        page.wait_for_selector(tabell_selector, timeout=TIMEOUT)
        tabell_html: str = (
            page.locator(tabell_selector, has_text="Etternavn").first.inner_html()
        )
    except Exception as e:
        raise ParseFeil(f"Kunne ikke åpne troppen til {lag}: {e}") from e

    return parse_spilletropp_html(tabell_html, lag)


def parse_kamphendelser(
    page: Page, hjemmelag_id: str, bortelag_id: str
) -> pd.DataFrame:
    """Henter kamphendelsene. En tom DataFrame betyr at kampen ikke har hendelser."""
    panel_lenke = "#matchIncidentsRootContainer > div > div.panel.panel-default > div.panel-heading > h4 > a"
    tabell_selector = "#matchIncidentsContainer > div.table-responsive > table"

    try:
        page.wait_for_selector(panel_lenke, timeout=TIMEOUT)
        page.locator(panel_lenke).all()[0].click()

        try:
            page.wait_for_selector(tabell_selector, timeout=TIMEOUT)
        except PlaywrightTimeoutError:
            # Panelet er åpnet, men har ingen tabell: kampen har ingen hendelser
            if page.locator("#matchIncidentsContainer").count() > 0:
                return pd.DataFrame(columns=KOLONNER_KAMPHENDELSER)
            raise

        tabell_html: str = (
            page.locator(tabell_selector, has_text="Hendelse").first.inner_html()
        )
    except Exception as e:
        raise ParseFeil(f"Kunne ikke åpne kamphendelsene: {e}") from e

    return parse_kamphendelser_html(tabell_html, hjemmelag_id, bortelag_id)
