"""
Script để đếm số lần các ICD code xuất hiện (theo hadm_id).
Đọc từ file diagnoses_icd.csv.gz trong proc (đã lọc non-disease) và tạo file icd_hadm_freq.csv.
Format: icd_full, hadm_freq (số lần xuất hiện unique hadm_id)
"""

import pandas as pd
from pathlib import Path

# Đường dẫn
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROC_DIR = DATA_DIR / "proc"

# File input và output
INPUT_FILE = PROC_DIR / "diagnoses_icd.csv.gz"  # File đã lọc non-disease trong proc
OUTPUT_FILE = PROC_DIR / "icd_hadm_freq.csv"

def count_icd_frequency():
    """Đếm tần suất ICD code theo hadm_id (số lần xuất hiện unique hadm_id)"""
    
    print("=" * 60)
    print("ĐẾM TẦN SUẤT ICD CODES THEO HADM_ID")
    print("(Từ file đã lọc non-disease trong proc)")
    print("=" * 60)
    
    if not INPUT_FILE.exists():
        print(f"❌ File không tồn tại: {INPUT_FILE}")
        print("   Chạy jobs/01_filter_non_disease_icd.py.py trước để tạo file đã lọc")
        return
    
    print(f"\n📖 Đang đọc: {INPUT_FILE.name}")
    
    # Đếm tần suất ICD codes theo hadm_id (unique hadm_id)
    print("\n🔄 Đang đếm tần suất ICD codes theo hadm_id...")
    
    total_rows = 0
    chunk_size = 100_000
    hadm_icd_dict = {}  # {hadm_id: set(icd_full)}
    
    # Đọc theo chunks để tiết kiệm memory
    for chunk in pd.read_csv(INPUT_FILE, compression='gzip',
                            usecols=['hadm_id', 'icd_code', 'icd_version'],
                            chunksize=chunk_size, low_memory=False):
        total_rows += len(chunk)
        
        # Tạo icd_full: version-code
        chunk['icd_full'] = (
            chunk['icd_version'].astype(str) + "-" + 
            chunk['icd_code'].astype(str)
        )
        
        # Nhóm theo hadm_id và lưu các ICD unique
        for hadm_id, group in chunk.groupby('hadm_id'):
            hadm_id_int = int(hadm_id)
            if hadm_id_int not in hadm_icd_dict:
                hadm_icd_dict[hadm_id_int] = set()
            hadm_icd_dict[hadm_id_int].update(group['icd_full'].tolist())
        
        if total_rows % 1_000_000 == 0:
            print(f"   Đã xử lý {total_rows:,} dòng...")
    
    print(f"   Tổng số dòng đã xử lý: {total_rows:,}")
    print(f"   Tổng số hadm_id unique: {len(hadm_icd_dict):,}")
    
    # Đếm số hadm_id cho mỗi ICD code
    from collections import Counter
    icd_hadm_counter = Counter()
    for hadm_id, icd_set in hadm_icd_dict.items():
        for icd_full in icd_set:
            icd_hadm_counter[icd_full] += 1
    
    print(f"   Tổng số ICD code unique: {len(icd_hadm_counter):,}")
    print(f"   Tổng số lần xuất hiện (hadm_freq): {sum(icd_hadm_counter.values()):,}")
    
    # Tạo DataFrame với format: icd_full, hadm_freq
    frequency_df = pd.DataFrame([
        {'icd_full': icd, 'hadm_freq': count}
        for icd, count in icd_hadm_counter.items()
    ])
    
    # Sắp xếp theo hadm_freq giảm dần
    frequency_df = frequency_df.sort_values('hadm_freq', ascending=False).reset_index(drop=True)
    
    # Lưu file
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    frequency_df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Đã lưu: {OUTPUT_FILE}")
    print(f"   Kích thước: {OUTPUT_FILE.stat().st_size / 1024:.2f} KB")
    
    # Thống kê
    print(f"\n📊 Thống kê:")
    print(f"   Tổng số ICD code unique: {len(frequency_df):,}")
    print(f"   ICD code xuất hiện nhiều nhất: {frequency_df.iloc[0]['icd_full']} ({frequency_df.iloc[0]['hadm_freq']:,} hadm_id)")
    print(f"   ICD code xuất hiện ít nhất: {frequency_df.iloc[-1]['icd_full']} ({frequency_df.iloc[-1]['hadm_freq']:,} hadm_id)")
    
    # Top 10 ICD codes
    print(f"\n📋 Top 10 ICD codes phổ biến nhất:")
    for idx, row in frequency_df.head(10).iterrows():
        print(f"   {idx+1:2d}. {row['icd_full']:15s} - {row['hadm_freq']:6,} hadm_id")
    
    # Thống kê theo version
    print(f"\n📊 Thống kê theo ICD version:")
    frequency_df['icd_version'] = frequency_df['icd_full'].str.split('-').str[0]
    version_stats = frequency_df.groupby('icd_version').agg({
        'icd_full': 'count',
        'hadm_freq': 'sum'
    }).rename(columns={'icd_full': 'count', 'hadm_freq': 'total_hadm_freq'})
    version_stats = version_stats.sort_values('total_hadm_freq', ascending=False)
    
    for version, row in version_stats.iterrows():
        print(f"   ICD-{version}: {row['count']:,} codes, {row['total_hadm_freq']:,} tổng hadm_freq")
    
    return frequency_df

if __name__ == "__main__":
    count_icd_frequency()

