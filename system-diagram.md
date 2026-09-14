# Football Analytics RAG System Overview

```mermaid
flowchart LR
    U[User] --> UI[Web Interface<br/>Flask Chat UI]
    UI --> API[/get route<br/>app.py]

    API --> SESS[Session Store<br/>Flask session + ChatMessageHistory]
    API --> CHECK{Greeting or small talk?}

    CHECK -- Yes --> GREET[LLM response without retrieval<br/>chatModel.invoke]
    GREET --> RESP[Answer to user]

    CHECK -- No --> HIST[Conversation History]
    HIST --> CTX[History-aware retriever<br/>create_history_aware_retriever]
    CTX --> QF[Formulate standalone question]
    QF --> RETR[Retriever<br/>Pinecone vector search<br/>k = 20]

    PDF[Football PDF corpus<br/>data/ folders] --> LOAD[Loader + chunking<br/>PyPDFLoader + RecursiveCharacterTextSplitter]
    LOAD --> EMB[Embeddings<br/>multilingual-e5-large]
    EMB --> INDEX[Pinecone index<br/>football-knowledge-base-v2]
    INDEX --> RETR

    RETR --> DOCS[Retrieved documents]
    DOCS --> RERANK{Use reranking?}
    RERANK -- Yes --> RR[Reranker<br/>CrossEncoder]
    RERANK -- No --> RR2[Take top k docs directly]
    RR --> TOP[Top 3 documents]
    RR2 --> TOP

    TOP --> PROMPT[Prompt assembly<br/>system_prompt + chat history + user input + context]
    HIST --> PROMPT
    PROMPT --> LLM[LLM Layer<br/>Groq first, Kaggle fallback]

    LLM --> OUT[Answer + source references]
    OUT --> RESP
    TOP --> SRC[Source formatter<br/>document metadata + pages + category]
    SRC --> OUT

    subgraph ModelFallback[Model fallback logic]
        G[Groq<br/>openai/gpt-oss-120b] --> F[Fallback: Kaggle/Qwen<br/>ChatOpenAI on ENDPOINT_BASE_URL]
        G -. rate limit / outage .-> F
    end

    LLM --> G
    LLM --> F

    classDef user fill:#dbeafe,stroke:#1d4ed8,color:#111827;
    classDef data fill:#dcfce7,stroke:#15803d,color:#111827;
    classDef model fill:#fef3c7,stroke:#d97706,color:#111827;
    classDef flow fill:#f3e8ff,stroke:#7c3aed,color:#111827;

    class U,UI,API,SESS,CHECK,GREET,RESP user;
    class PDF,LOAD,EMB,INDEX,RETR,DOCS,RERANK,RR,RR2,TOP,SRC data;
    class HIST,CTX,QF,PROMPT,LLM,G,F,OUT model;
    class RESP,TOP flow;
```

## Flow summary

1. The user asks a question in the Flask web app.
2. The app checks whether the message is a greeting or small talk.
3. If it is a normal football question, the system uses conversation history to reformulate the query.
4. The reformulated question is sent to Pinecone, which searches the indexed football knowledge base.
5. Relevant documents are optionally reranked to improve relevance.
6. The top context is passed to the LLM alongside history and the user’s question.
7. The model responds with an answer and source references.
8. Groq is used first, with a Kaggle-hosted fallback if Groq is unavailable.

## Project components

- Frontend: Flask template + chat UI
- Retrieval: Pinecone + embeddings
- Knowledge base: PDF documents from the data folders
- LLM: Groq / Kaggle fallback
- Session memory: in-memory chat history
- Source tracking: page/category/provider metadata
