# Debra – Football Analytics RAG

An AI-powered football analytics mentor that explains football data concepts, terminology, and tactics through a retrieval-augmented chat interface.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)](https://www.langchain.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-VectorDB-blueviolet.svg)](https://www.pinecone.io/)
[![Groq](https://img.shields.io/badge/Groq-LLM-red.svg)](https://groq.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-success.svg)](https://render.com)

**Live Demo:** [askdebra.onrender.com](https://askdebra.onrender.com/)

---

## Overview

Debra bridges the gap between technical data skills and football domain knowledge, delivering clear, educational explanations of football analytics concepts such as Expected Goals (`xG`), Expected Assists (`xA`), pressing metrics, and possession value, tailored to the user's experience level.

---

## Key Features

| Feature | Description |
|---|---|
| RAG-based Retrieval | Retrieves relevant knowledge from a curated corpus in a Pinecone vector database. |
| Conversational Memory | Maintains session context to support follow-up questions. |
| History-Aware Retrieval | Rephrases queries using prior conversation history for better retrieval. |
| Optional Reranking | Applies cross-encoder reranking to refine results; can be disabled. |
| Source Attribution | Displays deduplicated sources with page numbers and metadata. |
| Educational/Adaptive Responses | Adjusts explanation depth to the user's experience level. |
| Greeting and Small-Talk Detection | Bypasses retrieval for casual interactions to save tokens. |

---

## Architecture

Debra follows a retrieval-augmented generation pipeline: incoming questions are checked for greetings, then reformulated using chat history, retrieved from Pinecone, optionally reranked, and passed to the LLM along with conversation history to produce a sourced answer.

```mermaid
graph TD
    A[User Question] --> B{Greeting Check}
    B -- Greeting --> C[LLM Only - No Retrieval]
    B -- Football Question --> D[History-Aware Retriever]
    D --> E[Pinecone Vector Search]
    E --> F["Retrieved Documents (k=20)"]
    F --> G[Reranker - Optional]
    G --> H["Top-k Documents (k=3)"]
    H --> I[LLM with Context + Chat History]
    I --> J[Answer + Sources]

    K[Session Memory] <--> I
    L[Conversation History] <--> D
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Flask |
| Orchestration | LangChain |
| Vector Database | Pinecone |
| Language Model | Groq |
| Runtime | Python 3.10+ |
| Deployment | Render |

---

## Deployment

Debra is deployed on Render.

**Live Demo:** [askdebra.onrender.com](https://askdebra.onrender.com/)

---

## Author

**Oseko Ashpe**
GitHub: [github.com/ashpe-osk](https://github.com/ashpe-osk)
LinkedIn: [linkedin.com/in/ashpe-ayubu](http://linkedin.com/in/ashpe-ayubu)
