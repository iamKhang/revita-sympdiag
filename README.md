# 🧠 Quy trình Huấn luyện và Sử dụng Mô hình Dự đoán Bệnh Từ Ghi Chú (Discharge Note)

Tài liệu này mô tả chi tiết **quy trình huấn luyện (5 bước)** và **cách sử dụng mô hình sau khi huấn luyện**, bao gồm ví dụ với 4 ghi chú bệnh, dữ liệu tuổi và giới tính, cùng phần giải thích rõ ràng về cách tính toán và suy luận kết quả.

---

## 🩺 **Bước 1 — Chuẩn bị dữ liệu và biểu diễn văn bản bằng TF‑IDF (chi tiết)**

> Mục tiêu: biến ghi chú dạng chữ thành **ma trận đặc trưng thưa** (sparse) để mô hình học được.

### 1.1. Chuẩn hoá & làm sạch văn bản

* **Giới hạn độ dài**: cắt tối đa `MAX_TOKENS_PER_DOC = 8000` token để tiết kiệm RAM.
* **Chuẩn hoá**: lower‑case, chuẩn hoá khoảng trắng, bỏ ký tự/emoji không cần thiết.
* **Tokenize**: tách từ theo khoảng trắng, có thể giữ dấu gạch dưới cho multi‑word (vd. `tăng_huyết_áp`).
* **Stopwords**: tuỳ ngữ cảnh (tài liệu gốc không loại riêng), TF‑IDF tự giảm trọng số từ phổ biến nhờ **IDF**.

### 1.2. Thiết lập vectorizer (theo mã của bạn)

* **WORD_NGRAM_RANGE = (1, 2)**: dùng uni‑gram & bi‑gram từ.
* **USE_CHAR_NGRAMS = False**: không dùng char n‑gram.
* **MAX_FEATURES_WORD = 200000**: giới hạn tối đa 200k từ khoá.
* **MIN_DF = 2**: bỏ những từ xuất hiện < 2 tài liệu.
* **SUBLINEAR_TF = True**: dùng `tf' = log(1 + tf)` thay vì tf thô.
* **norm = "l2"**, **dtype = float32**: chuẩn hoá vector về độ dài 1, tiết kiệm bộ nhớ.
* **Fit trên TRAIN ONLY**: `word_vec.fit(train.text)` để **tránh rò rỉ**; chỉ `transform()` cho val/test.

### 1.3. Xây từ điển & ma trận đặc trưng

Giả sử sau khi fit, từ điển (rút gọn minh hoạ) gồm 10 mục:

```
['huyết_áp', 'tiểu_đường', 'nhiễm_trùng', 'sốt', 'phẫu_thuật',
 'hen', 'thuốc', 'ngực', 'khó_thở', 'điều_trị']
```

* **Chỉ mục** (vocabulary index) cố định theo thứ tự tần suất/IDF nội bộ.
* **OOV** (từ ngoài từ điển) khi transform sẽ bị **bỏ qua** (đặt 0).
* **Đầu ra** khi biến đổi N tài liệu: `X` có **shape `(N, V)`** với `V ≤ 200000`, định dạng **CSR sparse**.

### 1.4. Công thức TF‑IDF (và ý nghĩa từng thành phần)

Với một tài liệu *d* và một từ/bi‑gram *t*:

```
TF_sublinear(t, d) = log(1 + tf(t, d))
IDF(t)             = log( (1 + N) / (1 + df(t)) ) + 1
TFIDF(t, d)        = TF_sublinear(t, d) × IDF(t)
```

* `tf(t, d)`: số lần *t* xuất hiện trong *d*.
* `df(t)`: số tài liệu chứa *t*.
* `N`: tổng số tài liệu trong **tập TRAIN**.
* **Chuẩn hoá L2**: sau khi tính TF‑IDF cho mọi *t* trong *d*, vector được chuẩn hoá về độ dài 1.

### 1.5. Ví dụ tính tay (4 ghi chú — rút gọn)

Dữ liệu (như ở phần tổng quan):

| ID | Ghi chú                                                    | Tuổi | Giới |
| -- | ---------------------------------------------------------- | ---- | ---- |
| 1  | "Bệnh nhân đau **ngực** và **huyết_áp** cao"               | 58   | Nam  |
| 2  | "Bệnh nhân bị **tiểu_đường** và **huyết_áp**"              | 62   | Nữ   |
| 3  | "Sau **phẫu_thuật**, bệnh nhân **sốt** và **nhiễm_trùng**" | 45   | Nam  |
| 4  | "**Hen** phế quản, **khó_thở**, điều trị bằng **thuốc**"   | 36   | Nữ   |

