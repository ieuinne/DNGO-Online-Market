import mysql.connector
import pandas as pd
import re
import random
import string
import requests
from io import BytesIO
from PIL import Image
from google.cloud import storage
import unicodedata
import sys
import time
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================================
# CẤU HÌNH DATABASE
# ============================================================
DB_CONFIG = {
    "host": "136.110.35.142",
    "user": "DA1",
    "password": "choonline43",
    "database": "DNGO",
    "charset": "utf8mb4"
}

BUCKET_NAME = "monan-bucket"
BASE_URL = "https://monngonmoingay.com"
TOTAL_PAGES = 203
MAX_STOP = 3

# ============================================================
# PHẦN 1: CÀO DỮ LIỆU TỪ WEBSITE
# ============================================================

def connect_database():
    """Kết nối đến Cloud SQL"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("☁️ Đã kết nối Cloud SQL thành công!")
        return conn
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        sys.exit(1)

def safe_get(url, session, retries=3, timeout=10):
    """Tải trang web an toàn với retry"""
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"⚠️ Lỗi tải {url}: {e}")
        time.sleep(1 + i)
    return None

def link_exists_in_db(link, cursor):
    """Kiểm tra link đã tồn tại trong DB chưa"""
    cursor.execute("SELECT 1 FROM rawdata_test WHERE `Link món ăn` = %s", (link,))
    return cursor.fetchone() is not None

def parse_list_page(html):
    """Phân tích trang danh sách món ăn"""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for item in soup.select("div.flex-recipe"):
        a_tag = item.find("a", title=True)
        if not a_tag:
            continue

        link = BASE_URL + a_tag["href"] if a_tag["href"].startswith("/") else a_tag["href"]
        ten = a_tag["title"].strip()

        img = item.find("img")
        img_url = img["src"] if img else None
        if img_url and img_url.startswith("/"):
            img_url = BASE_URL + img_url

        tags = item.select("div.tags div.tag")
        khau_phan = tags[0].get_text(strip=True) if len(tags) >= 1 else None
        do_kho = tags[1].get_text(strip=True) if len(tags) >= 2 else None
        thoi_gian = tags[2].get_text(strip=True) if len(tags) >= 3 else None

        results.append({
            "link": link,
            "ten": ten,
            "anh": img_url,
            "khau_phan": khau_phan,
            "do_kho": do_kho,
            "thoi_gian": thoi_gian
        })

    return results

def crawl_details_and_save(temp_df, cursor, conn, session):
    """Cào chi tiết món ăn và lưu vào MySQL"""
    if temp_df.empty:
        print("Không có món mới.")
        return

    print(f"\n🔍 BẮT ĐẦU CÀO CHI TIẾT {len(temp_df)} MÓN...")

    for idx, row in temp_df.iterrows():
        link = row['link']
        ten = row['ten']
        print(f"\n[{idx+1}/{len(temp_df)}] {ten}")

        try:
            html = safe_get(link, session)
            if not html:
                print("Lỗi tải link.")
                continue

            soup = BeautifulSoup(html, "html.parser")

            # === DANH MỤC ===
            ul = soup.select_one("div.flex.flex-col.gap-2.items-center > ul")
            danh_muc = ", ".join(li.get_text(strip=True) for li in ul.select("li")) if ul else None

            # === CALORIES ===
            calories = None
            for table in soup.find_all("table"):
                for td in table.find_all("td"):
                    match = re.search(r"\d+\s*kcal", td.get_text(), re.IGNORECASE)
                    if match:
                        calories = match.group(0)
                        break

            # === NGUYÊN LIỆU ===
            nl_div = soup.select_one("div.block-nguyenlieu.tab-content#tab-muong ul")
            nguyen_lieu = ", ".join(li.get_text(strip=True) for li in nl_div.select("li")) if nl_div else None

            # === SƠ CHẾ ===
            sc_div = soup.select_one("#section-soche")
            so_che = "\n".join(t.get_text(strip=True) for t in sc_div.select("p,li,span")) if sc_div else None

            # === CÁCH THỰC HIỆN ===
            th_div = soup.find("div", id="section-thuchien")
            cach_thuc_hien = None
            if th_div:
                cach_thuc_hien = "\n".join(t.get_text(strip=True) for t in th_div.find_all("p"))

            # === CÁCH DÙNG ===
            cd_divs = soup.select("#section-howtouse > div")
            cach_dung = "\n".join(div.get_text(strip=True) for div in cd_divs) if cd_divs else None

            # === LƯU MYSQL ===
            cursor.execute("""
                INSERT INTO rawdata_test(
                    `Calories`, `Cách dùng`, `Cách thực hiện`, `Danh mục món ăn`,
                    `Hình ảnh`, `Khẩu phần`, `Link món ăn`, `Nguyên liệu`,
                    `Sơ chế`, `Thời gian thực hiện`, `Tên món ăn`, `Độ khó`
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                calories,
                cach_dung,
                cach_thuc_hien,
                danh_muc,
                row["anh"],
                row["khau_phan"],
                link,
                nguyen_lieu,
                so_che,
                row["thoi_gian"],
                ten,
                row["do_kho"]
            ))

            conn.commit()
            print(f"  ✓ Đã lưu: {ten}")

        except Exception as e:
            print(f"❌ Lỗi chi tiết: {e}")
            conn.rollback()

        time.sleep(random.uniform(1.2, 2.0))

    print("\n✅ HOÀN TẤT CÀO CHI TIẾT!")

