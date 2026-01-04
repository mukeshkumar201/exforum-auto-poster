import os, requests, time, random, json, io
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---
HISTORY_FILE = "posted_urls.txt"
PORN_SOURCE = "https://www.pornpics.com/tags/indian-pussy/"
THREAD_REPLY_URL = "https://exforum.live/threads/office-party-mein-boss-ki-biwi-chodi-1.203512/reply"

IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY')
EX_COOKIES = os.environ.get('EX_COOKIES')

def add_watermark(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB': img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        width, height = img.size
        font_size = int(width * 0.05)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        text = "freepornx.site"
        bbox = draw.textbbox((0, 0), text, font=font)
        x, y = width - (bbox[2]-bbox[0]) - 20, height - (bbox[3]-bbox[1]) - 20
        draw.text((x+2, y+2), text, font=font, fill="black")
        draw.text((x, y), text, font=font, fill="white")
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=95)
        return img_io.getvalue()
    except: return None

def upload_to_imgbb(img_bytes):
    api_url = "https://api.imgbb.com/1/upload"
    payload = {"key": IMGBB_API_KEY, "expiration": "0"}
    files = {"image": ("image.jpg", img_bytes, "image/jpeg")}
    try:
        r = requests.post(api_url, data=payload, files=files)
        res = r.json()
        if res.get("status") == 200:
            link = res["data"]["url"]
            print(f"SUCCESS: ImgBB Link -> {link}")
            return link
        return None
    except: return None

def get_processed_image():
    print("--- Step 1: Scraping and Processing ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(PORN_SOURCE, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        gal_links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        target = random.choice(gal_links)
        if not target.startswith('http'): target = "https://www.pornpics.com" + target
        
        r_gal = requests.get(target, headers=headers)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') 
                      if "pornpics.com" in (img.get('data-src') or img.get('src', ''))]
        
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        if new_imgs:
            sel = random.choice(new_imgs)
            print(f"Processing Image: {sel}")
            raw = requests.get(sel).content
            marked = add_watermark(raw)
            if marked:
                final = upload_to_imgbb(marked)
                if final:
                    with open(HISTORY_FILE, "a") as f: f.write(sel + "\n")
                    return final
        return None
    except: return None

def post_to_forum(p, hosted_url):
    print("--- Step 4: Posting to Forum ---")
    # Chrome jaisa behavior set kiya hai
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1280, 'height': 720}
    )
    
    try:
        cookies_list = json.loads(EX_COOKIES)
        context.add_cookies(cookies_list)
    except:
        print("CRITICAL: Cookie JSON format error."); return

    page = context.new_page()
    try:
        page.goto(THREAD_REPLY_URL, wait_until="networkidle", timeout=60000)
        time.sleep(5)
        
        # New Login Check: Agar 'Log in' button dikh raha hai, toh login nahi hua
        is_login_button = page.locator('a:has-text("Log in"), span:has-text("Log in")').first
        if is_login_button.is_visible():
            print(f"CRITICAL: Login Failed. Redirected to: {page.url}")
            return

        editor = page.locator('.fr-element').first
        editor.wait_for(state="visible", timeout=30000)
        editor.focus()
        page.keyboard.type(f"[IMG]{hosted_url}[/IMG]")
        time.sleep(3)
        
        # Click Reply
        page.locator('button:has-text("Post reply"), .button--icon--reply').first.click()
        page.wait_for_timeout(10000)
        print("--- SUCCESS: IMAGE POSTED ---")
    except Exception as e:
        print(f"Forum Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        link = get_processed_image()
        if link:
            post_to_forum(playwright, link)
