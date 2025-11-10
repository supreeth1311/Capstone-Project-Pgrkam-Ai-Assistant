# scraper.py (Final Stable Version – Works with Real Chrome)
import os, time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BASE = os.getenv("PGRKAM_BASE", "https://www.pgrkam.com")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR = DATA_DIR / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

USER_DATA_DIR = "pgrkam_user"  # keeps login session

def wait(page, sec=1.0):
    page.wait_for_timeout(int(sec * 1000))

def auto_scroll(page, steps=12):
    for _ in range(steps):
        page.mouse.wheel(0, 1200)
        time.sleep(0.25)

def save_debug(page, name):
    page.screenshot(path=str(DEBUG_DIR / f"{name}.png"), full_page=True)
    with open(DEBUG_DIR / f"{name}.html", "w", encoding="utf-8") as f:
        f.write(page.content())

def extract_items(page_or_frame):
    rows = []
    cards = page_or_frame.locator("div, li, article").all()

    for c in cards:
        try:
            title = c.locator("h1, h2, h3, h4, .title").first.inner_text().strip()
        except: continue
        org = c.locator(".company, .provider, .org, .company-name").first.inner_text().strip() if c.locator(".company, .provider, .org, .company-name").count() else ""
        loc = c.locator(".location, .city, .district, .place, .venue").first.inner_text().strip() if c.locator(".location, .city, .district, .place, .venue").count() else ""
        dur = c.locator(".duration, .time, .tenure").first.inner_text().strip() if c.locator(".duration, .time, .tenure").count() else ""

        link = ""
        a = c.locator("a")
        if a.count():
            link = a.first.get_attribute("href") or ""

        rows.append({
            "Title": title,
            "Organization": org,
            "Location": loc,
            "Duration": dur,
            "Link": link
        })

    return rows

def scrape_section(page, label_list, outfile):
    print(f"\n➡ Navigate in the browser to the section: {label_list}")
    print("⚠️ When the page is fully visible → PRESS ENTER HERE.")
    input("Press ENTER to start scraping this section... ")

    wait(page, 2)
    auto_scroll(page, 15)
    save_debug(page, outfile.stem + "_view")

    rows = extract_items(page)
    # Try iframes too
    for f in page.frames:
        rows += extract_items(f)

    df = pd.DataFrame(rows)
    df.to_csv(outfile, index=False)
    print(f"✅ Saved {len(df)} items → {outfile}")

def main():
    print("📌 Launching Chrome with persistent login session...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="chrome",         # ✅ Use your real Chrome (Fixes Blank Page problem)
            headless=False,
            args=[
                "--start-maximized",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded")
        wait(page, 2)

        if "login" in page.url.lower():
            print("\n⚠️ Please LOGIN with MOBILE OTP in the browser.")
            input("After dashboard is visible → Press ENTER here to continue... ")

        print("✅ Login detected. Starting data extraction...")

        scrape_section(page, ["Jobs"], DATA_DIR / "pgrkam_jobs.csv")
        scrape_section(page, ["Skill Development", "Training"], DATA_DIR / "pgrkam_training.csv")
        scrape_section(page, ["Job Mela", "Job Fair", "Events"], DATA_DIR / "pgrkam_job_melas.csv")

        context.storage_state(path="auth_state.json")
        print("\n🎉 ALL DONE! Data Saved. Browser Session Stored.\n")

if __name__ == "__main__":
    main()