def crawl_data():
    """Hàm chính cào dữ liệu từ website"""
    print("\n" + "="*60)
    print("🌐 BẮT ĐẦU CÀO DỮ LIỆU TỪ WEBSITE")
    print("="*60)
    
    # Kết nối database
    conn = connect_database()
    cursor = conn.cursor(buffered=True)
    
    # Tạo session requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    # DataFrame tạm để lưu món mới
    temp_data = []
    no_new_count = 0
    
    print("📄 Đang cào danh sách món ăn...")
    
    for page in range(1, TOTAL_PAGES + 1):
        url = f"{BASE_URL}/tim-kiem-mon-ngon/page/{page}/"
        print(f"\nTrang {page}...")
        
        html = safe_get(url, session)
        if not html:
            no_new_count += 1
            print("Không tải được trang.")
            if no_new_count >= MAX_STOP:
                print("⛔ DỪNG vì liên tiếp 3 trang lỗi.")
                break
            continue
        
        data = parse_list_page(html)
        
        if not data:
            no_new_count += 1
            print("Trang không có món.")
            if no_new_count >= MAX_STOP:
                print("⛔ DỪNG vì 3 trang trống.")
                break
            continue
        
        added_in_page = 0
        for item in data:
            link = item["link"]
            
            # Kiểm tra đã tồn tại chưa
            if link_exists_in_db(link, cursor):
                continue
            
            temp_data.append(item)
            added_in_page += 1
            print(f"  + {item['ten']}")
        
        print(f"Trang {page}: +{added_in_page} món mới")
        
        if added_in_page == 0:
            no_new_count += 1
            if no_new_count >= MAX_STOP:
                print("⛔ DỪNG vì 3 trang liên tiếp không có món mới.")
                break
        else:
            no_new_count = 0
        
        time.sleep(random.uniform(1, 2))
    
    # Cào chi tiết các món mới
    if temp_data:
        temp_df = pd.DataFrame(temp_data)
        print(f"\n📊 TỔNG MỚI: {len(temp_df)} món → Cào chi tiết...")
        crawl_details_and_save(temp_df, cursor, conn, session)
    else:
        print("\nℹ️ Không có món mới nào.")
    
    # Đóng kết nối
    cursor.close()
    conn.close()
    print("🔒 Đã đóng kết nối database (cào dữ liệu)")
    
    return len(temp_data) > 0  # Trả về True nếu có dữ liệu mới

# ============================================================
# PHẦN 2: XỬ LÝ DỮ LIỆU VÀ UPLOAD LÊN CLOUD
# ============================================================

def random_code():
    """Tạo mã món ăn ngẫu nhiên"""
    return "M" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def extract_number(v):
    """Trích xuất số từ chuỗi"""
    if pd.isna(v):
        return 0
    m = re.search(r'\d+', str(v))
    return int(m.group()) if m else 0

def read_rawdata(conn):
    """Đọc dữ liệu chưa xử lý từ rawdata_test"""
    print("\n" + "="*60)
    print("📥 ĐỌC DỮ LIỆU RAWDATA")
    print("="*60)
    
    df_raw = pd.read_sql("SELECT * FROM rawdata_test;", conn)
    
    df_chua_xu_ly = df_raw[df_raw["tinh_trang_xu_ly"] == 0].copy()
    df_chua_xu_ly = df_chua_xu_ly.rename(columns={
        "Tên món ăn": "ten_mon_an",
        "Calories": "calories",
        "Cách dùng": "cach_dung",
        "Cách thực hiện": "cach_thuc_hien",
        "Danh mục món ăn": "danh_muc_mon_an",
        "Hình ảnh": "hinh_anh",
        "Khẩu phần": "khau_phan",
        "Link món ăn": "link_mon_an",
        "Nguyên liệu": "nguyen_lieu",
        "Sơ chế": "so_che",
        "Thời gian thực hiện": "thoi_gian_thuc_hien",
        "Độ khó": "do_kho",
    })
    
    print(f"📊 Số dòng chưa xử lý: {len(df_chua_xu_ly)}")
    
    if len(df_chua_xu_ly) == 0:
        print("⚠️ Không có dữ liệu mới cần xử lý!")
        return None
    
    return df_chua_xu_ly

def upload_image_to_cloud(image_url, blob_name, bucket):
    """Upload hình ảnh lên Google Cloud Storage"""
    try:
        resp = requests.get(image_url, timeout=8)
        if resp.status_code != 200:
            return None

        img_bytes = BytesIO(resp.content)
        blob = bucket.blob(blob_name)
        blob.upload_from_file(img_bytes, content_type="image/webp")
        blob.make_public()
        return blob.public_url

    except Exception as e:
        print(f"⚠️ Lỗi upload {blob_name}: {e}")
        return None

def process_images(df_chua_xu_ly):
    """Xử lý và upload tất cả hình ảnh"""
    print("\n" + "="*60)
    print("🖼️ XỬ LÝ HÌNH ẢNH")
    print("="*60)
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        
        count = 0
        for idx, row in df_chua_xu_ly.iterrows():
            link = row["hinh_anh"]
            if isinstance(link, str) and link.startswith("http") and "storage.googleapis.com" not in link:
                # Tạo tên file an toàn
                safe_name = re.sub(r'[^\w\-_]', '_', row['ten_mon_an'])
                blob_name = f"mon_an/{datetime.now().strftime('%Y%m%d')}/{safe_name}_{idx}.webp"
                new_link = upload_image_to_cloud(link, blob_name, bucket)
                if new_link:
                    df_chua_xu_ly.loc[idx, "hinh_anh"] = new_link
                    count += 1
                    print(f"  ✓ Uploaded: {blob_name}")
        
        print(f"✅ Đã upload {count} hình ảnh lên Cloud Storage")
        return df_chua_xu_ly
    except Exception as e:
        print(f"⚠️ Lỗi xử lý hình ảnh: {e}")
        return df_chua_xu_ly

