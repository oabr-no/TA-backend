import re
from datetime import datetime
from typing import List

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Page
from playwright.sync_api._generated import Locator

TIMEOUT = 10000
IKKE_SPILLER = ["Støtteapparat"]
KOLONNER_LAG = [
    "Etternavn",
    "Fornavn",
    "Fødselsdato",
    "Rolle",
    "Posisjon/Funksjon",
    "DraktNr",
    "Deltatt",
    "Klubbtilhørighet",
    "Betalt Lisens",
]


class ParseFeil(Exception):
    """Kampsiden hadde ikke forventet struktur, så data kunne ikke leses."""


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


def parse_kamp_resultat(page: Page, kampnr: int) -> dict[str, int]:
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

        resultat: dict[str, int] = {}

        verdi_h: str = rad.locator("td").nth(1).inner_text().strip()
        resultat["hjemme"] = int(verdi_h) if verdi_h.isdigit() else 999

        verdi_b: str = rad.locator("td").nth(2).inner_text().strip()
        resultat["borte"] = int(verdi_b) if verdi_b.isdigit() else 999

        return resultat

    except Exception as e:
        raise ParseFeil(f"Kunne ikke lese resultatet for kamp {kampnr}: {e}") from e


def parse_spilletropp_hjemmelag(page: Page) -> pd.DataFrame:
    spillere_hjemmelag = []

    try:
        page.wait_for_selector(
            "#MatchPlayersBindingContainer > div.panel-body > div:nth-child(1) > div.panel-heading > h4 > a",
            timeout=TIMEOUT,
        )
        page.locator(
            "#MatchPlayersBindingContainer > div.panel-body > div:nth-child(1) > div.panel-heading > h4 > a"
        ).all()[0].click()

        page.wait_for_selector(
            "#collapseHomeTeamIndividuals > div > div > div.table-responsive > table",
            timeout=TIMEOUT,
        )
        html_data_hjemmelag: Locator = page.locator(
            "#collapseHomeTeamIndividuals > div > div > div.table-responsive > table",
            has_text="Etternavn",
        ).first

        soup = BeautifulSoup(html_data_hjemmelag.inner_html(), "html.parser")
        rader = soup.find("tbody").find_all("tr", recursive=False)

        for rad in rader:
            # Hopp over de ekstra radene som inneholder lisenser
            if "noborder" in rad.get("class", []):
                continue

            tds = rad.find_all("td", recursive=False)
            if len(tds) < 13:
                continue

            spiller_info = {
                "Etternavn": tds[1].text.strip(),
                "Fornavn": tds[2].text.strip(),
                "Fødselsdato": tds[3].text.strip(),
                "Rolle": tds[4].text.strip(),
                "Posisjon/Funksjon": tds[5].text.strip(),
                "DraktNr": tds[6].text.strip(),
                "Deltatt": (
                    "Ja" if tds[10].find("span", class_="glyphicon-ok") else "Nei"
                ),
                "Klubbtilhørighet": tds[12].text.strip(),
                "Betalt Lisens": "Ja" if "Ja" in tds[13].text else "Nei",
            }

            spillere_hjemmelag.append(spiller_info)

        df = pd.DataFrame(spillere_hjemmelag, columns=KOLONNER_LAG)

        df["Navn"] = df["Fornavn"] + " " + df["Etternavn"]
        df = df.drop(columns=["Fornavn", "Etternavn"])
        df["Fødselsdato"] = pd.to_datetime(df["Fødselsdato"], format="%d.%m.%Y").dt.date

        nye_kolonner = ["Navn"] + [col for col in df.columns if col != "Navn"]
        df = df[nye_kolonner]

        df_spillere: pd.DataFrame = df[~df["Rolle"].isin(IKKE_SPILLER)]

        return df_spillere

    except Exception as e:
        print(f"En feil oppstod i hjemmelag: {e}")
        return pd.DataFrame()


