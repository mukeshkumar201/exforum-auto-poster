import os, requests, time, random, json
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
WATERMARK_TEXT = "freepornx.site"
PORN_SOURCE = "https://www.pornpics.com/tags/desi/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

def get_new_image():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(PORN_SOURCE, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        if not links: return None
        target = random.choice(links)
        target_url = target if target.startswith('http') else "https://www.pornpics.com" + target
        r_gal = requests.get(target_url, headers=headers)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') if "pornpics.com" in (img.get('data-src') or img.get('src', ''))]
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        return random.choice(new_imgs) if new_imgs else None
    except: return None

def add_watermark(url):
    print("--- Step: Watermarking image ---")
    try:
        img_data = requests.get(url).content
        with open('final.jpg', 'wb') as f: f.write(img_data)
        img = Image.open('final.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.05)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            font = ImageFont.load_default()
        draw.text((w - (fs*4), h - (fs*2)), WATERMARK_TEXT, fill="white", font=font)
        img.save('final.jpg')
        return True
    except: return False

def post_to_forum_direct():
    with sync_playwright() as p:
        print("--- Step: Launching Browser for Direct Post ---")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        cookies_raw = os.environ.get('EX_COOKIES')
        if not cookies_raw:
            print("ERROR: EX_COOKIES missing!"); return False
        
        context.add_cookies(json.loads(cookies_raw))
        page = context.new_page()

        try:
            print(f"Opening Thread: {THREAD_REPLY_URL}")
            page.goto(THREAD_REPLY_URL, wait_until="networkidle")
            
            # Login check
            is_logged_in = page.evaluate("document.body.getAttribute('data-logged-in')")
            if is_logged_in != "true":
                print("SESSION FAIL: Cookies not working!"); return False

            # --- DIRECT UPLOAD ---
            print("Step: Uploading final.jpg directly to forum...")
            # XenForo attachment input
            file_input = page.locator('input[type="file"][name="upload[]"]').first
            file_input.set_files("final.jpg")
            
            print("Waiting for upload to finish (15s)...")
            page.wait_for_timeout(15000)

            # Attachment ko editor mein "Full image" ki tarah insert karna
            try:
                full_img_btn = page.locator('button:has-text("Full image")').first
                full_img_btn.click()
                print("Clicked 'Full image' button.")
            except:
                print("Could not find 'Full image' button, inserting manually...")
                page.locator('.fr-element').click()
                page.keyboard.type("\n\n[ATTACH=full]1[/ATTACH]\n\nEnjoy! 🔥")

            print("Submitting post...")
            page.locator('button.button--icon--reply').first.click()
            page.wait_for_timeout(5000)
            
            print("--- SUCCESS: Post is Live! ---")
            return True
        except Exception as e:
            print(f"Post Error: {e}")
            page.screenshot(path="error_debug.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    img_url = get_new_image()
    if img_url:
        print(f"Found Image: {img_url}")
        if add_watermark(img_url):
            if post_to_forum_direct():
                with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
