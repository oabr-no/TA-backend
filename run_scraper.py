import os
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas import DataFrame
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from src import database
from src.manifest import KampStatus, Manifest

# from src.save_auth import lagre_innlogging
from src.parsers import statistikk
from src.parsers.kamp import ParseFeil, har_registrert_deltakelse
from src.scraper import kampside, skansom
from src.scraper.soke_kamper import KamplisteFeil, hent_kamper_klasse

TIMEOUT = 10000
MANIFEST_MAPPE = Path("data") / "manifest"


def som_dato(fdato: Any) -> date:
    """Fødselsdato fra troppen som date, enten den er tekst (DD.MM.ÅÅÅÅ) eller dato."""
    if isinstance(fdato, str):
        return datetime.strptime(fdato.strip(), "%d.%m.%Y").date()
    return pd.to_datetime(fdato).date()


def main():
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=False)
        user_agent: str = skansom.lag_user_agent(browser)
        manifest = Manifest()

        try:
            if os.path.exists("state.json"):
                context: BrowserContext = browser.new_context(
                    storage_state="state.json", user_agent=user_agent
                )
            else:
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()

                # Gå til innloggingssiden til nettstedet
                page.goto("https://ta.nif.no")

                print("Vennligst logg inn på nettsiden i nettleservinduet.")
                input(
                    "Trykk ENTER i denne terminalen når du er helt ferdig innlogget..."
                )

                # Lagrer cookies og local storage til en JSON-fil
                context.storage_state(path="state.json")
                print("Innloggingsstatus er lagret i state.json!")

                browser.close()
                return  # Avslutter programmet etter lagring av innloggingsstatus

            page: Page = context.new_page()

            if not skansom.er_innlogget(page):
                raise SystemExit(
                    "[FEIL] Innloggingen i state.json er utløpt eller ugyldig. "
                    "Slett state.json og kjør programmet på nytt for å logge inn."
                )

            klasser: list[int] = [
                # -- 2023/2024 --
                # 420058,  # regionscup OK
                # 421558,  # J13 OK
                # 421559,  # J15 OK
                # 421560,  # J17 OK
                # 420491,  # kvinner elite OK
                # 421563,  # kvinner 1. div OK
                # 421564,  # kvinner 2. div OK
                # 421562,  # old girls OK
                # 421609,  # G12 OK
                # 421610,  # G13 OK
                # 421611,  # G14 OK
                # 421614,  # G15 OK
                # 421612,  # G17 OK
                # 421613,  # G18-23 OK
                # 421179,  # menn elite OK
                # 421180,  # menn 1. div OK
                # 421617,  # menn 2. div OK
                # 421618,  # menn 3. div OK
                # 421619,  # menn 4. div OK
                # 421620,  # menn 5. div OK
                # 421615,  # old boys OK
                # 421616,  # veteran OK
                # 422340,  # NM J15 OK
                # 422341,  # NM J17 OK
                # 427885,  # NM kvinner senior OK
                # 422323,  # NM G15 OK
                # 422338,  # NM G17 OK
                # 422339,  # NM G19 OK
                # 427652,  # NM menn senior OK
                # -- 2024/2025 --
                # 428776,  # regionscup jenter/kvinner OK
                # 428752,  # J13 OK
                # 428753,  # J15 Ok
                # 428754,  # J17 OK
                # 428755,  # J18-23 OK
                # 430742,  # kvinner elite OK
                # 428756,  # kvinner 1. og 2. div OK
                # 428757,  # old girls OK
                # 428775,  # regionscup gutter/menn OK
                # 428762,  # G12 OK
                # 428763,  # G13 OK
                # 428764,  # G14 OK
                # 428765,  # G15 OK
                # 428766,  # G17 OK
                # 428767,  # G18-23 OK
                # 430743,  # menn elite OK
                # 430744,  # menn 1. div OK
                # 429978,  # menn 2. div A OK
                # 429979,  # menn 2. div B OK
                # 429980,  # menn 3. div A OK
                # 429981,  # menn 3. div B OK
                # 429982,  # menn 4. div A OK
                # 429983,  # menn 4. div B OK
                # 429984,  # menn 5. div A OK
                # 429985,  # menn 5. div B OK
                # 428770,  # old boys OK
                # 428771,  # veteran OK
                # 430868,  # NM J15 OK
                # 430869,  # NM J17 OK
                # 435960,  # NM kvinner senior OK
                # 430871,  # NM G15 OK
                # 430872,  # NM G17 OK
                # 430873,  # NM G19 OK
                # 435896,  # NM menn senior OK
                # 435959,  # menn senior elitekval OK
                # -- 2025/2026 --
                # 439927,  # regionscup jenter/kvinner OK
                # 439954,  # J12 OK
                # 439955,  # J13 OK
                # 439957,  # J15 OK
                # 439959,  # J17 OK
                # 439960,  # J18-23 OK
                # 439961,  # kvinner senior OK
                # 439962,  # old girls Ok
                # 439926,  # regionscup gutter/menn OK
                # 439940,  # G12 OK
                # 439941,  # G13 OK
                # 439943,  # G15 OK
                # 439945,  # G17 OK
                # 439946,  # G18-23 OK
                # 439947,  # menn senior OK
                # 439948,  # old boys OK
                # 439949,  # veteran OK
                # 440906,  # kvinner elite OK
                # 441677,  # NM J15 OK
                # 441678,  # NM J17 OK
                # 441679,  # NM J19 OK
                # 446378,  # NM kvinner senior OK
                # 448698,  # NM kvinner veteran OK
                # 440904,  # menn elite OK
                # 439964,  # menn 1. div OK
                # 441680,  # NM G15 OK
                # 441681,  # NM G17 OK
                # 441682,  # NM G19 OK
                # 446297,  # NM menn senior OK
                # 448666,  # NM menn veteran OK
            ]

            for klassenr in klasser:
                try:
                    sesong_og_kamper: tuple[str, set[int]] = hent_kamper_klasse(
                        page=page,
                        tournament_id=int(klassenr),
                    )
                except KamplisteFeil as e:
                    print(f"[ADVARSEL] {e}. Hopper over klassen.")
                    manifest.klasse_feilet(klassenr, str(e))
                    continue

                sesong: str = sesong_og_kamper[0]

                with database.transaksjon() as session:
                    sesong_id: int = database.hent_eller_lagre_sesong(session, sesong)

                alle_kampnr: set[int] = sesong_og_kamper[1]

                manifest.klasse_hentet(klassenr, sesong, alle_kampnr)

                for i, kampnr in enumerate(sorted(alle_kampnr), start=1):
                    print(
                        f"[INFO] Henter kamp {i}/{len(alle_kampnr)}: {kampnr} i klasse {klassenr}"
                    )

                    if database.sjekk_om_kamp_finnes(kampnr):
                        manifest.sett_status(klassenr, kampnr, KampStatus.ALLEREDE_LAGRET)
                        continue

                    kamp_url: str = f"https://ta.nif.no/MatchDetails/Overview/{kampnr}"
                    skansom.pause()
                    page.goto(kamp_url, wait_until="domcontentloaded")

                    try:
                        page.wait_for_selector(
                            f"#matchDetailsViewModel_{kampnr}", timeout=TIMEOUT
                        )
                    except Exception:
                        print(
                            f"[ADVARSEL] Fant ikke detaljer-containeren for kamp {kampnr}. Hopper over."
                        )
                        manifest.sett_status(
                            klassenr,
                            kampnr,
                            KampStatus.FEILET,
                            "fant ikke detaljer-containeren på kampsiden",
                        )
                        continue

                    try:
                        # Hente kampinfo

                        kamp_info: dict[Any, Any] = kampside.parse_kamp_info(
                            page, kampnr
                        )

                        if not kamp_info["kamp_er_spilt"]:
                            manifest.sett_status(
                                klassenr, kampnr, KampStatus.IKKE_SPILT_ENNA
                            )
                            continue

                        # Hente resultat

                        resultat: dict[str, int | None] = kampside.parse_kamp_resultat(
                            page, kampnr
                        )

                        # Hente troppene før noe lagres, så kampen ikke blir halvveis lagret

                        spillere_hjemmelag: DataFrame = (
                            kampside.parse_spilletropp_hjemmelag(page)
                        )
                        spillere_bortelag: DataFrame = (
                            kampside.parse_spilletropp_bortelag(page)
                        )

                        kamphendelser: DataFrame = kampside.parse_kamphendelser(
                            page, kamp_info["hjemmelag_id"], kamp_info["bortelag_id"]
                        )
                    except ParseFeil as e:
                        print(f"[ADVARSEL] {e}. Hopper over.")
                        manifest.sett_status(klassenr, kampnr, KampStatus.FEILET, str(e))
                        continue

                    # Uten kamphendelser regnes kampen som ikke spilt, også om spillere
                    # er huket av for «Spilt». Den lagres ikke, så den hentes på nytt
                    # ved neste kjøring (f.eks. hvis den er utsatt).

                    if kamphendelser.empty:
                        print(
                            f"[INFO] Kamp {kampnr} har ingen kamphendelser og regnes "
                            "som ikke spilt. Hopper over."
                        )
                        manifest.sett_status(klassenr, kampnr, KampStatus.INGEN_HENDELSER)
                        continue

                    # Bare spillere som er huket av for «Spilt» har deltatt. Er ingen
                    # huket av, er registreringen trolig ufullstendig. Kampen lagres
                    # da ikke, så den hentes på nytt ved neste kjøring.

                    lag_uten_deltakelse: list[str] = [
                        lag
                        for lag, tropp in (
                            ("hjemmelaget", spillere_hjemmelag),
                            ("bortelaget", spillere_bortelag),
                        )
                        if not har_registrert_deltakelse(tropp)
                    ]

                    if lag_uten_deltakelse:
                        print(
                            f"[ADVARSEL] Ingen spillere er huket av for «Spilt» på "
                            f"{' og '.join(lag_uten_deltakelse)} i kamp {kampnr}. Hopper over."
                        )
                        manifest.sett_status(
                            klassenr,
                            kampnr,
                            KampStatus.INGEN_SPILT,
                            f"gjelder {' og '.join(lag_uten_deltakelse)}",
                        )
                        continue

                    # Beregne statistikk før noe lagres. Lag-ID-ene er kjent fra
                    # kampinfo, så bare spiller-ID-ene trenger databasen.

                    try:
                        spillere_hjemmelag["lag_id"] = kamp_info["hjemmelag_id"]
                        spillere_bortelag["lag_id"] = kamp_info["bortelag_id"]

                        alle_spillere: DataFrame = pd.concat(
                            [spillere_hjemmelag, spillere_bortelag], ignore_index=True
                        )

                        stats_utespillere: DataFrame = (
                            statistikk.sortere_statistikk_utespillere(kamphendelser)
                        )
                        stats_keepere: DataFrame = (
                            statistikk.sortere_statistikk_keepere(kamphendelser)
                        )

                        utespillere_med_stats_keepere_uten: DataFrame = (
                            statistikk.legg_til_stats_utespillere(
                                alle_spillere, stats_utespillere
                            )
                        )
                        kampforekomster: DataFrame = statistikk.legg_til_stats_keepere(
                            utespillere_med_stats_keepere_uten, stats_keepere
                        )
                    except Exception as e:
                        print(
                            f"[ADVARSEL] Kunne ikke beregne statistikk for kamp {kampnr}: {e}. Hopper over."
                        )
                        manifest.sett_status(
                            klassenr, kampnr, KampStatus.FEILET, f"statistikk: {e}"
                        )
                        continue

                    # Lagre hele kampen i én transaksjon. Feiler noe underveis, rulles
                    # alt tilbake, og kampen hentes på nytt ved neste kjøring.

                    try:
                        with database.transaksjon() as session:
                            klasse_id: int = database.hent_eller_lagre_klasse(
                                session, kamp_info["klasse"]
                            )

                            hjemmelag: str = database.hent_eller_lagre_klubb_og_lag(
                                session,
                                kamp_info["hjemmeklubb_id"],
                                kamp_info["hjemmeklubb_navn"],
                                kamp_info["hjemmelag_id"],
                                kamp_info["hjemmelag_navn"],
                            )
                            bortelag: str = database.hent_eller_lagre_klubb_og_lag(
                                session,
                                kamp_info["borteklubb_id"],
                                kamp_info["borteklubb_navn"],
                                kamp_info["bortelag_id"],
                                kamp_info["bortelag_navn"],
                            )

                            kampnr_id: int = database.hent_eller_lagre_kamp(
                                session,
                                kampnr,
                                klasse_id,
                                hjemmelag,
                                bortelag,
                                kamp_info["tidspunkt"],
                                sesong_id,
                                resultat["hjemme"],
                                resultat["borte"],
                            )

                            for _, rad in kampforekomster.iterrows():
                                spiller_id: str = database.hent_eller_lagre_spiller(
                                    session,
                                    rad["Navn"].strip(),
                                    som_dato(rad["Fødselsdato"]),
                                    fornavn=rad["Fornavn"],
                                    etternavn=rad["Etternavn"],
                                )
                                database.hent_eller_lagre_kampforekomst(
                                    session,
                                    {**rad.to_dict(), "spiller_id": spiller_id, "kamp_id": kampnr_id},
                                )
                    except Exception as e:
                        print(
                            f"[ADVARSEL] Kunne ikke lagre kamp {kampnr}: {e}. Ingenting er lagret. Hopper over."
                        )
                        manifest.sett_status(
                            klassenr, kampnr, KampStatus.FEILET, f"lagring: {e}"
                        )
                        continue

                    manifest.sett_status(klassenr, kampnr, KampStatus.LAGRET)

        except Exception as e:
            print(f"[RUN_SCRAPER-FEIL] Noe gikk galt i hovedloopen: {e}")
            traceback.print_exc()

        finally:
            # Lagres også når kjøringen stopper underveis, så det synes hva som mangler
            if manifest.klasser:
                for linje in manifest.oppsummering():
                    print(f"[OPPSUMMERING] {linje}")

                mangler = manifest.kontroller()
                if mangler:
                    print(
                        f"[FEIL] {len(mangler)} kamper i kamplistene ble ikke behandlet. "
                        "Kjøringen er ufullstendig."
                    )

                fil = manifest.lagre(MANIFEST_MAPPE)
                print(f"[OPPSUMMERING] Manifest lagret i {fil}")
            browser.close()


if __name__ == "__main__":
    main()