def create_df_mon_an(df_chua_xu_ly):
    """Tạo DataFrame món ăn với mã món ăn"""
    print("\n" + "="*60)
    print("🍜 TẠO BẢNG MÓN ĂN")
    print("="*60)
    
    # Tạo mã món ăn
    df_chua_xu_ly["ma_mon_an"] = [random_code() for _ in range(len(df_chua_xu_ly))]
    
    # Chọn các cột cần thiết
    df_mon_an = df_chua_xu_ly[[
        "ma_mon_an", "ten_mon_an", "thoi_gian_thuc_hien", "do_kho",
        "khau_phan", "calories", "hinh_anh", "cach_thuc_hien",
        "cach_dung", "so_che"
    ]].copy()
    
    # Làm sạch dữ liệu số
    df_mon_an["thoi_gian_thuc_hien"] = df_mon_an["thoi_gian_thuc_hien"].apply(extract_number)
    df_mon_an["khau_phan"] = df_mon_an["khau_phan"].apply(extract_number)
    df_mon_an["calories"] = df_mon_an["calories"].apply(extract_number)
    
    # Xử lý dữ liệu trống
    df_mon_an = df_mon_an.fillna({
        "ten_mon_an": "",
        "do_kho": "",
        "hinh_anh": "",
        "cach_thuc_hien": "",
        "cach_dung": "",
        "so_che": ""
    })
    
    print(f"✅ Đã tạo {len(df_mon_an)} món ăn")
    
    return df_mon_an

def process_danh_muc(df_chua_xu_ly, conn):
    """Xử lý phân loại danh mục món ăn"""
    print("\n" + "="*60)
    print("🏷️ XỬ LÝ DANH MỤC MÓN ĂN")
    print("="*60)
    
    # Đọc danh mục từ Cloud
    query_dm = "SELECT ma_danh_muc_mon_an, ten_danh_muc_mon_an FROM danh_muc_mon_an;"
    df_dm_cloud = pd.read_sql(query_dm, conn)
    df_dm_cloud["ten_norm"] = df_dm_cloud["ten_danh_muc_mon_an"].str.lower().str.strip()
    
    print(f"📊 Có {len(df_dm_cloud)} danh mục trên Cloud")
    
    def tach_danh_muc(danh_muc):
        if pd.isna(danh_muc):
            return []
        return [x.strip().lower() for x in str(danh_muc).split(",") if x.strip()]
    
    rows = []
    
    for idx, row in df_chua_xu_ly.iterrows():
        ma_mon_an = row["ma_mon_an"]
        danh_muc_list = tach_danh_muc(row["danh_muc_mon_an"])
        
        for dm in danh_muc_list:
            match = df_dm_cloud[df_dm_cloud["ten_norm"] == dm]
            
            if not match.empty:
                ma_dm = match.iloc[0]["ma_danh_muc_mon_an"]
            else:
                ma_dm = None
            
            rows.append({
                "ma_mon_an": ma_mon_an,
                "ten_danh_muc": dm,
                "ma_danh_muc_mon_an": ma_dm
            })
    
    df_mapping = pd.DataFrame(rows)
    
    df_phan_loai = df_mapping[[
        "ma_mon_an",
        "ma_danh_muc_mon_an"
    ]].dropna(subset=["ma_danh_muc_mon_an"]).reset_index(drop=True)
    
    print(f"✅ Đã phân loại {len(df_phan_loai)} dòng")
    
    return df_phan_loai

