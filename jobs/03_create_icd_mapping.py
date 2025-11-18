"""
Script để tạo mapping thống nhất các ICD code có long_title trùng lặp.
Với mỗi long_title trùng, chọn một ICD canonical (ưu tiên ICD-10) và tạo mapping
để chuyển đổi các ICD code trong diagnoses_icd.csv và các nơi khác.
"""

import pandas as pd
from pathlib import Path
import os

# Đường dẫn gốc của project
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Đường dẫn các file
SOURCE_FILE = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "d_icd_diagnoses.csv.gz"
DUPLICATE_FILE = DATA_DIR / "mimic-iv-lite" / "duplicate_icd_diagnoses.csv"
MAPPING_FILE = DATA_DIR / "mimic-iv-lite" / "icd_deduplicated_mapping.csv"

def create_icd_mapping():
    """Tạo mapping để thống nhất các ICD code trùng long_title"""
    
    print("=" * 60)
    print("TẠO MAPPING THỐNG NHẤT ICD CODE")
    print("=" * 60)
    
    # Kiểm tra file nguồn
    if not SOURCE_FILE.exists():
        print(f"❌ File không tồn tại: {SOURCE_FILE}")
        return
    
    if not DUPLICATE_FILE.exists():
        print(f"⚠️  File duplicate không tồn tại: {DUPLICATE_FILE}")
        print("   Chạy script 02_create_icd_duplicates_report.py trước")
        return
    
    print(f"\n📖 Đang đọc file gốc: {SOURCE_FILE.name}")
    df_all = pd.read_csv(SOURCE_FILE, compression='gzip', low_memory=False)
    print(f"   Tổng số ICD: {len(df_all)}")
    
    print(f"\n📖 Đang đọc file duplicate: {DUPLICATE_FILE.name}")
    df_duplicate = pd.read_csv(DUPLICATE_FILE)
    print(f"   Số ICD trùng: {len(df_duplicate)}")
    
    # Chuẩn hóa long_title để nhóm
    df_all['long_title_normalized'] = df_all['long_title'].astype(str).str.strip().str.lower()
    df_duplicate['long_title_normalized'] = df_duplicate['long_title'].astype(str).str.strip().str.lower()
    
    # Tạo mapping: với mỗi long_title trùng, chọn ICD canonical
    # Quy tắc: Ưu tiên ICD-10, nếu có nhiều ICD-10 thì chọn theo thứ tự alphabet của icd_code
    mappings = []
    
    # Nhóm các ICD theo long_title_normalized
    duplicate_titles = df_duplicate['long_title_normalized'].unique()
    print(f"\n🔄 Đang xử lý {len(duplicate_titles)} long_title trùng lặp...")
    
    for title_norm in duplicate_titles:
        # Lấy tất cả ICD có cùng long_title
        group = df_duplicate[df_duplicate['long_title_normalized'] == title_norm].copy()
        
        # Sắp xếp: ưu tiên ICD-10, sau đó theo icd_code
        group = group.sort_values(['icd_version', 'icd_code'], ascending=[False, True])
        
        # Chọn ICD đầu tiên làm canonical (ưu tiên ICD-10)
        canonical = group.iloc[0]
        canonical_icd_code = canonical['icd_code']
        canonical_icd_version = canonical['icd_version']
        
        # Tạo mapping cho tất cả các ICD trong nhóm (bao gồm cả canonical)
        for _, row in group.iterrows():
            mappings.append({
                'original_icd_code': row['icd_code'],
                'original_icd_version': row['icd_version'],
                'canonical_icd_code': canonical_icd_code,
                'canonical_icd_version': canonical_icd_version,
                'long_title': row['long_title']
            })
    
    # Tạo DataFrame mapping
    mapping_df = pd.DataFrame(mappings)
    
    # Loại bỏ các mapping trùng (nếu có)
    mapping_df = mapping_df.drop_duplicates(['original_icd_code', 'original_icd_version'])
    
    print(f"\n✅ Đã tạo {len(mapping_df)} mapping")
    
    # Thống kê
    icd9_to_icd10 = len(mapping_df[
        (mapping_df['original_icd_version'] == 9) & 
        (mapping_df['canonical_icd_version'] == 10)
    ])
    icd10_to_icd10 = len(mapping_df[
        (mapping_df['original_icd_version'] == 10) & 
        (mapping_df['canonical_icd_version'] == 10)
    ])
    icd9_to_icd9 = len(mapping_df[
        (mapping_df['original_icd_version'] == 9) & 
        (mapping_df['canonical_icd_version'] == 9)
    ])
    
    print(f"\n📊 Thống kê mapping:")
    print(f"   ICD-9 -> ICD-10: {icd9_to_icd10}")
    print(f"   ICD-10 -> ICD-10: {icd10_to_icd10}")
    print(f"   ICD-9 -> ICD-9: {icd9_to_icd9}")
    
    # Sắp xếp để dễ đọc
    mapping_df = mapping_df.sort_values(['long_title', 'original_icd_version', 'original_icd_code'])
    
    # Lưu file mapping
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(MAPPING_FILE, index=False)
    print(f"\n✅ Đã lưu mapping: {MAPPING_FILE}")
    print(f"   Kích thước: {os.path.getsize(MAPPING_FILE) / 1024:.2f} KB")
    
    # Hiển thị một vài ví dụ
    print("\n📋 Một vài ví dụ mapping:")
    sample = mapping_df.head(10)
    for _, row in sample.iterrows():
        if row['original_icd_version'] != row['canonical_icd_version']:
            print(f"   {row['original_icd_version']}-{row['original_icd_code']} -> "
                  f"{row['canonical_icd_version']}-{row['canonical_icd_code']}")
            print(f"      '{row['long_title'][:60]}...'")
    
    return mapping_df

