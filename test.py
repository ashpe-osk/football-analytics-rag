from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os


load_dotenv()

embeddings = download_embeddings()


# Connect to new Pinecone index
docsearch = PineconeVectorStore.from_existing_index(
    index_name="football-knowledge-base",
    embedding=embeddings
)


retriever = docsearch.as_retriever(
    search_kwargs={
        "k": 5
    }
)


docs = retriever.invoke(
    "What is a progressive pass?"
)


for i, doc in enumerate(docs):

    print("\n------------")
    print("DOCUMENT", i+1)

    print(doc.page_content[:500])

    print("\nMETADATA:")
    print(doc.metadata)