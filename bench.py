"""Benchmark tool for Thang (Thanh vien 4) - SentenceChunker strategy.

1. Doc tung file .md, tach frontmatter thanh metadata va phan than thanh content.
2. Chunk phan than bang SentenceChunker, moi chunk thanh mot Document.
3. Nap vao EmbeddingStore, chay 5 query qua search_with_filter().
4. In top-3 kem score va doc_id de doi chieu voi gold answer.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from dotenv import load_dotenv

from src.chunking import SentenceChunker
from src.embeddings import GeminiEmbedder
from src.models import Document
from src.store import EmbeddingStore

def demo_llm(prompt: str) -> str:
    """Cung mock LLM nhu main.py dung, vi lab khong bat buoc API key cho phan sinh cau tra loi."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def build_prompt(question: str, results: list[dict]) -> str:
    """Sao chep dung logic dung prompt cua KnowledgeBaseAgent.answer, de dung duoc voi
    ket qua da qua search_with_filter (agent.answer() mac dinh khong ho tro filter)."""
    context_lines = [
        f"[{i}] (nguồn: {r['metadata'].get('doc_id')}) {r['content']}"
        for i, r in enumerate(results, start=1)
    ]
    context = "\n".join(context_lines)
    return (
        "Bạn là trợ lý trả lời câu hỏi chỉ dựa trên ngữ cảnh dưới đây. "
        "Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ là không tìm thấy thông tin, "
        "đừng bịa. Khi trả lời, trích dẫn số thứ tự đoạn ngữ cảnh đã dùng, ví dụ [1].\n\n"
        f"Ngữ cảnh:\n{context}\n\n"
        f"Câu hỏi: {question}\n"
        "Trả lời:"
    )

CORPUS_DIR = Path("data/chinh_sach_thuong_mai_dien_tu")
CACHE_PATH = Path(".embedding_cache.json")

QUERIES = [
    {
        "question": "Người mua có thời hạn bao nhiêu ngày để gửi yêu cầu Trả hàng/Hoàn tiền đối với hàng thông thường và thực phẩm?",
        "filter": None,
    },
    {
        "question": "Các bước gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp từ trang đơn hàng trên ứng dụng Shopee?",
        "filter": None,
    },
    {
        "question": "Video mở kiện hàng của Người mua cần đáp ứng tiêu chuẩn kỹ thuật và dung lượng nào?",
        "filter": None,
    },
    {
        "question": "Người mua có phải trả phí vận chuyển khi gửi hàng hoàn trả về cho Người bán không?",
        "filter": None,
    },
    {
        "question": "Thời gian xử lý yêu cầu Trả hàng / Hoàn tiền là bao lâu?",
        "filter": {"audience": "buyer"},
    },
]

FRONTMATTER_LINE = re.compile(r"^(\w+):\s*(.*)$", re.M)


class CachedEmbedder:
    """Wrap an embedder with an on-disk cache keyed by content hash.

    Gemini's free tier has request quotas, and re-running the same 400+
    chunks on every bench.py invocation would burn through them for no
    reason -- the embedding of unchanged text never changes.
    """

    def __init__(self, embedder, cache_path: Path) -> None:
        self._embedder = embedder
        self._cache_path = cache_path
        self._backend_name = embedder._backend_name
        self._cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def __call__(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self._cache:
            return self._cache[key]
        last_error = None
        for attempt in range(5):
            try:
                vector = self._embedder(text)
                break
            except Exception as error:  # rate limit / transient network errors
                last_error = error
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"Embedding failed after retries: {last_error}")
        self._cache[key] = vector
        return vector

    def save(self) -> None:
        self._cache_path.write_text(json.dumps(self._cache), encoding="utf-8")


def load_documents(chunker) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        _, frontmatter, body = text.split("---", 2)
        metadata = dict(FRONTMATTER_LINE.findall(frontmatter))
        metadata["doc_id"] = path.stem

        chunks = chunker.chunk(body.strip())
        for index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata=dict(metadata),
                )
            )
    return documents


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"), override=False)
    print("Dang khoi tao GeminiEmbedder (gemini-embedding-001)...")
    embedder = CachedEmbedder(GeminiEmbedder(), CACHE_PATH)
    print(f"Backend: {embedder._backend_name}\n")

    chunker = SentenceChunker(max_sentences_per_chunk=3)
    documents = load_documents(chunker)

    store = EmbeddingStore(collection_name="bench_thang", embedding_fn=embedder)
    store.add_documents(documents)
    embedder.save()
    n_files = len(list(CORPUS_DIR.glob("*.md")))
    print(f"Da nap {store.get_collection_size()} chunk tu {n_files} file, "
          f"chien luoc SentenceChunker(max_sentences_per_chunk=3)\n")

    for i, item in enumerate(QUERIES, start=1):
        question = item["question"]
        metadata_filter = item["filter"]
        print(f"=== Cau {i}: {question}")
        if metadata_filter:
            print(f"    (filter: {metadata_filter})")
        results = store.search_with_filter(question, top_k=3, metadata_filter=metadata_filter)
        for rank, r in enumerate(results, start=1):
            preview = r["content"][:200].replace("\n", " ")
            print(f"    top-{rank}: score={r['score']:.4f} doc_id={r['metadata'].get('doc_id')}")
            print(f"             {preview}")
        answer = demo_llm(build_prompt(question, results)) if results else "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
        print(f"    Agent: {answer}")
        print()

    embedder.save()


if __name__ == "__main__":
    main()
