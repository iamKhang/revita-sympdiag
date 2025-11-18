"""
Script để tạo các file CSV mẫu (lite) từ dữ liệu MIMIC-IV đầy đủ.
Tạo các file CSV không nén trong thư mục data/mimic-iv-lite
"""

import pandas as pd
from pathlib import Path
import os

# Đường dẫn gốc của project
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "mimic-iv-lite"

# Tạo thư mục output nếu chưa tồn tại
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Định nghĩa các file nguồn và tên file output
FILES_TO_PROCESS = [
    {
        "source": DATA_DIR / "mimiciv" / "3.1" / "hosp" / "admissions.csv.gz",
        "output": OUTPUT_DIR / "admissions.csv"
    },
    {
        "source": DATA_DIR / "mimiciv" / "3.1" / "hosp" / "d_icd_diagnoses.csv.gz",
        "output": OUTPUT_DIR / "d_icd_diagnoses.csv"
    },
    {
        "source": DATA_DIR / "mimiciv" / "3.1" / "hosp" / "diagnoses_icd.csv.gz",
        "output": OUTPUT_DIR / "diagnoses_icd.csv"
    },
    {
        "source": DATA_DIR / "mimiciv" / "3.1" / "hosp" / "patients.csv.gz",
        "output": OUTPUT_DIR / "patients.csv"
    },
    {
        "source": DATA_DIR / "mimic-iv-note" / "2.2" / "note" / "discharge.csv.gz",
        "output": OUTPUT_DIR / "discharge.csv"
    }
]

# Số dòng mẫu để lấy từ mỗi file (có thể điều chỉnh)
SAMPLE_SIZE = 1000

def create_sample_data():
    """Tạo các file CSV mẫu từ dữ liệu gốc"""
    
    for file_info in FILES_TO_PROCESS:
        source_path = file_info["source"]
        output_path = file_info["output"]
        
        if not source_path.exists():
            print(f"⚠️  File không tồn tại: {source_path}")
            continue
        
        print(f"📖 Đang đọc: {source_path.name}")
        
        try:
            # Đọc file gzip
            df = pd.read_csv(source_path, compression='gzip', low_memory=False)
            
            print(f"   Tổng số dòng: {len(df)}")
            
            # Lấy mẫu dữ liệu
            # Nếu file nhỏ hơn SAMPLE_SIZE, lấy toàn bộ
            if len(df) <= SAMPLE_SIZE:
                sample_df = df.copy()
                print(f"   File nhỏ, lấy toàn bộ: {len(sample_df)} dòng")
            else:
                # Lấy mẫu ngẫu nhiên
                sample_df = df.sample(n=SAMPLE_SIZE, random_state=42)
                print(f"   Lấy mẫu: {len(sample_df)} dòng")
            
            # Lưu file CSV không nén
            sample_df.to_csv(output_path, index=False)
            print(f"✅ Đã lưu: {output_path}")
            print(f"   Kích thước: {os.path.getsize(output_path) / 1024:.2f} KB\n")
            
        except Exception as e:
            print(f"❌ Lỗi khi xử lý {source_path.name}: {str(e)}\n")
            continue
    
    print("✨ Hoàn thành tạo dữ liệu mẫu!")

if __name__ == "__main__":
    create_sample_data()

