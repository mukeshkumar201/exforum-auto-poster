import os, requests, time, random, json, re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_images.txt"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

WATERMARK_VARIANTS = [
    "freepornx [dot] site", "freepornx {dot} site", "freepornx (dot) site", 
    "f\u200Breepornx\u200B.\u200Bsite", "freepornx [.] site", "freepornx DOT site"
]

def get_new_image():
    print("--- Step 1: Scraping Image ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get("https://www.pornpics.com/tags/desi/", headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        target_gal = random.choice(links)
        if not target_gal.startswith('http'): target_gal = "https://www.pornpics.com" + target_gal
        
        r_gal = requests.get(target_gal, headers=headers, timeout=30)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') if "pornpics.com" in (img.get('data-src') or img.get('src', ''))]
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        
        if new_imgs: 
            img_url = random.choice(new_imgs).replace('/460/', '/1280/')
            print(f"Found Image: {img_url}")
            return img_url
        return None
    except Exception as e:
        print(f"Scrape Error: {e}"); return None

def add_watermark(url):
    img_wm = random.choice(WATERMARK_VARIANTS)
    print(f"--- Step 2: Watermarking with [{img_wm}] ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.pornpics.com/'
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"Failed to download image. Status: {r.status_code}")
            return None
            
        with open('temp.jpg', 'wb') as f: 
            f.write(r.content)
            
        img = Image.open('temp.jpg').convert("RGB")
        img.thumbnail((1280, 1280), Image.LANCZOS)
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.065)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), img_wm, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos = random.choice([(w-tw-40, h-th-40), (40, h-th-40), (w-tw-40, 40), (40, 40)])
        
        for adj in range(-1, 2):
            for b in range(-1, 2): 
                draw.text((pos[0]+adj, pos[1]+b), img_wm, fill="black", font=font)
        draw.text(pos, img_wm, fill="white", font=font)
        
        img.save('final.jpg', "JPEG", quality=85)
        return img_wm
    except Exception as e:
        print(f"Watermark Error: {e}"); return None

def upload_and_post(p, used_wm):
    print("--- Step 3 & 4: Uploading & Posting ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    
    cookies_raw = os.environ.get('EX_COOKIES')
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()

    try:
        # ImageBam Upload
        print("Uploading to ImageBam...")
        page.goto("https://www.imagebam.com/", wait_until="networkidle")
        page.set_input_files('input[type="file"]', 'final.jpg')
        page.click('button:has-text("Start upload")')
        
        page.wait_for_selector('textarea', timeout=60000)
        all_text = page.content()
        
        thumb_match = re.search(r'https://thumbs\d+\.imagebam\.com/[\w/]+_t\.(?:jpeg|jpg|png|webp)', all_text)
        if not thumb_match:
            print("Link not found on ImageBam."); return

        direct_url = thumb_match.group(0).replace('thumbs', 'images').replace('_t.', '.')
        print(f"Direct Link: {direct_url}")

        # Post to Forum
        print("Posting to Forum...")
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded")
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        
        full_content = f"[IMG]{direct_url}[/IMG]\n\nFresh Update! 🔥\nCheck more: {used_wm}\n#Desi #Hot #Bhabhi"
        
        editor.click()
        page.keyboard.type(full_content)
        time.sleep(2)
        page.locator('button.button--icon--reply').first.click()
        time.sleep(8)
        
        with open(HISTORY_FILE, "a") as f: f.write(direct_url + "\n")
        print("--- ALL STEPS SUCCESSFUL ---")

    except Exception as e:
        print(f"Process Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            used_wm = add_watermark(img_url)
            if used_wm:
                upload_and_post(playwright, used_wm)
