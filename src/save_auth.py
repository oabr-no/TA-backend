from playwright.sync_api import sync_playwright


def lagre_innlogging():
    with sync_playwright() as p:
        # Vi starter en synlig nettleser (headless=False)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Gå til innloggingssiden til nettstedet
        page.goto("https://ta.nif.no")

        print("Vennligst logg inn på nettsiden i nettleservinduet.")
        input("Trykk ENTER i denne terminalen når du er helt ferdig innlogget...")

        # Lagrer cookies og local storage til en JSON-fil
        context.storage_state(path="state.json")
        print("Innloggingsstatus er lagret i state.json!")
        
        browser.close()

if __name__ == "__main__":
    lagre_innlogging()