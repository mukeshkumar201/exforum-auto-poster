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

# --- Step 1: Image Scraping ---
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
    print("--- Step 2: Watermarking Image (Size: 8%) ---")
    try:
        r = requests.get(url, timeout=30)
        with open('img.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('img.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.08) # 8% Font Size
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", fs)
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

# --- Step 3: Posting to Forum (ULTIMATE FIX) ---
def post_to_forum(p):
    print("--- Step 3: Posting to Forum with Drag & Drop Logic ---")
    
    # Permissions grant kar rahe hain taaki clipboard/files access easy ho
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-web-security"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        permissions=['clipboard-read', 'clipboard-write']
    )
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        print(f"Navigating to: {THREAD_REPLY_URL}")
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        # Editor load hone ka wait
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        print("Editor loaded.")

        # --- STRATEGY 1: DIRECT DRAG AND DROP (Best for XenForo) ---
        print("Attempting Method 1: Direct Drag & Drop to Editor...")
        try:
            # Playwright ka set_input_files agar 'div' par use karein toh wo Drop event simulate karta hai
            page.locator('.fr-element').set_input_files("final.jpg")
            print("Drag & Drop command sent.")
            time.sleep(3) # Wait for upload to start
        except Exception as e:
            print(f"Drag & Drop failed: {e}")

        # Check agar Method 1 se upload ho gaya
        if check_upload_success(editor):
            submit_post(page)
            return

        # --- STRATEGY 2: HIDDEN INPUT MANIPULATION (Fallback) ---
        print("Method 1 failed/slow. Attempting Method 2: Hidden Input Injection...")
        try:
            # Input ko visible banao
            page.evaluate("""
                const input = document.querySelector('input[type="file"]');
                if(input) {
                    input.style.display = 'block'; 
                    input.style.visibility = 'visible';
                    input.style.position = 'fixed';
                    input.style.zIndex = '9999';
                    input.style.top = '0';
                    input.style.left = '0';
                }
            """)
            # File set karo
            page.set_input_files('input[type="file"]', 'final.jpg')
            
            # MULTIPLE Event Triggers (Bahut zaroori hai)
            page.evaluate("""
                const input = document.querySelector('input[type="file"]');
                if(input) {
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            """)
            print("Force injection & events dispatched.")
        except Exception as e:
            print(f"Injection failed: {e}")

        # Final Wait for upload
        if check_upload_success(editor):
            submit_post(page)
        else:
            print("ERROR: All upload methods failed. Saving debug screenshot.")
            page.screenshot(path="upload_failed_final.png")

    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_crash.png")
    finally:
        browser.close()

def check_upload_success(editor_locator):
    print("Waiting for BBCode ([IMG] tag)...")
    for i in range(15): # 45 seconds total wait
        content = editor_locator.inner_html()
        if "[IMG]" in content or "<img" in content.lower():
            print(f"SUCCESS: Image detected in editor after {i*3}s!")
            return True
        time.sleep(3)
    return False

def submit_post(page):
    print("Adding text and submitting...")
    # Text append karna
    page.locator('.fr-element').click()
    page.keyboard.press("Control+End")
    page.keyboard.type(f"\n\n🔥 Desi Bhabhi Viral Update! 🔥\nSource: {WATERMARK_TEXT}")
    time.sleep(2)

    # Submit Button Logic
    submit_btn = page.locator('button:has-text("Post reply")').first
    if not submit_btn.is_visible():
            submit_btn = page.locator('.button--icon--reply').first
    
    if submit_btn.is_visible():
        submit_btn.click()
        page.wait_for_timeout(5000)
        page.screenshot(path="success_post.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
    else:
        print("Submit button not found!")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
