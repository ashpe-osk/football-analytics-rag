from flask import Flask, render_template, request, session as flask_session, jsonify
from dotenv import load_dotenv
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_community.chat_message_histories import ChatMessageHistory
from groq import APIConnectionError, NotFoundError, RateLimitError

from src.helper import (
    download_embeddings,
    rerank_documents,
    format_sources,
    is_greeting_or_smalltalk,
)
from src.prompt import system_prompt

import logging
import os
import re
import time
import uuid


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


# Knowledge base

embeddings = download_embeddings()
index_name = "football-knowledge-base-v2"

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings,
)

base_retriever = docsearch.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 20},
)


# Models

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "default")

LOCAL_ENDPOINT_URL = os.getenv("ENDPOINT_BASE_URL")
LOCAL_ENDPOINT_KEY = os.getenv("ENDPOINT_API_KEY")

MAX_ANSWER_TOKENS = 1500

groq_model = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.2,
    max_tokens=MAX_ANSWER_TOKENS,
)

# Local fallback is optional; runs Groq-only when env vars are missing.
local_model = None
if LOCAL_ENDPOINT_URL and LOCAL_ENDPOINT_KEY:
    local_model = ChatOpenAI(
        model=LOCAL_MODEL,
        base_url=LOCAL_ENDPOINT_URL,
        api_key=LOCAL_ENDPOINT_KEY,
        temperature=0.2,
        max_tokens=MAX_ANSWER_TOKENS,
        timeout=120,
        max_retries=1,
    )
    logging.info("Local fallback model configured.")
else:
    logging.info(
        "ENDPOINT_BASE_URL / ENDPOINT_API_KEY not set. "
        "Running without local model fallback."
    )

if local_model is not None:
    chat_model = groq_model.with_fallbacks(
        [local_model],
        exceptions_to_handle=(
            RateLimitError,
            APIConnectionError,
            NotFoundError,
        ),
    )
else:
    chat_model = groq_model


# Source label shortening

SOURCE_SHORT_NAMES = {
    "Soccer Analytics with Machine Learning - Learning Predictive Modeling Techniques with Sports Data (Haipeng Gao, Ari Joury, Weining Shen etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf": "Soccer Analytics with Machine Learning",
    "opta-event-definitions.pdf": "Opta Event Definitions",
    "Football hackers.pdf": "Football Hackers",
    "The numbers game.pdf": "The Numbers Game",
    "How to Win the Premier League The Sunday Times Bestselling Inside Story of Footballs Data Revolution (Ian Graham) (z-library.sk, 1lib.sk, z-lib.sk) (1).pdf": "How to Win the Premier League",
    "Common Data Format.pdf": "Common Data Format",
    "Data Analytics in Football Positional Data Collection, Modelling and Analysis.pdf": "Data Analytics in Football",
    "Perspectives on data analytics for gaining a competitive advantage in football  computational approaches to tactics.pdf": "Perspectives on Data Analytics in Football",
    "Expected Goals The Story Of How Data Conquered Football And Changed The Game Forever (Rory Smith) (z-library.sk, 1lib.sk, z-lib.sk).pdf": "Expected Goals (Rory Smith)",
    "Expected Possession Value (EPV) Research Paper.pdf": "Expected Possession Value (EPV) Research Paper",
    "fifa-coaching-manual-3.pdf": "FIFA Coaching Manual",
    "Data analytics in the football industry  a survey investigating operational frameworks and practices in professional clubs and national federations fr.pdf": "Data Analytics in the Football Industry",
    "the-fa-handbook-2024-25---feb-update.pdf": "The FA Handbook",
}

_PDF_EXT_RE = re.compile(r"\.pdf$", re.IGNORECASE)
_TRAILING_PARENS_RE = re.compile(
    r"\s*\(\s*(?:\d+|[^()]*lib[^()]*)\s*\)\s*$",
    re.IGNORECASE,
)


def shorten_source(name: str) -> str:
    if not name:
        return "unknown source"

    if name in SOURCE_SHORT_NAMES:
        return SOURCE_SHORT_NAMES[name]

    short = _PDF_EXT_RE.sub("", name).strip()

    while True:
        stripped = _TRAILING_PARENS_RE.sub("", short).strip()
        if stripped == short:
            break
        short = stripped

    if " - " in short:
        head = short.split(" - ", 1)[0].strip()
        if 3 <= len(head) <= 70:
            short = head

    if len(short) > 70:
        short = short[:67].rstrip() + "..."

    return short or "unknown source"


