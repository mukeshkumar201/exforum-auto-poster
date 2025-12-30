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
        
        # Font Selection Logic
        try:
            # Linux server path
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            try:
                # Windows fallback
                font = ImageFont.truetype("arial.ttf", fs)
            except:
                # Default fallback
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = (w - tw - 50, h - th - 50)

        # Black Outline
        for adj in range(-2, 3):
            for b in range(-2, 3):
                draw.text((pos[0]+adj, pos[1]+b), WATERMARK_TEXT, fill="black", font=font)
        
        # White Text
        draw.text(pos, WATERMARK_TEXT, fill="white", font=font)
        img.save('final.jpg', quality=95)
        print(f"Watermark applied: {fs}px size.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

# --- Step 3: Posting to Forum (FIXED) ---
def post_to_forum(p):
    print("--- Step 3: Posting to Forum with Enhanced Upload Logic ---")
    
    # Debugging ke liye headless=False kar sakte ho agar dekhna hai browser me kya ho raha hai
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Cookies Check
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL ERROR: 'EX_COOKIES' environment variable not found!")
        print("Please set export EX_COOKIES='[...]' in your terminal.")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000) # 60 seconds timeout
    
    try:
        print(f"Navigating to: {THREAD_REPLY_URL}")
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        # Editor load hone ka wait
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        print("Editor loaded.")

        # --- FIX: ROBUST UPLOAD HANDLING ---
        print("Attempting to upload image...")
        upload_successful_trigger = False

        # Method 1: File Chooser (Standard Click)
        try:
            with page.expect_file_chooser(timeout=5000) as fc_info:
                # Chevereto plugin button click
                page.click('button[data-chevereto-pup-trigger]', force=True)
            
            file_chooser = fc_info.value
            file_chooser.set_files("final.jpg")
            print("Method 1: File Chooser detected and file set.")
            upload_successful_trigger = True
            
        except Exception as e:
            print(f"Method 1 failed ({e}), trying Method 2 (Direct Injection)...")
            
            # Method 2: Force Injection into hidden input
            try:
                # Input ko visible banao aur file set karo
                page.evaluate("""
                    const input = document.querySelector('input[type="file"]');
                    if(input) {
                        input.style.display = 'block'; 
                        input.style.visibility = 'visible';
                    }
                """)
                page.set_input_files('input[type="file"]', 'final.jpg')
                
                # Manual Event Dispatch (Bahut zaroori hai!)
                page.evaluate("""
                    const input = document.querySelector('input[type="file"]');
                    if(input) {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                """)
                print("Method 2: Force injection completed.")
                upload_successful_trigger = True
            except Exception as e2:
                print(f"Method 2 failed: {e2}")

        if not upload_successful_trigger:
            print("CRITICAL: Could not trigger upload mechanism.")
            return

        # --- WAIT FOR UPLOAD TO COMPLETE (BBCode Check) ---
        print("Waiting for image URL/BBCode to appear in editor...")
        uploaded = False
        
        # 10 checks * 3 seconds = 30 seconds wait for upload
        for i in range(10): 
            content = editor.inner_html()
            # Check for [IMG] tag or <img> html tag
            if "[IMG]" in content or "<img" in content.lower():
                print("SUCCESS: Image detected in editor!")
                uploaded = True
                break
            print(f"Uploading... {i+1}/10")
            time.sleep(3)

        if not uploaded:
            print("ERROR: Upload timeout. Image did not appear in editor.")
            page.screenshot(path="upload_failed_debug.png")
            return 

        # --- ADD TEXT AND SUBMIT ---
        print("Adding text...")
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nFresh Desi Bhabhi Update! 🔥\nCheck more at: {WATERMARK_TEXT}")
        time.sleep(2)

        print("Submitting post...")
        # Submit button ke multiple selectors try karenge
        submit_btn = page.locator('button:has-text("Post reply")').first
        if not submit_btn.is_visible():
             submit_btn = page.locator('.button--icon--reply').first
             
        if submit_btn.is_visible():
            submit_btn.click()
            print("Post button clicked.")
            
            # Wait for submission to process
            page.wait_for_timeout(5000)
            page.screenshot(path="success_post.png")
            print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        else:
            print("Error: Submit button not found!")
            page.screenshot(path="submit_btn_missing.png")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_crash.png")
    finally:
        browser.close()

# --- Main Execution ---
if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
            else:
                print("Watermarking failed.")
        else:
            print("No new images found.")
