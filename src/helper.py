from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_pinecone import PineconeEmbeddings

from typing import List
import hashlib
import os
import re


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
                provider = (
                    category
                    if category.lower() in ["uefa", "fifa", "rsssf"]
                    else "unknown"
                )
                doc.metadata.update({
                    "category": category,
                    "source": source,
                    "page": page,
                    "provider": provider,
                })
            documents.extend(docs)
    return documents


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


def text_split(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function=len,
    )
    return text_splitter.split_documents(extracted_data)


def download_embeddings():
    return PineconeEmbeddings(model="multilingual-e5-large")


# These phrases bypass retrieval.
_GREETINGS = {
    "hi", "hello", "hey", "hey debra", "hi debra", "hello debra",
    "good morning", "good afternoon", "good evening",
    "howdy", "greetings", "yo", "sup",
}

_SMALLTALK = {
    "thanks", "thank you", "thanks debra", "thank you debra",
    "bye", "goodbye", "see you", "see you later", "see ya",
    "ok", "okay", "k", "alright", "all right", "sure", "cool",
    "nice", "got it", "i see", "understood", "makes sense",
    "that makes sense", "fair enough", "no problem",
    "yes", "yeah", "yep", "no", "nope",
    "how are you", "how are you doing", "how's it going",
    "what's up", "what is your name", "who are you",
    "who made you", "who developed you", "who created you",
}

_SMALLTALK_ALL = _GREETINGS | _SMALLTALK


def is_greeting_or_smalltalk(text: str) -> bool:
    """
    Return True if the message is a greeting, acknowledgement, farewell,
    or identity question that should bypass retrieval.

    Matches exact phrases (after trimming trailing punctuation) and
    short prefix variants such as "hello there" or "hey Debra!".
    The prefix check is length-bounded so a long question that happens
    to begin with a greeting word is not misclassified.
    """
    stripped = text.lower().strip().rstrip("!?.,;: ")

    if not stripped:
        return False

    if stripped in _SMALLTALK_ALL:
        return True

    for phrase in _SMALLTALK_ALL:
        if (
            stripped.startswith(phrase + " ")
            and len(stripped) <= len(phrase) + 20
        ):
            return True

    return False


def _content_key(doc: Document) -> str:
    content = (doc.page_content or "").strip()
    normalized = re.sub(r"\s+", " ", content)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def deduplicate_documents(documents: List[Document]) -> List[Document]:
    seen = set()
    unique = []
    for doc in documents:
        key = _content_key(doc)
        if key in seen:
            continue
        seen.add(key)
        unique.append(doc)
    return unique


USE_RERANK = os.getenv("USE_RERANK", "true").lower() == "true"

_reranker = None


def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-2-v2"):
    global _reranker
    if not USE_RERANK:
        return None
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(model_name, device="cpu")
        except ImportError:
            print(
                "sentence-transformers not installed. "
                "Reranking disabled."
            )
            return None
    return _reranker


def _apply_quota(documents, top_k, max_per_source):
    """
    Take up to top_k documents while limiting how many come from the
    same source. Prevents a single large book from monopolizing the
    context window and lets answers cite a more varied set of sources.
    """
    per_source = {}
    selected = []

    for doc in documents:
        source = (doc.metadata or {}).get("source", "unknown")
        count = per_source.get(source, 0)
        if count >= max_per_source:
            continue
        per_source[source] = count + 1
        selected.append(doc)
        if len(selected) >= top_k:
            break

    if len(selected) < top_k:
        for doc in documents:
            if doc in selected:
                continue
            selected.append(doc)
            if len(selected) >= top_k:
                break

    return selected


def rerank_documents(query, documents, top_k=6, max_per_source=2):
    if not documents:
        return []

    unique_docs = deduplicate_documents(documents)
    if not unique_docs:
        return []

    if not USE_RERANK:
        return _apply_quota(unique_docs, top_k, max_per_source)

    reranker = get_reranker()
    if reranker is None:
        return _apply_quota(unique_docs, top_k, max_per_source)

    pairs = [(query, doc.page_content) for doc in unique_docs]
    scores = reranker.predict(pairs)
    scored = sorted(
        zip(unique_docs, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    top = _apply_quota([d for d, _ in scored], top_k, max_per_source)

    for doc in top:
        for ranked_doc, score in scored:
            if ranked_doc is doc:
                metadata = dict(doc.metadata or {})
                metadata["rerank_score"] = float(score)
                doc.metadata = metadata
                break

    return top


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
        lines.append(
            f"[{i}] {clean_name}{page_str} "
            f"(Provider: {provider}, Category: {category})"
        )
    return "\n".join(lines)