# Football Analytics RAG

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C)
![Chroma](https://img.shields.io/badge/VectorStore-Chroma-005571)
![License](https://img.shields.io/badge/License-MIT-green)

An AI-powered football learning assistant designed to help data analysts, data scientists, and developers with little or no football background understand football analytics concepts, terminology, and match events through Retrieval-Augmented Generation (RAG).

Football Analytics RAG bridges the gap between technical data skills and football knowledge by providing contextual explanations of football concepts such as expected goals (xG), progressive passes, PPDA, tactical principles, player roles, and event definitions used across football data providers.

---

## Overview

Football Analytics RAG is a Streamlit application that acts as an interactive tutor for football analytics.

The assistant retrieves relevant information from a curated football knowledge base and uses a large language model to generate accurate, context-aware explanations. Users can ask questions about football terminology, analytics metrics, tactical concepts, and match events while receiving responses tailored to their knowledge level.

The project is designed for:

- Data analysts entering the football analytics field.
- Developers and data scientists who want to apply their technical skills to football.
- Football enthusiasts who want to understand the analytical side of the game.

The goal is to reduce the barrier to entry into football analytics by making complex football concepts easier to understand.

---

# Motivation

Football analytics has grown rapidly, but entering the field requires understanding both data and football.

Many analysts have strong technical backgrounds but struggle with football-specific concepts, while football enthusiasts often understand the game but lack familiarity with analytical terminology.

Concepts such as:

- Expected Goals (xG)
- Expected Assists (xA)
- Progressive passes
- Pressing metrics
- Possession value
- Player roles
- Event definitions

often require knowledge that is spread across different sources, including provider documentation, research papers, and football analytics communities.

Football Analytics RAG brings these concepts together into a single conversational learning assistant, helping users develop the football knowledge required to work with football data.

---

# Features

- Natural language football analytics assistant.
- Retrieval-Augmented Generation pipeline using a football knowledge base.
- Streamlit-based interactive chat interface.
- Synthetic user profiles for testing different knowledge levels.
- Personalized responses based on user experience and learning goals.
- Retrieval of football terminology, metrics, tactical concepts, and event definitions.
- Streaming responses for improved user experience.
- Session-based conversation memory.
- Vector similarity search for relevant football context.

---

# Technologies Used

| Category | Technology |
|---|---|
| Programming Language | Python 3.10+ |
| User Interface | Streamlit |
| LLM Framework | LangChain |
| Retrieval Approach | Retrieval-Augmented Generation (RAG) |
| Vector Database | Chroma |
| Embeddings | Configurable embedding provider |
| Language Model | Configurable LLM provider |
| Data Processing | Python libraries |
| Monitoring | LangSmith |

---

# System Architecture

```mermaid
flowchart LR

A[User Question] --> B[Streamlit Chat Interface]

B --> C[User Profile]
B --> D[Query Embedding]

D --> E[Vector Database]

E --> F[Retrieved Football Knowledge]

C --> G[Prompt Construction]
F --> G

G --> H[Large Language Model]

H --> I[Generated Response]

I --> B


subgraph Knowledge Base Creation

J[Football Documents] --> K[Document Processing]

K --> L[Text Chunking]

L --> M[Embedding Generation]

M --> E

end