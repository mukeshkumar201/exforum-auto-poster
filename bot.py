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
    print("--- Step 2: Watermarking Image ---")
    try:
        r = requests.get(url, timeout=30)
        with open('img.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('img.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.08)
        
        try:
            # Font path for Linux/GitHub Actions
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = (w - tw - 50, h - th - 50)

        # Black outline for visibility
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

def upload_to_free_host(file_path):
    print("--- Step 2.5: Uploading to Telegra.ph (Free) ---")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': ('file', f, 'image/jpeg')}
            r = requests.post('https://telegra.ph/upload', files=files)
            data = r.json()
            if isinstance(data, list) and 'src' in data[0]:
                hosted_url = 'https://telegra.ph' + data[0]['src']
                print(f"Hosted Link: {hosted_url}")
                return hosted_url
        return None
    except Exception as e:
        print(f"Hosting Error: {e}")
        return None

def post_to_forum(p, hosted_url):
    print("--- Step 3: Posting to Forum via Image URL ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(90000)
    
    try:
        print(f"Opening Forum Reply: {THREAD_REPLY_URL}")
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        # 1. Editor Check
        editor = page.locator('.fr-element').first
        editor.wait_for(state="visible")
        print("Froala Editor is ready.")

        # 2. Click "Insert Image" Toolbar Button
        # Id 'insertImage-1' use ho raha hai aapke toolbar mein
        print("Clicking Toolbar Image Button...")
        page.click('#insertImage-1', force=True)
        
        # 3. Wait for URL Input and Fill it
        print("Filling Image URL...")
        # Froala ka URL input field dhoondna
        url_input = page.locator('input.fr-link-input, input[placeholder*="URL"]').first
        url_input.wait_for(state="visible", timeout=15000)
        url_input.fill(hosted_url)

        # 4. Press "Insert" Button in Popup
        print("Inserting URL into Editor...")
        # Command button for URL insert
        page.keyboard.press("Enter") # Aksar enter se insert ho jata hai
        time.sleep(3)
        
        # Agar enter se na ho toh direct button click
        insert_confirm = page.locator('button:has-text("Insert")').first
        if insert_confirm.is_visible():
            insert_confirm.click()

        # 5. Add Text Content
        print("Adding caption text...")
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nFresh Desi Update! 🔥\nEnjoy: {WATERMARK_TEXT}")
        time.sleep(2)

        # 6. Submit Post
        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        page.wait_for_timeout(10000)
        page.screenshot(path="final_check.png")
        print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url and add_watermark(img_url):
            hosted_link = upload_to_free_host('final.jpg')
            if hosted_link:
                post_to_forum(playwright, hosted_link)
            else:
                print("Hosting failed.")
