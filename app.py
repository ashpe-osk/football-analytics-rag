from flask import Flask, render_template, request

from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv

from src.prompt import system_prompt

import os


# --------------------------------------------------
# Flask Application
# --------------------------------------------------

app = Flask(__name__)


# --------------------------------------------------
# Environment Configuration
# --------------------------------------------------

load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not PINECONE_API_KEY:
    raise ValueError(
        "Missing PINECONE_API_KEY in environment variables"
    )


if not GROQ_API_KEY:
    raise ValueError(
        "Missing GROQ_API_KEY in environment variables"
    )


os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY



# --------------------------------------------------
# Load Embeddings
# --------------------------------------------------

embeddings = download_embeddings()



# --------------------------------------------------
# Pinecone Vector Database
# --------------------------------------------------

index_name = "football-knowledge-base"


docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)



# --------------------------------------------------
# Retriever
# --------------------------------------------------

retriever = docsearch.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 5
    }
)



# --------------------------------------------------
# Groq LLM
# --------------------------------------------------

chatModel = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
)



# --------------------------------------------------
# Prompt
# --------------------------------------------------

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            system_prompt
        ),
        (
            "human",
            "{input}"
        ),
    ]
)



# --------------------------------------------------
# RAG Chain
# --------------------------------------------------

question_answer_chain = create_stuff_documents_chain(
    chatModel,
    prompt
)


rag_chain = create_retrieval_chain(
    retriever,
    question_answer_chain
)



# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.route("/")
def index():

    return render_template(
        "chat.html"
    )



@app.route("/get", methods=["POST"])
def chat():

    try:

        msg = request.form.get("msg")


        if not msg:

            return "Please enter a question."



        print("\n========================")
        print("USER QUESTION:")
        print(msg)



        response = rag_chain.invoke(
            {
                "input": msg
            }
        )


        answer = response.get(
            "answer",
            "I could not find an answer."
        )


        print("\nFOOTY BOT RESPONSE:")
        print(answer)



        # Debug retrieved sources
        print("\nRETRIEVED SOURCES:")

        for doc in response.get("context", []):

            print("----------------")
            print(doc.metadata)



        return answer



    except Exception as e:

        print("\nERROR:")
        print(e)


        return (
            "Sorry, Footy Bot encountered an error "
            "while processing your question."
        )



# --------------------------------------------------
# Run Application
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True,
        use_reloader=False
    )