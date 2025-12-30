import os, requests, time, random, json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/indian-pussy/"
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

        # --- UPDATE: Image ke upar BADA text add karna ---
        print("Adding Large text ABOVE the image...")
        editor.focus()
        # [SIZE=6] text ko bada karega aur [B] bold karega
        page.keyboard.type("[SIZE=6][B]visit website - freepornx.site[/B][/SIZE]\n")
        time.sleep(1)

        # 1. Click Main Image Button
        print("Clicking Toolbar Image Button (#insertImage-1)...")
        page.click('#insertImage-1', force=True)
        page.wait_for_timeout(3000)

        # 2. Click 'By URL' Tab
        print("Switching to 'By URL' tab...")
        by_url_tab = page.locator('button[data-cmd="imageByURL"], .fr-popup button[data-cmd="imageByURL"]').first
        
        if by_url_btn_visible := by_url_tab.is_visible():
            by_url_tab.click(force=True)
            print("'By URL' button clicked.")
        else:
            print("By URL button not directly visible, attempting to find in active popup...")

        # 3. Handle URL Input
        print("Waiting for URL input box...")
        url_input_selectors = [
            'input[name="src"]',
            '.fr-image-by-url-layer input[type="text"]',
            '.fr-link-input',
            'input[placeholder*="URL"]'
        ]
        
        input_found = False
        for selector in url_input_selectors:
            try:
                input_field = page.locator(selector).first
                if input_field.is_visible(timeout=5000):
                    input_field.fill(direct_img_url)
                    print(f"URL Filled using selector: {selector}")
                    input_found = True
                    break
            except:
                continue

        if not input_found:
            raise Exception("Could not find the URL input field in any popup layer.")

        # 4. Confirm Insertion
        print("Inserting image...")
        page.keyboard.press("Enter")
        
        insert_btn = page.locator('button[data-cmd="imageInsertByURL"], .fr-popup button:has-text("Insert")').first
        if insert_btn.is_visible():
            insert_btn.click(force=True)
        
        time.sleep(5) # Image rendering wait

        # --- UPDATE: Image ke niche BADA text add karna ---
        print("Adding Large text BELOW the image...")
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type("\n[SIZE=10][B]New Fresh Desi Update! 🔥[/B][/SIZE]")
        page.keyboard.type("\n[SIZE=10][B]visit website - freepornx.site[/B][/SIZE]")

        # 5. Finalize Post
        print("Adding final caption...")
      
        time.sleep(2)

        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        # Success navigation wait
        page.wait_for_timeout(10000)
        page.screenshot(path="final_check.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug_by_url.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            post_to_forum(playwright, img_url)
