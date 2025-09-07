# README: Ý nghĩa các file CSV trong MIMIC-IV và MIMIC-IV-Note

---

## 📂 mimic-iv-note/2.2/note
Các bảng chứa **ghi chú lâm sàng** (clinical notes).

- **discharge.csv / discharge.csv.gz**  
  Ghi chú xuất viện, tóm tắt toàn bộ quá trình nằm viện của bệnh nhân.

- **discharge_detail.csv.gz**  
  Bản chi tiết hơn của discharge, bao gồm cấu trúc từng phần (Chief complaint, History, Medications...).

- **radiology.csv.gz**  
  Ghi chú chẩn đoán hình ảnh (X-quang, CT, MRI...), tóm tắt kết quả.

- **radiology_detail.csv.gz**  
  Bản chi tiết hơn của radiology, chứa thông tin phân đoạn từng phần của báo cáo.

---

## 📂 mimiciv/3.1/hosp
Các bảng liên quan đến **hệ thống bệnh viện (hospital module)**.

- **admissions.csv.gz**  
  Thông tin lần nhập viện: thời gian, loại nhập viện (cấp cứu, tự nguyện...), tình trạng ra viện.

- **patients.csv.gz**  
  Thông tin bệnh nhân cơ bản: tuổi, giới, chủng tộc, ngày sinh.

- **diagnoses_icd.csv.gz**  
  Các chẩn đoán gán cho bệnh nhân theo mã ICD.

- **procedures_icd.csv.gz**  
  Thủ thuật, phẫu thuật được thực hiện, mã ICD.

- **d_icd_diagnoses.csv.gz**  
  Bảng từ điển: giải thích chi tiết từng mã ICD chẩn đoán.

- **d_icd_procedures.csv.gz**  
  Bảng từ điển: giải thích chi tiết từng mã ICD thủ thuật.

- **labevents.csv.gz**  
  Kết quả xét nghiệm (lab test) cho bệnh nhân (ví dụ: huyết học, sinh hóa, điện giải).

- **d_labitems.csv.gz**  
  Bảng từ điển: mô tả tên xét nghiệm, đơn vị đo.

- **pharmacy.csv.gz**  
  Đơn thuốc, lịch sử cấp phát thuốc từ khoa dược.

- **prescriptions.csv.gz**  
  Thông tin đơn thuốc chi tiết: tên thuốc, liều, đường dùng, thời gian.

- **poe.csv.gz / poe_detail.csv.gz**  
  Physician Order Entry – các y lệnh của bác sĩ (thuốc, xét nghiệm, dịch truyền).

- **emar.csv.gz / emar_detail.csv.gz**  
  Electronic Medication Administration Record – ghi nhận thực tế việc dùng thuốc cho bệnh nhân.

- **drgcodes.csv.gz**  
  Diagnosis-Related Groups – nhóm thanh toán theo chẩn đoán.

- **hcpcsevents.csv.gz**  
  Các thủ tục/bill mã hóa theo hệ thống HCPCS.

- **d_hcpcs.csv.gz**  
  Bảng từ điển: mô tả mã HCPCS.

- **microbiologyevents.csv.gz**  
  Kết quả cấy vi sinh, kháng sinh đồ.

- **services.csv.gz**  
  Thông tin khoa/phòng phục vụ bệnh nhân trong đợt nằm viện.

- **transfers.csv.gz**  
  Dịch chuyển bệnh nhân giữa các khoa/phòng trong bệnh viện.

- **provider.csv.gz**  
  Thông tin về nhà cung cấp dịch vụ y tế (ID bác sĩ, điều dưỡng…).

- **omr.csv.gz**  
  Outpatient Medical Record – hồ sơ khám ngoại trú (BMI, dấu hiệu sinh tồn...).

---

## 📂 mimiciv/3.1/icu
Các bảng liên quan đến **điều trị hồi sức (ICU module)**.

- **icustays.csv.gz**  
  Thông tin về các lần nằm ICU: thời gian vào/ra, liên kết với admissions.

- **chartevents.csv.gz**  
  Dữ liệu monitor tại giường: nhịp tim, huyết áp, SpO₂, nhiệt độ… (cực lớn).

- **d_items.csv.gz**  
  Bảng từ điển: giải thích mã ITEMID trong ICU (thuốc, thiết bị, xét nghiệm tại giường).

- **inputevents.csv.gz**  
  Các dịch truyền, thuốc đưa vào bệnh nhân trong ICU.

- **outputevents.csv.gz**  
  Ghi nhận đầu ra (nước tiểu, dịch dẫn lưu...) trong ICU.

- **procedureevents.csv.gz**  
  Thủ thuật thực hiện trong ICU (đặt ống, lọc máu...).

- **ingredientevents.csv.gz**  
  Chi tiết về thành phần thuốc/dịch được truyền.

- **datetimeevents.csv.gz**  
  Các sự kiện có dấu mốc thời gian đặc biệt (ví dụ thời gian dùng thuốc, can thiệp).

- **caregiver.csv.gz**  
  Thông tin nhân viên y tế liên quan đến bệnh nhân ICU.

---

## 📌 Tóm tắt
- **mimic-iv-note**: chứa ghi chú lâm sàng (discharge summaries, radiology reports).  
- **mimiciv/hosp**: chứa dữ liệu bệnh viện chung (nhập viện, chẩn đoán ICD, lab, thuốc, dịch chuyển).  
- **mimiciv/icu**: chứa dữ liệu chi tiết khi bệnh nhân ở ICU (monitor, thuốc, thủ thuật, nhân viên).  
