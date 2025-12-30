import os, requests, time, random, json, sys
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_images.txt"
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
        if not target_gal.startswith('http'): target_gal = "https://www.pornpics.com" + target_gal
            
        print(f"Target Gallery: {target_gal}")
        r_gal = requests.get(target_gal, headers=headers, timeout=30)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        
        valid_imgs = []
        for img in gal_soup.find_all('img'):
            src = img.get('data-src') or img.get('src') or ''
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png']):
                if 'logo' not in src.lower() and '.svg' not in src.lower() and "pornpics.com" in src:
                    full_url = src if src.startswith('http') else "https:" + src
                    if full_url not in posted: valid_imgs.append(full_url)
        
        if valid_imgs:
            img_url = random.choice(valid_imgs).replace('/460/', '/1280/') 
            print(f"SUCCESS: Image Found -> {img_url}")
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
        return None
    except Exception as e:
        print(f"Scrape Error: {e}"); return None

def add_watermark(url):
    print("--- Step 2: Watermarking Image ---")
    try:
        r = requests.get(url, timeout=30)
        with open('final.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('final.jpg').convert("RGB")
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
        print("Watermark applied successfully.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}"); return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum ---")
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
    # Full HD view taaki element chhup na jaye
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(90000)
    
    try:
        print(f"Navigating to {THREAD_REPLY_URL}...")
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        print("Editor visible.")

        # 1. Upload Button Click Logic
        print("Clicking Upload Button...")
        upload_btn = page.locator('button.js-attachmentUpload').first
        upload_btn.scroll_into_view_if_needed()
        upload_btn.click(force=True)
        
        # 2. Wait for Iframe with state 'attached' instead of 'visible'
        print("Waiting for Iframe to attach...")
        # Headless mein visibility issues ho sakte hain, isliye state="attached" use kar rahe hain
        page.wait_for_selector('iframe', state="attached", timeout=60000)
        
        # Thoda wait taaki iframe fully load ho jaye
        time.sleep(5)
        
        # Iframe locator
        upload_frame = page.frame_locator('iframe').last
        print("Frame located.")
        
        # 3. File Upload
        print("Injecting file into iframe...")
        # Check multiple selectors for file input
        file_input = upload_frame.locator('#anywhere-upload-input')
        file_input.set_input_files('final.jpg')
        
        # 4. Insert button wait aur click
        print("Waiting for 'Insert' button...")
        insert_btn = upload_frame.locator("button[data-action='openerPostMessage']")
        
        # Agar upload slow hai toh wait badha diya
        insert_btn.wait_for(state="visible", timeout=120000)
        
        time.sleep(2)
        insert_btn.click()
        print("Insert button clicked.")

        # 5. Text aur Submit
        time.sleep(5) # BBCode editor mein aane ka wait
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\n🔥 New Desi Update! 🔥\nCheck: {WATERMARK_TEXT}")
        
        print("Submitting Reply...")
        submit_btn = page.locator('button.button--icon--reply').first
        submit_btn.click()
        
        page.wait_for_load_state("networkidle")
        print("--- TASK COMPLETED: SUCCESS ---")

    except Exception as e:
        print(f"❌ Forum Error: {e}")
        page.screenshot(path="error_debug.png")
        print("Screenshot saved to error_debug.png")
        sys.exit(1) # GitHub Action ko fail dikhao agar post nahi hua
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url and add_watermark(img_url):
            post_to_forum(playwright)
