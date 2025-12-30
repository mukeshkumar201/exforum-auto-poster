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
    print(f"--- Step 1: Scraping Image from {PORN_SOURCE} ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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

def add_watermark(url):
    print("--- Step 2: Watermarking Image ---")
    try:
        r = requests.get(url, timeout=30)
        with open('img.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('img.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.08)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = (w - tw - 50, h - th - 50)

        for adj in range(-2, 3):
            for b in range(-2, 3):
                draw.text((pos[0]+adj, pos[1]+b), WATERMARK_TEXT, fill="black", font=font)
        
        draw.text(pos, WATERMARK_TEXT, fill="white", font=font)
        img.save('final.jpg', quality=95)
        print("Watermark applied.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        # Editor check
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible", timeout=30000)

        # 1. Trigger Plugin
        print("Opening Upload Dialog...")
        page.click('button[data-chevereto-pup-trigger]', force=True)
        time.sleep(3)

        # 2. Upload File - Specific Selector
        print("Injecting file into hidden input...")
        # Kabhi kabhi multiple inputs hote hain, hum 'last' wala try karte hain jo aksar plugin ka hota hai
        file_input = page.locator('input[type="file"]')
        file_input.last.set_input_files('final.jpg')
        print("File injected. Waiting for upload completion...")

        # 3. Wait for BBCode (Critical Fix)
        # Hum 90 seconds tak wait karenge jab tak [IMG] tag na dikh jaye
        success_upload = False
        for i in range(18): # 18 * 5 = 90 seconds
            time.sleep(5)
            content = editor.inner_html()
            print(f"Checking Editor (Attempt {i+1})...")
            if "[IMG]" in content or "img" in content.lower() or "data-p-id" in content:
                print("SUCCESS: Image detected in editor!")
                success_upload = True
                break
        
        if not success_upload:
            print("FAILED: Image didn't appear in editor. Skipping post to avoid empty message.")
            page.screenshot(path="failed_upload.png")
            return

        # 4. Text Message add karna
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nNew Hot Desi Update! 🔥\nVisit: {WATERMARK_TEXT}")
        time.sleep(2)

        # 5. Submit
        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        # Confirmation
        page.wait_for_timeout(10000)
        page.screenshot(path="final_check.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url and add_watermark(img_url):
            post_to_forum(playwright)