def clean_raw_nguyen_lieu(text):
    """Làm sạch tên nguyên liệu thô"""
    if not isinstance(text, str):
        return ""
    
    # Bỏ phần định lượng
    text = re.sub(r'\b\d+([.,/]?\d+)?\s*[a-zA-ZÀ-ỹ]*\b', '', text)
    text = text.replace(':', '').replace(';', '')
    text = re.sub(r"[^a-zA-ZÀ-ỹ\s.,]", "", text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_all_ingredients(df_chua_xu_ly):
    """Tách tất cả nguyên liệu thành các nhóm"""
    nguyen_lieu_list = []
    
    for line in df_chua_xu_ly['nguyen_lieu']:
        if pd.notna(line):
            # Tách theo ** và xuống dòng
            items = re.split(r'\*\*|\n', str(line))
            items = [x.strip() for x in items if x.strip()]
            nguyen_lieu_list.extend(items)
    
    # Làm sạch
    nguyen_lieu_sach = [clean_raw_nguyen_lieu(x) for x in nguyen_lieu_list 
                       if clean_raw_nguyen_lieu(x)]
    
    # Tách nhóm
    gia_vi = [x for x in nguyen_lieu_sach if re.search(r'gia vị', x, re.IGNORECASE)]
    rau_gia_vi = [x for x in nguyen_lieu_sach if re.search(r'rau nêm', x, re.IGNORECASE)]
    dung_cu = [x for x in nguyen_lieu_sach if re.search(r'đồ dùng|dụng cụ', x, re.IGNORECASE)]
    
    # Loại bỏ các nhóm đặc biệt khỏi danh sách chính
    nguyen_lieu_sach = [
        x for x in nguyen_lieu_sach
        if not re.search(r'gia vị|rau nêm|ăn kèm|đồ dùng|dụng cụ', x, re.IGNORECASE)
    ]
    
    return nguyen_lieu_sach, gia_vi, rau_gia_vi, dung_cu

def process_gia_vi(gia_vi_list):
    """Xử lý danh sách gia vị"""
    gia_vi_items = []
    
    for item in gia_vi_list:
        if isinstance(item, str) and item.strip():
            # Xóa nội dung trong ngoặc
            item = re.sub(r'\(.*?\)|\[.*?\]|\{.*?\}|\<.*?\>', '', item)
            item = re.sub(r'\bgia vị\b', '', item, flags=re.IGNORECASE).strip()
            item = re.sub(r'mua tokyo shop|cao cấp\s*ajinomoto up|nêm sẵn|ajinomoto', 
                         '', item, flags=re.IGNORECASE)
            item = re.sub(r'\bhoặc\b.*', '', item, flags=re.IGNORECASE).strip()
            item = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s.,]', '', item)
            item = re.sub(r'\s+', ' ', item).strip()
            
            parts = re.split(r'[,.]', item)
            parts = [x.strip() for x in parts if x.strip()]
            gia_vi_items.extend(parts)
    
    gia_vi_unique_lower = list(dict.fromkeys([x.lower() for x in gia_vi_items]))
    gia_vi_unique = [x.capitalize() for x in gia_vi_unique_lower]
    
    return pd.DataFrame({
        "ten_nguyen_lieu": gia_vi_unique,
        "loai_nhom_nguyen_lieu": ["Gia vị"] * len(gia_vi_unique),
        "ten_nhom_nguyen_lieu": ["Gia vị"] * len(gia_vi_unique),
        "ma_nhom_nguyen_lieu": ["N19"] * len(gia_vi_unique)
    })

def process_rau_gia_vi(rau_gia_vi_list):
    """Xử lý danh sách rau gia vị"""
    rau_gia_vi_items = []
    remove_keywords = [
        'đập dập', 'chiên giòn', "thái chỉ", "băm", "phi", 'cắt nhỏ',
        'cắt khúc', "rang", "cắt sợi", "thái nhỏ", "cắt lát", "tươi",
        "băm nhỏ", "cắt que", "các loại", "để trang trí", "gia vị",
        "cắt khoanh", "ngắt lá", "dày lá"
    ]
    
    for item in rau_gia_vi_list:
        if isinstance(item, str) and item.strip():
            item = unicodedata.normalize("NFC", item)
            item = re.sub(r'\brau nêm\b', '', item, flags=re.IGNORECASE).strip()
            
            parts = re.split(r'[,.]|\s+và\s+', item, flags=re.IGNORECASE)
            
            for p in parts:
                p = unicodedata.normalize("NFC", p)
                p = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s]', '', p)
                p = re.sub(r'\s+', ' ', p).strip()
                
                if any(kw in p.lower() for kw in remove_keywords):
                    continue
                
                if p:
                    rau_gia_vi_items.append(p)
    
    seen = set()
    rau_gia_vi_unique = []
    for item in rau_gia_vi_items:
        lower_item = item.lower().strip()
        if lower_item not in seen:
            seen.add(lower_item)
            rau_gia_vi_unique.append(item.strip())
    
    return pd.DataFrame({
        "ten_nguyen_lieu": rau_gia_vi_unique,
        "loai_nhom_nguyen_lieu": ["Rau gia vị"] * len(rau_gia_vi_unique),
        "ten_nhom_nguyen_lieu": ["Rau gia vị"] * len(rau_gia_vi_unique),
        "ma_nhom_nguyen_lieu": ["N18"] * len(rau_gia_vi_unique)
    })

def process_dung_cu(dung_cu_list):
    """Xử lý danh sách dụng cụ"""
    dung_cu_items = []
    remove_keywords = [
        "đỏ", "shop bán đồ làm bánh", "tre hoặc inox", "rộng",
        "cao", "tre", "để cuốn", "cần máy đánh trứng"
    ]
    
    for item in dung_cu_list:
        if isinstance(item, str) and item.strip():
            item = unicodedata.normalize("NFC", item)
            item = re.sub(r'\bdụng cụ\b', '', item, flags=re.IGNORECASE).strip()
            
            parts = re.split(r'[,.]|\s+và\s+', item, flags=re.IGNORECASE)
            
            for p in parts:
                p = unicodedata.normalize("NFC", p)
                p = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s]', '', p)
                p = re.sub(r'\s+', ' ', p).strip()
                
                if any(kw in p.lower() for kw in remove_keywords):
                    continue
                
                if p:
                    dung_cu_items.append(p)
    
    seen = set()
    dung_cu_unique = []
    for item in dung_cu_items:
        lower_item = item.lower().strip()
        if lower_item not in seen:
            seen.add(lower_item)
            dung_cu_unique.append(item.strip())
    
    return pd.DataFrame({
        "ten_nguyen_lieu": dung_cu_unique,
        "loai_nhom_nguyen_lieu": ["Dụng cụ"] * len(dung_cu_unique),
        "ten_nhom_nguyen_lieu": ["Dụng cụ"] * len(dung_cu_unique),
        "ma_nhom_nguyen_lieu": ["N20"] * len(dung_cu_unique)
    })

