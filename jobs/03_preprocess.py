"""
Script để tạo file train_unified.parquet từ các file nguồn.
Kết hợp discharge notes, demographics, và ICD codes đã unified.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import re
from pathlib import Path

# Đường dẫn
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "proc"

# Đường dẫn các file nguồn
DISCHARGE_FILE = DATA_DIR / "mimic-iv-note" / "2.2" / "note" / "discharge.csv.gz"
PATIENTS_FILE = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "patients.csv.gz"
ADMISSIONS_FILE = DATA_DIR / "mimiciv" / "3.1" / "hosp" / "admissions.csv.gz"
DIAGNOSES_FILE = DATA_DIR / "proc" / "diagnoses_icd_unified.csv.gz"

# File output
OUTPUT_FILE = OUTPUT_DIR / "train_unified.parquet"

# Cấu hình
MAX_CHARS = 8000  # Giới hạn độ dài text
TEXT_FROM_SERVICE_ONLY = True  # Chỉ lấy phần từ "Service:" trở đi

def keep_from_service(text: str) -> str:
    """Lấy phần text từ 'Service:' trở đi"""
    if not isinstance(text, str):
        return ""
    match = re.search(r'\bService\s*:', text, flags=re.I)
    if match is not None:
        return text[match.start():]
    return text

def create_train_unified():
    """Tạo file train_unified.parquet"""
    
    print("=" * 60)
    print("TẠO FILE train_unified.parquet")
    print("=" * 60)
    
    # Kiểm tra các file nguồn
    required_files = {
        "discharge": DISCHARGE_FILE,
        "patients": PATIENTS_FILE,
        "admissions": ADMISSIONS_FILE,
        "diagnoses": DIAGNOSES_FILE
    }
    
    for name, path in required_files.items():
        if not path.exists():
            print(f"❌ File không tồn tại: {path}")
            return
        print(f"✅ {name}: {path.name}")
    
    # Bước 1: Đọc và chuẩn bị demographics
    print("\n📖 Bước 1: Đọc demographics...")
    print("   Đang đọc patients...")
    patients = pd.read_csv(PATIENTS_FILE, compression='gzip', 
                          usecols=['subject_id', 'gender', 'anchor_age', 'anchor_year'])
    
    print("   Đang đọc admissions...")
    admissions = pd.read_csv(ADMISSIONS_FILE, compression='gzip',
                            usecols=['subject_id', 'hadm_id', 'admittime'],
                            parse_dates=['admittime'])
    
    # Merge và tính age_at_admit
    print("   Tính toán age_at_admit...")
    adm_pat = admissions.merge(patients, on='subject_id', how='left')
    adm_pat['age_at_admit'] = (
        adm_pat['anchor_age'] + 
        (adm_pat['admittime'].dt.year - adm_pat['anchor_year'])
    ).clip(lower=0, upper=120)
    
    demographics = adm_pat[['subject_id', 'hadm_id', 'gender', 'age_at_admit']].copy()
    print(f"   Đã tạo demographics: {len(demographics):,} dòng")
    
    # Bước 2: Đọc và chuẩn bị ICD codes
    print("\n📖 Bước 2: Đọc ICD codes...")
    print("   Đang đọc diagnoses_icd_unified...")
    
    # Tạo mapping hadm_id -> list icd_full
    hadm2codes = {}
    chunk_size = 200_000
    
    for chunk in pd.read_csv(DIAGNOSES_FILE, compression='gzip',
                            usecols=['hadm_id', 'icd_code', 'icd_version'],
                            chunksize=chunk_size):
        # Loại bỏ duplicate
        chunk = chunk.drop_duplicates(['hadm_id', 'icd_code', 'icd_version'])
        
        # Tạo icd_full: version-code
        chunk['icd_full'] = (
            chunk['icd_version'].astype(str) + "-" + 
            chunk['icd_code'].astype(str)
        )
        
        # Gộp theo hadm_id
        for hadm_id, group in chunk.groupby('hadm_id'):
            hadm_id_int = int(hadm_id)
            if hadm_id_int not in hadm2codes:
                hadm2codes[hadm_id_int] = []
            hadm2codes[hadm_id_int].extend(group['icd_full'].tolist())
    
    # Loại bỏ duplicate trong mỗi hadm_id và sắp xếp
    for hadm_id in hadm2codes:
        hadm2codes[hadm_id] = sorted(set(hadm2codes[hadm_id]))
    
    print(f"   Đã tạo mapping cho {len(hadm2codes):,} hadm_id")
    
    # Bước 3: Đọc discharge notes và merge
    print("\n📖 Bước 3: Đọc discharge notes và merge...")
    
    # Tìm cột text
    header = pd.read_csv(DISCHARGE_FILE, compression='gzip', nrows=0).columns
    text_col = None
    for col in header:
        if col.lower() in ['text', 'note_text']:
            text_col = col
            break
    
    if text_col is None:
        print(f"❌ Không tìm thấy cột text trong {DISCHARGE_FILE}")
        return
    
    print(f"   Sử dụng cột: {text_col}")
    
    # Xóa file output nếu đã tồn tại
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Xử lý theo chunks
    writer = None
    batch = []
    batch_size = 10_000
    total_processed = 0
    total_written = 0
    
    print("   Đang xử lý discharge notes...")
    
    for chunk_num, chunk in enumerate(pd.read_csv(
        DISCHARGE_FILE, 
        compression='gzip',
        usecols=['subject_id', 'hadm_id', text_col],
        chunksize=100_000,
        low_memory=True
    )):
        total_processed += len(chunk)
        
        # Merge với demographics
        chunk = chunk.merge(demographics, on=['subject_id', 'hadm_id'], how='left')
        
        # Lọc các dòng có text hợp lệ
        txt = chunk[text_col].astype(str)
        mask = ~(txt.isna() | txt.str.lower().isin(['nan', 'none', '']))
        chunk = chunk[mask].copy()
        
        if chunk.empty:
            continue
        
        # Tạo text_clean
        if TEXT_FROM_SERVICE_ONLY:
            chunk['text_clean'] = txt[mask].map(keep_from_service)
        else:
            chunk['text_clean'] = txt[mask].str.slice(0, MAX_CHARS)
        
        # Giới hạn độ dài
        chunk['text_clean'] = chunk['text_clean'].str.slice(0, MAX_CHARS)
        
        # Gắn ICD codes
        chunk['icd_codes'] = chunk['hadm_id'].map(
            lambda h: ';'.join(hadm2codes.get(int(h), []))
        )
        
        # Chỉ giữ các dòng có cả text_clean và icd_codes
        chunk = chunk[
            (chunk['text_clean'].str.len() > 0) & 
            (chunk['icd_codes'].str.len() > 0)
        ].copy()
        
        if chunk.empty:
            continue
        
        # Chọn các cột cần thiết
        output_cols = ['subject_id', 'hadm_id', 'gender', 'age_at_admit', 
                      'icd_codes', 'text_clean']
        chunk = chunk[output_cols].copy()
        
        batch.append(chunk)
        
        # Ghi batch khi đủ lớn
        if sum(len(b) for b in batch) >= batch_size:
            combined = pd.concat(batch, ignore_index=True)
            
            try:
                table = pa.Table.from_pandas(combined)
                if writer is None:
                    writer = pq.ParquetWriter(OUTPUT_FILE, table.schema, compression='snappy')
                writer.write_table(table)
                total_written += len(combined)
                batch.clear()
                
                if (chunk_num + 1) % 10 == 0:
                    print(f"   Đã xử lý {total_processed:,} dòng, đã ghi {total_written:,} dòng...")
            except Exception as e:
                print(f"⚠️  Lỗi khi ghi parquet: {e}")
                # Fallback: ghi CSV
                csv_file = OUTPUT_DIR / "train_unified.csv"
                if not csv_file.exists():
                    combined.to_csv(csv_file, index=False, mode='w', header=True)
                else:
                    combined.to_csv(csv_file, index=False, mode='a', header=False)
                total_written += len(combined)
                batch.clear()
    
    # Ghi phần còn lại
    if batch:
        combined = pd.concat(batch, ignore_index=True)
        try:
            table = pa.Table.from_pandas(combined)
            if writer is None:
                writer = pq.ParquetWriter(OUTPUT_FILE, table.schema, compression='snappy')
            writer.write_table(table)
            total_written += len(combined)
        except Exception as e:
            print(f"⚠️  Lỗi khi ghi parquet: {e}")
            csv_file = OUTPUT_DIR / "train_unified.csv"
            if not csv_file.exists():
                combined.to_csv(csv_file, index=False, mode='w', header=True)
            else:
                combined.to_csv(csv_file, index=False, mode='a', header=False)
            total_written += len(combined)
    
    # Đóng writer
    if writer is not None:
        writer.close()
    
    print("\n" + "=" * 60)
    print("✨ HOÀN THÀNH!")
    print("=" * 60)
    print(f"\n📊 Thống kê:")
    print(f"   Tổng số dòng đã xử lý: {total_processed:,}")
    print(f"   Số dòng đã ghi: {total_written:,}")
    print(f"   File output: {OUTPUT_FILE}")
    
    if OUTPUT_FILE.exists():
        file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
        print(f"   Kích thước file: {file_size:.2f} MB")
        
        # Kiểm tra file
        print("\n📋 Kiểm tra file output:")
        df_sample = pd.read_parquet(OUTPUT_FILE).head(5)
        print(f"   Số cột: {len(df_sample.columns)}")
        print(f"   Các cột: {list(df_sample.columns)}")
        print("\n   Mẫu dữ liệu:")
        print(df_sample.to_string())

if __name__ == "__main__":
    create_train_unified()

