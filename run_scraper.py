import os
from datetime import datetime
from typing import Any

import pandas as pd
from pandas import DataFrame
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from backend.src import database

# from src.save_auth import lagre_innlogging
from backend.src.scraper import kamp_parser
from backend.src.scraper.soke_kamper import hent_kamper_klasse

TIMEOUT = 10000


def main():
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=False)
        feilede_kamper: list[int] = []

        try:
            if os.path.exists("state.json"):
                context: BrowserContext = browser.new_context(
                    storage_state="state.json"
                )
            else:
                context = browser.new_context()
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
                sesong_og_kamper: tuple[str, set[int]] = hent_kamper_klasse(
                    page=page,
                    tournament_id=int(klassenr),
                )

                sesong: str = sesong_og_kamper[0]

                sesong_id: int = database.hent_eller_lagre_sesong(sesong)

                alle_kampnr: set[int] = sesong_og_kamper[1]

                for i, kampnr in enumerate(alle_kampnr, start=1):
                    print(
                        f"[INFO] Henter kamp {i}/{len(alle_kampnr)}: {kampnr} i klasse {klassenr}"
                    )

                    if database.sjekk_om_kamp_finnes(kampnr):
                        continue

                    kamp_url: str = f"https://ta.nif.no/MatchDetails/Overview/{kampnr}"
                    page.goto(kamp_url, wait_until="domcontentloaded")

                    try:
                        page.wait_for_selector(
                            f"#matchDetailsViewModel_{kampnr}", timeout=TIMEOUT
                        )
                    except Exception:
                        print(
                            f"[ADVARSEL] Fant ikke detaljer-containeren for kamp {kampnr}. Hopper over."
                        )
                        continue

                    try:
                        # Hente kampinfo

                        kamp_info: dict[Any, Any] = kamp_parser.parse_kamp_info(
                            page, kampnr
                        )

                        if not kamp_info["kamp_er_spilt"]:
                            continue

                        # Hente resultat

                        resultat: dict[str, int] = kamp_parser.parse_kamp_resultat(
                            page, kampnr
                        )
                    except kamp_parser.ParseFeil as e:
                        print(f"[ADVARSEL] {e}. Hopper over.")
                        feilede_kamper.append(kampnr)
                        continue

                    # Lagre klasse

                    klasse_navn: str = kamp_info["klasse"]

                    klasse_id: int = database.hent_eller_lagre_klasse(klasse_navn)

                    # Lagre klubber og lag

                    hjemmelag: str = database.hent_eller_lagre_klubb_og_lag(
                        kamp_info["hjemmeklubb_id"],
                        kamp_info["hjemmeklubb_navn"],
                        kamp_info["hjemmelag_id"],
                        kamp_info["hjemmelag_navn"],
                    )

                    bortelag: str = database.hent_eller_lagre_klubb_og_lag(
                        kamp_info["borteklubb_id"],
                        kamp_info["borteklubb_navn"],
                        kamp_info["bortelag_id"],
                        kamp_info["bortelag_navn"],
                    )

                    kampnr_id: int = database.hent_eller_lagre_kamp(
                        kampnr,
                        klasse_id,
                        hjemmelag,
                        bortelag,
                        kamp_info["tidspunkt"],
                        sesong_id,
                        resultat["hjemme"],
                        resultat["borte"],
                    )

                    # Hente hjemmelag

                    spillere_hjemmelag: DataFrame = (
                        kamp_parser.parse_spilletropp_hjemmelag(page)
                    )

                    if spillere_hjemmelag.empty:
                        continue

                    sp_hj_ids = []

                    for navn, fdato in zip(
                        spillere_hjemmelag["Navn"],
                        spillere_hjemmelag["Fødselsdato"],
                    ):
                        if isinstance(fdato, str):
                            ekte_dato = datetime.strptime(
                                fdato.strip(), "%d.%m.%Y"
                            ).date()
                        else:
                            ekte_dato = pd.to_datetime(fdato).date()

                        spiller_id = database.hent_eller_lagre_spiller(
                            navn.strip(),
                            ekte_dato,
                        )

                        sp_hj_ids.append(spiller_id)

                    spillere_hjemmelag["spiller_id"] = sp_hj_ids
                    spillere_hjemmelag["kamp_id"] = kampnr_id
                    spillere_hjemmelag["lag_id"] = hjemmelag

                    # Hente bortelag

                    spillere_bortelag: DataFrame = (
                        kamp_parser.parse_spilletropp_bortelag(page)
                    )

                    if spillere_bortelag.empty:
                        continue

                    sp_bo_ids = []

                    for navn, fdato in zip(
                        spillere_bortelag["Navn"],
                        spillere_bortelag["Fødselsdato"],
                    ):
                        if isinstance(fdato, str):
                            ekte_dato = datetime.strptime(
                                fdato.strip(), "%d.%m.%Y"
                            ).date()
                        else:
                            ekte_dato = pd.to_datetime(fdato).date()

                        spiller_id = database.hent_eller_lagre_spiller(
                            navn.strip(),
                            ekte_dato,
                        )

                        sp_bo_ids.append(spiller_id)

                    spillere_bortelag["spiller_id"] = sp_bo_ids
                    spillere_bortelag["kamp_id"] = kampnr_id
                    spillere_bortelag["lag_id"] = bortelag

                    # Samle hjemme- og bortelag

                    alle_spillere: DataFrame = pd.concat(
                        [spillere_hjemmelag, spillere_bortelag], ignore_index=True
                    )

                    # print("--- Alle Spillere ---")
                    # print(alle_spillere)
                    # print("\n")

                    # Hente kamphendelser

                    kamphendelser: DataFrame = kamp_parser.parse_kamphendelser(
                        page, kamp_info["hjemmelag_id"], kamp_info["bortelag_id"]
                    )

                    if kamphendelser.empty:
                        continue

                    # print("--- Kamphendelser ---")
                    # print(kamphendelser.head(5))
                    # print("\n")

                    # Lage stats på utespillere

                    stats_utespillere: DataFrame = (
                        kamp_parser.sortere_statistikk_utespillere(kamphendelser)
                    )

                    # print("--- Stats utespillere ---")
                    # print(stats_utespillere)
                    # print("\n")

                    # Lage stats på målvakter

                    stats_keepere: DataFrame = kamp_parser.sortere_statistikk_keepere(
                        kamphendelser
                    )

                    # print("--- Stats keepere ---")
                    # print(stats_keepere)
                    # print("\n")

                    # Legge til stats på utespillere

                    utespillere_med_stats_keepere_uten: DataFrame = (
                        kamp_parser.legg_til_stats_utespillere(
                            alle_spillere, stats_utespillere
                        )
                    )

                    # print("--- Stats utespillere u/keeper ---")
                    # print(utespillere_med_stats_keepere_uten)
                    # print("\n")

                    # Legge til stats på målvakter

                    utespillere_keepere_med_stats: DataFrame = (
                        kamp_parser.legg_til_stats_keepere(
                            utespillere_med_stats_keepere_uten, stats_keepere
                        )
                    )

                    for _, rad in utespillere_keepere_med_stats.iterrows():
                        kamphendelse_dict = rad.to_dict()

                        forekomst_id = database.hent_eller_lagre_kampforekomst(
                            kamphendelse_dict
                        )

                    # print("--- Stats alle | LAGRES ---")
                    # print(utespillere_keepere_med_stats)
                    # print("\n")

        except Exception as e:
            print(f"[RUN_SCRAPER-FEIL] Noe gikk galt i hovedloopen: {e}")

        finally:
            if feilede_kamper:
                print(
                    f"[OPPSUMMERING] {len(feilede_kamper)} kamper kunne ikke leses: "
                    f"{sorted(feilede_kamper)}"
                )
            browser.close()


if __name__ == "__main__":
    main()
