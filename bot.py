import os, requests, time, random, json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/indian-pussy/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

# Tera Random Caption Pool
CAPTION_VARIANTS = [
    "freepornx [dot] site", "freepornx {dot} site", "freepornx (dot) site",
    "freepornx | site", "f r e e p o r n x . s i t e", "f\u200Breepornx\u200B.\u200Bsite",
    "freepornx [.] site", "freepornx ( . ) site", "freepornx / site",
    "FreePornX.Site", "freepornx DOT site", "freepornx * site",
    "freepornx ~ site", "freepornx ::: site", "f.r.e.e.p.o.r.n.x.s.i.t.e",
    "freepornx @ site", "freepornx_site", "FrEePoRnX.SiTe",
    "f-r-e-e-p-o-r-n-x-site", "freepornx [at] site"
]

def get_new_image():
    print(f"--- Step 1: Scraping Image ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
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
    # --- YAHAN RANDOM SELECTION HOGA ---
    # Top aur Bottom ke liye alag-alag random variant chunna
    top_cap = random.choice(CAPTION_VARIANTS)
    bottom_cap = random.choice(CAPTION_VARIANTS)
    
    print(f"--- Step 2: Posting ---")
    print(f"Top Caption: {top_cap} | Bottom Caption: {bottom_cap}")
    
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

        # --- 1. Image ke UPAR Random Text ---
        editor.focus()
        page.keyboard.type(f"[SIZE=6][B]visit website - {top_cap}[/B][/SIZE]\n")
        time.sleep(1)

        # --- 2. Image Insert Logic ---
        page.click('#insertImage-1', force=True)
        page.wait_for_timeout(3000)
        page.locator('button[data-cmd="imageByURL"], .fr-popup button[data-cmd="imageByURL"]').first.click(force=True)
        page.locator('input[name="src"], .fr-image-by-url-layer input[type="text"]').first.fill(direct_img_url)
        page.keyboard.press("Enter")
        time.sleep(5) 

        # --- 3. Image ke NICHE Random Text ---
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n[SIZE=7][B]New Fresh Desi Update! 🔥[/B][/SIZE]")
        page.keyboard.type(f"\n[SIZE=6][B]visit website - {bottom_cap}[/B][/SIZE]")

        # --- 4. Submit ---
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        page.wait_for_timeout(8000)
        print("--- POST SUCCESSFUL ---")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            post_to_forum(playwright, img_url)
