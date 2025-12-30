import os
import requests
import time
import random
import json
import base64
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

# --- Step 3: Posting to Forum (JS INJECTION METHOD) ---
def post_to_forum(p):
    print("--- Step 3: Posting via JS Injection (No Buttons Needed) ---")
    
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    if not cookies_raw:
        print("CRITICAL: EX_COOKIES missing!")
        return
        
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    page.set_default_timeout(60000)
    
    try:
        print(f"Navigating to: {THREAD_REPLY_URL}")
        page.goto(THREAD_REPLY_URL, wait_until="networkidle")
        
        # Editor load hone ka wait
        editor_selector = '.fr-element'
        page.wait_for_selector(editor_selector, state="visible")
        print("Editor loaded.")

        # --- MAGIC: Convert Image to Base64 & Inject ---
        print("Preparing image for injection...")
        with open("final.jpg", "rb") as image_file:
            b64_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        print("Injecting image via JavaScript Drag-Event...")
        
        # Ye JavaScript browser ke andar run karegi. 
        # Ye 'fake' file banayegi aur editor par 'drop' kar degi.
        page.evaluate(f"""
            async () => {{
                const b64 = "{b64_string}";
                const mime = "image/jpeg";
                const filename = "final.jpg";

                // Base64 se Blob banana
                const res = await fetch(`data:${{mime}};base64,${{b64}}`);
                const blob = await res.blob();
                const file = new File([blob], filename, {{ type: mime }});

                // DataTransfer object banana (Drag event ke liye)
                const dt = new DataTransfer();
                dt.items.add(file);
                const list = dt.files;

                // Editor dhoondna
                const editor = document.querySelector('{editor_selector}');
                
                // Drop Event Fire karna
                const event = new DragEvent('drop', {{
                    bubbles: true,
                    cancelable: true,
                    dataTransfer: dt
                }});
                editor.dispatchEvent(event);
            }}
        """)
        
        print("JS Injection executed. Waiting for upload to process...")
        time.sleep(5) # Thoda wait taaki upload start ho jaye

        # --- VERIFICATION ---
        uploaded = False
        for i in range(15): # 45 seconds total wait
            content = page.locator(editor_selector).inner_html()
            # [IMG] tag ya <img src="..."> dhoondo
            if "[IMG]" in content or "<img" in content.lower():
                print(f"SUCCESS: Image code detected in editor!")
                uploaded = True
                break
            print(f"Processing upload... {i+1}/15")
            time.sleep(3)

        if not uploaded:
            print("ERROR: Upload failed. Check 'upload_failed.png'.")
            page.screenshot(path="upload_failed.png")
            return

        # --- SUBMIT ---
        print("Adding text and submitting...")
        page.locator(editor_selector).click()
        page.keyboard.press("Control+End")
        page.keyboard.type(f"\n\n🔥 Desi Bhabhi Latest Leak! 🔥\nMore at: {WATERMARK_TEXT}")
        time.sleep(2)

        submit_btn = page.locator('button:has-text("Post reply")').first
        if not submit_btn.is_visible():
            submit_btn = page.locator('.button--icon--reply').first
            
        if submit_btn.is_visible():
            submit_btn.click()
            page.wait_for_timeout(5000)
            page.screenshot(path="success_post.png")
            print("--- BOT TASK FINISHED SUCCESSFULLY ---")
        else:
            print("Submit button missing!")

    except Exception as e:
        print(f"Script Error: {e}")
        page.screenshot(path="error_crash.png")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            if add_watermark(img_url):
                post_to_forum(playwright)
