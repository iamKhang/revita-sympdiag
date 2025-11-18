"""
Script để lọc bỏ các ICD code không phải bệnh lý thực sự.
Copy file từ mimiciv/3.1/hosp/ vào proc/ và lọc theo config non_disease_icd.json
"""

import pandas as pd
import json
import shutil
from pathlib import Path

# Đường dẫn
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "configs" / "non_disease_icd.json"
SOURCE_DIR = DATA_DIR / "mimiciv" / "3.1" / "hosp"
OUTPUT_DIR = DATA_DIR / "proc"

# File cần xử lý
FILES_TO_PROCESS = [
    "d_icd_diagnoses.csv.gz",
    "diagnoses_icd.csv.gz"
]

def load_config():
    """Đọc config từ file JSON"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_non_disease_icd(icd_code, icd_version, config):
    """
    Kiểm tra xem ICD code có phải là non-disease không
    
    Returns:
        True nếu là non-disease (cần loại bỏ)
        False nếu là disease (cần giữ lại)
    """
    icd_code = str(icd_code).strip()
    icd_version = int(icd_version)
    
    # Kiểm tra exceptions_to_keep trước (ưu tiên giữ lại)
    exceptions = config.get("exceptions_to_keep", {})
    if icd_version == 10:
        for exc in exceptions.get("icd10", []):
            if icd_code.startswith(exc) or icd_code == exc:
                return False  # Giữ lại
    elif icd_version == 9:
        for exc in exceptions.get("icd9", []):
            if icd_code.startswith(exc) or icd_code == exc:
                return False  # Giữ lại
    
    # Kiểm tra prefixes để loại bỏ
    if icd_version == 10:
        prefixes = config.get("icd10_prefixes", [])
        for prefix in prefixes:
            if icd_code.startswith(prefix):
                return True  # Loại bỏ
    elif icd_version == 9:
        prefixes = config.get("icd9_prefixes", [])
        for prefix in prefixes:
            if icd_code.startswith(prefix):
                return True  # Loại bỏ
    
    # Kiểm tra manual_exclude
    manual_exclude = config.get("manual_exclude", {})
    if icd_version == 10:
        for exclude_pattern in manual_exclude.get("icd10", []):
            # Kiểm tra cả prefix và exact match
            if icd_code.startswith(exclude_pattern) or icd_code == exclude_pattern:
                return True  # Loại bỏ
    elif icd_version == 9:
        for exclude_pattern in manual_exclude.get("icd9", []):
            # Kiểm tra cả prefix và exact match
            if icd_code.startswith(exclude_pattern) or icd_code == exclude_pattern:
                return True  # Loại bỏ
    
    return False  # Giữ lại (là disease)

def filter_d_icd_diagnoses(input_file, output_file, config):
    """Lọc file d_icd_diagnoses.csv.gz"""
    print(f"\n📖 Đang xử lý: {input_file.name}")
    
    df = pd.read_csv(input_file, compression='gzip', low_memory=False)
    print(f"   Số dòng ban đầu: {len(df):,}")
    
    # Lọc bỏ non-disease ICD
    mask = df.apply(
        lambda row: not is_non_disease_icd(
            row['icd_code'], 
            row['icd_version'], 
            config
        ), 
        axis=1
    )
    
    df_filtered = df[mask].copy()
    print(f"   Số dòng sau khi lọc: {len(df_filtered):,}")
    print(f"   Đã loại bỏ: {len(df) - len(df_filtered):,} dòng")
    
    # Lưu file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_filtered.to_csv(output_file, index=False, compression='gzip')
    print(f"✅ Đã lưu: {output_file}")
    
    return df_filtered

def filter_diagnoses_icd(input_file, output_file, config):
    """Lọc file diagnoses_icd.csv.gz (xử lý theo chunks)"""
    print(f"\n📖 Đang xử lý: {input_file.name}")
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    total_rows = 0
    total_kept = 0
    first_chunk = True
    chunk_size = 100_000
    
    # Xóa file output nếu đã tồn tại
    if output_file.exists():
        output_file.unlink()
    
    for chunk_num, chunk in enumerate(pd.read_csv(
        input_file, 
        compression='gzip', 
        chunksize=chunk_size, 
        low_memory=False
    )):
        total_rows += len(chunk)
        
        # Lọc bỏ non-disease ICD
        mask = chunk.apply(
            lambda row: not is_non_disease_icd(
                row['icd_code'], 
                row['icd_version'], 
                config
            ), 
            axis=1
        )
        
        chunk_filtered = chunk[mask].copy()
        total_kept += len(chunk_filtered)
        
        # Lưu chunk
        if not chunk_filtered.empty:
            chunk_filtered.to_csv(
                output_file, 
                mode='w' if first_chunk else 'a',
                header=first_chunk,
                index=False, 
                compression='gzip'
            )
            first_chunk = False
        
        if (chunk_num + 1) % 10 == 0:
            print(f"   Đã xử lý {total_rows:,} dòng, giữ lại {total_kept:,} dòng...")
    
    print(f"   Tổng số dòng ban đầu: {total_rows:,}")
    print(f"   Tổng số dòng sau khi lọc: {total_kept:,}")
    print(f"   Đã loại bỏ: {total_rows - total_kept:,} dòng")
    print(f"✅ Đã lưu: {output_file}")
    
    return total_kept

def main():
    """Hàm chính"""
    print("=" * 60)
    print("LỌC BỎ NON-DISEASE ICD CODES")
    print("=" * 60)
    
    # Đọc config
    print(f"\n📋 Đang đọc config: {CONFIG_FILE.name}")
    config = load_config()
    print(f"   Version: {config.get('version', 'N/A')}")
    print(f"   Description: {config.get('description', 'N/A')[:60]}...")
    
    # Xử lý từng file
    for filename in FILES_TO_PROCESS:
        input_file = SOURCE_DIR / filename
        output_file = OUTPUT_DIR / filename
        
        if not input_file.exists():
            print(f"\n⚠️  File không tồn tại: {input_file}")
            continue
        
        # Xử lý theo loại file
        if filename == "d_icd_diagnoses.csv.gz":
            filter_d_icd_diagnoses(input_file, output_file, config)
        elif filename == "diagnoses_icd.csv.gz":
            filter_diagnoses_icd(input_file, output_file, config)
    
    print("\n" + "=" * 60)
    print("✨ HOÀN THÀNH!")
    print("=" * 60)
    print(f"\n📁 Các file đã được lọc và lưu vào: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

