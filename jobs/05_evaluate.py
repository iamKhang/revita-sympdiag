#!/usr/bin/env python3
"""
Script để đánh giá kết quả dự đoán từ file CSV.
Tính toán các chỉ số: Hit@K, trung bình số mã đúng, số ca dự đoán đúng hoàn toàn.
"""

import pandas as pd
from pathlib import Path
from typing import List, Set

# Đường dẫn file
BASE_DIR = Path(__file__).parent.parent
PREDS_FILE = BASE_DIR / "data" / "proc" / "preds_sample.csv"


def parse_gold(gold_str: str) -> Set[str]:
    """Parse chuỗi gold thành set các mã ICD."""
    if pd.isna(gold_str) or gold_str == "":
        return set()
    return set(code.strip() for code in gold_str.split(";") if code.strip())


def parse_pred_topk(pred_str: str, top_k: int = 10) -> List[str]:
    """Parse chuỗi pred_topK thành list các mã ICD theo thứ tự xác suất giảm dần."""
    if pd.isna(pred_str) or pred_str == "":
        return []
    
    # Parse các cặp code:prob
    items = []
    for item in pred_str.split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            code, prob = item.rsplit(":", 1)
            try:
                prob = float(prob)
                items.append((code.strip(), prob))
            except ValueError:
                continue
    
    # Sắp xếp theo xác suất giảm dần và lấy top-K
    items.sort(key=lambda x: x[1], reverse=True)
    return [code for code, _ in items[:top_k]]


def calculate_hit_at_k(gold_set: Set[str], pred_list: List[str], k: int) -> bool:
    """Kiểm tra xem có ít nhất 1 mã trong gold xuất hiện trong top-K dự đoán không."""
    if not gold_set or not pred_list:
        return False
    top_k_preds = set(pred_list[:k])
    return len(gold_set & top_k_preds) > 0


def calculate_correct_count(gold_set: Set[str], pred_list: List[str]) -> int:
    """Đếm số mã trong gold xuất hiện trong top-10 dự đoán."""
    if not gold_set or not pred_list:
        return 0
    top_10_preds = set(pred_list[:10])
    return len(gold_set & top_10_preds)


def calculate_fully_correct(gold_set: Set[str], pred_list: List[str]) -> bool:
    """Kiểm tra xem tất cả mã trong gold có đều nằm trong top-10 dự đoán không."""
    if not gold_set:
        return False
    top_10_preds = set(pred_list[:10])
    return gold_set.issubset(top_10_preds)


