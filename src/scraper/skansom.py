"""Felles regler for skånsom skraping av TA: pause mellom kall og tydelig User-Agent."""

import time

from playwright.sync_api import Browser, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# Pause før hver ny side eller blading i TA
PAUSE_SEKUNDER = 1.5

# Legges til nettleserens vanlige User-Agent, så TA ser hvem som henter data,
# uten at nettsiden behandler oss som en ukjent nettleser
USER_AGENT_TILLEGG = "OABR-TA-regelsjekk (Oslo og Akershus Bandyregion)"

TA_FORSIDE = "https://ta.nif.no"


def pause() -> None:
    time.sleep(PAUSE_SEKUNDER)


def lag_user_agent(browser: Browser) -> str:
    """Nettleserens egen User-Agent med vårt tillegg."""
    context = browser.new_context()
    try:
        standard: str = context.new_page().evaluate("navigator.userAgent")
    finally:
        context.close()
    return f"{standard} {USER_AGENT_TILLEGG}"


def er_innlogget(page: Page) -> bool:
    """Åpner forsiden til TA og sjekker om vi fortsatt er innlogget.

    Er økten utløpt, sendes nettleseren til en innloggingsside. Vi regner oss
    som innlogget når vi blir på ta.nif.no og siden ikke ber om passord.
    """
    pause()
    page.goto(TA_FORSIDE, wait_until="domcontentloaded")
    try:
        # Gir eventuelle videresendinger til innlogging tid til å skje
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    url: str = page.url.lower()
    paa_ta: bool = url.startswith(TA_FORSIDE)
    ber_om_innlogging: bool = (
        "login" in url or page.locator("input[type=password]").count() > 0
    )
    return paa_ta and not ber_om_innlogging
