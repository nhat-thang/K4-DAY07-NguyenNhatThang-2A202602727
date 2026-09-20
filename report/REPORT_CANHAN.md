# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Nhật Thăng — MSSV 2A202602727
**Nhóm:** Four Bot
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding gần như cùng hướng trong không gian nhiều chiều — tức hai đoạn văn bản mang ý nghĩa/ngữ cảnh gần nhau, dù có thể dùng từ vựng khác nhau hoàn toàn.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người bán không được đăng sản phẩm giả nhãn hiệu."
- Câu B: "Cấm người bán rao bán hàng nhái, hàng giả mạo thương hiệu."
- Tại sao tương đồng: Hai câu dùng từ vựng gần như khác hoàn toàn ("giả nhãn hiệu" vs "hàng nhái, hàng giả mạo thương hiệu") nhưng cùng diễn đạt một quy định — cấm bán hàng giả — nên một embedder có ngữ nghĩa tốt phải xếp cặp này gần nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Giá sản phẩm phải tính theo đơn vị VNĐ."
- Câu B: "Con mèo là loài động vật ăn thịt phổ biến làm thú cưng."
- Tại sao khác: Hai câu không liên quan cả về chủ đề (quy định giá bán vs. động vật) lẫn từ vựng.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo góc giữa hai vector, không bị ảnh hưởng bởi độ dài (magnitude) của vector — mà độ dài vector embedding thường lệch nhau do độ dài văn bản khác nhau chứ không phản ánh khác biệt ngữ nghĩa. Euclidean distance cộng dồn cả chênh lệch độ lớn đó vào, dễ đánh giá sai hai văn bản cùng nghĩa nhưng độ dài khác nhau là "khác nhau".

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Trình bày phép tính: `ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> Đáp án: **23 chunks** — đã kiểm lại bằng `FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)`, kết quả thực tế cũng ra đúng 23.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Overlap=100 → `ceil((10000−100)/(500−100)) = ceil(9900/400) = 25` chunks (kiểm lại bằng code cũng ra 25, tăng thêm 2 chunk so với overlap=50). Muốn overlap lớn hơn vì thông tin nằm ngay ranh giới giữa hai chunk (ví dụ một điều khoản bị cắt đôi) sẽ xuất hiện trọn vẹn trong ít nhất một chunk thay vì bị mất một nửa ở cả hai phía — đánh đổi là tốn thêm chunk (thêm chi phí embedding/lưu trữ).

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex `(?<=[.!?])\s+` với `re.split` — lookbehind giữ nguyên dấu câu ở cuối câu trước thay vì để `re.split` nuốt mất nó (bẫy mà đề bài cảnh báo nếu split bằng `[.!?]\s+`). `\s+` bắt được cả khoảng trắng lẫn xuống dòng nên đồng thời xử lý cả 4 kiểu ranh giới `". "`, `"! "`, `"? "`, `".\n"` chỉ bằng một pattern. Edge case chưa xử lý: chữ viết tắt (`TS.`, `v.v.`) và số thập phân (`3.14`) sẽ bị nhận nhầm thành ranh giới câu và bị cắt sai.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử lần lượt separator theo độ ưu tiên `["\n\n", "\n", ". ", " ", ""]`: tách bằng separator hiện tại, mảnh nào vẫn dài hơn `chunk_size` thì đệ quy xuống với separator nhỏ hơn (`_split`), mảnh nào đã đủ nhỏ thì gom vào danh sách "good_splits" và nối lại bằng `_merge_splits` cho tới sát `chunk_size` trước khi ghép vào kết quả — nếu thiếu bước gom này thì văn bản nhiều dòng ngắn sẽ vỡ thành hàng trăm chunk vụn. Có 3 base case: (1) `len(current_text) <= chunk_size` → trả nguyên văn bản; (2) hết separator để thử → cắt cứng theo `chunk_size`; (3) separator hiện tại là chuỗi rỗng `""` → cũng cắt cứng, vì tách theo `""` chỉ cho từng ký tự một, không có ý nghĩa.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` gọi `_make_record` cho từng `Document` — hàm này copy `metadata` (tránh sửa trực tiếp object của người gọi) và đảm bảo luôn có `metadata['doc_id']` (mặc định bằng `doc.id` nếu người gọi chưa set, nhưng ưu tiên giữ giá trị đã có — quan trọng khi một file bị chunk thành nhiều `Document` với id kiểu `"file#0"`, `doc_id` phải trỏ về file gốc). Record được append vào `self._store` (in-memory, không dùng ChromaDB). `search` gọi chung `_search_records`, tính similarity bằng `_dot` (tích vô hướng) — vì embedding đã chuẩn hoá `||v||=1` nên dot product bằng đúng cosine — rồi sắp xếp giảm dần và cắt lấy `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc **trước**: duyệt `self._store`, chỉ giữ record có toàn bộ cặp key/value trong `metadata_filter` khớp với `record['metadata']`, rồi mới đưa tập đã lọc vào `_search_records`. Lọc trước quan trọng vì nếu lấy top-k rồi mới lọc, có thể mất hết kết quả dù store vẫn còn tài liệu hợp lệ (k slot đã bị tài liệu sai đối tượng chiếm hết). `delete_document` xoá bằng cách rebuild `self._store` chỉ giữ lại các record có `metadata['doc_id'] != doc_id`, trả `True`/`False` dựa vào việc kích thước store có giảm hay không.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: chặn store rỗng → trả thông báo cố định thay vì gọi LLM vô ích; gọi `store.search(question, top_k)` lấy top-k chunk; dựng ngữ cảnh bằng cách đánh số từng chunk `[1] [2] [3]` kèm nguồn (`metadata['doc_id']`) rồi ghép vào prompt. Prompt yêu cầu model chỉ dùng thông tin trong ngữ cảnh, nói rõ nếu không tìm thấy (chống bịa), và trích dẫn số thứ tự đoạn đã dùng khi trả lời — để câu trả lời truy vết được về đúng chunk/file (Source Traceability trong `docs/EVALUATION.md`).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.06s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Người bán không được đăng sản phẩm giả nhãn hiệu." | "Cấm người bán rao bán hàng nhái, hàng giả mạo thương hiệu." (paraphrase, khác từ vựng) | cao | -0.1501 | Sai |
| 2 | "Hình ảnh sản phẩm phải là ảnh chụp thật, rõ nét." | "Tên sản phẩm phải viết đúng chính tả, rõ nghĩa." (cùng chủ đề lớn, khác nội dung cụ thể) | trung bình/thấp | -0.1992 | Đúng hướng |
| 3 | "Chính sách này áp dụng cho tất cả người bán trên Shopee." | (câu giống hệt câu A) | cao | 1.0000 | Đúng |
| 4 | "Giá sản phẩm phải tính theo đơn vị VNĐ." | "Con mèo là loài động vật ăn thịt phổ biến làm thú cưng." (không liên quan) | thấp | -0.1723 | Đúng |
| 5 | "Người bán được phép đăng bán hàng đã qua sử dụng." | "Người bán không được phép đăng bán hàng đã qua sử dụng." (chỉ khác từ "không" — ý nghĩa TRÁI NGƯỢC nhưng câu chữ gần như giống hệt) | cao (vì câu chữ rất giống) nhưng thực chất phải THẤP vì nghĩa đối lập | 0.0466 | Mơ hồ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là cặp 1: hai câu diễn đạt cùng một ý ("cấm bán hàng giả") bằng từ vựng gần như hoàn toàn khác nhau, nhưng điểm thực tế lại âm (-0.15) như thể không liên quan — ngược hẳn với dự đoán "cao" dựa trên nghĩa. Lý do là môi trường lab đang chạy `MockEmbedder`, vector sinh ra từ hash MD5 của chuỗi ký tự chứ không mã hoá ngữ nghĩa thật, nên hai câu chỉ giống nhau khi *chuỗi ký tự giống hệt nhau* (cặp 3 ra đúng 1.0) — còn lại điểm số gần như ngẫu nhiên bất kể ý nghĩa. Điều này minh hoạ đúng cảnh báo trong `day7-lab-data-foundations.md`: benchmark chạy bằng mock sẽ cho số liệu nhiễu, phải bật embedder thật (Phụ lục B) mới đo được chất lượng retrieval một cách có ý nghĩa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> **Đã chạy thật bằng `bench.py`** trên corpus đầy đủ 8 tài liệu (`data/chinh_sach_thuong_mai_dien_tu/`), chiến lược `SentenceChunker(max_sentences_per_chunk=3)` (410 chunk), embedder thật **Gemini `gemini-embedding-001`** (không dùng Mock — đã bật `EMBEDDING_PROVIDER=gemini` trong `.env`). Output đầy đủ nằm trong `ket_qua_benchmark.txt`.

> `KnowledgeBaseAgent` dùng `demo_llm` (mock, echo lại prompt) vì không có API key cho model sinh văn bản — chỉ có key Gemini cho **embedding**. Vì vậy cột "Agent" dưới đây không phải câu trả lời tự nhiên thật, mà tôi tự đánh giá **grounding**: đáp án đúng có nằm trong ngữ cảnh (top-3) truyền cho agent hay không — đúng cách chấm 2 mức mà lab yêu cầu (không chỉ nhìn "có liên quan" mà kiểm tra chuỗi đáp án cụ thể có thật trong ngữ cảnh).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Score top-1 | Đáp án đúng có trong top-3? | Điểm (/2, theo `docs/SCORING.md`) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn gửi yêu cầu cho hàng thường và thực phẩm? | (doc_id=77251) "...15 (mười lăm) ngày... Riêng đối với...thực phẩm tươi sống và đông lạnh...trong vòng 24 giờ..." | 0.8315 | Có, **ngay ở top-1** — 1 chunk duy nhất chứa cả 2 mốc (15 ngày / 24 giờ) | **2/2** |
| 2 | Các bước gửi yêu cầu trực tiếp từ trang đơn hàng? | (doc_id=79233) "...Cách 1: Gửi yêu cầu trực tiếp tại trang đơn hàng. Bước 1: Mở ứng dụng Shopee... Bước 2: Tại đơn hàng..." | 0.9113 | Có, đúng nguồn hướng dẫn, top-1 có Bước 1-2 | **2/2** |
| 3 | Video mở kiện hàng cần tiêu chuẩn kỹ thuật/dung lượng nào? | (doc_id=79467) "Góc quay rõ ràng...Quay 6 mặt của kiện hàng để chứng minh tình trạng..." | 0.7998 | **Một phần** — top-1..3 đều đúng chủ đề, có tiêu chí "quay 6 mặt", nhưng **thiếu** thông số dung lượng (ảnh ≤5MB, video ≤100MB/1 phút — nằm ở đoạn "Quy định về bằng chứng" cùng file nhưng bị `SentenceChunker` tách sang chunk khác, không lọt top-3) | **1/2** |
| 4 | Người mua có phải trả phí vận chuyển hoàn hàng? | (doc_id=77251) "TRÁCH NHIỆM VỀ CHI PHÍ HOÀN TRẢ SẢN PHẨM CỦA NGƯỜI MUA... không phải thanh toán bất cứ chi phí vận chuyển nào... Tự sắp xếp: cần thanh toán trước..." | 0.8344 | Có, đầy đủ ngay ở top-1 (cả 2 trường hợp: miễn phí / tự sắp xếp phải trả trước) | **2/2** |
| 5 | Thời gian **xử lý** yêu cầu Trả hàng/Hoàn tiền là bao lâu? *(`metadata_filter={"audience":"buyer"}`)* | (doc_id=188931) "...15 ngày... 20 ngày kể từ lúc đơn hàng được cập nhật trạng thái 'Lấy hàng thành công'..." | 0.8033 | **Đáp án đúng không ở top-1** — top-1 (188931) thực ra trả lời nhầm sang "thời hạn *gửi* yêu cầu" (15/20 ngày), còn đáp án đúng "xử lý trong khoảng 3-5 ngày làm việc" nằm ở **top-2** (doc_id=79233) | **1/2** |

**Tổng điểm truy xuất theo `docs/SCORING.md`: 2+2+1+2+1 = 8/10**

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5/5** — nhưng chỉ **3/5** có đáp án đúng nằm ngay ở top-1; đây chính là khoảng cách giữa "chấm ngây thơ" (chỉ xét top-3 có liên quan) và "chấm thật" mà `day7-lab-data-foundations.md` mục 7 cảnh báo — nếu chấm theo kiểu ngây thơ sẽ ra 5/5 (thổi phồng), chấm đúng theo nội dung ra 8/10.

**A/B với metadata filter (câu 5):** chưa chạy `search_with_filter(metadata_filter=None)` để so sánh trực tiếp trong lần này (việc này thuộc REPORT_NHOM mục 3, do R2/nhóm tổng hợp), nhưng xác nhận được filter *có tác dụng lọc thật*: cả 2 tài liệu `audience: seller` (`77246`, `77247`) không xuất hiện trong top-3 nào của câu 5 khi bật filter.

**Phân tích lỗi (câu 3 và câu 5):** đây là ví dụ thật cho hiện tượng "chunk đúng chủ đề nhưng không chứa đáp án cụ thể thắng chunk có đáp án" — cosine đo độ giống *chủ đề*, không đo *mật độ thông tin trả lời được*. Câu 5 đặc biệt đáng chú ý: hai chunk (thời hạn *gửi* yêu cầu vs. thời gian *xử lý* yêu cầu) dùng chung rất nhiều từ vựng ("Trả hàng/Hoàn tiền", "ngày") nên điểm cosine gần nhau (0.8033 vs 0.8008), khiến chunk sai chủ đề con lại xếp trên chunk đúng. Đề xuất sửa: dùng `RecursiveChunker` hoặc chunker theo heading để giữ tiêu đề mục ("1.2. Thời gian tối đa để gửi yêu cầu" vs "Thời gian xử lý") gắn liền với nội dung, giúp phân biệt rõ hai mục dễ nhầm này hơn `SentenceChunker` (vốn cắt theo câu, không giữ ngữ cảnh tiêu đề mục).

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *(điền sau buổi demo — CP6/CP7, chưa diễn ra)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 (42/42 test pass) |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 — chạy thật bằng Gemini embedder; 5/5 câu có chunk liên quan trong top-3, nhưng chỉ 3/5 đúng đáp án ngay ở top-1 (chấm theo `docs/SCORING.md`: 2+2+1+2+1) |
| **Tổng phần cá nhân** | **58 / 60** |
