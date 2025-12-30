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
        print("Watermark applied.")
        return True
    except Exception as e:
        print(f"Watermark Error: {e}")
        return False

def post_to_forum(p):
    print("--- Step 3: Posting to Forum (Direct Fix) ---")
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
        print(f"Navigating to {THREAD_REPLY_URL}...")
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        print("Editor is ready.")

        # --- FIX START ---
        print("Injecting file into the LAST hidden upload input...")
        # multiple inputs mein se humesha 'last' wala choose karein taaki strict mode error na aaye
        file_input = page.locator('input[type="file"]').last
        file_input.set_input_files('final.jpg')
        
        print("Triggering upload event...")
        # JavaScript se last input ka change event fire karein
        page.evaluate('''() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            const lastInput = inputs[inputs.length - 1];
            if(lastInput) lastInput.dispatchEvent(new Event('change', { bubbles: true }));
        }''')
        # --- FIX END ---

        print("Waiting for image to appear in editor...")
        success_upload = False
        for i in range(25): # Wait 2 minutes
            time.sleep(5)
            content = editor.inner_html()
            if any(marker in content for marker in ["[IMG]", "img", "data-p-id", "blob:"]):
                print(f"SUCCESS: Image detected in editor (Attempt {i+1})!")
                success_upload = True
                break
            print(f"Checking Editor (Attempt {i+1})...")

        if not success_upload:
            print("Image not auto-inserted. Trying fallback 'Insert' button...")
            insert_btn = page.locator('button:has-text("Insert"), .js-attachmentAction').first
            if insert_btn.is_visible():
                insert_btn.click()
                time.sleep(2)
                full_img = page.locator('button:has-text("Full image")').first
                if full_img.is_visible(): full_img.click()
                success_upload = True

        if not success_upload:
            print("FAILED: Image upload logic failed.")
            page.screenshot(path="failed_upload.png")
            return

        # Finalizing Text
        print("Adding message text...")
        editor.focus()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\nLatest Fresh Desi Update! 🔥\nCheck more: {WATERMARK_TEXT}")
        time.sleep(2)

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
            post_to_forum(playwright)
