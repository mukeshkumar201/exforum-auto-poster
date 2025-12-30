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

def add_watermark(url):
    print("--- Step 2: Watermarking Image (Size: 8%) ---")
    try:
        r = requests.get(url, timeout=30)
        with open('img.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('img.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.08) # 8% Font Size
        
        try:
            # Linux environment standard font
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
        print(f"Watermark applied: {fs}px size.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum via ImgBB Plugin ---")
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(90000)
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        if page.locator('text=Log in').is_visible():
            print("Session Expired! Update EX_COOKIES.")
            return

        # 1. Editor ka wait karo
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")

        # 2. ImgBB Plugin Button Trigger karo
        print("Clicking ImgBB Upload Button...")
        upload_btn = page.locator('button[data-chevereto-pup-trigger]')
        
        with page.expect_file_chooser() as fc_info:
            upload_btn.click()
        
        file_chooser = fc_info.value
        file_chooser.set_files("final.jpg")
        print("File selected. Waiting for upload to finish...")

        # 3. Wait for BBCode: Plugin upload ke baad [IMG] code editor mein daalta hai
        # Hum check karenge ki editor mein content aaya ya nahi
        success_upload = False
        for _ in range(12): # 1 minute wait (12 * 5s)
            time.sleep(5)
            content = editor.inner_html()
            if "img" in content.lower() or "ibb" in content.lower():
                print("SUCCESS: Image BBCode detected in editor.")
                success_upload = True
                break
        
        if not success_upload:
            print("WARNING: Upload might have failed or took too long.")

        # 4. Text Add karo (Image ke niche)
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nFresh Desi Bhabhi Update! 🔥\nCheck: {WATERMARK_TEXT}")
        time.sleep(2)

        # 5. Submit Post
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        time.sleep(10)
        page.screenshot(path="final_check.png")
        print("--- TASK COMPLETED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                # Is baar hum seedha post_to_forum call kar rahe hain bina external link ke
                post_to_forum(playwright)
