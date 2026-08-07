# Debra – Football Analytics RAG

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)](https://www.langchain.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-VectorDB-blueviolet.svg)](https://www.pinecone.io/)
[![Groq](https://img.shields.io/badge/Groq-LLM-red.svg)](https://groq.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-success.svg)](https://render.com)

**Live Demo:** [https://askdebra.onrender.com/](https://askdebra.onrender.com/)

---

## Overview

Debra is an AI-powered Football Analytics Mentor and Learning Assistant. It bridges the gap between technical data skills and football domain knowledge by delivering clear, educational explanations of football analytics concepts, terminology, tactical ideas, and event data definitions.

The system is designed for data analysts, performance analysts, scouts, coaches, students, and football enthusiasts who wish to understand the analytical aspects of the sport.

Debra explains concepts such as Expected Goals (xG), Expected Assists (xA), pressing metrics, possession value, progressive actions, and other football analytics topics. It contextualises these concepts within match situations, tactical frameworks, and data-driven decision-making processes.

---

## Core Capabilities

| Capability | Description |
| :--- | :--- |
| Conversational Memory | Maintains session context to handle follow-up questions (e.g., "How is it calculated?" after an xG explanation). |
| RAG-based Retrieval | Retrieves relevant knowledge from a curated PDF corpus stored in a Pinecone vector database. |
| History-Aware Retrieval | Rephrases user questions using conversation history to improve retrieval accuracy. |
| Reranking (Optional) | Applies cross-encoder reranking to refine retrieved results; can be disabled for low-memory deployments. |
| Source Attribution | Displays clean, deduplicated sources with page numbers and metadata via a collapsible user interface. |
| Greeting and Small Talk Detection | Skips retrieval for casual interactions (e.g., "Hi", "Who made you?") to reduce token usage and improve user experience. |
| Ignorance Suppression | Hides source attribution when the system indicates that it does not know the answer. |
| Identity and Creator Credit | Responds to identity-related questions with creator information and a GitHub link. |
| Nickname Flexibility | Accepts variations of the assistant name (e.g., "Debby", "Debs") without correction, provided they are not abusive. |
| Educational Mentorship | Adapts explanations to user experience levels (beginner, intermediate, advanced). |
| Rate Limit and Error Handling | Provides user-friendly error messages for API rate limits and connectivity issues. |
| Session Management | Preserves conversation context using Flask session handling. |

---

## RAG Architecture

The system implements a retrieval-augmented generation pipeline with conversational memory.

```mermaid
graph TD
    A[User Question] --> B{Greeting Check}
    B -- Greeting --> C[LLM Only - No Retrieval]
    B -- Football Question --> D[History-Aware Retriever]
    D --> E[Pinecone Vector Search]
    E --> F[Retrieved Documents (k=20)]
    F --> G[Reranker (Optional)]
    G --> H[Top-k Documents (k=3)]
    H --> I[LLM with Context + Chat History]
    I --> J[Answer + Sources]

    K[Session Memory] <--> I
    L[Conversation History] <--> D
