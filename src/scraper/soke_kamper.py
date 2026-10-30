from playwright.sync_api import Page
from playwright.sync_api._generated import Locator

from src.scraper import skansom

TIMEOUT = 10000


class KamplisteFeil(Exception):
    """Kamplisten for en klasse kunne ikke hentes fullstendig."""


def hent_kamper_klasse(page: Page, tournament_id: int) -> tuple[str, set[int]]:
    alle_kampid: set[int] = set()
    url: str = (
        f"https://ta.nif.no/Tournament/Details/{tournament_id}?detailsView=matches"
    )

    sesong = ""

    try:
        skansom.pause()
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

        if not sesong:
            raise ValueError("fant ikke sesongnavnet på siden")

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

            skansom.pause()
            neste_knapp.click()

            if forste_lenke:
                page.wait_for_function(
                    f"document.querySelector('{target_selector}').getAttribute('href') !== '{forste_lenke}'",
                    timeout=TIMEOUT,
                )

    except Exception as e:
        raise KamplisteFeil(
            f"Kunne ikke hente kamplisten for klasse {tournament_id}: {e}"
        ) from e

    return (sesong, alle_kampid)
