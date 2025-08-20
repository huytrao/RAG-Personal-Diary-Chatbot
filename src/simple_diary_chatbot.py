"""
Simple Diary Chatbot (RAG Minimal Core)

Chức năng bắt buộc (giữ thật đơn giản nhưng vẫn là RAG):
1. add    -> Lưu entry vào SQLite + CHUNK + EMBEDDING bắt buộc + lưu vector
2. delete -> Xoá entry (DB + vector theo entry_id)
3. chat   -> similarity search (k), nếu có API key thì generate câu trả lời, không thì trả về context

Embedding LÀ BẮT BUỘC (sản phẩm RAG). Nếu không có GOOGLE_API_KEY sẽ báo lỗi rõ ràng.

Chunking tối giản: cắt theo độ dài cố định (mặc định 800 ký tự) và không overlap để giảm phức tạp.

File này thay thế các pipeline phức tạp trước đây khi bạn chỉ cần RAG CRUD cơ bản.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from textwrap import wrap
import asyncio

# Fix event loop issue for Streamlit
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Dùng lại lớp embedding hiện có (Chroma + Google Embedding)
from Indexingstep.embedding_and_storing import DiaryEmbeddingAndStorage

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_diary")

DB_PATH = os.path.join(os.getcwd(), "diary.db")  # Một file DB duy nhất
CHUNK_SIZE = 800  # Có thể chỉnh nếu cần


def get_conn():
    return sqlite3.connect(DB_PATH)


def ensure_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


@dataclass
class DiaryEntry:
    id: int
    date: str
    content: str
    tags: str
    created_at: str


class SimpleDiaryChatbot:
    """Core RAG tối giản – luôn yêu cầu embedding hoạt động."""

    def __init__(self, api_key: Optional[str] = None, user_id: int = 1, chunk_size: int = CHUNK_SIZE):
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        ensure_db()
        self.user_id = user_id
        self.chunk_size = chunk_size

        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "GOOGLE_API_KEY chưa được thiết lập. Set trong PowerShell: $env:GOOGLE_API_KEY='YOUR_KEY'"
            )

        # Fix event loop for Streamlit
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Khởi tạo embedding + vector store (bắt buộc)
        self.embedding_store = DiaryEmbeddingAndStorage(user_id=user_id, api_key=key)

        # (Tuỳ chọn) LLM để tạo câu trả lời tự nhiên – nếu lỗi vẫn tiếp tục dùng context
        self._model = None
        if genai:
            try:
                genai.configure(api_key=key)
                self._model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                logger.warning(f"Không khởi tạo được LLM (tiếp tục với retrieval-only): {e}")

    # ------------- CRUD -------------
    def _chunk(self, text: str) -> List[str]:
        """Chunk đơn giản theo độ dài cố định, cắt ở khoảng trắng gần nhất nếu có."""
        if len(text) <= self.chunk_size:
            return [text]
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            # Cố gắng lùi về khoảng trắng để tránh cắt từ
            if end < len(text):
                last_space = text.rfind(" ", start, end)
                if last_space != -1 and last_space - start > self.chunk_size * 0.5:
                    end = last_space
            chunks.append(text[start:end].strip())
            start = end
        return [c for c in chunks if c]

    def add_entry(self, date: str, content: str, tags: str = "") -> int:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO diary_entries(date, content, tags) VALUES (?, ?, ?)",
            (date, content, tags),
        )
        entry_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Chunk + embed từng chunk (metadata chung entry)
        chunks = self._chunk(content)
        metadatas = [
            {"entry_id": entry_id, "date": date, "tags": tags, "chunk_index": i, "total_chunks": len(chunks)}
            for i, _ in enumerate(chunks)
        ]
        self.embedding_store.embed_and_store_texts(chunks, metadatas)
        # logger.info(f"Added entry {entry_id} với {len(chunks)} chunk")
        return entry_id

    def delete_entry(self, entry_id: int) -> bool:
        # Xoá vector theo metadata
        try:
            self.embedding_store.delete_documents_by_metadata({"entry_id": entry_id})
        except Exception as e:
            logger.warning(f"Failed to delete vectors for entry {entry_id}: {e}")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        if deleted:
            logger.info(f"Deleted entry {entry_id}")
            return True
        logger.warning(f"Entry {entry_id} not found")
        return False

    def list_entries(self, limit: int = 10) -> List[DiaryEntry]:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, date, content, tags, created_at FROM diary_entries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [DiaryEntry(*r) for r in cur.fetchall()]
        conn.close()
        return rows

    # ------------- Chat -------------
    def chat(self, question: str, k: int = 4) -> Dict[str, Any]:
        """
        Trả về:
            {
              'answer': str,
              'contexts': [ { 'snippet': ..., 'date': ..., 'entry_id': ... } ]
            }
        """
        try:
            results = self.embedding_store.similarity_search(question, k=k)
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            results = []
        contexts = []
        for doc in results:
            contexts.append(
                {
                    "snippet": doc.page_content[:300],
                    "date": doc.metadata.get("date"),
                    "entry_id": doc.metadata.get("entry_id"),
                    "tags": doc.metadata.get("tags"),
                }
            )

        if self._model and contexts:
            context_text = "\n".join(
                [f"[Entry {c['entry_id']} - {c['date']}] {c['snippet']}" for c in contexts]
            )
            prompt = (
                "You are a helpful diary assistant. Use only the context below to answer.\n\n"
                f"CONTEXT:\n{context_text}\n\nQUESTION: {question}\n\nAnswer in the same language as the question."
            )
            try:
                resp = self._model.generate_content(prompt)
                answer = resp.text.strip()
            except Exception as e:
                answer = f"(LLM error, showing raw context) -> {e}\n" + " | ".join(
                    c["snippet"] for c in contexts
                )
        else:
            answer = " | ".join(c["snippet"] for c in contexts) if contexts else "Không tìm thấy nội dung liên quan."

        return {"answer": answer, "contexts": contexts}


def _cli():  # Simple command line interface
    import argparse
    parser = argparse.ArgumentParser(description="Simple Diary Chatbot")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Add a diary entry")
    p_add.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--tags", default="")

    p_del = sub.add_parser("delete", help="Delete an entry by id")
    p_del.add_argument("--id", type=int, required=True)

    p_chat = sub.add_parser("chat", help="Ask a question")
    p_chat.add_argument("--q", required=True, help="Question")
    p_chat.add_argument("--k", type=int, default=4)

    p_list = sub.add_parser("list", help="List recent entries")
    p_list.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    bot = SimpleDiaryChatbot(api_key=os.getenv("GOOGLE_API_KEY"))

    if args.cmd == "add":
        eid = bot.add_entry(args.date, args.content, args.tags)
        print(f"Added entry id={eid}")
    elif args.cmd == "delete":
        ok = bot.delete_entry(args.id)
        print("Deleted" if ok else "Not found")
    elif args.cmd == "chat":
        resp = bot.chat(args.q, k=args.k)
        print("Answer:\n", resp["answer"]) 
        print("\nContexts:")
        for c in resp["contexts"]:
            print(f"- ({c['entry_id']}) {c['date']} :: {c['snippet'][:80]}...")
    elif args.cmd == "list":
        entries = bot.list_entries(limit=args.limit)
        for e in entries:
            print(f"{e.id} | {e.date} | {e.tags} | {e.content[:60]}...")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