# Answer chain

document_prompt = PromptTemplate.from_template(
    "[Source: {source_short}]\n{page_content}"
)

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    (
        "human",
        "Reference material:\n\n"
        "{context}\n\n"
        "Question: {input}\n\n"
        "Instructions: Answer the question above. The retrieved documents "
        "may describe the concept using different terminology than the "
        "question uses (for example, 'pass map' may appear as 'pass "
        "location heatmap' or 'passing network'; 'xG' may appear as "
        "'expected goals'). If the documents describe the concept, use "
        "them and cite them by the [Source: ...] tag shown on each "
        "document. Only say the information is not in the sources if the "
        "documents are genuinely silent on it."
    ),
])

question_answer_chain = create_stuff_documents_chain(
    chat_model,
    qa_prompt,
    document_prompt=document_prompt,
)


# Sessions

session_histories = {}


def get_session_history(session_id: str):
    if session_id not in session_histories:
        session_histories[session_id] = ChatMessageHistory()
    return session_histories[session_id]


# Helpers

def describe_model(response) -> str:
    metadata = getattr(response, "response_metadata", None) or {}
    name = (
        metadata.get("model_name")
        or metadata.get("model")
        or metadata.get("model_id")
    )
    return str(name or GROQ_MODEL)


def model_details(response) -> dict:
    name = describe_model(response)
    is_local = (
        local_model is not None
        and (name == LOCAL_MODEL or name.lower() == "default")
    )
    return {
        "model": name,
        "model_role": "fallback" if is_local else "primary",
    }


def clean_answer_citations(answer: str) -> str:
    answer = re.sub(r"【[^】]*†L\d+(?:-L\d+)?】", "", answer)
    answer = re.sub(r"【[^】]{0,200}】", "", answer)
    return answer.strip()


_SOURCE_TAG_RE = re.compile(r"\[Source:\s*[^\]]+\]")


def answer_used_sources(answer: str, sources):
    """
    Return the sources string only when the answer actually cites a
    retrieved source. If the answer contains no [Source: ...] tag, the
    model either answered from general knowledge or refused, and the
    sources panel must not be displayed.
    """
    if not sources:
        return None

    if not _SOURCE_TAG_RE.search(answer):
        return None

    return sources


def enrich_documents(documents):
    for doc in documents:
        metadata = dict(doc.metadata or {})
        source = (
            metadata.get("source")
            or metadata.get("title")
            or metadata.get("file_name")
            or "unknown source"
        )
        metadata["source"] = source
        metadata["source_short"] = shorten_source(source)
        doc.metadata = metadata
    return documents


def log_retrieved_documents(query, documents):
    logging.info("RETRIEVAL QUERY: %s", query)
    logging.info("RETRIEVED DOCUMENT COUNT: %d", len(documents))

    debug_documents = []

    for number, document in enumerate(documents, start=1):
        metadata = getattr(document, "metadata", {}) or {}
        content = (document.page_content or "").strip()
        snippet = content[:800].replace("\n", " ")

        source = (
            metadata.get("source")
            or metadata.get("title")
            or metadata.get("file_name")
            or "unknown"
        )

        score = (
            metadata.get("rerank_score")
            or metadata.get("relevance_score")
            or metadata.get("score")
        )

        logging.info(
            "DOCUMENT %d | source=%s | score=%s | snippet=%s",
            number,
            source,
            score,
            snippet,
        )

        debug_documents.append({
            "number": number,
            "source": source,
            "source_short": metadata.get("source_short") or source,
            "score": score,
            "snippet": snippet,
            "metadata": metadata,
        })

    if not documents:
        logging.warning(
            "RETRIEVAL FAILED: Pinecone returned no documents for: %s",
            query,
        )

    return {
        "query": query,
        "document_count": len(documents),
        "documents": debug_documents,
        "reason": (
            "Documents retrieved successfully."
            if documents
            else "No documents were returned by Pinecone."
        ),
    }


