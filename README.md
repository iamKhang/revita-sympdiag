# KẾ HOẠCH TRIỂN KHAI
**(6 bước huấn luyện mô hình với BioBERT trên MIMIC-IV – bản dễ hiểu, có ví dụ)**

---

## Mục tiêu
Xây dựng mô hình **nhập TRIỆU CHỨNG (văn bản)** → **gợi ý CHẨN ĐOÁN (ICD)** và **XÉT NGHIỆM** (lab/cận lâm sàng).  
Mô hình nền: **BioBERT** (đã đọc rất nhiều văn bản y khoa), ta **tinh chỉnh (fine-tune)** bằng dữ liệu MIMIC-IV.

---

## Dữ liệu cần có (tóm tắt)
- **Triệu chứng/ghi chú sớm**: câu chữ mô tả tình trạng ban đầu của bệnh nhân.
- **Nhãn thật**:
  - **Chẩn đoán (ICD/ICD-block)**: mã bệnh được gán cho ca bệnh.
  - **Xét nghiệm**: các xét nghiệm/cận lâm sàng **thực sự được chỉ định** (ví dụ trong 6 giờ đầu).
- Chia **train / validation / test** theo **bệnh nhân** (tránh rò rỉ).

---

## 6 BƯỚC HUẤN LUYỆN (TRAINING)

### Bước 1 — ĐƯA ĐẦU VÀO (Input)
- Lấy **triệu chứng** dạng câu chữ, ví dụ: “Đau ngực, khó thở, vã mồ hôi.”  
- Đưa câu này vào **BioBERT** để xử lý.  
> Nghĩ đơn giản: bạn đưa CÂU HỎI cho “bác sĩ AI”.

### Bước 2 — BIOBERT ĐỌC HIỂU (Embedding)
- BioBERT “đọc” câu và biến thành **vector số** (embedding) chứa ý nghĩa y khoa của câu.  
- Ví dụ: “đau ngực, khó thở” → `[0.2, -0.7, 0.5, …]` (một dãy số dài).  
> Giống như dịch câu chữ sang **ngôn ngữ số** mà máy hiểu.

### Bước 3 — BỘ RA QUYẾT ĐỊNH (Classifier Head)
- Vector từ BioBERT đi qua **một lớp nhỏ** (Dense).  
- Lớp này có **nhiều “ô”** – mỗi ô là **một nhãn** cần dự đoán:
  - Ô1 = “ICD I21 – Nhồi máu cơ tim”
  - Ô2 = “ICD J18 – Viêm phổi”
  - Ô3 = “Xét nghiệm Troponin”
  - Ô4 = “X-quang ngực”
  - …
- Kết quả: mỗi ô sáng lên **một xác suất (0→1)**, ví dụ: `[0.85, 0.30, 0.92, 0.75]`.  
> Hình dung như **bảng công tắc**: công tắc nào sáng mạnh → mô hình “nghiêng” về nhãn đó.

### Bước 4 — SO SÁNH VỚI SỰ THẬT (Ground Truth)
- Lấy **nhãn thật** từ MIMIC-IV (chẩn đoán & xét nghiệm đã làm).  
- So sánh với dự đoán ở Bước 3 để biết **đúng/sai**.  
> Đây là lúc “**chấm bài**” cho mô hình.

### Bước 5 — TÍNH SAI SỐ (Loss)
- Tính **điểm sai (loss)** – càng gần nhãn thật, loss càng nhỏ.  
- Vì một bệnh nhân có thể có **nhiều nhãn cùng lúc** (multi-label) → dùng **Binary Cross-Entropy (BCE)**.  
> Hiểu nôm na: sai ít bị trừ ít điểm, sai nhiều bị trừ nhiều.

### Bước 6 — SỬA SAI & HỌC LẠI (Training)
- Dùng **thuật toán tối ưu AdamW** (biến thể của gradient descent) để **sửa dần** các “núm chỉnh” bên trong mô hình.  
- Lặp lại qua **nhiều ca bệnh** và **nhiều vòng (epoch)** → mô hình ngày càng chính xác.  
> Làm nhiều đề, rút kinh nghiệm, điểm ngày càng cao.

---

## VÍ DỤ NGẮN – DỄ HÌNH DUNG

**Input (triệu chứng):** “Đau ngực, khó thở, vã mồ hôi.”  

**Dự đoán của mô hình (sau Bước 3):**
- I21 – Nhồi máu cơ tim: **0.85**
- J18 – Viêm phổi: **0.30**
- Troponin: **0.92**
- X-quang ngực: **0.75**

**Nhãn thật (từ bệnh án):**
- I21 ✔️
- Troponin ✔️
- X-quang ngực ✔️

**Đánh giá:**
- Dự đoán khá khớp thực tế → **loss nhỏ** → tiếp tục huấn luyện để còn chính xác hơn.

---

## GỢI Ý THỰC TẾ
- **Ngôn ngữ**: nếu nhập tiếng Việt, hãy **dịch sang tiếng Anh** trước khi đưa vào BioBERT (vì BioBERT học tiếng Anh y khoa).  
- **Chia dữ liệu**: theo **subject_id** (bệnh nhân) để tránh cùng một người lọt vào cả train và test.  
- **Chỉ số đánh giá nên báo cáo**: F1 (micro/macro), **AUPRC**, Precision@k / Recall@k.  
- **Tài nguyên**: có thể chạy demo trên laptop; để train lớn thì dùng **Colab/Kaggle (miễn phí)** hoặc GPU cloud.

---

## TỪ KHÓA NHỚ NHANH
- **BioBERT**: “bác sĩ AI” biết đọc hiểu tiếng Anh y khoa.  
- **Classifier head**: “bảng công tắc” bật/tắt nhãn (ICD, xét nghiệm).  
- **Fine-tuning**: dạy thêm bằng dữ liệu của bạn để mô hình quen “bài thi” thực tế.
