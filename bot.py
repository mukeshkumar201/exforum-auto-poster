import os, requests, time, random, json, sys
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
        print("Watermark added.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum ---")
    
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    
    # FIX: Viewport size badha diya taaki desktop site load ho
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES environment variable missing!")
        sys.exit(1)
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        print(f"Navigating to {THREAD_REPLY_URL}...")
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        
        # Editor check
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        print("Editor found.")
        
        # --- UPLOAD PROCESS FIX ---
        print("Finding Upload Button...")
        
        # FIX: Selector change kiya 'js-attachmentUpload' par jo zyada reliable hai
        upload_btn = page.locator('.js-attachmentUpload').first
        
        # FIX: Button ko view me layenge click karne se pehle
        upload_btn.scroll_into_view_if_needed()
        time.sleep(1)
        
        print("Clicking Upload Button...")
        upload_btn.click(force=True)
        
        print("Waiting for Iframe to appear...")
        # Iframe wait logic
        page.wait_for_selector('iframe', state="attached", timeout=30000)
        
        # Frame locator
        upload_frame = page.frame_locator('iframe').last
        
        print("Uploading Image inside Iframe...")
        # Upload file
        upload_frame.locator('#anywhere-upload-input').set_input_files('final.jpg')
        
        print("Waiting for 'Insert' button...")
        # Wait for Insert Button
        insert_btn = upload_frame.locator("button[data-action='openerPostMessage']")
        insert_btn.wait_for(state="visible", timeout=60000)
        
        # Click Insert
        time.sleep(2)
        insert_btn.click()
        print("Clicked Insert.")
        # --- END UPLOAD ---

        # Validation
        time.sleep(5)
        content = editor.inner_html()
        if "img" not in content.lower() and "[IMG]" not in content:
            print("ERROR: Image code NOT found in editor. Taking screenshot.")
            page.screenshot(path="failed_upload.png")
            sys.exit(1)
        
        print("Image code verified.")

        # Add Text
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\n🔥 Hot Update 🔥\nSource: {WATERMARK_TEXT}")
        time.sleep(1)

        # Submit
        print("Clicking Post Reply...")
        page.click('button.button--icon--reply')
        
        print("Waiting for submission to complete...")
        page.wait_for_load_state('networkidle') 
        time.sleep(5)
        
        print("--- POST SUCCESSFUL ---")

    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        try:
            # Error ke time screenshot le lenge debug ke liye
            page.screenshot(path="error_state.png")
            print("Screenshot saved as error_state.png")
        except:
            pass
        sys.exit(1)
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
        else:
            print("No new images found.")