**Bước A — Đếm df(t) (xuất hiện theo tài liệu)**

* `huyết_áp`: xuất hiện ở note 1 & 2 → `df=2`
* `tiểu_đường`: note 2 → `df=1`
* `nhiễm_trùng`: note 3 → `df=1`
* `sốt`: note 3 → `df=1`
* `phẫu_thuật`: note 3 → `df=1`
* `hen`: note 4 → `df=1`
* `thuốc`: note 4 → `df=1`
* `ngực`: note 1 → `df=1`
* `khó_thở`: note 4 → `df=1`
* `điều_trị`: note 4 → `df=1`

Với `N=4`, tính **IDF** (minh hoạ):

```
IDF(huyết_áp) = log((1+4)/(1+2)) + 1 = log(5/3) + 1 ≈ 1.511
IDF(từ có df=1) = log((1+4)/(1+1)) + 1 = log(5/2) + 1 ≈ 1.916
```

**Bước B — Tính TF_sublinear và TF‑IDF cho note 2**

* Note 2 chứa: `tiểu_đường (tf=1)`, `huyết_áp (tf=1)` …
* `TF_sublinear = log(1+1) = log(2) ≈ 0.693`
* `TFIDF(tiểu_đường, note2) ≈ 0.693 × 1.916 ≈ 1.327`
* `TFIDF(huyết_áp, note2)  ≈ 0.693 × 1.511 ≈ 1.047`
* Các mục khác = 0.
* Vector thô (theo thứ tự V ở trên):

```
[1.047, 1.327, 0, 0, 0, 0, 0, 0, 0, 0]
```

* **Chuẩn hoá L2**: chia toàn bộ vector cho norm để có vector cuối cùng (tổng bình phương = 1).

**Bước C — Ma trận đầu ra X (rút gọn V=10)**

| ID | X[d, :] (sau chuẩn hoá, minh hoạ)                            |
| -- | ------------------------------------------------------------ |
| 1  | [0.90, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.70, 0.00, 0.00] |
| 2  | [0.62, 0.78, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00] |
| 3  | [0.00, 0.00, 0.80, 0.70, 0.60, 0.00, 0.00, 0.00, 0.00, 0.00] |
| 4  | [0.00, 0.00, 0.00, 0.00, 0.00, 0.90, 0.80, 0.00, 0.70, 0.50] |

> Thực tế V có thể tới **200.000**; ma trận `X` là **sparse CSR**: chỉ lưu các mục khác 0 để tiết kiệm bộ nhớ.

### 1.6. Hình dạng dữ liệu tổng quan (train/val/test)

* **Train**: `X_train` shape `(N_train, V)` được **fit+transform**.
* **Val/Test**: `X_val`, `X_test` dùng **cùng vocabulary** → chỉ **transform**.
* Các đặc trưng tabular (tuổi, giới) sẽ được ghép thêm ở **Bước 3 (Fusion)**.

---

## 👩‍🔬 **Bước 2 — Chuẩn hóa dữ liệu tuổi và giới tính (Tabular Features)**

— Chuẩn hóa dữ liệu tuổi và giới tính (Tabular Features)**

| Thuộc tính | Dạng dữ liệu | Mã hóa                 | Ví dụ                       |
| ---------- | ------------ | ---------------------- | --------------------------- |
| Tuổi       | Số           | `age_norm = age / 120` | 60 tuổi → 0.5               |
| Giới tính  | Danh mục     | One-hot (M,F,U)        | Nam → [1,0,0]; Nữ → [0,1,0] |

| ID | age_norm | onehot_M | onehot_F | onehot_U |
| -- | -------- | -------- | -------- | -------- |
| 1  | 0.48     | 1        | 0        | 0        |
| 2  | 0.52     | 0        | 1        | 0        |
| 3  | 0.38     | 1        | 0        | 0        |
| 4  | 0.30     | 0        | 1        | 0        |

---

## 🧩 **Bước 3 — Hợp nhất đặc trưng (Fusion)**

Ghép TF-IDF và tabular lại thành vector `x_full`.

