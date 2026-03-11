import requests
import base64
import json
import logging
from urllib.parse import urljoin

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thông tin cấu hình bạn cung cấp
XAPI_URL = "https://cloud.scorm.com/lrs/IV2M3KSGCL/sandbox/statements"
XAPI_USERNAME = "IV2M3KSGCL"
XAPI_PASSWORD = "1rCwrXheGPaOMq1XmEm0NWQjFnhBt8KjDIekEqQu"
OUTPUT_FILE = "sample_data.json"
LIMIT = 9999 # Số lượng statement muốn lấy

def get_auth_header(username, password):
    """Tạo Basic Auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def fetch_and_save():
    try:
        all_statements = []
        headers = {
            "Authorization": get_auth_header(XAPI_USERNAME, XAPI_PASSWORD),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Experience-API-Version": "1.0.3"
        }
        
        current_url = XAPI_URL
        params = {"limit": LIMIT}
        
        logger.info(f"Đang bắt đầu fetch từ {XAPI_URL}...")
        
        while True:
            logger.info(f"Đang gọi: {current_url}")
            response = requests.get(
                current_url, 
                headers=headers, 
                params=params if current_url == XAPI_URL else None, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            batch = data.get("statements", []) if isinstance(data, dict) else data
            more_url = data.get("more") if isinstance(data, dict) else None
            
            all_statements.extend(batch)
            logger.info(f"Đã lấy được {len(batch)} statements. Tổng cộng: {len(all_statements)}")

            # Dừng nếu không còn trang tiếp theo hoặc đủ số lượng LIMIT
            if not more_url or len(all_statements) >= LIMIT:
                break
            
            # Cập nhật URL cho trang tiếp theo (Pagination)
            current_url = more_url if more_url.startswith("http") else urljoin(XAPI_URL, more_url)
        
        # Cắt bớt nếu vượt quá LIMIT
        if len(all_statements) > LIMIT:
            all_statements = all_statements[:LIMIT]

        # Lưu vào file JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_statements, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Đã lưu thành công {len(all_statements)} statements vào {OUTPUT_FILE}")

    except Exception as e:
        logger.error(f"Lỗi khi fetch dữ liệu: {str(e)}")

if __name__ == "__main__":
    fetch_and_save()
