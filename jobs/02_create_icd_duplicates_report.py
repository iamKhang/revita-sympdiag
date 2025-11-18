"""
Script để tìm và lưu các ICD code có long_title bị trùng lặp.
Đọc từ d_icd_diagnoses.csv.gz và lưu kết quả vào duplicate_icd_diagnoses.csv
"""

import pandas as pd
from pathlib import Path
import os

# Đường dẫn gốc của project
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Đường dẫn file nguồn và file output
SOURCE_FILE = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "d_icd_diagnoses.csv.gz"
OUTPUT_FILE = DATA_DIR / "mimic-iv-lite" / "duplicate_icd_diagnoses.csv"

def find_duplicate_icd_diagnoses():
    """Tìm và lưu các ICD code có long_title trùng lặp"""
    
    # Kiểm tra file nguồn có tồn tại không
    if not SOURCE_FILE.exists():
        print(f"❌ File không tồn tại: {SOURCE_FILE}")
        return
    
    print(f"📖 Đang đọc: {SOURCE_FILE}")
    
    try:
        # Đọc file gzip
        df = pd.read_csv(SOURCE_FILE, compression='gzip', low_memory=False)
        
        print(f"   Tổng số dòng: {len(df)}")
        print(f"   Số ICD-9: {len(df[df['icd_version'] == 9])}")
        print(f"   Số ICD-10: {len(df[df['icd_version'] == 10])}")
        
        # Chuẩn hóa long_title: loại bỏ khoảng trắng thừa và chuyển về lowercase để so sánh
        df['long_title_normalized'] = df['long_title'].astype(str).str.strip().str.lower()
        
        # Tìm các long_title xuất hiện nhiều hơn 1 lần
        title_counts = df.groupby('long_title_normalized').size()
        duplicate_titles = title_counts[title_counts > 1].index.tolist()
        
        print(f"   Tìm thấy {len(duplicate_titles)} long_title trùng lặp")
        
        if len(duplicate_titles) == 0:
            print("   Không có long_title nào bị trùng lặp")
            # Tạo file rỗng với header
            output_df = pd.DataFrame(columns=['icd_code', 'icd_version', 'long_title'])
        else:
            # Lọc ra tất cả các dòng có long_title trùng lặp
            mask = df['long_title_normalized'].isin(duplicate_titles)
            duplicate_df = df[mask].copy()
            
            # Xóa cột normalized (chỉ dùng để so sánh)
            duplicate_df = duplicate_df[['icd_code', 'icd_version', 'long_title']]
            
            # Sắp xếp theo long_title để dễ xem
            duplicate_df = duplicate_df.sort_values(['long_title', 'icd_version', 'icd_code'])
            
            output_df = duplicate_df
            
            print(f"   Tổng số ICD code bị trùng: {len(output_df)}")
            print(f"   Số long_title duy nhất bị trùng: {len(duplicate_titles)}")
        
        # Đảm bảo thư mục output tồn tại
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Lưu file CSV
        output_df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Đã lưu: {OUTPUT_FILE}")
        print(f"   Kích thước: {os.path.getsize(OUTPUT_FILE) / 1024:.2f} KB")
        
        # Hiển thị một vài ví dụ
        if len(output_df) > 0:
            print("\n📋 Một vài ví dụ long_title trùng lặp:")
            sample_titles = output_df['long_title'].value_counts().head(5)
            for title, count in sample_titles.items():
                print(f"   - '{title[:60]}...' ({count} ICD codes)")
        
    except Exception as e:
        print(f"❌ Lỗi khi xử lý: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_duplicate_icd_diagnoses()