| ID | x_text (10 từ)                         | x_tab (4 giá trị) | x_full (14 giá trị)                                   |
| -- | -------------------------------------- | ----------------- | ----------------------------------------------------- |
| 1  | [0.9, 0, 0, 0, 0, 0, 0, 0.7, 0, 0]     | [0.48, 1, 0, 0]   | [0.9, 0, 0, 0, 0, 0, 0, 0.7, 0, 0, 0.48, 1, 0, 0]     |
| 2  | [0.8, 0.6, 0, 0, 0, 0, 0, 0, 0, 0]     | [0.52, 0, 1, 0]   | [0.8, 0.6, 0, 0, 0, 0, 0, 0, 0, 0, 0.52, 0, 1, 0]     |
| 3  | [0, 0, 0.8, 0.7, 0.6, 0, 0, 0, 0, 0]   | [0.38, 1, 0, 0]   | [0, 0, 0.8, 0.7, 0.6, 0, 0, 0, 0, 0, 0.38, 1, 0, 0]   |
| 4  | [0, 0, 0, 0, 0, 0.9, 0.8, 0, 0.7, 0.5] | [0.30, 0, 1, 0]   | [0, 0, 0, 0, 0, 0.9, 0.8, 0, 0.7, 0.5, 0.30, 0, 1, 0] |

---

## ⚙️ **Bước 4 — Tách bài toán bằng One-Vs-Rest**

Chia bài toán đa nhãn thành nhiều bài toán nhị phân độc lập (mỗi bệnh 1 mô hình riêng):

| ID | Nhãn  | A (Huyết áp) | B (Tiểu đường) | C (Nhiễm trùng) |
| -- | ----- | ------------ | -------------- | --------------- |
| 1  | [A]   | 1            | 0              | 0               |
| 2  | [A,B] | 1            | 1              | 0               |
| 3  | [C]   | 0            | 0              | 1               |
| 4  | [ ]   | 0            | 0              | 0               |

Mỗi mô hình học cách dự đoán “Có bệnh X / Không có bệnh X”.

---

## 🧮 **Bước 5 — Huấn luyện từng mô hình bằng SGDClassifier (Hạ Gradient Ngẫu nhiên)**

> Mục tiêu: Tối ưu **trọng số** để mô hình hiểu *mỗi đặc trưng (từ TF‑IDF, tuổi, giới tính)* đóng góp như thế nào vào **xác suất có bệnh**.

### 5.1. Ký hiệu, ý nghĩa và **shape** (hình dạng dữ liệu)

| Ký hiệu | Ý nghĩa                                                              | Shape (kích thước)     | Ghi chú dễ hiểu                                                                     |
| ------- | -------------------------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------- |
| `x`     | Vector đặc trưng cho **một** bệnh nhân (TF‑IDF + tuổi + giới tính)   | `(F, 1)` hoặc `(1, F)` | F = số đặc trưng (vd. 200004). Mỗi phần tử nói lên “độ mạnh” của một từ/thuộc tính. |
| `W`     | **Vector trọng số** của **một** bệnh (mô hình con trong One‑Vs‑Rest) | `(1, F)`               | Mỗi phần tử cân nặng ảnh hưởng của một từ/thuộc tính lên bệnh đó.                   |
| `b`     | **Bias** (độ lệch nền) của **một** bệnh                              | `(1,)`                 | Điều chỉnh ngưỡng/độ phổ biến nền của bệnh.                                         |
| `z`     | **Điểm kích hoạt** trước sigmoid                                     | `(1,)`                 | Tổng có trọng số: “bằng chứng” cho bệnh.                                            |
| `P`     | **Xác suất** có bệnh (sau sigmoid)                                   | `(1,)`                 | Giá trị 0→1.                                                                        |
| `y`     | Nhãn thật (có/không bệnh)                                            | `(1,)`                 | 1 nếu có bệnh, 0 nếu không.                                                         |

> Với **1700** bệnh, ta có **1700 bộ** `(W, b)`; x **dùng chung** cho mọi bệnh.

### 5.2. Công thức (và ý nghĩa từng hạng)

```
z = W × x + b            # tổng có trọng số (bằng chứng)
P = σ(z) = 1/(1+e^(−z))  # chuẩn hoá về [0,1] → xác suất
Loss = −[y·log(P) + (1−y)·log(1−P)]  # sai số dự đoán
```

* `W × x` : mỗi **từ/thuộc tính** trong `x` được nhân với **trọng số** mà mô hình học được cho **bệnh đó**; sau đó cộng lại → “mức phù hợp” của ghi chú với bệnh.
* `+ b` : hiệu chỉnh nền (bệnh phổ biến/hiếm).
* `σ` (sigmoid) : biến tổng điểm `z` thành **xác suất**.
* `Loss` : càng nhỏ càng tốt; 0 nghĩa là dự đoán khớp nhãn.

### 5.3. Cập nhật học (gradient) — diễn giải dễ hiểu

Sau mỗi mẫu (hoặc mini‑batch), mô hình điều chỉnh `W, b` **ngược chiều sai số**:

```
W ← W − α · ∂Loss/∂W    
b ← b − α · ∂Loss/∂b
```

