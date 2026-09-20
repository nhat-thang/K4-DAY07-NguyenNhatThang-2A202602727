# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Four Bot
**Thành viên:** Nguyễn Nhật Thăng (MSSV 2A202602727) — Thành viên 4; 3 thành viên còn lại *(chưa có tên đầy đủ trong tài liệu tôi có, sẽ bổ sung khi nhóm chốt)*
**Ngày:** 2026-09-20 *(đang cập nhật — báo cáo này mới điền phần có dữ liệu thật, xem ghi chú "chưa hoàn thành" trong từng mục)*

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách quy định người bán trên sàn thương mại điện tử Shopee (bắt buộc của lớp L3B — xem `K4_VARIANT.md`)

**Tại sao nhóm chọn chủ đề này?**
> *(để nhóm điền — tôi không phải người chốt chủ đề, không tự suy diễn lý do thay nhóm)*

### Danh sách tài liệu (Data Inventory)

> Chỉ điền 2 dòng tôi đã crawl thật (thành viên 4, `article/77246` và `article/77247`). 3–8 dòng còn lại thuộc phần crawl của 3 thành viên khác — để trống, chờ nhóm gộp `data/chinh_sach_thuong_mai_dien_tu/` đầy đủ rồi cập nhật bảng này.

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | seller-listing-requirements | https://help.shopee.vn/portal/4/article/77246 | 2026-09-20 / 14/8/2024 | 21.315 | doc_id, title, source_url, retrieved_at, document_version, audience=seller, category=listing-requirements-policy, language=vi |
| 2 | seller-prohibited-items-policy | https://help.shopee.vn/portal/4/article/77247 | 2026-09-20 / 28/4/2025 | 12.657 | doc_id, title, source_url, retrieved_at, document_version, audience=seller, category=prohibited-items-policy, language=vi |
| 3 | *(chờ thành viên khác)* | | | | |
| 4 | *(chờ thành viên khác)* | | | | |
| 5 | *(chờ thành viên khác)* | | | | |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] 2 tài liệu của tôi: nguồn công khai (`help.shopee.vn`, `robots.txt` cho phép crawl), không chứa dữ liệu cá nhân/đăng nhập/nội bộ. *(chưa kiểm tra được cho toàn bộ corpus vì chưa gộp đủ file từ nhóm)*
- [x] 2 tài liệu của tôi đều có đủ `source_url`, `retrieved_at`, `document_version` trong metadata (đã xác nhận bằng script checklist CP2). *(chưa xác nhận cho toàn corpus)*

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string (buyer/seller/both) | `seller` | Bắt buộc của L3B — lọc câu hỏi theo đối tượng hỏi (buyer hỏi thì không lẫn tài liệu seller và ngược lại) |
| `category` | string | `prohibited-items-policy`, `listing-requirements-policy` | Phân biệt tài liệu theo loại quy định cụ thể, tránh nhầm giữa các chính sách khác chủ đề nhưng cùng audience |
| `document_version` | string (ngày hiệu lực hoặc `not-stated`) | `28/4/2025` | Biết tài liệu còn hiệu lực hay đã lỗi thời khi có nhiều phiên bản chính sách |
| `language` | string | `vi` | Lọc theo ngôn ngữ nếu corpus sau này có thêm tài liệu tiếng Anh

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

> Đã chạy thật trên 2 tài liệu tôi crawl, với `chunk_size=500`, đã bỏ frontmatter trước khi so sánh.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| seller-listing-requirements (21.315 ký tự) | FixedSizeChunker (`fixed_size`) | 48 | 493.0 | Không — cắt cứng theo ký tự, có thể chia đôi một mục quy định giữa chừng |
| seller-listing-requirements | SentenceChunker (`by_sentences`) | 78 | 270.5 | Giữ trọn câu, nhưng một mục nhiều câu bị tách thành nhiều chunk rời, mất tiêu đề mục |
| seller-listing-requirements | RecursiveChunker (`recursive`) | 52 | 408.0 | Tốt hơn — ưu tiên cắt theo đoạn (`\n\n`) trước nên giữ được nhiều ngữ cảnh mục hơn |
| seller-prohibited-items-policy (12.657 ký tự) | FixedSizeChunker (`fixed_size`) | 29 | 484.7 | Không |
| seller-prohibited-items-policy | SentenceChunker (`by_sentences`) | 55 | 227.7 | Giữ trọn câu, nhưng chunk khá ngắn vì văn bản có nhiều câu ngắn dạng liệt kê (4.1, 4.2...) |
| seller-prohibited-items-policy | RecursiveChunker (`recursive`) | 30 | 420.0 | Tốt hơn — giữ nguyên khối liệt kê nếu vừa `chunk_size` |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

> Phân công đã thống nhất trong nhóm: Thành viên 1 = chunker theo heading/section (bắt buộc L3B), Thành viên 2 = RecursiveChunker, Thành viên 3 = FixedSizeChunker tối ưu overlap, Thành viên 4 (tôi) = chunker tùy chỉnh Q&A/Bullet hoặc SentenceChunker. Chỉ khối của tôi (Thành viên 4) đã thực sự chạy và có kết quả; khối 1–3 để tên/mô tả trống vì tôi không tự ý viết thay kết quả người khác chưa làm.