def phan_loai_nguyen_lieu(ten):
    """Phân loại nguyên liệu theo tên"""
    t = ten.lower()
    
    def has_word(word):
        return re.search(rf'\b{re.escape(word)}\b', t) is not None
    
    # Thịt
    if has_word("gà"):
        return "Thịt", "Thịt gà"
    elif has_word("bò"):
        return "Thịt", "Thịt bò"
    elif has_word("heo") or has_word("lợn"):
        return "Thịt", "Thịt heo"
    elif has_word("vịt"):
        return "Thịt", "Thịt vịt"
    
    # Hải sản
    for x in ["ốc", "ếch", "cá", "tôm", "mực", "bạch tuộc"]:
        if has_word(x):
            return "Hải sản", x.capitalize()
    
    # Rau củ quả
    if has_word("cà rốt") or has_word("củ"):
        return "Rau củ quả", "Củ"
    elif has_word("quả") or has_word("cà chua"):
        return "Rau củ quả", "Quả"
    elif has_word("nấm") or has_word("rau"):
        return "Rau củ quả", "Rau"
    
    # Tinh bột
    if has_word("gạo"):
        return "Tinh bột", "Gạo"
    elif has_word("bánh mì"):
        return "Tinh bột", "Bánh mì"
    elif any(has_word(x) for x in ["bún", "miến", "phở", "hủ tiếu"]):
        return "Tinh bột", "Phở/Bún/Hủ tiếu/Miến"
    
    return "Khác", "Khác"

def process_main_ingredients(nguyen_lieu_list):
    """Xử lý danh sách nguyên liệu chính"""
    remove_keywords = [
        "đập dập", "bào", "luộc", "non", "già", "xắt lát", "xắt sợi",
        "xắt nhỏ", "xắt mỏng", "băm", "cắt khúc", "cắt lát", "cắt nhỏ",
        "bào sợi", "giã", "giã bể", "xé nhỏ", "nướng", "chiên", "rán",
        "luộc chín", "thái", "bóc vỏ", "rửa sạch", "ajinomoto", "aji",
        "xốt", "ướp", "nấu", "hấp", "đun", "trộn", "rang", "ngâm",
        "thái nhỏ", "gọt vỏ", "rửa", "bỏ hạt", "cắt", "giã nhỏ",
        "mỗi loại", "băm nhỏ", "mỗi thứ", "cắt miếng", "mỏng"
    ]
    
    nguyen_lieu_items = []
    
    for item in nguyen_lieu_list:
        if isinstance(item, str) and item.strip():
            item = unicodedata.normalize("NFC", item)
            parts = re.split(r',|\s+hoặc\s+', item, flags=re.IGNORECASE)
            
            for p in parts:
                p = unicodedata.normalize("NFC", p)
                p = re.sub(r'[^a-zA-ZÀ-ỹ0-9\s]', '', p)
                p = re.sub(r'\s+', ' ', p).strip()
                p = re.sub(r'\băn kèm\b', '', p, flags=re.IGNORECASE).strip()
                
                if any(kw.lower() in p.lower() for kw in remove_keywords):
                    continue
                
                if p:
                    nguyen_lieu_items.append(p)
    
    seen = set()
    nguyen_lieu_unique = []
    for item in nguyen_lieu_items:
        lower_item = item.lower().strip()
        if lower_item not in seen:
            seen.add(lower_item)
            nguyen_lieu_unique.append(item.strip())
    
    loai_nhom = []
    ten_nhom = []
    for ten in nguyen_lieu_unique:
        loai, nhom = phan_loai_nguyen_lieu(ten)
        loai_nhom.append(loai)
        ten_nhom.append(nhom)
    
    return pd.DataFrame({
        "ten_nguyen_lieu": nguyen_lieu_unique,
        "loai_nhom_nguyen_lieu": loai_nhom,
        "ten_nhom_nguyen_lieu": ten_nhom,
        "ma_nhom_nguyen_lieu": [""] * len(nguyen_lieu_unique)
    })

