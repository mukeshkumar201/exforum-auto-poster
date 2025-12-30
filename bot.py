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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0 ...)'}
    try:
        r = requests.get(PORN_SOURCE, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        if not links: return None
        
        target_gal = random.choice(links)
        if not target_gal.startswith('http'): target_gal = "https://www.pornpics.com" + target_gal
            
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
        pos = (w - (bbox[2]-bbox[0]) - 50, h - (bbox[3]-bbox[1]) - 50)
        for adj in range(-2, 3):
            for b in range(-2, 3):
                draw.text((pos[0]+adj, pos[1]+b), WATERMARK_TEXT, fill="black", font=font)
        draw.text(pos, WATERMARK_TEXT, fill="white", font=font)
        img.save('final.jpg', quality=95)
        print("Watermark applied.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}"); return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum ---")
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    # Viewport badha rakha hai taaki button easily dikhe
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    
    cookies_raw = os.environ.get('EX_COOKIES')
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")

        # 1. Upload Button dhundo aur click karo
        print("Opening Upload Popup...")
        upload_btn = page.locator('.js-attachmentUpload').first
        upload_btn.click(force=True)

        # 2. Iframe (ImgBB) handle karo
        print("Waiting for Iframe...")
        page.wait_for_selector('iframe', state="attached")
        upload_frame = page.frame_locator('iframe').last
        
        # 3. File upload karo
        print("Uploading to ImgBB via Popup...")
        upload_frame.locator('#anywhere-upload-input').set_input_files('final.jpg')
        
        # 4. Insert button ka wait aur click
        print("Waiting for Insert button...")
        insert_btn = upload_frame.locator("button[data-action='openerPostMessage']")
        insert_btn.wait_for(state="visible", timeout=90000)
        time.sleep(2)
        insert_btn.click()
        print("Image inserted into editor.")

        # 5. Extra Text aur Post
        time.sleep(3)
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\n🔥 Fresh Update! 🔥\nCheck: {WATERMARK_TEXT}")
        
        print("Submitting Post...")
        page.click('button.button--icon--reply')
        page.wait_for_load_state('networkidle')
        time.sleep(5)
        print("--- SUCCESS ---")

    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url and add_watermark(img_url):
            post_to_forum(playwright)