def apply_mapping_to_diagnoses_icd(mapping_df=None, input_file=None, output_file=None):
    """Áp dụng mapping vào diagnoses_icd.csv"""
    
    if mapping_df is None:
        if not MAPPING_FILE.exists():
            print(f"\n⚠️  File mapping chưa tồn tại. Chạy create_icd_mapping() trước.")
            return None
        mapping_df = pd.read_csv(MAPPING_FILE)
    
    if input_file is None:
        input_file = DATA_DIR / "mimic-iv-lite" / "diagnoses_icd.csv"
    
    if output_file is None:
        output_file = DATA_DIR / "mimic-iv-lite" / "diagnoses_icd_deduplicated.csv"
    
    if not input_file.exists():
        print(f"\n⚠️  File {input_file.name} không tồn tại. Bỏ qua.")
        return None
    
    print(f"\n🔄 Áp dụng mapping vào {input_file.name}...")
    
    # Đọc diagnoses_icd
    df_diag = pd.read_csv(input_file)
    print(f"   Số dòng ban đầu: {len(df_diag)}")
    
    # Tạo mapping dictionary để lookup nhanh
    mapping_dict = {}
    for _, row in mapping_df.iterrows():
        key = (str(row['original_icd_code']), int(row['original_icd_version']))
        mapping_dict[key] = (str(row['canonical_icd_code']), int(row['canonical_icd_version']))
    
    # Đếm số dòng sẽ bị thay đổi
    original_icd_keys = set(zip(df_diag['icd_code'].astype(str), df_diag['icd_version'].astype(int)))
    changed_count = sum(1 for key in original_icd_keys if key in mapping_dict)
    print(f"   Số ICD sẽ được chuyển đổi: {changed_count}")
    
    # Áp dụng mapping
    def map_icd(row):
        key = (str(row['icd_code']), int(row['icd_version']))
        if key in mapping_dict:
            canonical_code, canonical_version = mapping_dict[key]
            return pd.Series({
                'icd_code': canonical_code,
                'icd_version': canonical_version
            })
        return pd.Series({
            'icd_code': row['icd_code'],
            'icd_version': row['icd_version']
        })
    
    # Áp dụng mapping
    mapped = df_diag.apply(lambda row: map_icd(row), axis=1)
    df_diag['icd_code'] = mapped['icd_code']
    df_diag['icd_version'] = mapped['icd_version']
    
    # Lưu file mới
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_diag.to_csv(output_file, index=False)
    print(f"✅ Đã lưu file đã deduplicate: {output_file}")
    print(f"   Số dòng sau mapping: {len(df_diag)}")
    
    # Thống kê sau mapping
    unique_icd_after = df_diag.groupby(['icd_code', 'icd_version']).size().reset_index(name='count')
    print(f"   Số ICD unique sau mapping: {len(unique_icd_after)}")
    
    return df_diag

def load_icd_mapping():
    """Hàm tiện ích để load mapping từ file"""
    if not MAPPING_FILE.exists():
        print(f"⚠️  File mapping chưa tồn tại: {MAPPING_FILE}")
        return None
    
    mapping_df = pd.read_csv(MAPPING_FILE)
    
    # Tạo dictionary để lookup nhanh: (icd_code, icd_version) -> (canonical_code, canonical_version)
    mapping_dict = {}
    for _, row in mapping_df.iterrows():
        key = (str(row['original_icd_code']), int(row['original_icd_version']))
        mapping_dict[key] = (str(row['canonical_icd_code']), int(row['canonical_icd_version']))
    
    return mapping_dict

def map_single_icd(icd_code, icd_version, mapping_dict=None):
    """Hàm tiện ích để map một ICD code đơn lẻ"""
    if mapping_dict is None:
        mapping_dict = load_icd_mapping()
        if mapping_dict is None:
            return icd_code, icd_version
    
    key = (str(icd_code), int(icd_version))
    if key in mapping_dict:
        return mapping_dict[key]
    return (str(icd_code), int(icd_version))

if __name__ == "__main__":
    # Tạo mapping
    mapping_df = create_icd_mapping()
    
    # Tự động áp dụng mapping vào diagnoses_icd.csv
    print("\n" + "=" * 60)
    print("ÁP DỤNG MAPPING VÀO diagnoses_icd.csv")
    print("=" * 60)
    apply_mapping_to_diagnoses_icd(mapping_df)
    
    print("\n" + "=" * 60)
    print("✨ HOÀN THÀNH!")
    print("=" * 60)
    print(f"\n📁 Các file đã tạo:")
    print(f"   1. Mapping: {MAPPING_FILE}")
    print(f"   2. Diagnoses đã deduplicate: {DATA_DIR / 'mimic-iv-lite' / 'diagnoses_icd_deduplicated.csv'}")
    print(f"\n💡 Để sử dụng mapping trong code khác:")
    print(f"   from jobs.03_create_icd_mapping import load_icd_mapping, map_single_icd")
    print(f"   mapping = load_icd_mapping()")
    print(f"   canonical_code, canonical_version = map_single_icd('99962', 9, mapping)")

