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

def post_to_forum(p):
    print("--- Step 3: Posting to Forum via Playwright ---")
    # Debugging ke liye headless=False rakha hai, kaam karne lage to True kar dena
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"]) 
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing! Make sure to set env variable.")
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

        # ---------------------------------------------------------
        # FIX START: Iframe Handling for ImgBB
        # ---------------------------------------------------------
        print("Opening Upload Popup...")
        
        # 1. Trigger button click karo
        page.click('button[data-chevereto-pup-trigger]', force=True)
        
        # 2. Iframe ke load hone ka wait karo
        # ImgBB usually ek iframe load karta hai popup ke andar
        print("Waiting for ImgBB Iframe...")
        page.wait_for_selector('iframe', state="attached")
        
        # Sare iframes me se last wala usually popup hota hai
        # Hum generic iframe target kar rahe hain
        upload_frame = page.frame_locator('iframe').last
        
        # 3. File Input Frame ke andar dhundo aur file upload karo
        print("Injecting file into Iframe input...")
        # Tere HTML ke hisab se input ki ID 'anywhere-upload-input' hai
        file_input = upload_frame.locator('#anywhere-upload-input') 
        file_input.set_input_files('final.jpg')
        print("File set successfully inside iframe.")

        # 4. Upload hone ke baad 'Insert' button ka wait karo
        # HTML me button ka selector: button[data-action='openerPostMessage']
        print("Waiting for upload to finish & Insert button...")
        
        insert_btn = upload_frame.locator("button[data-action='openerPostMessage']")
        # Upload me time lag sakta hai isliye timeout badhaya
        insert_btn.wait_for(state="visible", timeout=90000) 
        
        # Thoda safety pause
        time.sleep(1)
        insert_btn.click()
        print("Clicked 'Insert' - Image code should be in editor now.")

        # ---------------------------------------------------------
        # FIX END
        # ---------------------------------------------------------

        # 5. Check karo ki BBCode editor me aaya ya nahi
        time.sleep(3) # Insert ke baad thoda wait
        content = editor.inner_html()
        
        if "[IMG]" in content or "img" in content.lower():
             print("SUCCESS: Image BBCode detected!")
        else:
             print("WARNING: Link not detected automatically. Checking fallback...")

        # 6. Text Message add karna
        editor.click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nFresh Desi Bhabhi Update! 🔥\nCheck: {WATERMARK_TEXT}")
        time.sleep(2)

        # 7. Submit
        print("Submitting post...")
        submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
        submit_btn.click()
        
        print("Post submitted. Waiting for redirection...")
        time.sleep(5)
        page.screenshot(path="final_check.png")
        print("--- BOT TASK FINISHED ---")
        
    except Exception as e:
        print(f"Forum Error: {e}")
        page.screenshot(path="error_debug.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