def parse_spilletropp_bortelag(page: Page) -> pd.DataFrame:
    spillere_bortelag = []

    try:
        page.wait_for_selector(
            "#MatchPlayersBindingContainer > div.panel-body > div:nth-child(2) > div.panel-heading > h4 > a",
            timeout=TIMEOUT,
        )
        page.locator(
            "#MatchPlayersBindingContainer > div.panel-body > div:nth-child(2) > div.panel-heading > h4 > a"
        ).all()[0].click()

        page.wait_for_selector(
            "#collapseAwayTeamIndividuals > div > div > div.table-responsive > table",
            timeout=TIMEOUT,
        )
        html_data_bortelag: Locator = page.locator(
            "#collapseAwayTeamIndividuals > div > div > div.table-responsive > table",
            has_text="Etternavn",
        ).first

        soup = BeautifulSoup(html_data_bortelag.inner_html(), "html.parser")
        rader = soup.find("tbody").find_all("tr", recursive=False)

        for rad in rader:
            # Hopp over de ekstra radene som inneholder lisenser
            if "noborder" in rad.get("class", []):
                continue

            tds = rad.find_all("td", recursive=False)
            if len(tds) < 13:
                continue

            spiller_info: dict[str, str] = {
                "Etternavn": tds[1].text.strip(),
                "Fornavn": tds[2].text.strip(),
                "Fødselsdato": tds[3].text.strip(),
                "Rolle": tds[4].text.strip(),
                "Posisjon/Funksjon": tds[5].text.strip(),
                "DraktNr": tds[6].text.strip(),
                # Sjekker om ikonet for OK/hake finnes i kolonnen
                "Kaptein": (
                    "Ja" if tds[8].find("span", class_="glyphicon-ok") else "Nei"
                ),
                "Deltatt": (
                    "Ja" if tds[10].find("span", class_="glyphicon-ok") else "Nei"
                ),
                "Klubbtilhørighet": tds[12].text.strip(),
                "Betalt Lisens": "Ja" if "Ja" in tds[13].text else "Nei",
            }

            spillere_bortelag.append(spiller_info)

        df = pd.DataFrame(spillere_bortelag, columns=KOLONNER_LAG)

        df["Navn"] = df["Fornavn"] + " " + df["Etternavn"]
        df = df.drop(columns=["Fornavn", "Etternavn"])
        df["Fødselsdato"] = pd.to_datetime(df["Fødselsdato"], format="%d.%m.%Y").dt.date

        nye_kolonner = ["Navn"] + [col for col in df.columns if col != "Navn"]
        df = df[nye_kolonner]

        df_spillere: pd.DataFrame = df[~df["Rolle"].isin(IKKE_SPILLER)]

        return df_spillere

    except Exception as e:
        print(f"En feil oppstod i bortelag: {e}")
        return pd.DataFrame()