* `α` (learning rate): bước nhảy. Quá lớn → dao động; quá nhỏ → học chậm.
* Trực giác: nếu mô hình **đánh giá thấp** bệnh khi đáng ra **phải dương tính**, các trọng số ở những đặc trưng liên quan (ví dụ từ “huyết_áp” cho bệnh Tăng huyết áp) sẽ **tăng lên**.

### 5.4. Ví dụ tính toán **tường minh** (rút gọn)

Giả sử học bệnh **Tăng huyết áp (A)** với **F = 6** đặc trưng: 3 TF‑IDF + tuổi_norm + onehot_M + onehot_F.

* `x` (1 bệnh nhân):

```
x = [huyet_ap=0.90, tieu_duong=0.10, sot=0.00, age_norm=0.48, M=1, F=0]
```

* Trọng số ban đầu (giả lập):

```
W = [1.00, 0.10, 0.00, 0.30, 0.10, 0.00]
b = −0.40
```

* Tính `z, P`:

```
z = 1.00·0.90 + 0.10·0.10 + 0.00·0.00 + 0.30·0.48 + 0.10·1 + 0.00·0  + (−0.40)
  = 0.90 + 0.01 + 0 + 0.144 + 0.10 + 0 − 0.40 = 0.754
P = σ(0.754) ≈ 0.680
```

* Nhãn thật: `y = 1` (có tăng huyết áp) ⇒ sai số còn **lớn**.
* Gradient (trực giác): `error = P − y = −0.32` (dự đoán thấp hơn thật). Các trọng số gắn với tín hiệu liên quan ("huyet_ap", "age_norm", "M") sẽ được **tăng lên** sau cập nhật.

> Lặp lại qua nhiều mẫu → `W, b` hội tụ. Kết quả: từ/cột nào quan trọng cho **A** sẽ có **trọng số lớn** ở hàng **A** trong ma trận.

### 5.5. Toàn cục (1700 bệnh)

* Ma trận trọng số tổng thể: `W_all` **shape** `(1700, F)` (vd. `1700 × 200004`).
* Vector bias: `b_all` **shape** `(1700,)`.
* Mỗi hàng của `W_all` là “dấu vân tay ngôn ngữ” cho một bệnh.

---

## 🚀 **Bước 6 — Sử dụng mô hình để dự đoán (Inference)**

> Mục tiêu: Nhập **giới tính, tuổi, note** → trả về **top‑K bệnh gợi ý** với xác suất.

### 6.1. Dòng chảy dữ liệu (không cần học lại)

1. **Vector hoá note** bằng `word_vec` đã huấn luyện: tạo `x_text` (TF‑IDF, shape `(1, V)`; `V ≈ 200000`).
2. **Mã hoá tabular**: `age_norm = age/120`, `onehot_gender = [M, F, U]` → `x_tab` shape `(1, 4)`.
3. **Ghép**: `x_full = [x_text | x_tab]` → shape `(1, F)`.
4. **Tính cho tất cả bệnh cùng lúc** bằng ma trận:

```
Z = W_all × x_fullᵀ + b_all      # Z shape: (1700, 1)
P = sigmoid(Z)                    # P shape: (1700, 1)
```

> Không cần “chạy 1700 mô hình nối tiếp” — đây là **một phép nhân ma trận** đã được tối ưu hoá.

### 6.2. Ý nghĩa từng biến **khi dự đoán**

| Biến     | Shape       | Vai trò                                 |
| -------- | ----------- | --------------------------------------- |
| `x_text` | `(1, V)`    | Sức nặng TF‑IDF của từng từ trong note. |
| `x_tab`  | `(1, 4)`    | Tuổi (chuẩn hoá) + one‑hot giới tính.   |
| `x_full` | `(1, F)`    | Đầu vào cuối cùng cho mô hình.          |
| `W_all`  | `(1700, F)` | Trọng số cho **1700** bệnh.             |
| `b_all`  | `(1700,)`   | Bias cho **1700** bệnh.                 |
| `P`      | `(1700, 1)` | Xác suất từng bệnh.                     |

### 6.3. Ví dụ tường minh (rút gọn F=6)

Giả sử sau ghép ta có:

```
x_full = [huyet_ap=0.80, tieu_duong=0.60, nhiem_trung=0.00, age_norm=0.50, M=1, F=0]
```

Với 3 bệnh A/B/C, trọng số học được (giả lập):

```
W_A = [1.40, 0.20, 0.00, 0.60, 0.20, 0.00];  b_A = −0.30
W_B = [0.10, 1.30, 0.00, 0.40, 0.00, 0.10];  b_B = −0.20
W_C = [0.00, 0.00, 1.20, 0.10, 0.00, 0.20];  b_C = −0.50
```

