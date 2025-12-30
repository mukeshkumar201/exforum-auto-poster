import os, requests, time, random, json
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
WATERMARK_TEXT = "freepornx.site"
PORN_SOURCE = "https://www.pornpics.com/tags/desi/"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

def get_new_image():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(PORN_SOURCE, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        if not links: return None
        
        target_gal = random.choice(links)
        target_gal = target_gal if target_gal.startswith('http') else "https://www.pornpics.com" + target_gal
        
        r_gal = requests.get(target_gal, headers=headers, timeout=20)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') if "pornpics.com" in (img.get('data-src') or img.get('src', ''))]
        
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        if new_imgs:
            img_url = random.choice(new_imgs)
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
        return None
    except: return None

def add_watermark(url):
    print("--- Step: Watermarking image ---")
    try:
        img_data = requests.get(url).content
        with open('img.jpg', 'wb') as f: f.write(img_data)
        img = Image.open('img.jpg').convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.05)
        pos = (w - (len(WATERMARK_TEXT) * (fs // 2)) - 30, h - fs - 30)
        for adj in range(-1, 2):
            for b in range(-1, 2): draw.text((pos[0]+adj, pos[1]+b), WATERMARK_TEXT, fill="black")
        draw.text(pos, WATERMARK_TEXT, fill="white")
        img.save('final.jpg')
        return True
    except: return False

def upload_anonymous():
    """Bina kisi API key ke image upload karne ke liye (Catbox/File.io fallback)"""
    print("--- Step: Hosting image anonymously ---")
    try:
        # Using Catbox.moe for stable anonymous hosting
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        files = {"fileToUpload": open("final.jpg", "rb")}
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            print(f"Hosted Link: {response.text}")
            return response.text
    except Exception as e:
        print(f"Hosting failed: {e}")
    return None

def post_to_forum(image_link):
    with sync_playwright() as p:
        print("--- Step: Launching Browser ---")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        cookies_raw = os.environ.get('EX_COOKIES')
        context.add_cookies(json.loads(cookies_raw))
        
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            print("--- Navigating to Thread ---")
            page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
            
            # Editor check
            editor = page.locator('.fr-element')
            editor.wait_for(state="visible")

            print("--- Inserting Content ---")
            # Image Link + Text Message
            content = f"[IMG]{image_link}[/IMG]\n\nFresh Update! 🔥\nCheck: {WATERMARK_TEXT}"
            
            editor.click()
            page.keyboard.type(content)
            time.sleep(3)

            print("--- Submitting Post ---")
            submit_btn = page.locator('button:has-text("Post reply"), .button--icon--reply').first
            submit_btn.click()
            
            time.sleep(8)
            print("--- BOT COMPLETED SUCCESSFULLY ---")
            return True

        except Exception as e:
            print(f"Post Error: {e}")
            page.screenshot(path="error_debug.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    img = get_new_image()
    if img and add_watermark(img):
        hosted_url = upload_anonymous()
        if hosted_url:
            post_to_forum(hosted_url)
