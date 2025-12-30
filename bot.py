import os, requests, time, random, json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/desi/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

def get_new_image():
    print(f"--- Step 1: Scraping Image from {PORN_SOURCE} ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(PORN_SOURCE, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        if not links: return None
        
        target_gal = random.choice(links)
        target_gal = target_gal if target_gal.startswith('http') else "https://www.pornpics.com" + target_gal
        
        r_gal = requests.get(target_gal, headers=headers, timeout=30)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') if "pornpics.com" in (img.get('data-src') or img.get('src', ''))]
        
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        if new_imgs:
            img_url = random.choice(new_imgs)
            print(f"SUCCESS: Image Found -> {img_url}")
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
        return None
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

def post_to_forum(p, direct_img_url):
    print("--- Step 2: Posting to Forum via By URL ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        print(f"Opening thread...")
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        editor = page.locator('.fr-element').first
        editor.wait_for(state="visible")
        print("Editor ready.")

        # 1. Click Main Image Button
        print("Clicking Toolbar Image Button...")
        page.click('#insertImage-1', force=True)
        page.wait_for_timeout(3000)

        # 2. Specifically find and click the 'By URL' tab/button
        # Froala editor mein ye button aksar popup ke toolbar mein hota hai
        print("Switching to 'By URL' tab...")
        by_url_tab = page.locator('button[data-cmd="imageByURL"], .fr-command[data-cmd="imageByURL"]').first
        
        # Agar button visible hai toh click karein, warna ho sakta hai pehle se open ho
        if by_url_tab.is_visible():
            by_url_tab.click(force=True)
            print("'By URL' tab clicked.")
        else:
            print("'By URL' tab not visible, checking if already open...")

        page.wait_for_timeout(2000)

        # 3. Fill the URL Input Box
        print("Locating URL input field...")
        # XenForo Froala selectors for the URL input
        url_input = page.locator('input[name="src"], .fr-link-input, input[placeholder*="URL"]').first
        
        # Wait until it's actually ready for input
        url_input.wait_for(state="visible", timeout=20000)
        url_input.fill(direct_img_url)
        print(f"URL Filled: {direct_img_url}")

        # 4. Click the 'Insert' button in the popup
        # URL daalne ke baad ek 'Insert' ya blue checkmark button hota hai
        print("Confirming Insertion...")
        page.keyboard.press("Enter")
        
        # Backup: Agar enter se kaam na chale toh Insert button click karein
        insert_btn = page.locator('.fr-popup button[data-cmd="imageInsertByURL"], .fr-popup button:has-text("Insert")').first
        if insert_btn.is_visible():
            insert_btn.click()
        
        time.sleep(5) # Wait for image to render in editor

        # 5. Add Text and Submit
        print("Finalizing message text...")
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type("\n\nNew Fresh Desi Update! 🔥")
        time.sleep(2)

        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        # Wait for success
        page.wait_for_timeout(10000)
        page.screenshot(path="final_check.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        # Error ke time screenshot lelo taaki pata chale popup kaisa dikh raha hai
        page.screenshot(path="error_debug_by_url.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            post_to_forum(playwright, img_url)