def retrieve_and_rerank(message, top_k=6):
    retrieved_documents = base_retriever.invoke(message)
    retrieval_debug = log_retrieved_documents(message, retrieved_documents)

    if not retrieved_documents:
        return [], retrieval_debug

    try:
        top_documents = rerank_documents(
            query=message,
            documents=retrieved_documents,
            top_k=top_k,
        )
    except Exception:
        logging.exception("Reranking failed; using retrieved documents.")
        top_documents = retrieved_documents[:top_k]

    return enrich_documents(top_documents), retrieval_debug


def invoke_with_retry(chain, inputs, retries=2):
    for attempt in range(retries):
        try:
            return chain.invoke(inputs)

        except APIConnectionError:
            if attempt == retries - 1:
                raise

            logging.warning(
                "Model connection failed. Retrying attempt %d/%d.",
                attempt + 1,
                retries,
            )
            time.sleep(2)

    raise RuntimeError("Model request failed.")


def invoke_chat_model(messages):
    try:
        return chat_model.invoke(messages)
    except (RateLimitError, APIConnectionError, NotFoundError):
        if local_model is None:
            logging.warning(
                "Groq unavailable and no local fallback is configured."
            )
            raise
        logging.warning(
            "Groq unavailable or model is not accessible; "
            "invoking the configured local model."
        )
        return local_model.invoke(messages)


def log_context_sent(documents):
    if not documents:
        logging.info("CONTEXT SENT TO MODEL: (no documents)")
        return

    chunks = []
    for doc in documents:
        metadata = doc.metadata or {}
        source = (
            metadata.get("source_short")
            or metadata.get("source", "MISSING")
        )
        preview = (doc.page_content or "")[:300].replace("\n", " ")
        chunks.append(f"[Source: {source}]\n{preview}")

    logging.info(
        "CONTEXT SENT TO MODEL:\n%s", "\n\n---\n\n".join(chunks)
    )


# Routes

@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["POST"])
def chat():
    try:
        message = (request.form.get("msg") or "").strip()

        if not message:
            return jsonify({
                "error": "Please enter a question."
            }), 400

        session_id = flask_session.get("session_id")

        if not session_id:
            session_id = str(uuid.uuid4())
            flask_session["session_id"] = session_id

        history = get_session_history(session_id)
        chat_history = history.messages

        logging.info("USER QUESTION: %s", message)

        # Greetings and small talk — no retrieval.
        if is_greeting_or_smalltalk(message):
            response = invoke_chat_model(
                qa_prompt.format_messages(
                    context="",
                    input=message,
                    chat_history=chat_history,
                )
            )

            answer = clean_answer_citations(response.content)
            model_used = describe_model(response)

            history.add_user_message(message)
            history.add_ai_message(answer)

            logging.info(
                "ANSWER (greeting, %s): %s", model_used, answer
            )

            return jsonify({
                "answer": answer,
                "sources": None,
                **model_details(response),
                "debug": {
                    "reason": "Greeting or small talk. Retrieval skipped."
                },
            })

        # Normal path — retrieve, rerank, answer.
        top_documents, retrieval_debug = retrieve_and_rerank(message)
        log_context_sent(top_documents)

        response = invoke_with_retry(
            question_answer_chain,
            {
                "context": top_documents,
                "input": message,
                "chat_history": chat_history,
            },
        )

        answer = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
        answer = clean_answer_citations(answer)
        model_used = describe_model(response)

        history.add_user_message(message)
        history.add_ai_message(answer)

        logging.info("ANSWER (%s): %s", model_used, answer)

        sources = format_sources(top_documents) if top_documents else None
        sources = answer_used_sources(answer, sources)

        return jsonify({
            "answer": answer,
            "sources": sources,
            **model_details(response),
            "debug": retrieval_debug,
        })

    except RateLimitError:
        logging.exception("Groq rate limit error")
        return jsonify({
            "error": (
                "The main model has reached its rate limit. "
                "Please try again shortly."
            )
        }), 429

    except APIConnectionError:
        logging.exception("Model connection error")
        return jsonify({
            "error": "Could not connect to the answer service."
        }), 503

    except Exception:
        logging.exception("Unexpected application error")
        return jsonify({
            "error": "Sorry, an unexpected error occurred."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=True,
        use_reloader=False,
    )