def parse_kamphendelser(
    page: Page, hjemmelag_id: str, bortelag_id: str
) -> pd.DataFrame:
    try:
        page.wait_for_selector(
            "#matchIncidentsRootContainer > div > div.panel.panel-default > div.panel-heading > h4 > a",
            timeout=TIMEOUT,
        )
        page.locator(
            "#matchIncidentsRootContainer > div > div.panel.panel-default > div.panel-heading > h4 > a"
        ).all()[0].click()

        page.wait_for_selector(
            "#matchIncidentsContainer > div.table-responsive > table",
            timeout=TIMEOUT,
        )
        html_data_kamphendelser: Locator = page.locator(
            "#matchIncidentsContainer > div.table-responsive > table",
            has_text="Hendelse",
        ).first

        soup = BeautifulSoup(html_data_kamphendelser.inner_html(), "html.parser")
        tbody = soup.find("tbody")

        kamphendelser = []

        gjeldende_hendelse: str = ""
        gjeldende_omgang: str = ""
        gjeldende_tidspunkt: str = ""

        rader = tbody.find_all("tr", recursive=False)

        for rad in rader:
            class_list = rad.get("class", [])
            tds = rad.find_all("td", recursive=False)

            # Sjekk om dette er en hovedhendelse (MainIncident)
            if "active" not in class_list:
                if len(tds) >= 6:
                    gjeldende_hendelse = tds[0].text.strip()
                    gjeldende_omgang = tds[1].text.strip()
                    gjeldende_tidspunkt = tds[2].text.strip()

                    # Noen ganger har hovedhendelsen en aktør direkte (men ofte er det tomt her)
                    aktor: str = tds[5].text.strip()

                    # Hvis hovedhendelsen har en aktør, lagrer vi den som en egen rad
                    if aktor:
                        kamphendelser.append(
                            {
                                "Hendelse": gjeldende_hendelse,
                                "Omgang": gjeldende_omgang,
                                "Tidspunkt": gjeldende_tidspunkt,
                                "Type": tds[3].text.strip() or "Hovedhendelse",
                                "Lag": tds[4].text.strip(),
                                "Aktør": aktor,
                            }
                        )
            else:
                if len(tds) >= 6:
                    kamphendelser.append(
                        {
                            "Hendelse": gjeldende_hendelse,
                            "Omgang": gjeldende_omgang,
                            "Tidspunkt": gjeldende_tidspunkt,
                            "Type": tds[3].text.strip(),
                            "Lag": tds[4].text.strip(),
                            "Aktør": tds[5].text.strip(),
                        }
                    )

        df_kamphendelser = pd.DataFrame(kamphendelser)

        df_kamphendelser[["Nr", "Navn"]] = df_kamphendelser["Aktør"].str.split(
            " - ", n=1, expand=True
        )

        df_kamphendelser: pd.DataFrame = df_kamphendelser.drop(columns=["Aktør"])

        df_kamphendelser["Lag"] = df_kamphendelser["Lag"].replace(
            {"H": hjemmelag_id, "B": bortelag_id}
        )

        return df_kamphendelser

    except Exception as e:
        print(f"En feil oppstod i kamphendelser: {e}")
        return pd.DataFrame()


def sortere_statistikk_utespillere(kamphendelser: pd.DataFrame) -> pd.DataFrame:
    # Lag hjelpekolonner med 0 eller 1 for hver statistikktype
    kamphendelser["Mål"] = np.where(
        kamphendelser["Type"] == "Målscorer",
        1,
        np.nan,
    )
    kamphendelser["Assist"] = np.where(
        kamphendelser["Type"] == "Assist",
        1,
        np.nan,
    )
    kamphendelser["2M utvisning"] = np.where(
        (kamphendelser["Hendelse"] == "2M utvisning")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )
    kamphendelser["2+10M utvisning"] = np.where(
        (kamphendelser["Hendelse"] == "2+10M utvisning")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )
    kamphendelser["Kampstraff"] = np.where(
        (kamphendelser["Hendelse"] == "Kampstraff")
        & (kamphendelser["Type"] == "Bestraffet spiller"),
        1,
        np.nan,
    )

    # Grupper på spillerne (Nr og Navn) og summer opp hendelsene
    utespiller_stat: pd.DataFrame = (
        kamphendelser.groupby(["Nr", "Navn", "Lag"])[
            ["Mål", "Assist", "2M utvisning", "2+10M utvisning", "Kampstraff"]
        ]
        .sum()
        .reset_index()
    )

    # Vi filtrerer ut rader der spilleren ikke har gjort noen av delene (for å unngå keepere her)
    # og sorterer etter flest poeng (mål + assist)
    # utespiller_stat["Poeng"] = utespiller_stat["Mål"] + utespiller_stat["Assist"]
    # utespiller_stat = utespiller_stat[
    #     (utespiller_stat["Poeng"] > 0) | (utespiller_stat["2M utvisning"] > 0)
    # ].sort_values(by="Poeng", ascending=False)

    return utespiller_stat


