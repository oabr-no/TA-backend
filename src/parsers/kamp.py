"""Tolker HTML fra kampsiden i TA. Ingen nettverkskall og ingen nettleser."""

import pandas as pd
from bs4 import BeautifulSoup


IKKE_SPILLER = ["Støtteapparat"]
KOLONNER_LAG = [
    "Etternavn",
    "Fornavn",
    "Fødselsdato",
    "Rolle",
    "Posisjon/Funksjon",
    "DraktNr",
    "Kaptein",
    "Spilt",
    "Klubbtilhørighet",
    "Betalt Lisens",
]


class ParseFeil(Exception):
    """Kampsiden hadde ikke forventet struktur, så data kunne ikke leses."""

def parse_spilletropp_html(tabell_html: str, lag: str = "laget") -> pd.DataFrame:
    """Gjør tropptabellen om til en DataFrame med én rad per spiller.

    Hele troppen tas med. Kolonnen «Spilt» er True for spillere som er huket av
    for «Spilt» i TA, og det er bare de som regnes som å ha deltatt i kampen.
    """
    try:
        soup = BeautifulSoup(tabell_html, "html.parser")
        spilt_kolonne: int = _finn_kolonne(soup, "Spilt")

        tbody = soup.find("tbody")
        if tbody is None:
            raise ParseFeil("fant ikke tabellinnholdet (tbody)")

        spillere = []

        for rad in tbody.find_all("tr", recursive=False):
            # Hopp over de ekstra radene som inneholder lisenser
            if "noborder" in rad.get("class", []):
                continue

            tds = rad.find_all("td", recursive=False)
            if len(tds) < 14:
                continue

            spiller_info = {
                "Etternavn": tds[1].text.strip(),
                "Fornavn": tds[2].text.strip(),
                "Fødselsdato": tds[3].text.strip(),
                "Rolle": tds[4].text.strip(),
                "Posisjon/Funksjon": tds[5].text.strip(),
                "DraktNr": tds[6].text.strip(),
                # Sjekker om ikonet for OK/hake finnes i kolonnen
                "Kaptein": tds[8].find("span", class_="glyphicon-ok") is not None,
                "Spilt": tds[spilt_kolonne].find("span", class_="glyphicon-ok")
                is not None,
                "Klubbtilhørighet": tds[12].text.strip(),
                "Betalt Lisens": "Ja" if "Ja" in tds[13].text else "Nei",
            }

            spillere.append(spiller_info)

        df = pd.DataFrame(spillere, columns=KOLONNER_LAG)

        # Navn er spilleridentiteten (sammen med fødselsdato). Fornavn og
        # etternavn beholdes også, til koblingen mot dobbel representasjon.
        df["Navn"] = df["Fornavn"] + " " + df["Etternavn"]
        df["Fødselsdato"] = pd.to_datetime(df["Fødselsdato"], format="%d.%m.%Y").dt.date
        df["Spilt"] = df["Spilt"].astype(bool)
        df["Kaptein"] = df["Kaptein"].astype(bool)

        nye_kolonner = ["Navn"] + [col for col in df.columns if col != "Navn"]
        df = df[nye_kolonner]

        df_spillere: pd.DataFrame = df[~df["Rolle"].isin(IKKE_SPILLER)]

        return df_spillere

    except Exception as e:
        raise ParseFeil(f"Kunne ikke lese troppen til {lag}: {e}") from e


def _finn_kolonne(soup: BeautifulSoup, navn: str) -> int:
    """Finner posisjonen til kolonnen med overskriften `navn` i første overskriftsrad."""
    thead = soup.find("thead")
    overskriftsrad = thead.find("tr") if thead else None
    if overskriftsrad is None:
        raise ParseFeil("fant ikke overskriftsraden i tabellen")

    overskrifter: list[str] = []
    treff: list[int] = []
    posisjon = 0

    for celle in overskriftsrad.find_all(["th", "td"], recursive=False):
        tekst: str = celle.get_text(strip=True)
        overskrifter.append(tekst)
        if tekst.lower() == navn.lower():
            treff.append(posisjon)
        posisjon += int(celle.get("colspan", 1))

    if len(treff) != 1:
        raise ParseFeil(
            f"fant ikke nøyaktig én kolonne «{navn}». Overskriftene er {overskrifter}"
        )

    return treff[0]


def har_registrert_deltakelse(tropp: pd.DataFrame) -> bool:
    """True hvis minst én spiller i troppen er huket av for «Spilt»."""
    return not tropp.empty and bool(tropp["Spilt"].any())


KOLONNER_KAMPHENDELSER = ["Hendelse", "Omgang", "Tidspunkt", "Type", "Lag", "Nr", "Navn"]


def parse_kamphendelser_html(
    tabell_html: str, hjemmelag_id: str, bortelag_id: str
) -> pd.DataFrame:
    """Gjør hendelsestabellen om til en DataFrame. Tom tabell gir tom DataFrame."""
    try:
        soup = BeautifulSoup(tabell_html, "html.parser")
        tbody = soup.find("tbody")
        if tbody is None:
            raise ParseFeil("fant ikke tabellinnholdet (tbody)")

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

        if not kamphendelser:
            return pd.DataFrame(columns=KOLONNER_KAMPHENDELSER)

        df_kamphendelser = pd.DataFrame(kamphendelser)

        # reindex sikrer to kolonner også når ingen aktør inneholder « - »
        df_kamphendelser[["Nr", "Navn"]] = (
            df_kamphendelser["Aktør"]
            .str.split(" - ", n=1, expand=True)
            .reindex(columns=[0, 1])
        )

        df_kamphendelser: pd.DataFrame = df_kamphendelser.drop(columns=["Aktør"])

        df_kamphendelser["Lag"] = df_kamphendelser["Lag"].replace(
            {"H": hjemmelag_id, "B": bortelag_id}
        )

        return df_kamphendelser

    except Exception as e:
        raise ParseFeil(f"Kunne ikke lese kamphendelsene: {e}") from e
