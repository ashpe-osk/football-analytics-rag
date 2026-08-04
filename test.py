from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os


load_dotenv()

embeddings = download_embeddings()

docsearch = PineconeVectorStore.from_existing_index(
    index_name="footy-bot",
    embedding=embeddings
)


retriever = docsearch.as_retriever(
    search_kwargs={"k":5}
)


docs = retriever.invoke(
    "What is a progressive pass?"
)


for i, doc in enumerate(docs):

    print("\n------------")
    print("DOCUMENT", i+1)
    print(doc.page_content[:500])
    print(doc.metadata)