def sortere_statistikk_keepere(kamphendelser: pd.DataFrame) -> pd.DataFrame:
    # Keepere er registrert som 'Type' == 'Målvakt'
    df_keeper: pd.DataFrame = kamphendelser[kamphendelser["Type"] == "Målvakt"].copy()

    # Et 'Skudd' betyr en redning for målvakten
    df_keeper["Redning"] = np.where(df_keeper["Hendelse"] == "Skudd", 1, np.nan)

    # Et 'Mål' eller 'Straffeslag' (som gikk inn) betyr mål imot
    df_keeper["Innsluppet"] = np.where(
        df_keeper["Hendelse"].isin(["Mål", "Straffeslag"]), 1, np.nan
    )

    # Grupper per målvakt for å telle skudd og redninger
    keeper_stat: pd.DataFrame = (
        df_keeper.groupby(["Nr", "Navn", "Lag"])
        .agg(Redninger=("Redning", "sum"), Innsluppet=("Innsluppet", "sum"))
        .reset_index()
    )

    return keeper_stat


def legg_til_stats_utespillere(
    spillere: pd.DataFrame, stats: pd.DataFrame
) -> pd.DataFrame:
    if "2M utvisning" not in stats:
        stats["2M utvisning"] = np.nan
    if "2+10M utvisning" not in stats:
        stats["2+10M utvisning"] = np.nan
    if "Kampstraff" not in stats:
        stats["Kampstraff"] = np.nan

    spillere["DraktNr"] = pd.to_numeric(spillere["DraktNr"], errors="coerce")
    stats["Nr"] = pd.to_numeric(stats["Nr"], errors="coerce")

    spillere["Navn_clean"] = spillere["Navn"].str.strip().str.lower()
    stats["Navn_clean"] = stats["Navn"].str.strip().str.lower()

    df_sammenslått: pd.DataFrame = pd.merge(
        spillere,
        stats[
            [
                "Nr",
                "Navn_clean",
                "Mål",
                "Assist",
                "2M utvisning",
                "2+10M utvisning",
                "Kampstraff",
            ]
        ],
        left_on=["DraktNr", "Navn_clean"],
        right_on=["Nr", "Navn_clean"],
        how="left",
    )

    df_sammenslått = df_sammenslått.drop(columns=["Nr", "Navn_clean"])

    return df_sammenslått


def legg_til_stats_keepere(spillere: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    if "Redninger" not in stats:
        stats["Redninger"] = np.nan
    if "Innsluppet" not in stats:
        stats["Innsluppet"] = np.nan

    spillere["Målvakt"] = spillere["Posisjon/Funksjon"].str.contains(
        "Målvakt", case=False, na=False
    )

    spillere["DraktNr"] = pd.to_numeric(spillere["DraktNr"], errors="coerce")
    stats["Nr"] = pd.to_numeric(stats["Nr"], errors="coerce")

    spillere["Navn_clean"] = spillere["Navn"].str.strip().str.lower()
    stats["Navn_clean"] = stats["Navn"].str.strip().str.lower()

    df_sammenslått: pd.DataFrame = pd.merge(
        spillere,
        stats[["Nr", "Navn_clean", "Redninger", "Innsluppet"]],
        left_on=["DraktNr", "Navn_clean"],
        right_on=["Nr", "Navn_clean"],
        how="left",
    )

    df_sammenslått = df_sammenslått.drop(columns=["Nr", "Navn_clean"])

    tall_kolonner = [
        "Mål",
        "Assist",
        "2M utvisning",
        "2+10M utvisning",
        "Kampstraff",
        "Redninger",
        "Innsluppet",
    ]
    df_sammenslått[tall_kolonner] = df_sammenslått[tall_kolonner].fillna(0).astype(int)

    # Sørg for at Målvakt-kolonnen er en ren True/False (ikke NaN)
    df_sammenslått["Målvakt"] = df_sammenslått["Målvakt"].fillna(False).astype(bool)

    return df_sammenslått