def process_all_ingredients(df_chua_xu_ly, conn):
    """Xử lý toàn bộ nguyên liệu"""
    print("\n" + "="*60)
    print("🥬 XỬ LÝ NGUYÊN LIỆU")
    print("="*60)
    
    # 1. Tách nguyên liệu
    nguyen_lieu_list, gia_vi_list, rau_gia_vi_list, dung_cu_list = \
        extract_all_ingredients(df_chua_xu_ly)
    
    print(f"📊 Nguyên liệu chính: {len(nguyen_lieu_list)}")
    print(f"📊 Gia vị: {len(gia_vi_list)}")
    print(f"📊 Rau gia vị: {len(rau_gia_vi_list)}")
    print(f"📊 Dụng cụ: {len(dung_cu_list)}")
    
    # 2. Xử lý từng nhóm
    df_gia_vi = process_gia_vi(gia_vi_list)
    df_rau_gia_vi = process_rau_gia_vi(rau_gia_vi_list)
    df_dung_cu = process_dung_cu(dung_cu_list)
    df_nguyen_lieu_chinh = process_main_ingredients(nguyen_lieu_list)
    
    # 3. Gộp tất cả
    df_bang_nguyen_lieu = pd.concat([
        df_nguyen_lieu_chinh,
        df_rau_gia_vi,
        df_gia_vi,
        df_dung_cu
    ], ignore_index=True)
    
    print(f"✅ Tổng số nguyên liệu: {len(df_bang_nguyen_lieu)}")
    
    # 4. Đọc dữ liệu từ Cloud
    nguyen_lieu_cld = pd.read_sql("SELECT * FROM nguyen_lieu;", conn)
    nhom_nguyen_lieu_cld = pd.read_sql("SELECT * FROM nhom_nguyen_lieu;", conn)
    
    print(f"📊 Nguyên liệu trên Cloud: {len(nguyen_lieu_cld)}")
    print(f"📊 Nhóm nguyên liệu trên Cloud: {len(nhom_nguyen_lieu_cld)}")
    
    # 5. Xử lý mã nhóm
    nhom_map = nhom_nguyen_lieu_cld.copy()
    
    def new_group_code():
        max_num = 0
        for code in nhom_map["ma_nhom_nguyen_lieu"]:
            if code.startswith("N"):
                try:
                    num = int(code[1:])
                    max_num = max(max_num, num)
                except:
                    pass
        return "N" + str(max_num + 1).zfill(2)
    
    ma_nhom_list = []
    new_nhom_rows = []
    
    for idx, row in df_bang_nguyen_lieu.iterrows():
        ten_nhom = row["ten_nhom_nguyen_lieu"]
        
        # Tìm trong nhóm hiện có
        match = nhom_map[nhom_map["ten_nhom_nguyen_lieu"].str.lower() == ten_nhom.lower()]
        if not match.empty:
            ma = match.iloc[0]["ma_nhom_nguyen_lieu"]
        else:
            ma = new_group_code()
            new_nhom_rows.append({
                "ma_nhom_nguyen_lieu": ma,
                "ten_nhom_nguyen_lieu": ten_nhom,
                "loai_nhom_nguyen_lieu": row["loai_nhom_nguyen_lieu"]
            })
            # Thêm vào nhom_map tạm thời để tránh trùng
            nhom_map = pd.concat([nhom_map, pd.DataFrame([{
                "ma_nhom_nguyen_lieu": ma,
                "ten_nhom_nguyen_lieu": ten_nhom,
                "loai_nhom_nguyen_lieu": row["loai_nhom_nguyen_lieu"]
            }])], ignore_index=True)
        
        ma_nhom_list.append(ma)
    
    df_bang_nguyen_lieu["ma_nhom_nguyen_lieu"] = ma_nhom_list
    
    # 6. Tạo mã nguyên liệu
    existing_nl = nguyen_lieu_cld.copy()
    
    def new_nl_code():
        return "NL" + str(random.randint(10000, 99999))
    
    ma_nl_list = []
    new_nl_rows = []
    
    for idx, row in df_bang_nguyen_lieu.iterrows():
        ten = row["ten_nguyen_lieu"]
        
        # Tìm trong nguyên liệu hiện có
        match = existing_nl[existing_nl["ten_nguyen_lieu"].str.lower() == ten.lower()]
        if not match.empty:
            ma = match.iloc[0]["ma_nguyen_lieu"]
        else:
            ma = new_nl_code()
            new_nl_rows.append({
                "ma_nguyen_lieu": ma,
                "ten_nguyen_lieu": ten,
                "ma_nhom_nguyen_lieu": row["ma_nhom_nguyen_lieu"]
            })
        
        ma_nl_list.append(ma)
    
    df_bang_nguyen_lieu["ma_nguyen_lieu"] = ma_nl_list
    
    # 7. Tạo DataFrames mới
    df_new_nhom_nguyen_lieu = pd.DataFrame(new_nhom_rows)
    df_new_nguyen_lieu = pd.DataFrame(new_nl_rows)
    
    print(f"✅ Nhóm nguyên liệu mới: {len(df_new_nhom_nguyen_lieu)}")
    print(f"✅ Nguyên liệu mới: {len(df_new_nguyen_lieu)}")
    
    return df_new_nhom_nguyen_lieu, df_new_nguyen_lieu, df_bang_nguyen_lieu

def tao_cong_thuc_mon_an(df_chua_xu_ly, df_bang_nguyen_lieu):
    """
    Tạo bảng chi tiết nguyên liệu từng món ăn:
    - Tự dò định lượng trong chuỗi 'nguyen_lieu'
    - Gắn mã món ăn (ma_mon_an)
    """
    print("\n" + "="*60)
    print("📝 TẠO BẢNG CÔNG THỨC MÓN ĂN")
    print("="*60)

    if df_bang_nguyen_lieu is None or len(df_bang_nguyen_lieu) == 0:
        print("⚠️ Không có dữ liệu nguyên liệu")
        return pd.DataFrame()

    df_bang_ngl = df_bang_nguyen_lieu.copy()
    df_bang_ngl["ten_nguyen_lieu_lower"] = df_bang_ngl["ten_nguyen_lieu"].str.lower()

    all_rows = []

    for idx, row in df_chua_xu_ly.iterrows():
        ma_mon_an = row["ma_mon_an"]
        chuoi = str(row["nguyen_lieu"]).lower() if pd.notna(row["nguyen_lieu"]) else ""

        # Tạo bản sao của bảng nguyên liệu
        df_ngl = df_bang_ngl.copy()

        # Hàm tìm định lượng
        def lay_dinh_luong(ten, text):
            if not ten or not text:
                return None
            
            # Tìm số trước tên nguyên liệu
            pattern1 = rf'(\d+)\s*[a-zA-ZÀ-ỹ]*\s*{re.escape(ten)}'
            match1 = re.search(pattern1, text)
            if match1:
                return match1.group(1)
            
            # Tìm số sau tên nguyên liệu
            pattern2 = rf'{re.escape(ten)}\s*:\s*(\d+)'
            match2 = re.search(pattern2, text)
            if match2:
                return match2.group(1)
            
            return None

        # Ánh xạ định lượng
        df_ngl["dinh_luong"] = df_ngl["ten_nguyen_lieu_lower"].apply(
            lambda ten: lay_dinh_luong(ten, chuoi)
        )

        # Lọc chỉ những nguyên liệu có trong món ăn này
        df_ngl = df_ngl[df_ngl["ten_nguyen_lieu_lower"].apply(
            lambda ten: ten in chuoi if chuoi else False
        )]

        if not df_ngl.empty:
            df_ngl["ma_mon_an"] = ma_mon_an
            df_ct = df_ngl[[
                "ma_mon_an",
                "ma_nguyen_lieu",
                "ten_nguyen_lieu",
                "dinh_luong"
            ]].copy()
            all_rows.append(df_ct)

    if all_rows:
        df_cong_thuc = pd.concat(all_rows, ignore_index=True)
    else:
        df_cong_thuc = pd.DataFrame(columns=["ma_mon_an", "ma_nguyen_lieu", "ten_nguyen_lieu", "dinh_luong"])
    
    print(f"✅ Đã tạo {len(df_cong_thuc)} dòng công thức nguyên liệu")
    
    return df_cong_thuc

