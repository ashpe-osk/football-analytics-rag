from flask import Flask, render_template, request, session as flask_session, jsonify
from src.helper import (
    download_embeddings,
    rerank_documents,
    format_sources,
    is_greeting_or_smalltalk
)
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
from src.prompt import system_prompt
import os
import uuid
import traceback
import time
import re
from groq import RateLimitError, APIConnectionError

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

load_dotenv()

embeddings = download_embeddings()
index_name = "football-knowledge-base-v2"

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

#Base retriever 
base_retriever = docsearch.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 20}
)

# Use smaller model to save tokens 
chatModel = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

# History-aware retriever 
contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system", "Given a chat history and the latest user question, formulate a standalone question."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

history_aware_retriever = create_history_aware_retriever(
    chatModel,
    base_retriever,
    contextualize_prompt
)

# Main QA prompt 
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])

question_answer_chain = create_stuff_documents_chain(
    chatModel,
    qa_prompt
)

#  Session history store 
session_histories = {}

def get_session_history(session_id: str):
    if session_id not in session_histories:
        session_histories[session_id] = ChatMessageHistory()
    return session_histories[session_id]


# DETECT "I DON'T KNOW" IN ANSWER
def is_ignorance_response(answer: str) -> bool:
    """
    Returns True if the answer indicates the bot doesn't know the answer.
    """
    ignorance_phrases = [
        r"couldn't find",
        r"no information",
        r"not available",
        r"i don't know",
        r"i don't have",
        r"i couldn't find",
        r"unable to find",
        r"not in my knowledge base",
        r"doesn't appear",
        r"no data",
        r"cannot find",
    ]
    answer_lower = answer.lower()
    for phrase in ignorance_phrases:
        if re.search(phrase, answer_lower):
            return True
    return False


# RETRY HELPER
def invoke_with_retry(chain, inputs, max_retries=2, delay=2):
    for attempt in range(max_retries):
        try:
            return chain.invoke(inputs)
        except APIConnectionError as e:
            if attempt == max_retries - 1:
                raise
            print(f"Connection error, retrying in {delay}s... (attempt {attempt+1}/{max_retries})")
            time.sleep(delay)
        except RateLimitError:
            raise
    raise RuntimeError("Max retries exceeded")


# FLASK ROUTES
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/get", methods=["POST"])
def chat():
    try:
        msg = request.form.get("msg")
        if not msg:
            return jsonify({"error": "Please enter a question."}), 400

        session_id = flask_session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            flask_session['session_id'] = session_id

        print("\n========================")
        print(f"SESSION: {session_id}")
        print("USER QUESTION:", msg)

        history = get_session_history(session_id)
        chat_history = history.messages

        #Greeting check
        if is_greeting_or_smalltalk(msg):
            print("→ Detected greeting/small talk – skipping retrieval.")
            response = chatModel.invoke(
                qa_prompt.format_prompt(
                    input=msg,
                    chat_history=chat_history,
                    context="",
                    sources=""
                )
            )
            answer = response.content
            history.add_user_message(msg)
            history.add_ai_message(answer)
            print("DEBRA RESPONSE:", answer)
            return jsonify({"answer": answer, "sources": None})

        #RAG pipeline 
        print("→ Running retrieval & generation...")
        retrieved_docs = invoke_with_retry(
            history_aware_retriever,
            {"input": msg, "chat_history": chat_history}
        )

        top_docs = rerank_documents(query=msg, documents=retrieved_docs, top_k=3)
        sources_str = format_sources(top_docs)

        response = invoke_with_retry(
            question_answer_chain,
            {
                "context": top_docs,
                "sources": sources_str,
                "input": msg,
                "chat_history": chat_history
            }
        )

        answer = response["answer"] if isinstance(response, dict) else str(response)

        history.add_user_message(msg)
        history.add_ai_message(answer)

        print("DEBRA RESPONSE:", answer)

        # SUPPRESS SOURCES IF THE BOT DOESN'T KNOW
        if is_ignorance_response(answer):
            print("→ Detected 'I don't know' – suppressing sources.")
            sources_str = None

        return jsonify({"answer": answer, "sources": sources_str})

    except RateLimitError as e:
        print("\nRATE LIMIT ERROR:", e)
        return jsonify({
            "error": "I've reached my daily token limit for the Groq API. Please try again later."
        }), 429

    except APIConnectionError as e:
        print("\nAPI CONNECTION ERROR:", e)
        return jsonify({
            "error": "I'm having trouble connecting to my knowledge services. Please check your internet connection and try again."
        }), 503

    except Exception as e:
        print("\nUNEXPECTED ERROR:")
        traceback.print_exc()
        return jsonify({"error": "Sorry, I encountered an unexpected error. Please try again later."}), 500

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=True,
        use_reloader=False
    )