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
        
        # Sirf galleries ke links nikaalna
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        
        if not links:
            print("ERROR: No galleries found.")
            return None
        
        target_gal = random.choice(links)
        if not target_gal.startswith('http'):
            target_gal = "https://www.pornpics.com" + target_gal
            
        print(f"Targeting Gallery: {target_gal}")
        r_gal = requests.get(target_gal, headers=headers, timeout=30)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        
        # Sabhi img tags nikaalo
        all_imgs = gal_soup.find_all('img')
        valid_imgs = []

        for img in all_imgs:
            src = img.get('data-src') or img.get('src') or ''
            
            # --- FILTER LOGIC START ---
            # 1. Image URL hona chahiye
            # 2. .svg nahi hona chahiye (Logo filter)
            # 3. 'logo' ya 'icon' word nahi hona chahiye
            # 4. pornpics ka domain hona chahiye
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png']):
                if 'logo' not in src.lower() and 'icon' not in src.lower() and '.svg' not in src.lower():
                    if "pornpics.com" in src:
                        if src not in posted:
                            # Relative URL ko Absolute banana
                            full_url = src if src.startswith('http') else "https:" + src
                            valid_imgs.append(full_url)
            # --- FILTER LOGIC END ---
        
        if valid_imgs:
            img_url = random.choice(valid_imgs)
            # Thumbnail ko Large image mein badalna (optional)
            img_url = img_url.replace('/460/', '/1280/') 
            
            print(f"SUCCESS: Valid Image Found -> {img_url}")
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
            
        print("ERROR: No new valid images found after filtering.")
        return None
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

def add_watermark(url):
    print("--- Step 2: Watermarking Image ---")
    try:
        r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        with open('temp.jpg', 'wb') as f: f.write(r.content)
        
        # File check: Kahin khali toh nahi download hui?
        if os.path.getsize('temp.jpg') < 1000:
            print("Error: Downloaded file is too small or corrupted.")
            return False

        img = Image.open('temp.jpg').convert("RGB")
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
        print(f"Watermark Error: {e}")
        return False

def upload_to_catbox():
    print("--- Step 3: Uploading to Catbox ---")
    try:
        url = "https://catbox.moe/user/api.php"
        with open("final.jpg", "rb") as f:
            r = requests.post(url, data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=60)
            if r.status_code == 200:
                print(f"SUCCESS: Catbox Link -> {r.text}")
                return r.text
    except Exception as e:
        print(f"Upload Error: {e}")
    return None

def post_to_forum(p, image_link):
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
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded", timeout=90000)
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        
        content = f"[IMG]{image_link}[/IMG]\n\nFresh Desi Bhabhi Update! 🔥\nCheck: {WATERMARK_TEXT}"
        
        editor.click()
        page.keyboard.type(content)
        time.sleep(2)
        
        page.locator('button:has-text("Post reply"), .button--icon--reply').first.click()
        
        time.sleep(8)
        print("--- TASK COMPLETED: SUCCESS ---")
    except Exception as e:
        print(f"Forum Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                hosted_url = upload_to_catbox()
                if hosted_url:
                    post_to_forum(playwright, hosted_url)
