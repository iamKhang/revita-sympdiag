"""
Script để thống nhất các ICD code có long_title trùng lặp.
Tìm các ICD trùng, tạo mapping và áp dụng vào diagnoses_icd.csv
Giữ nguyên dữ liệu, chỉ cập nhật ICD code để thống nhất.
"""

import pandas as pd
from pathlib import Path
import os
import sys

# Đường dẫn gốc của project
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Đường dẫn các file
SOURCE_FILE = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "d_icd_diagnoses.csv.gz"
DUPLICATE_FILE = DATA_DIR / "mimic-iv-lite" / "duplicate_icd_diagnoses.csv"
MAPPING_FILE = DATA_DIR / "mimic-iv-lite" / "icd_deduplicated_mapping.csv"

def find_duplicate_icd_diagnoses():
    """Tìm và lưu các ICD code có long_title trùng lặp"""
    
    print("=" * 60)
    print("BƯỚC 1: TÌM CÁC ICD CODE TRÙNG LẶP")
    print("=" * 60)
    
    if not SOURCE_FILE.exists():
        print(f"❌ File không tồn tại: {SOURCE_FILE}")
        return None
    
    print(f"📖 Đang đọc: {SOURCE_FILE.name}")
    
    try:
        # Đọc file gzip
        df = pd.read_csv(SOURCE_FILE, compression='gzip', low_memory=False)
        
        print(f"   Tổng số dòng: {len(df):,}")
        print(f"   Số ICD-9: {len(df[df['icd_version'] == 9]):,}")
        print(f"   Số ICD-10: {len(df[df['icd_version'] == 10]):,}")
        
        # Chuẩn hóa long_title: loại bỏ khoảng trắng thừa và chuyển về lowercase để so sánh
        df['long_title_normalized'] = df['long_title'].astype(str).str.strip().str.lower()
        
        # Tìm các long_title xuất hiện nhiều hơn 1 lần
        title_counts = df.groupby('long_title_normalized').size()
        duplicate_titles = title_counts[title_counts > 1].index.tolist()
        
        print(f"   Tìm thấy {len(duplicate_titles):,} long_title trùng lặp")
        
        if len(duplicate_titles) == 0:
            print("   Không có long_title nào bị trùng lặp")
            return pd.DataFrame(columns=['icd_code', 'icd_version', 'long_title'])
        
        # Lọc ra tất cả các dòng có long_title trùng lặp
        mask = df['long_title_normalized'].isin(duplicate_titles)
        duplicate_df = df[mask].copy()
        
        # Xóa cột normalized (chỉ dùng để so sánh)
        duplicate_df = duplicate_df[['icd_code', 'icd_version', 'long_title']]
        
        # Sắp xếp theo long_title để dễ xem
        duplicate_df = duplicate_df.sort_values(['long_title', 'icd_version', 'icd_code'])
        
        print(f"   Tổng số ICD code bị trùng: {len(duplicate_df):,}")
        print(f"   Số long_title duy nhất bị trùng: {len(duplicate_titles):,}")
        
        # Thống kê các trường hợp trùng
        duplicate_df['long_title_normalized'] = duplicate_df['long_title'].astype(str).str.strip().str.lower()
        
        # Đếm các trường hợp: 9-9, 9-10, 10-10
        icd9_vs_icd9 = 0
        icd9_vs_icd10 = 0
        icd10_vs_icd10 = 0
        
        for title_norm in duplicate_titles:
            group = duplicate_df[duplicate_df['long_title_normalized'] == title_norm]
            versions = set(group['icd_version'].unique())
            
            if len(versions) == 1:
                if 9 in versions:
                    icd9_vs_icd9 += 1
                elif 10 in versions:
                    icd10_vs_icd10 += 1
            else:
                if 9 in versions and 10 in versions:
                    icd9_vs_icd10 += 1
        
        print(f"\n📊 Thống kê các trường hợp trùng:")
        print(f"   ICD-9 trùng với ICD-9: {icd9_vs_icd9:,} nhóm")
        print(f"   ICD-9 trùng với ICD-10: {icd9_vs_icd10:,} nhóm")
        print(f"   ICD-10 trùng với ICD-10: {icd10_vs_icd10:,} nhóm")
        
        # Lưu file duplicate (tùy chọn, để tham khảo)
        DUPLICATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        duplicate_df[['icd_code', 'icd_version', 'long_title']].to_csv(DUPLICATE_FILE, index=False)
        print(f"\n✅ Đã lưu danh sách duplicate: {DUPLICATE_FILE.name}")
        
        return duplicate_df
        
    except Exception as e:
        print(f"❌ Lỗi khi xử lý: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_icd_mapping(duplicate_df=None):
    """Tạo mapping để thống nhất các ICD code trùng long_title"""
    
    print("\n" + "=" * 60)
    print("BƯỚC 2: TẠO MAPPING THỐNG NHẤT ICD CODE")
    print("=" * 60)
    
    if duplicate_df is None:
        if not DUPLICATE_FILE.exists():
            print(f"⚠️  File duplicate không tồn tại. Chạy find_duplicate_icd_diagnoses() trước")
            return None
        duplicate_df = pd.read_csv(DUPLICATE_FILE)
    
    # Chuẩn hóa long_title để nhóm
    duplicate_df['long_title_normalized'] = duplicate_df['long_title'].astype(str).str.strip().str.lower()
    
    # Tạo mapping: với mỗi long_title trùng, chọn ICD canonical
    # Quy tắc: Ưu tiên ICD-10, nếu có nhiều ICD-10 thì chọn theo thứ tự alphabet của icd_code
    mappings = []
    
    # Nhóm các ICD theo long_title_normalized
    duplicate_titles = duplicate_df['long_title_normalized'].unique()
    print(f"\n🔄 Đang xử lý {len(duplicate_titles):,} long_title trùng lặp...")
    
    for title_norm in duplicate_titles:
        # Lấy tất cả ICD có cùng long_title
        group = duplicate_df[duplicate_df['long_title_normalized'] == title_norm].copy()
        
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
    
    print(f"\n✅ Đã tạo {len(mapping_df):,} mapping")
    
    # Thống kê chi tiết các trường hợp mapping
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
    print(f"   ICD-9 -> ICD-10: {icd9_to_icd10:,}")
    print(f"   ICD-10 -> ICD-10: {icd10_to_icd10:,}")
    print(f"   ICD-9 -> ICD-9: {icd9_to_icd9:,}")
    
    # Sắp xếp để dễ đọc
    mapping_df = mapping_df.sort_values(['long_title', 'original_icd_version', 'original_icd_code'])
    
    # Lưu file mapping
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(MAPPING_FILE, index=False)
    print(f"\n✅ Đã lưu mapping: {MAPPING_FILE.name}")
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

def apply_mapping_to_diagnoses_icd(mapping_df=None, input_file=None, output_file=None, use_full_file=False):
    """Áp dụng mapping vào diagnoses_icd.csv
    
    Args:
        mapping_df: DataFrame chứa mapping (nếu None sẽ đọc từ file)
        input_file: Đường dẫn file input (nếu None sẽ dùng file mặc định)
        output_file: Đường dẫn file output (nếu None sẽ dùng file mặc định)
        use_full_file: Nếu True, xử lý file gốc đầy đủ từ mimiciv/3.1/hosp/
    """
    
    print("\n" + "=" * 60)
    print("BƯỚC 3: ÁP DỤNG MAPPING VÀO diagnoses_icd.csv")
    print("=" * 60)
    
    if mapping_df is None:
        if not MAPPING_FILE.exists():
            print(f"⚠️  File mapping chưa tồn tại. Chạy create_icd_mapping() trước.")
            return None
        mapping_df = pd.read_csv(MAPPING_FILE)
    
    # Xác định file input và output
    if use_full_file:
        # Sử dụng file gốc đầy đủ
        if input_file is None:
            input_file = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "diagnoses_icd.csv.gz"
        if output_file is None:
            # Lưu vào thư mục proc để không ảnh hưởng file gốc
            output_dir = DATA_DIR / "proc"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "diagnoses_icd_unified.csv.gz"
    else:
        # Sử dụng file lite (mặc định)
        if input_file is None:
            input_file = DATA_DIR / "mimic-iv-lite" / "diagnoses_icd.csv"
        if output_file is None:
            output_file = DATA_DIR / "mimic-iv-lite" / "diagnoses_icd_unified.csv"
    
    if not input_file.exists():
        print(f"⚠️  File {input_file} không tồn tại. Bỏ qua.")
        return None
    
    print(f"\n🔄 Áp dụng mapping vào {input_file.name}...")
    
    # Tạo mapping dictionary để lookup nhanh
    mapping_dict = {}
    for _, row in mapping_df.iterrows():
        key = (str(row['original_icd_code']), int(row['original_icd_version']))
        mapping_dict[key] = (str(row['canonical_icd_code']), int(row['canonical_icd_version']))
    
    print(f"   Đã load {len(mapping_dict):,} mapping")
    
    # Xử lý file gzip hoặc file thường
    is_gzip = str(input_file).endswith('.gz')
    use_chunks = use_full_file  # Chỉ dùng chunks cho file lớn
    
    if use_chunks:
        # Xử lý theo chunks để tiết kiệm memory
        print(f"   Xử lý file lớn theo chunks...")
        chunk_size = 100_000
        total_rows = 0
        changed_count = 0
        first_chunk = True
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Xóa file output nếu đã tồn tại
        if output_file.exists():
            output_file.unlink()
        
        for chunk_num, chunk in enumerate(pd.read_csv(input_file, compression='gzip' if is_gzip else None, 
                                                      chunksize=chunk_size, low_memory=False)):
            total_rows += len(chunk)
            
            # Áp dụng mapping
            def map_icd(row):
                key = (str(row['icd_code']), int(row['icd_version']))
                if key in mapping_dict:
                    return mapping_dict[key]
                return (str(row['icd_code']), int(row['icd_version']))
            
            # Lưu ICD gốc để đếm số thay đổi
            original_icd = chunk[['icd_code', 'icd_version']].copy()
            
            mapped = chunk.apply(lambda row: map_icd(row), axis=1)
            chunk['icd_code'] = [x[0] for x in mapped]
            chunk['icd_version'] = [x[1] for x in mapped]
            
            # Đếm số dòng thay đổi
            changed_mask = (original_icd['icd_code'] != chunk['icd_code']) | (original_icd['icd_version'] != chunk['icd_version'])
            changed_count += changed_mask.sum()
            
            # Lưu chunk
            mode = 'w' if first_chunk else 'a'
            header = first_chunk
            chunk.to_csv(output_file, mode=mode, header=header, index=False, 
                        compression='gzip' if str(output_file).endswith('.gz') else None)
            first_chunk = False
            
            if (chunk_num + 1) % 10 == 0:
                print(f"   Đã xử lý {total_rows:,} dòng, đã thay đổi {changed_count:,} dòng...")
        
        print(f"\n✅ Đã lưu file đã unified: {output_file}")
        print(f"   Tổng số dòng: {total_rows:,}")
        print(f"   Số dòng được thay đổi: {changed_count:,}")
        print(f"   Tỷ lệ thay đổi: {changed_count/total_rows*100:.2f}%")
        
    else:
        # Xử lý file nhỏ (load toàn bộ vào memory)
        df_diag = pd.read_csv(input_file, compression='gzip' if is_gzip else None, low_memory=False)
        print(f"   Số dòng ban đầu: {len(df_diag):,}")
        
        # Lưu ICD gốc để đếm
        original_icd = df_diag[['icd_code', 'icd_version']].copy()
        
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
        
        mapped = df_diag.apply(lambda row: map_icd(row), axis=1)
        df_diag['icd_code'] = mapped['icd_code']
        df_diag['icd_version'] = mapped['icd_version']
        
        # Đếm số dòng thay đổi
        changed_mask = (original_icd['icd_code'] != df_diag['icd_code']) | (original_icd['icd_version'] != df_diag['icd_version'])
        changed_count = changed_mask.sum()
        
        print(f"   Số dòng được thay đổi: {changed_count:,}")
        print(f"   Tỷ lệ thay đổi: {changed_count/len(df_diag)*100:.2f}%")
        
        # Lưu file mới
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_diag.to_csv(output_file, index=False, compression='gzip' if str(output_file).endswith('.gz') else None)
        print(f"\n✅ Đã lưu file đã unified: {output_file}")
        print(f"   Số dòng sau mapping: {len(df_diag):,}")
        
        # Thống kê sau mapping
        unique_icd_after = df_diag.groupby(['icd_code', 'icd_version']).size().reset_index(name='count')
        print(f"   Số ICD unique sau mapping: {len(unique_icd_after):,}")
        
        return df_diag
    
    return None

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
    # Tìm duplicate
    duplicate_df = find_duplicate_icd_diagnoses()
    
    if duplicate_df is None or len(duplicate_df) == 0:
        print("\n⚠️  Không có ICD trùng lặp để xử lý.")
        sys.exit(0)
    
    # Tạo mapping
    mapping_df = create_icd_mapping(duplicate_df)
    
    if mapping_df is None:
        print("\n⚠️  Không thể tạo mapping.")
        sys.exit(1)
    
    # Mặc định xử lý file gốc đầy đủ
    # Có thể dùng --lite để xử lý file mẫu
    use_lite = '--lite' in sys.argv
    
    if use_lite:
        print("\n📝 Chế độ: Xử lý file lite (mẫu)")
        apply_mapping_to_diagnoses_icd(mapping_df, use_full_file=False)
        
        print("\n" + "=" * 60)
        print("✨ HOÀN THÀNH!")
        print("=" * 60)
        print(f"\n📁 Các file đã tạo:")
        print(f"   1. Duplicate list: {DUPLICATE_FILE}")
        print(f"   2. Mapping: {MAPPING_FILE}")
        print(f"   3. Diagnoses đã unified (file lite): {DATA_DIR / 'mimic-iv-lite' / 'diagnoses_icd_unified.csv'}")
    else:
        print("\n⚠️  Xử lý file gốc đầy đủ (6M+ dòng), có thể mất vài phút...")
        apply_mapping_to_diagnoses_icd(mapping_df, use_full_file=True)
        
        print("\n" + "=" * 60)
        print("✨ HOÀN THÀNH!")
        print("=" * 60)
        print(f"\n📁 Các file đã tạo:")
        print(f"   1. Duplicate list: {DUPLICATE_FILE}")
        print(f"   2. Mapping: {MAPPING_FILE}")
        print(f"   3. Diagnoses đã unified (file gốc): {DATA_DIR / 'proc' / 'diagnoses_icd_unified.csv.gz'}")
    
    print(f"\n💡 Để sử dụng mapping trong code khác:")
    print(f"   from jobs.02_unify_duplicate_icd import load_icd_mapping, map_single_icd")
    print(f"   mapping = load_icd_mapping()")
    print(f"   canonical_code, canonical_version = map_single_icd('99962', 9, mapping)")

