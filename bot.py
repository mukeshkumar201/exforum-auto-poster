import os
import requests
import time
import random
import json
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
WATERMARK_TEXT = "freepornx.site"
PORN_SOURCE = "https://www.pornpics.com/tags/desi/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

# --- Helper: Cleanup Files ---
def cleanup_files():
    for f in ['img.jpg', 'final.jpg']:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

# --- Step 1: Scraping ---
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

# --- Step 2: Watermarking ---
def add_watermark(url):
    print("--- Step 2: Watermarking ---")
    try:
        cleanup_files()
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
        print("Watermarking Done.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

# --- Step 3: Upload to ImgBB (GREEN BUTTON FIX) ---
def upload_to_imgbb(p):
    print("--- Step 3: Uploading to ImgBB ---")
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()
    
    try:
        page.goto("https://imgbb.com/", timeout=60000)
        
        # Cookie banner handling
        try:
            page.click('.cmp-intro_accept-all', timeout=3000)
        except:
            pass

        # 1. File Input mein file daalo
        print("Selecting file...")
        page.set_input_files('input[type="file"]', 'final.jpg')
        
        # 2. FORCE EVENT (Website ko jagana)
        page.evaluate("""
            var input = document.querySelector('input[type="file"]');
            input.dispatchEvent(new Event('change', { bubbles: true }));
        """)
        
        # 3. Wait for UPLOAD button (TEXT BASED MATCHING)
        # Ab hum color class nahi, seedha text "UPLOAD" dhoond rahe hain
        print("Waiting for 'UPLOAD' button...")
        
        # Is line se wo Green button pakad lega jo screenshot me hai
        upload_btn = page.locator('button:has-text("UPLOAD")').first
        upload_btn.wait_for(state="visible", timeout=20000)
        
        # 4. Click Upload
        print("Clicking Green Upload Button...")
        upload_btn.click()
        
        # 5. Link Generation ka wait
        print("Waiting for link...")
        page.wait_for_selector('input#embed-code-1', state="visible", timeout=45000)
        
        # 6. BBCode select karo
        try:
            page.click('.input-group-btn') 
            page.click('li[data-text="BBCode full linked"]')
            time.sleep(1)
        except:
            print("Default link used.")

        bbcode = page.input_value('input#embed-code-1')
        print(f"ImgBB Success! BBCode: {bbcode[:20]}...")
        browser.close()
        return bbcode
        
    except Exception as e:
        print(f"ImgBB Upload Failed: {e}")
        page.screenshot(path="imgbb_failed.png")
        browser.close()
        return None

# --- Step 4: Posting to Forum ---
def post_to_forum(p, bbcode_content):
    print("--- Step 4: Posting to Forum ---")
    
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        
        editor.click()
        page.keyboard.press("Control+End")
        
        message = f"\n\n🔥 Desi Bhabhi Viral Update! 🔥\n{bbcode_content}\n\nCredit: {WATERMARK_TEXT}"
        
        print("Typing content...")
        page.keyboard.type(message)
        time.sleep(2)

        print("Submitting...")
        submit_btn = page.locator('button:has-text("Post reply")').first
        if not submit_btn.is_visible():
             submit_btn = page.locator('.button--icon--reply').first
        
        if submit_btn.is_visible():
            submit_btn.click()
            page.wait_for_timeout(6000)
            page.screenshot(path="success_post.png")
            print("--- POST SUCCESSFUL ---")
        else:
            print("Submit button not found.")

    except Exception as e:
        print(f"Forum Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        cleanup_files()
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                bbcode = upload_to_imgbb(playwright)
                if bbcode:
                    post_to_forum(playwright, bbcode)
                else:
                    print("Skipping post due to upload failure.")
