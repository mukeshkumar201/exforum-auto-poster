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

# --- Step 3: Upload to ImgBB (Automated) ---
def upload_to_imgbb(p):
    print("--- Step 3: Uploading to ImgBB (Automated) ---")
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()
    
    try:
        page.goto("https://imgbb.com/", timeout=60000)
        
        # 1. File Upload Trigger
        # ImgBB ke homepage par hidden input hota hai
        print("Selecting file on ImgBB...")
        page.set_input_files('input[type="file"]', 'final.jpg')
        
        # 2. Wait for Edit/Upload Modal
        print("Waiting for upload modal...")
        page.wait_for_selector('.btn-primary', state="visible") # 'Upload' button
        time.sleep(1)
        
        # 3. Click Upload
        print("Clicking Upload button...")
        # Kabhi kabhi multiple buttons hote hain, wo wala chahiye jo modal me ho
        page.click('button.btn-primary:has-text("Upload")')
        
        # 4. Wait for Result
        print("Waiting for generated link...")
        page.wait_for_selector('input#embed-code-1', state="visible", timeout=30000)
        
        # 5. Change Dropdown to 'BBCode full linked' (Optional, but safer)
        # Default usually works, but let's just grab the Viewer Link or Direct Link code
        # ImgBB by default gives "Viewer link" in the box. Let's switch to BBCode full.
        
        # Dropdown open karo
        page.click('.input-group-btn') 
        # Select "BBCode full linked" (data-value="bbcode-embed-medium" ya similar hota hai, text se pakdenge)
        page.click('li[data-text="BBCode full linked"]')
        
        # Code Copy karo
        bbcode = page.input_value('input#embed-code-1')
        print(f"ImgBB Success! BBCode obtained.")
        browser.close()
        return bbcode
        
    except Exception as e:
        print(f"ImgBB Upload Failed: {e}")
        page.screenshot(path="imgbb_error.png")
        browser.close()
        return None

# --- Step 4: Posting Link to Forum ---
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
        
        # Editor wait
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        
        # Click and Type
        editor.click()
        page.keyboard.press("Control+End")
        
        # Message banana
        message = f"\n\n🔥 Desi Bhabhi Viral! 🔥\n{bbcode_content}\n\nCredit: {WATERMARK_TEXT}"
        
        print("Typing BBCode into forum editor...")
        page.keyboard.type(message)
        time.sleep(2)

        # Submit
        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply")').first
        if not submit_btn.is_visible():
             submit_btn = page.locator('.button--icon--reply').first
        
        if submit_btn.is_visible():
            submit_btn.click()
            page.wait_for_timeout(6000) # Wait for processing
            page.screenshot(path="success_post.png")
            print("--- POST SUCCESSFUL ---")
        else:
            print("Submit button not found.")
            page.screenshot(path="error_submit.png")

    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_forum.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                # Step 3: ImgBB par upload karo
                bbcode = upload_to_imgbb(playwright)
                
                if bbcode:
                    # Step 4: Forum par paste karo
                    post_to_forum(playwright, bbcode)
                else:
                    print("Skipping post because ImgBB upload failed.")