def insert_nhom_nguyen_lieu(df_new_nhom_nguyen_lieu, conn):
    """Insert nhóm nguyên liệu mới"""
    if len(df_new_nhom_nguyen_lieu) == 0:
        print("ℹ️ Không có nhóm nguyên liệu mới để insert")
        return
    
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO nhom_nguyen_lieu (
            ma_nhom_nguyen_lieu,
            ten_nhom_nguyen_lieu,
            loai_nhom_nguyen_lieu
        ) VALUES (%s, %s, %s)
    """
    
    data = df_new_nhom_nguyen_lieu[["ma_nhom_nguyen_lieu", "ten_nhom_nguyen_lieu", "loai_nhom_nguyen_lieu"]].values.tolist()
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"✅ Đã insert {len(df_new_nhom_nguyen_lieu)} nhóm nguyên liệu mới")
    except Exception as e:
        print(f"❌ Lỗi insert nhóm nguyên liệu: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_nguyen_lieu(df_new_nguyen_lieu, conn):
    """Insert nguyên liệu mới"""
    if len(df_new_nguyen_lieu) == 0:
        print("ℹ️ Không có nguyên liệu mới để insert")
        return
    
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO nguyen_lieu (
            ma_nguyen_lieu,
            ten_nguyen_lieu,
            ma_nhom_nguyen_lieu
        ) VALUES (%s, %s, %s)
    """
    
    data = df_new_nguyen_lieu[["ma_nguyen_lieu", "ten_nguyen_lieu", "ma_nhom_nguyen_lieu"]].values.tolist()
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"🥬 Đã insert {len(df_new_nguyen_lieu)} nguyên liệu mới")
    except Exception as e:
        print(f"❌ Lỗi insert nguyên liệu: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_mon_an(df_mon_an, conn):
    """Insert món ăn mới"""
    if len(df_mon_an) == 0:
        print("ℹ️ Không có món ăn mới để insert")
        return
    
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO mon_an (
            ma_mon_an,
            ten_mon_an,
            khoang_thoi_gian,
            do_kho,
            khau_phan_tieu_chuan,
            calories,
            hinh_anh,
            cach_thuc_hien,
            cach_dung,
            so_che
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = df_mon_an[[
        "ma_mon_an", "ten_mon_an", "thoi_gian_thuc_hien", "do_kho",
        "khau_phan", "calories", "hinh_anh", "cach_thuc_hien",
        "cach_dung", "so_che"
    ]].values.tolist()
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"🍜 Đã insert {len(df_mon_an)} món ăn mới")
    except Exception as e:
        print(f"❌ Lỗi insert món ăn: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_cong_thuc(df_cong_thuc, conn):
    """Insert công thức món ăn"""
    if len(df_cong_thuc) == 0:
        print("ℹ️ Không có công thức mới để insert")
        return
    
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO cong_thuc_mon_an (
            ma_mon_an,
            ma_nguyen_lieu,
            ten_nguyen_lieu,
            dinh_luong
        ) VALUES (%s, %s, %s, %s)
    """
    
    data = df_cong_thuc[["ma_mon_an", "ma_nguyen_lieu", "ten_nguyen_lieu", "dinh_luong"]].values.tolist()
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"📑 Đã insert {len(df_cong_thuc)} dòng công thức")
    except Exception as e:
        print(f"❌ Lỗi insert công thức: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_phan_loai(df_phan_loai, conn):
    """Insert phân loại món ăn"""
    if len(df_phan_loai) == 0:
        print("ℹ️ Không có phân loại mới để insert")
        return
    
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO phan_loai_mon_an (
            ma_mon_an,
            ma_danh_muc_mon_an
        ) VALUES (%s, %s)
    """
    
    data = df_phan_loai[["ma_mon_an", "ma_danh_muc_mon_an"]].values.tolist()
    
    try:
        cursor.executemany(sql, data)
        conn.commit()
        print(f"🏷️ Đã insert {len(df_phan_loai)} dòng phân loại")
    except Exception as e:
        print(f"❌ Lỗi insert phân loại: {e}")
        conn.rollback()
    finally:
        cursor.close()

def update_tinh_trang_xu_ly(df_chua_xu_ly, conn):
    """Cập nhật tình trạng xử lý cho các món đã xử lý"""
    if len(df_chua_xu_ly) == 0:
        return
    
    cursor = conn.cursor()
    count = 0
    
    for idx, row in df_chua_xu_ly.iterrows():
        ten_mon_raw = str(row["ten_mon_an"]).strip()
        cursor.execute(
            """
            UPDATE rawdata_test 
            SET tinh_trang_xu_ly = 1 
            WHERE LOWER(TRIM(`Tên món ăn`)) = LOWER(%s)
            """,
            (ten_mon_raw,)
        )
        count += 1
    
    conn.commit()
    cursor.close()
    print(f"✅ Đã cập nhật tình trạng xử lý = 1 cho {count} món ăn")

def process_data():
    """Hàm chính xử lý dữ liệu và upload lên Cloud"""
    print("\n" + "="*60)
    print("🚀 BẮT ĐẦU XỬ LÝ DỮ LIỆU VÀ UPLOAD CLOUD")
    print("="*60)
    
    # 1. Kết nối database
    conn = connect_database()
    
    # 2. Đọc dữ liệu chưa xử lý
    df_chua_xu_ly = read_rawdata(conn)
    
    if df_chua_xu_ly is None or len(df_chua_xu_ly) == 0:
        conn.close()
        print("🔚 Không có dữ liệu mới cần xử lý. Kết thúc.")
        return False
    
    try:
        # 3. Xử lý hình ảnh
        df_chua_xu_ly = process_images(df_chua_xu_ly)
        
        # 4. Tạo bảng món ăn
        df_mon_an = create_df_mon_an(df_chua_xu_ly)
        
        # 5. Xử lý danh mục
        df_phan_loai = process_danh_muc(df_chua_xu_ly, conn)
        
        # 6. Xử lý nguyên liệu
        df_new_nhom, df_new_nl, df_bang_nl = process_all_ingredients(df_chua_xu_ly, conn)
        
        # 7. Tạo công thức món ăn
        df_cong_thuc = tao_cong_thuc_mon_an(df_chua_xu_ly, df_bang_nl)
        
        print("\n" + "="*60)
        print("☁️ BẮT ĐẦU INSERT DỮ LIỆU VÀO CLOUD")
        print("="*60)
        
        # 8. INSERT theo thứ tự đúng phụ thuộc
        # 8.1. Insert nhóm nguyên liệu trước (nếu có)
        insert_nhom_nguyen_lieu(df_new_nhom, conn)
        
        # 8.2. Insert nguyên liệu mới (nếu có)
        insert_nguyen_lieu(df_new_nl, conn)
        
        # 8.3. Insert món ăn
        insert_mon_an(df_mon_an, conn)
        
        # 8.4. Insert phân loại món ăn
        insert_phan_loai(df_phan_loai, conn)
        
        # 8.5. Insert công thức món ăn
        insert_cong_thuc(df_cong_thuc, conn)
        
        # 9. Cập nhật tình trạng xử lý
        update_tinh_trang_xu_ly(df_chua_xu_ly, conn)
        
        print("\n" + "="*60)
        print("🎉 XỬ LÝ HOÀN TẤT!")
        print("="*60)
        print(f"📊 TỔNG KẾT:")
        print(f"   • Món ăn đã xử lý: {len(df_mon_an)}")
        print(f"   • Nguyên liệu mới: {len(df_new_nl)}")
        print(f"   • Công thức: {len(df_cong_thuc)} dòng")
        print(f"   • Phân loại: {len(df_phan_loai)} dòng")
        
        return True
        
    except Exception as e:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH XỬ LÝ: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 10. Đóng kết nối
        conn.close()
        print("🔒 Đã đóng kết nối database (xử lý dữ liệu)")

# ============================================================
# HÀM CHÍNH CHẠY TOÀN BỘ PIPELINE
# ============================================================

def main():
    """Hàm chính chạy toàn bộ pipeline: cào → xử lý → upload"""
    print("\n" + "="*60)
    print("🚀 FOOD DATA PIPELINE - TỰ ĐỘNG HÓA")
    print("="*60)
    print("📌 Quy trình:")
    print("   1. Cào dữ liệu mới từ website")
    print("   2. Xử lý dữ liệu thô")
    print("   3. Upload lên Cloud (hình ảnh + database)")
    print("="*60)
    
    # Bước 1: Cào dữ liệu mới
    print("\n📍 BƯỚC 1: CÀO DỮ LIỆU MỚI")
    print("-"*40)
    
    has_new_data = crawl_data()
    
    if not has_new_data:
        print("\nℹ️ Không có dữ liệu mới, bỏ qua bước xử lý.")
        return
    
    print("\n" + "="*60)
    print("✅ HOÀN THÀNH CÀO DỮ LIỆU")
    print("⏳ Chờ 5 giây trước khi xử lý...")
    time.sleep(5)
    
    # Bước 2: Xử lý dữ liệu và upload Cloud
    print("\n📍 BƯỚC 2: XỬ LÝ DỮ LIỆU & UPLOAD CLOUD")
    print("-"*40)
    
    success = process_data()
    
    if success:
        print("\n" + "="*60)
        print("🎊 PIPELINE HOÀN THÀNH THÀNH CÔNG!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️ PIPELINE CÓ LỖI, VUI LÒNG KIỂM TRA!")
        print("="*60)

# ============================================================
# CHẠY CHƯƠNG TRÌNH
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Đã dừng chương trình bởi người dùng")
    except Exception as e:
        print(f"\n\n❌ LỖI KHÔNG XÁC ĐỊNH: {e}")
        import traceback
        traceback.print_exc()