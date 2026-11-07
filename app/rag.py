import os
import re
import sys
from pathlib import Path
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import (
    GOOGLE_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    RAG_TOP_K,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = REPO_ROOT / "data" / "policies"
CHROMA_DIR = REPO_ROOT / ".chroma"
COLLECTION_NAME = "policies"

def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )

def parse_policy_chunks() -> list[dict[str, Any]]:
    pattern = re.compile(r"^##\s+(\d+\.\d+)\s+(.+)$", re.MULTILINE)
    chunks = []
    for policy_file in sorted(POLICIES_DIR.glob("*.md")):
        doc_name = policy_file.stem
        content = policy_file.read_text(encoding="utf-8")
        matches = list(pattern.finditer(content))
        for i, match in enumerate(matches):
            clause_id = match.group(1)
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            chunks.append({
                "text": body,
                "metadata": {
                    "doc": doc_name,
                    "clause_id": clause_id,
                    "title": title,
                },
            })
    return chunks

def build_index() -> int:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    chunks = parse_policy_chunks()
    documents = [
        Document(page_content=c["text"], metadata=c["metadata"])
        for c in chunks
    ]
    ids = [f"{c['metadata']['doc']}_{c['metadata']['clause_id']}" for c in chunks]

    embedding_model = get_embedding_model()
    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
    )
    vectorstore.add_documents(documents=documents, ids=ids)
    print(f"Indexed {len(documents)} chunks.")
    return len(documents)

def search(query: str, k: int = RAG_TOP_K) -> list[dict[str, Any]]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_model = get_embedding_model()
    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_model,
    )
    docs = vectorstore.similarity_search(query, k=k)
    return [
        {
            "doc": d.metadata.get("doc", ""),
            "clause_id": d.metadata.get("clause_id", ""),
            "title": d.metadata.get("title", ""),
            "text": d.page_content,
        }
        for d in docs
    ]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.rag [build|query <text>]")
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "build":
        count = build_index()
    elif cmd == "query":
        if len(sys.argv) < 3:
            print('Usage: python -m app.rag query "your text"')
            sys.exit(1)
        query_text = " ".join(sys.argv[2:])
        results = search(query_text)
        for r in results:
            print(f"- {r['doc']} [{r['clause_id']}] {r['title']}: {r['text']}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
