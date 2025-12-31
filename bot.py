import os, requests, time, random, json, sys, re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

# --- Configuration ---
HISTORY_FILE = "posted_images.txt"
THREAD_REPLY_URL = "https://exforum.live/threads/desi-bhabhi.203220/reply"

# 1. Random Watermark & Caption Variants (Ban se bachne ke liye)
WATERMARK_VARIANTS = [
    "freepornx [dot] site", "freepornx {dot} site", "freepornx (dot) site", 
    "freepornx | site", "f r e e p o r n x . s i t e", "f\u200Breepornx\u200B.\u200Bsite",
    "freepornx [.] site", "freepornx ( . ) site", "freepornx / site", "FreePornX.Site",
    "freepornx DOT site", "freepornx * site", "freepornx ~ site", "freepornx ::: site",
    "f.r.e.e.p.o.r.n.x.s.i.t.e", "freepornx @ site", "freepornx_site", "FrEePoRnX.SiTe",
    "f-r-e-e-p-o-r-n-x-site", "freepornx [at] site"
]

CAPTIONS = [
    "Fresh Desi Bhabhi Update! 🔥", "New Indian Mallu Auntie Pics 🍑",
    "Desi Girl Next Door - Exclusive! 💦", "Latest Desi Collection updated now. 🔞",
    "Sunday Special Desi Bhabhi Dhamaka! 💥", "Hot Desi Auntie checking in... 👄",
    "Something fresh for you guys! ❤️", "Desi bhabhi ka jalwa! 🌶️"
]

TAGS_POOL = ["#Desi", "#Bhabhi", "#Indian", "#Hot", "#Auntie", "#Mallu", "#Exclusive", "#Trending"]

def get_new_image():
    print("--- Step 1: Scraping Image from PornPics ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get("https://www.pornpics.com/tags/desi/", headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "/galleries/" in a['href']]
        target_gal = random.choice(links)
        if not target_gal.startswith('http'): target_gal = "https://www.pornpics.com" + target_gal
        
        r_gal = requests.get(target_gal, headers=headers, timeout=30)
        gal_soup = BeautifulSoup(r_gal.text, 'html.parser')
        posted = open(HISTORY_FILE, "r").read().splitlines() if os.path.exists(HISTORY_FILE) else []
        
        valid_imgs = [img.get('data-src') or img.get('src') for img in gal_soup.find_all('img') 
                      if "pornpics.com" in (img.get('data-src') or img.get('src', '')) and '.svg' not in (img.get('data-src') or img.get('src', ''))]
        
        new_imgs = [u if u.startswith('http') else "https:" + u for u in valid_imgs if u not in posted]
        if new_imgs:
            img_url = random.choice(new_imgs).replace('/460/', '/1280/') 
            with open(HISTORY_FILE, "a") as f: f.write(img_url + "\n")
            return img_url
        return None
    except Exception as e:
        print(f"Scrape Error: {e}"); return None

def add_watermark(url):
    img_wm = random.choice(WATERMARK_VARIANTS)
    print(f"--- Step 2: Watermarking Image with [{img_wm}] ---")
    try:
        r = requests.get(url, timeout=30)
        with open('temp.jpg', 'wb') as f: f.write(r.content)
        img = Image.open('temp.jpg').convert("RGB")
        img.thumbnail((1280, 1280), Image.LANCZOS)
        
        draw = ImageDraw.Draw(img)
        w, h = img.size
        fs = int(h * 0.065)
        try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except: font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), img_wm, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # Random Position: Bottom-Right, Bottom-Left, Top-Right, Top-Left
        positions = [(w-tw-40, h-th-40), (40, h-th-40), (w-tw-40, 40), (40, 40)]
        pos = random.choice(positions)

        for adj in range(-1, 2):
            for b in range(-1, 2):
                draw.text((pos[0]+adj, pos[1]+b), img_wm, fill="black", font=font)
        draw.text(pos, img_wm, fill="white", font=font)
        
        img.save('final.jpg', "JPEG", quality=85, optimize=True)
        return img_wm
    except Exception as e:
        print(f"Watermark Error: {e}"); return None

def upload_to_imagebam():
    print("--- Step 3: Hosting on ImageBam ---")
    try:
        url = "https://www.imagebam.com/sys/upload/save"
        files = {'image[]': ('image.jpg', open('final.jpg', 'rb'), 'image/jpeg')}
        data = {'gallery_id': '0', 'thumb_size': '350', 'thumb_aspect_ratio': '0', 'thumb_file_type': 'jpg'}
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.post(url, files=files, data=data, headers=headers, timeout=60)
        
        match = re.search(r'https://images\d+\.imagebam\.com/[\w/]+/final\.jpg', r.text)
        if not match: match = re.search(r'https://www\.imagebam\.com/image/\w+', r.text)
        if match: return match.group(0)
    except Exception as e:
        print(f"ImageBam Error: {e}")
    return None

def post_to_forum(p, image_link, used_wm):
    print("--- Step 4: Posting to Forum ---")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    cookies_raw = os.environ.get('EX_COOKIES')
    context.add_cookies(json.loads(cookies_raw))
    page = context.new_page()
    
    try:
        page.goto(THREAD_REPLY_URL, wait_until="domcontentloaded", timeout=90000)
        editor = page.locator('.fr-element')
        editor.wait_for(state="visible")
        
        my_caption = random.choice(CAPTIONS)
        my_tags = " ".join(random.sample(TAGS_POOL, 3))
        
        # Caption mein bhi wahi random variant jayega
        full_content = f"[IMG]{image_link}[/IMG]\n\n{my_caption}\n\nCheck out more on: {used_wm}\n\n{my_tags}"
        
        editor.click()
        page.keyboard.type(full_content)
        time.sleep(2)
        
        page.locator('button.button--icon--reply').first.click()
        time.sleep(10)
        print(f"--- SUCCESS: Posted Image with caption and tags ---")
    except Exception as e:
        print(f"Forum Error: {e}")
    finally:
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        img_url = get_new_image()
        if img_url:
            used_wm = add_watermark(img_url)
            if used_wm:
                hosted_url = upload_to_imagebam()
                if hosted_url:
                    post_to_forum(playwright, hosted_url, used_wm)
