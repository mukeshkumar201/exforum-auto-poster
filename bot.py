import os, requests, time, random, json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/indian-pussy/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

# Tera Random Captions List
CAPTIONS_LIST = [
    "freepornx [dot] site", "freepornx {dot} site", "freepornx (dot) site",
    "freepornx | site", "f r e e p o r n x . s i t e", "f\u200Breepornx\u200B.\u200Bsite",
    "freepornx [.] site", "freepornx ( . ) site", "freepornx / site",
    "FreePornX.Site", "freepornx DOT site", "freepornx * site",
    "freepornx ~ site", "freepornx ::: site", "f.r.e.e.p.o.r.n.x.s.i.t.e",
    "freepornx @ site", "freepornx_site", "FrEePoRnX.SiTe",
    "f-r-e-e-p-o-r-n-x-site", "freepornx [at] site"
]

def get_new_image():
    # ... (Keep your existing get_new_image function as it is) ...
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
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
        return None
    except: return None

def post_to_forum(p, direct_img_url):
    # Har post ke liye ek naya random caption pick karega
    selected_caption = random.choice(CAPTIONS_LIST)
    
    print(f"--- Step 2: Posting with Caption: {selected_caption} ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw: return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        editor = page.locator('.fr-element').first
        editor.wait_for(state="visible")

        # --- ABOVE IMAGE: Random Text ---
        editor.focus()
        page.keyboard.type(f"[SIZE=6][B]visit website - {selected_caption}[/B][/SIZE]\n")
        time.sleep(1)

        # 1. Click Main Image Button
        page.click('#insertImage-1', force=True)
        page.wait_for_timeout(3000)

        # 2. Click 'By URL' Tab & Handle URL Input
        # (Using your existing logic here for the popup)
        by_url_tab = page.locator('button[data-cmd="imageByURL"], .fr-popup button[data-cmd="imageByURL"]').first
        by_url_tab.click(force=True)
        
        page.locator('input[name="src"], .fr-image-by-url-layer input[type="text"]').first.fill(direct_img_url)
        page.keyboard.press("Enter")
        time.sleep(5) 

        # --- BELOW IMAGE: Random Text ---
        editor.focus()
        page.keyboard.press("Control+End")
        # Niche wala caption thoda bada (SIZE 7) aur unique
        page.keyboard.type(f"\n[SIZE=7][B]New Fresh Desi Update! 🔥[/B][/SIZE]")
        page.keyboard.type(f"\n[SIZE=6][B]visit website - {selected_caption}[/B][/SIZE]")

        # Submit
        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        page.wait_for_timeout(10000)
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            post_to_forum(playwright, img_url)
