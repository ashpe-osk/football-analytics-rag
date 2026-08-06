import streamlit as st
from dotenv import load_dotenv
from src.helper import download_embeddings
from src.prompt import system_prompt
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
import os

load_dotenv()

st.set_page_config(page_title="Debra · Football Knowledge", page_icon="⚽", layout="centered")

# --------------------------------------------------
# Custom CSS — dark theme, chat bubbles, header
# --------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    #MainMenu, footer, header { visibility: hidden; }

    .chat-header {
        display: flex; align-items: center; gap: 12px;
        padding: 16px 20px; background: #161b22;
        border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #2a2f3a;
    }
    .chat-header img {
        width: 44px; height: 44px; border-radius: 50%;
    }
    .chat-header .name { font-weight: 600; font-size: 1.1rem; color: #f0f0f0; }
    .chat-header .tagline { font-size: 0.85rem; color: #9aa0a6; }
    .online-dot {
        width: 8px; height: 8px; background: #2ecc71; border-radius: 50%;
        display: inline-block; margin-left: 6px;
    }

    .welcome-box {
        text-align: center; padding: 40px 20px; color: #d0d0d0;
    }
    .welcome-box h2 { color: #f0f0f0; }
    .welcome-box span { color: #EC7D23; }

    .suggestion-chip {
        display: inline-block; padding: 6px 14px; margin: 4px;
        background: #1c2128; border: 1px solid #30363d; border-radius: 20px;
        font-size: 0.85rem; color: #ccc; cursor: pointer;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px; padding: 4px 8px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown("""
<div class="chat-header">
    <img src="https://cdn-icons-png.flaticon.com/512/861/861512.png">
    <div>
        <div class="name">Debra <span class="online-dot"></span></div>
        <div class="tagline">Your football knowledge companion</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Cache the RAG pipeline
# --------------------------------------------------
@st.cache_resource
def load_rag_chain():
    os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY")
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

    embeddings = download_embeddings()
    docsearch = PineconeVectorStore.from_existing_index(
        index_name="football-knowledge-base",
        embedding=embeddings
    )
    retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    chatModel = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
    return create_retrieval_chain(retriever, question_answer_chain)

rag_chain = load_rag_chain()

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# --------------------------------------------------
# Sidebar — clear chat
# --------------------------------------------------
with st.sidebar:
    st.markdown("### ⚽ Debra")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------
# Welcome state (only shows before first message)
# --------------------------------------------------
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
        <h2>Welcome, I'm <span>Debra</span></h2>
        <p>Your guide to understanding football — tactics, metrics, and the hidden story behind the numbers.</p>
        <p>👉 Ask me anything about the beautiful game</p>
    </div>
    """, unsafe_allow_html=True)

    suggestions = [
        "Explain xG",
        "What is PPDA?",
        "How are events recorded in football?",
        "What is a passing network?",
        "Explain progressive passes",
    ]
    cols = st.columns(len(suggestions))
    clicked = None
    for col, s in zip(cols, suggestions):
        if col.button(s, use_container_width=True):
            clicked = s
else:
    clicked = None

# --------------------------------------------------
# Render existing chat history
# --------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "⚽"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# --------------------------------------------------
# Handle input (typed or suggestion chip)
# --------------------------------------------------
user_input = st.chat_input("Ask about tactics, metrics, or player roles...") or clicked

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="⚽"):
        with st.spinner("Just a moment..."):
            try:
                response = rag_chain.invoke({"input": user_input})
                answer = response.get("answer", "I could not find an answer.")
            except Exception as e:
                answer = f"Sorry, Debra encountered an error: {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()