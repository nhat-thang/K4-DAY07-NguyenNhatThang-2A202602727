from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if self._store.get_collection_size() == 0:
            return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."

        results = self._store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."

        context_lines = []
        for index, result in enumerate(results, start=1):
            source = result["metadata"].get("doc_id", result["id"])
            context_lines.append(f"[{index}] (nguồn: {source}) {result['content']}")
        context = "\n".join(context_lines)

        prompt = (
            "Bạn là trợ lý trả lời câu hỏi chỉ dựa trên ngữ cảnh dưới đây. "
            "Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ là không tìm thấy thông tin, "
            "đừng bịa. Khi trả lời, trích dẫn số thứ tự đoạn ngữ cảnh đã dùng, ví dụ [1].\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n"
            "Trả lời:"
        )
        return self._llm_fn(prompt)
