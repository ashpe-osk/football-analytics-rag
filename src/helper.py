from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_pinecone import PineconeEmbeddings

from typing import List
import os
import re
import numpy as np

# --------------------------------------------------
# Load PDF files with category metadata + page numbers
# --------------------------------------------------

def load_pdf_file(data):
    documents = []
    for category in os.listdir(data):
        category_path = os.path.join(data, category)
        if os.path.isdir(category_path):
            loader = DirectoryLoader(
                category_path,
                glob="*.pdf",
                loader_cls=PyPDFLoader
            )
            docs = loader.load()
            for doc in docs:
                page = doc.metadata.get("page", 0)
                source = os.path.basename(doc.metadata.get("source", ""))
                provider = category if category.lower() in ["uefa", "fifa", "rsssf"] else "unknown"
                doc.metadata.update({
                    "category": category,
                    "source": source,
                    "page": page,
                    "provider": provider,
                })
            documents.extend(docs)
    return documents

# --------------------------------------------------
# Filter document metadata (keep essential fields)
# --------------------------------------------------

def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    minimal_docs = []
    for doc in docs:
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "source": doc.metadata.get("source"),
                    "category": doc.metadata.get("category"),
                    "page": doc.metadata.get("page", 0),
                    "provider": doc.metadata.get("provider", "unknown"),
                }
            )
        )
    return minimal_docs

# --------------------------------------------------
# Split documents into chunks – reduce size to save tokens
# --------------------------------------------------

def text_split(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,          # reduced from 800
        chunk_overlap=100,       # reduced overlap
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len,
    )
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks

# --------------------------------------------------
# Embeddings
# --------------------------------------------------

def download_embeddings():
    return PineconeEmbeddings(model="multilingual-e5-large")

# --------------------------------------------------
# Detect greetings and small talk
# --------------------------------------------------

def is_greeting_or_smalltalk(text: str) -> bool:
    text_lower = text.lower().strip()
    greetings = [
        "hi", "hello", "hey", "good morning", "good afternoon",
        "good evening", "howdy", "greetings", "yo", "sup"
    ]
    others = [
        "thanks", "thank you", "bye", "goodbye", "see you",
        "how are you", "what's up", "what is your name",
        "who are you", "who made you", "who developed you"
    ]
    for g in greetings:
        if text_lower == g or text_lower.startswith(g + " ") or text_lower.startswith(g + "!"):
            return True
    for o in others:
        if text_lower == o or text_lower.startswith(o + " ") or text_lower.startswith(o + "!"):
            return True
    return False

# --------------------------------------------------
# Deduplicate documents
# --------------------------------------------------

def deduplicate_documents(documents: List[Document]) -> List[Document]:
    seen = set()
    unique = []
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", 0)
        key = (source, page)
        if key not in seen:
            seen.add(key)
            unique.append(doc)
    return unique

# --------------------------------------------------
# Reranker – OPTIONAL (conditional import & environment flag)
# --------------------------------------------------

# Read environment variable: set USE_RERANK=false on Render to save memory
USE_RERANK = os.getenv("USE_RERANK", "true").lower() == "true"

_reranker = None

def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"):
    """
    Lazy-loads the cross-encoder only if USE_RERANK is True.
    If sentence_transformers is not installed, returns None.
    """
    global _reranker
    if not USE_RERANK:
        return None
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(model_name, device="cpu")
        except ImportError:
            print("⚠️ sentence-transformers not installed. Reranking disabled.")
            return None
    return _reranker

def rerank_documents(query: str, documents: List[Document], top_k: int = 3) -> List[Document]:
    """
    Rerank documents using a cross-encoder. Falls back to simple top‑k if reranking is disabled or not available.
    """
    if not documents:
        return []
    if not USE_RERANK:
        # No rerank – just return the first top_k (deduplicated first)
        unique_docs = deduplicate_documents(documents)
        return unique_docs[:top_k]
    reranker = get_reranker()
    if reranker is None:
        # If reranker couldn't be loaded, fall back
        unique_docs = deduplicate_documents(documents)
        return unique_docs[:top_k]
    # Actual reranking
    unique_docs = deduplicate_documents(documents)
    if not unique_docs:
        return []
    pairs = [(query, doc.page_content) for doc in unique_docs]
    scores = reranker.predict(pairs)
    scored = sorted(zip(unique_docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored[:top_k]]

# --------------------------------------------------
# Clean source filenames
# --------------------------------------------------

def clean_source_name(filename: str) -> str:
    if not filename:
        return "Unknown source"
    cleaned = re.sub(r'\(z-library\.[^)]*\)', '', filename)
    cleaned = re.sub(r'\([^)]*\.sk\)', '', cleaned)
    cleaned = re.sub(r'\([^)]*lib\.[^)]*\)', '', cleaned)
    cleaned = re.sub(r'\.pdf$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > 80:
        cleaned = cleaned[:77] + "..."
    return cleaned

# --------------------------------------------------
# Format sources for prompt
# --------------------------------------------------

def format_sources(documents: List[Document]) -> str:
    if not documents:
        return "No source metadata available."
    unique_docs = deduplicate_documents(documents)
    lines = []
    for i, doc in enumerate(unique_docs, 1):
        meta = doc.metadata
        raw_source = meta.get("source", "Unknown")
        clean_name = clean_source_name(raw_source)
        provider = meta.get("provider", "Unknown")
        category = meta.get("category", "General")
        page = meta.get("page", "")
        page_str = f", Page {page}" if page else ""
        lines.append(f"[{i}] {clean_name}{page_str} (Provider: {provider}, Category: {category})")
    return "\n".join(lines)