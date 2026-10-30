from playwright.sync_api import Page
from playwright.sync_api._generated import Locator

TIMEOUT = 10000


def hent_kamper_klasse(page: Page, tournament_id: int) -> tuple[str, set[int]]:
    alle_kampid: set[int] = set()
    url: str = (
        f"https://ta.nif.no/Tournament/Details/{tournament_id}?detailsView=matches"
    )

    sesong = ""

    try:
        page.goto(url)

        page.wait_for_selector(
            "#seasonSelectorDropdown",
            timeout=TIMEOUT,
        )
        sesong = (
            page.locator(
                "#switchSeasonForm > ul > li.dropdown.season-selector > ul > li.active > div"
            )
            .inner_text()
            .strip()
        )

        while True:
            target_selector: str = 'a[href*="MatchDetails/Overview/"]'
            page.wait_for_selector(target_selector, timeout=TIMEOUT)

            lenkeelementer: list[Locator] = page.locator(target_selector).all()

            forste_lenke = None
            if lenkeelementer:
                forste_lenke: str | None = lenkeelementer[0].get_attribute("href")

            for el in lenkeelementer:
                href: str | None = el.get_attribute("href")
                if href:
                    kampid: str = href.removeprefix("/MatchDetails/Overview/")
                    kampid_int: int = int(kampid)
                    alle_kampid.add(kampid_int)

            neste_knapp: Locator = page.locator(
                "#matchsearch_container > div > div > div > div.table-pager > div > div > ul > li:last-child > a"
            )

            if not neste_knapp.is_visible():
                break

            parent_li: Locator = page.locator(
                "#matchsearch_container > div > div > div > div.table-pager > div > div > ul > li:last-child"
            )
            li_classes: str = parent_li.get_attribute("class") or ""

            if "disabled" in li_classes or neste_knapp.is_disabled():
                break

            neste_knapp.click()

            if forste_lenke:
                try:
                    page.wait_for_function(
                        f"document.querySelector('{target_selector}').getAttribute('href') !== '{forste_lenke}'",
                        timeout=TIMEOUT,
                    )
                except Exception:
                    print("Tidsavbrudd under venting på neste side. Går videre.")
                    break

    except Exception as e:
        print(f"\n[FEIL] Kunne ikke hente kamp-liste for {tournament_id}: {e}")

    return (sesong, alle_kampid)
