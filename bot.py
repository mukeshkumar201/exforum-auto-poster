import os, requests, time, random, json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/indian-pussy/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

# 1. Top Desi Fillers (Inke saath domain variant aayega)
TOP_FILLERS = [
    "Dekho naya mast maal:", "Bhabhi ka jalwa yahan dekho:", "Garmi badhane wala item:", 
    "Jaldi aao asli maza yahan hai:", "Ekdam fresh desi tadka:", "Bhabhi ki jawani dekh lo:"
]

# 2. Bottom Spicy Phrases (Isme LINK NAHI HAI, sirf comments hain)
# Isse post real lagegi aur link repeat nahi hoga
BOTTOM_PHRASES = [
    "Maza aa gaya dekh ke! 🔥", "Kya mast cheez hai bhabhi! 🔞", "Ekdam kadak maal hai! 🌶️",
    "Aisi bhabhi mil jaye toh din ban jaye! 💦", "Jawaani ekdam full hai! 🍑",
    "Agli baar aur bhi khatarnak maal launga! 🔥", "Dekhte raho, maza aane wala hai! ❤️",
    "Bhabhi ne toh aag laga di! 💥", "Kya item hai yaar! 😍"
]

# 3. Domain variants (Sirf top mein use honge)
CAPTION_VARIANTS = [
    "freepornx [dot] site", "freepornx {dot} site", "freepornx (dot) site",
    "f r e e p o r n x . s i t e", "f\u200Breepornx\u200B.\u200Bsite", "freepornx [.] site",
    "freepornx DOT site", "freepornx * site", "freepornx ~ site", "freepornx @ site",
    "freepornx_site", "f-r-e-e-p-o-r-n-x-site", "freepornx [at] site",
    "freepornx ( . ) s i t e", "freepornx...site", "freepornx |-| site"
]

def get_new_image():
    # Scraper logic for Indian Pussy (PornPics)
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
    # Logic: Top mein RANDOM Link, Bottom mein RANDOM Spicy Comment (No Link)
    top_text = f"{random.choice(TOP_FILLERS)} {random.choice(CAPTION_VARIANTS)}"
    bottom_text = random.choice(BOTTOM_PHRASES)
    
    print(f"--- Posting ---")
    print(f"Top: {top_text}")
    print(f"Bottom: {bottom_text}")

    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0")
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw: return
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        editor = page.locator('.fr-element').first
        editor.wait_for(state="visible")

        # 1. Top Content (Desi Filler + Random Link)
        editor.focus()
        page.keyboard.type(f"[SIZE=6][B]{top_text}[/B][/SIZE]\n")
        time.sleep(1)

        # 2. Image Insert
        page.click('#insertImage-1', force=True)
        time.sleep(2)
        page.locator('button[data-cmd="imageByURL"], .fr-popup button[data-cmd="imageByURL"]').first.click(force=True)
        page.locator('input[name="src"]').first.fill(direct_img_url)
        page.keyboard.press("Enter")
        time.sleep(5) 

        # 3. Bottom Content (Sirf Spicy Desi Comment - Link Removed)
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n[SIZE=7][B]{bottom_text}[/B][/SIZE]")

        # 4. Final Submit
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        page.wait_for_timeout(8000)
        print("--- POST SUCCESSFUL (RANDOMIZED) ---")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            post_to_forum(playwright, img_url)