def main():
    """Hàm chính để tính toán các chỉ số đánh giá."""
    print("=" * 60)
    print("ĐÁNH GIÁ KẾT QUẢ DỰ ĐOÁN")
    print("=" * 60)
    
    # Đọc file CSV
    print(f"\nĐang đọc file: {PREDS_FILE}")
    df = pd.read_csv(PREDS_FILE)
    total_cases = len(df)
    print(f"Tổng số ca kiểm tra: {total_cases}")
    
    # Tính toán các chỉ số
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    hit_at_10 = 0
    total_correct_codes = 0
    fully_correct_cases = 0
    
    for idx, row in df.iterrows():
        gold_set = parse_gold(row["gold"])
        pred_list = parse_pred_topk(row["pred_topK"], top_k=10)
        
        # Tính Hit@K
        if calculate_hit_at_k(gold_set, pred_list, k=1):
            hit_at_1 += 1
        if calculate_hit_at_k(gold_set, pred_list, k=3):
            hit_at_3 += 1
        if calculate_hit_at_k(gold_set, pred_list, k=5):
            hit_at_5 += 1
        if calculate_hit_at_k(gold_set, pred_list, k=10):
            hit_at_10 += 1
        
        # Tính số mã đúng
        correct_count = calculate_correct_count(gold_set, pred_list)
        total_correct_codes += correct_count
        
        # Tính số ca dự đoán đúng hoàn toàn
        if calculate_fully_correct(gold_set, pred_list):
            fully_correct_cases += 1
    
    # Tính tỷ lệ
    hit_at_1_pct = (hit_at_1 / total_cases) * 100
    hit_at_3_pct = (hit_at_3 / total_cases) * 100
    hit_at_5_pct = (hit_at_5 / total_cases) * 100
    hit_at_10_pct = (hit_at_10 / total_cases) * 100
    avg_correct_per_case = total_correct_codes / total_cases
    fully_correct_pct = (fully_correct_cases / total_cases) * 100
    
    # In kết quả
    print("\n" + "=" * 60)
    print("KẾT QUẢ ĐỊNH LƯỢNG")
    print("=" * 60)
    print(f"\nTổng số ca kiểm tra: {total_cases}")
    print(f"\nHit@1: {hit_at_1_pct:.0f}% ({hit_at_1}/{total_cases})")
    print(f"  → {hit_at_1_pct:.0f}% ca có ít nhất 1 mã đúng ở vị trí đầu tiên")
    print(f"\nHit@3: {hit_at_3_pct:.0f}% ({hit_at_3}/{total_cases})")
    print(f"  → {hit_at_3_pct:.0f}% ca có ít nhất 1 mã đúng trong 3 mã đầu")
    print(f"\nHit@5: {hit_at_5_pct:.0f}% ({hit_at_5}/{total_cases})")
    print(f"  → {hit_at_5_pct:.0f}% ca có ít nhất 1 mã đúng trong top-5")
    print(f"\nHit@10: {hit_at_10_pct:.0f}% ({hit_at_10}/{total_cases})")
    print(f"  → {hit_at_10_pct:.0f}% ca có ít nhất 1 mã đúng trong top-10")
    print(f"\nTrung bình số mã đúng / ca: {avg_correct_per_case:.2f}")
    print(f"  → Mỗi ca dự đoán trúng trung bình ~{avg_correct_per_case:.2f} bệnh")
    print(f"\nSố ca dự đoán đúng hoàn toàn: {fully_correct_cases}/{total_cases} ({fully_correct_pct:.0f}%)")
    print(f"  → Toàn bộ mã thật đều nằm trong top-10")
    
    # In kết quả dạng bảng để copy vào LaTeX
    print("\n" + "=" * 60)
    print("KẾT QUẢ ĐỂ ĐIỀN VÀO BẢNG LaTeX")
    print("=" * 60)
    print(f"""
Tổng số ca kiểm tra & {total_cases} & Mẫu từ tập test \\\\
\\hline
Hit@1 & {hit_at_1_pct:.0f}\\% & {hit_at_1_pct:.0f}\\% ca có ít nhất 1 mã đúng ở vị trí đầu tiên \\\\
\\hline
Hit@3 & {hit_at_3_pct:.0f}\\% & {hit_at_3_pct:.0f}\\% ca có ít nhất 1 mã đúng trong 3 mã đầu \\\\
\\hline
Hit@5 & {hit_at_5_pct:.0f}\\% & {hit_at_5_pct:.0f}\\% ca có ít nhất 1 mã đúng trong top-5 \\\\
\\hline
Hit@10 & {hit_at_10_pct:.0f}\\% & {hit_at_10}/{total_cases} ca có ít nhất 1 mã đúng trong top-10 \\\\
\\hline
Trung bình số mã đúng / ca & {avg_correct_per_case:.2f} & Mỗi ca dự đoán trúng trung bình $\\sim${avg_correct_per_case:.2f} bệnh \\\\
\\hline
Số ca dự đoán đúng hoàn toàn & {fully_correct_cases}/{total_cases} ({fully_correct_pct:.0f}\\%) & Toàn bộ mã thật đều nằm trong top-10 \\\\
""")
    
    print("\n" + "=" * 60)
    print("HOÀN TẤT")
    print("=" * 60)


if __name__ == "__main__":
    main()

