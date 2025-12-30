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
        if not links: 
            print("No gallery links found!")
            return None
        
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
        
        print("No new images found in this gallery.")
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
        fs = int(h * 0.07) # 7% Font Size (Balanced)
        
        # Font check (Linux/Windows compatible)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", fs)
            except:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = (w - tw - 30, h - th - 30)

        # Black outline/shadow for visibility
        for adj in range(-2, 3):
            for b in range(-2, 3):
                draw.text((pos[0]+adj, pos[1]+b), WATERMARK_TEXT, fill="black", font=font)
        
        draw.text(pos, WATERMARK_TEXT, fill="white", font=font)
        img.save('final.jpg', quality=95)
        print(f"Watermark applied successfully.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum ---")
    # Debugging ke liye headless=False rakhein, server par True kar dein
    browser = p.chromium.launch(headless=True) 
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES environment variable not found!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        print(f"Navigating to {THREAD_REPLY_URL}...")
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        # Wait for Editor
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")

        # 1. Trigger Chevereto Upload
        print("Triggering upload plugin...")
        upload_trigger = page.locator('button[data-chevereto-pup-trigger]')
        if upload_trigger.is_visible():
            upload_trigger.click()
        else:
            print("Trigger button not found. Post might be locked or cookies expired.")
            return

        # 2. Upload File
        print("Uploading final.jpg...")
        # XenForo plugin typical file input selector
        page.set_input_files('input[type="file"]', 'final.jpg')

        # 3. Wait for BBCode to appear (Important!)
        print("Waiting for image to upload and BBCode to generate...")
        success_upload = False
        for _ in range(12): # 1 minute wait total
            time.sleep(5)
            content = editor.inner_html()
            if "[IMG]" in content or "img" in content.lower():
                print("SUCCESS: Image BBCode detected in editor!")
                success_upload = True
                break
        
        if not success_upload:
            print("WARNING: Upload might have failed or slow. Proceeding anyway...")

        # 4. Add Text content
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nFresh Desi Update! 🔥\nEnjoy: {WATERMARK_TEXT}")
        time.sleep(2)

        # 5. Submit
        print("Clicking Submit...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        # Wait for success navigation
        page.wait_for_timeout(8000)
        page.screenshot(path="post_confirmation.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug.png")
        print("Check error_debug.png for details.")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
            else:
                print("Watermark step failed.")
        else:
            print("Scraping failed.")