Tính `z` và `P` cho từng bệnh:

```
z_A = dot(W_A, x_full) + b_A = 1.40·0.80 + 0.20·0.60 + 0.60·0.50 + 0.20·1 + (−0.30) = 1.62
P_A = σ(1.62) ≈ 0.835

z_B = 0.10·0.80 + 1.30·0.60 + 0.40·0.50 + 0.10·0 + (−0.20) = 0.98
P_B = σ(0.98) ≈ 0.727

z_C = 1.20·0.00 + 0.10·0.50 + 0.20·0 + (−0.50) = −0.45
P_C = σ(−0.45) ≈ 0.389
```

**Top‑K (K=2)**: A (0.835), B (0.727).

### 6.4. Từ xác suất → gợi ý

* **Top‑K**: lấy `K` bệnh có `P` cao nhất (ví dụ `K=15` trong mã của bạn).
* **Theo ngưỡng**: chọn các bệnh `P ≥ τ` (ví dụ `τ = 0.5`).
* Có thể hiển thị kèm **một vài từ có trọng số lớn** (từ hàng `W_k`) để giải thích vì sao mô hình gợi ý bệnh `k` (giải thích tuyến tính cơ bản).

### 6.5. Mã mẫu (ngắn gọn) — đã chú thích

```python
# 1) Vector hoá note bằng từ điển đã học
x_text = word_vec.transform([note])           # (1, V)

# 2) Mã hoá tabular
age_norm = age / 120.0
onehot = [1,0,0] if gender=='M' else [0,1,0] if gender=='F' else [0,0,1]
x_tab = np.array([[age_norm] + onehot])      # (1, 4)

# 3) Ghép đặc trưng
x_full = np.concatenate([x_text.toarray(), x_tab], axis=1)  # (1, F)

# 4) Dự đoán xác suất cho toàn bộ bệnh
P = clf.predict_proba(x_full)                 # (1, 1700)

# 5) Lấy Top-K gợi ý
codes = mlb.classes_
K = 5
idx = np.argsort(-P[0])[:K]
results = [(codes[i], float(P[0,i])) for i in idx]
```

— Sử dụng mô hình để dự đoán (Inference)**

### 🎯 Mục đích

Khi có **ghi chú, tuổi, và giới tính** của một bệnh nhân mới, mô hình sẽ dự đoán xác suất mắc từng bệnh.

### ⚙️ Các bước thực hiện

1. **Tiền xử lý đầu vào:**

```python
note = "Bệnh nhân tiểu đường, tăng huyết áp, đang điều trị thuốc"
age = 60
gender = "M"
```

2. **Mã hóa dữ liệu:**

```python
age_norm = age / 120      # 60 tuổi → 0.5
onehot = [1,0,0] if gender=="M" else [0,1,0]
```

3. **Vector hóa văn bản:**

```python
x_text = word_vec.transform([note])      # TF-IDF vector (1 × 200000)
```

4. **Ghép đặc trưng:**

```python
x_tab = np.array([[age_norm] + onehot])  # (1 × 4)
x_full = np.concatenate([x_text.toarray(), x_tab], axis=1)
```

5. **Dự đoán xác suất:**

```python
P = clf.predict_proba(x_full)
```

6. **Trích xuất top-K gợi ý:**

```python
codes = mlb.classes_
idx = np.argsort(-P[0])[:5]
for i in idx:
    print(codes[i], P[0][i])
```

### 🧩 Ví dụ kết quả

| Mã ICD  | Bệnh              | Xác suất |
| ------- | ----------------- | -------- |
| 10-I10  | Tăng huyết áp     | 0.92     |
| 10-E119 | Tiểu đường type 2 | 0.88     |
| 10-E785 | Mỡ máu cao        | 0.53     |
| 10-K219 | Trào ngược dạ dày | 0.31     |
| 10-N179 | Suy thận cấp      | 0.25     |

Kết quả trên là **top 5 bệnh được mô hình gợi ý** dựa trên ghi chú, tuổi và giới tính.

---

✅ **Tổng kết**

| Giai đoạn        | Mục tiêu                          | Kết quả                            |
| ---------------- | --------------------------------- | ---------------------------------- |
| Huấn luyện (1–5) | Học trọng số và mô hình hóa bệnh  | Lưu mô hình `ovr_sgd_tfidf.joblib` |
| Sử dụng (6)      | Dự đoán xác suất bệnh từ note mới | Xuất top‑K gợi ý bệnh tiềm năng    |