**Thành viên 1 — [Tên — chưa có]**
- **Loại chiến lược:** Chunker theo Heading/Section (bắt buộc của L3B)
- **Mô tả & lý do chọn cho chủ đề này:** *(chờ thành viên 1 điền — chưa chạy)*

**Thành viên 2 — [Tên — chưa có]**
- **Loại chiến lược:** RecursiveChunker
- **Mô tả & lý do chọn:** *(chờ thành viên 2 điền — chưa chạy)*

**Thành viên 3 — [Tên — chưa có]**
- **Loại chiến lược:** FixedSizeChunker (tối ưu overlap)
- **Mô tả & lý do chọn:** *(chờ thành viên 3 điền — chưa chạy)*

**Thành viên 4 — Nguyễn Nhật Thăng (2A202602727)**
- **Loại chiến lược:** `SentenceChunker`
- **Mô tả & lý do chọn cho chủ đề này:** Ban đầu cân nhắc chunker tùy chỉnh theo Q&A/Bullet points, nhưng 2 tài liệu tôi thu thập (quy định đăng bán, chính sách cấm/hạn chế sản phẩm) là văn bản điều khoản dạng mục lớn (`1.`, `4.1.`, `4.2.`...), không phải cấu trúc hỏi-đáp — nên `SentenceChunker` phù hợp hơn để giữ trọn từng câu quy định thay vì cắt cứng theo ký tự như `FixedSizeChunker`. Baseline cho thấy `SentenceChunker` cho nhiều chunk hơn (78 và 55) và chunk ngắn hơn hẳn (avg ~228–271 ký tự) so với `recursive`/`fixed_size` — hợp với việc mỗi câu quy định thường đã là một đơn vị ngữ nghĩa độc lập trong văn bản này.

### So Sánh Giữa Các Thành Viên

> **Chưa thực hiện được** — cần chạy `bench.py` với đủ 5 câu hỏi benchmark của nhóm trên corpus đầy đủ (5–10 tài liệu), nhưng nhóm chưa gộp xong corpus (mới có 2/8 tài liệu của tôi) và chưa chốt 5 câu hỏi (thuộc CP5). Sẽ điền bảng dưới ngay sau khi có đủ hai điều kiện này.

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| | | | | |
| | | | | |
| | | | | |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *(chưa thể kết luận — cần chạy benchmark thật trước, không suy đoán)*

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

> **Chưa thực hiện được** — đây là việc của R2 (Benchmark) chủ trì cùng cả nhóm chốt (CP5), tôi không tự đặt câu hỏi/gold answer thay nhóm vì phải khớp với corpus đầy đủ (bao gồm cả tài liệu `audience: buyer` mà nhóm cần bổ sung — hiện 2 tài liệu tôi có đều là `audience: seller`).

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *(chưa chạy được — cần tài liệu `audience: buyer` để A/B test filter có ý nghĩa, xem ghi chú mục "Câu hỏi đánh giá" ở trên)*

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *(chưa demo — chờ CP6/CP7)*

**Bài học rút ra khi so sánh trong nhóm:**
> *(chưa so sánh được vì chưa chạy benchmark chung — riêng phần của tôi: baseline cho thấy `SentenceChunker` và `RecursiveChunker` cho số chunk và độ dài rất khác nhau trên cùng văn bản điều khoản — 78 vs 52 chunk trên cùng 1 tài liệu — nên khác biệt chiến lược là có thật ngay ở bước chunk, trước khi tới bước retrieval)*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *(chưa kết luận được — nhưng một điểm tôi thấy rõ từ phần dữ liệu của mình: nhóm cần crawl thêm tài liệu `audience: buyer` sớm hơn, vì K4_VARIANT.md yêu cầu ít nhất 1 câu benchmark cần metadata_filter mà hiện corpus toàn `seller`)*

---

## Tự Đánh Giá (Phần Nhóm)

> Tự đánh giá dưới đây chỉ phản ánh phần việc tôi (Thành viên 4) đã hoàn thành và kiểm chứng được; không đại diện cho điểm chung cuộc của nhóm — cần cả nhóm gộp dữ liệu và chạy benchmark chung mới tổng kết được.

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | phần của tôi: 2/8 tài liệu đã crawl + làm sạch + đủ metadata (CP2 pass); toàn nhóm: chưa đủ 5–10 file, chưa đa dạng `audience` — **/ 10 để nhóm chấm sau khi gộp** |
| Thiết kế chiến lược (Strategy Design) | phần của tôi: đã chọn `SentenceChunker` + chạy baseline thật; toàn nhóm: chưa gộp kết quả 4 người — **/ 15 để nhóm chấm sau** |
| Chất lượng truy xuất (Retrieval Quality) | chưa chạy được (chưa có 5 câu benchmark + corpus đầy đủ) — **0 / 10 tạm thời** |
| Thuyết trình (Demo) | chưa demo — **0 / 5 tạm thời** |
| **Tổng phần nhóm (hiện tại)** | **Chưa tổng kết được — còn thiếu dữ liệu từ 3 thành viên, 5 câu hỏi benchmark, và buổi demo** |
