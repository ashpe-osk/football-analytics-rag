from dotenv import load_dotenv
import os
import time

from src.helper import (
    load_pdf_file,
    filter_to_minimal_docs,
    text_split,
    download_embeddings
)

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore


# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


if not PINECONE_API_KEY:
    raise ValueError(
        "Missing PINECONE_API_KEY"
    )


# --------------------------------------------------
# Load documents
# --------------------------------------------------

print("📄 Loading PDFs...")


extracted_data = load_pdf_file(
    data="data/"
)


print(
    f"✅ Documents loaded: {len(extracted_data)}"
)



# --------------------------------------------------
# Metadata cleanup
# --------------------------------------------------

filter_data = filter_to_minimal_docs(
    extracted_data
)



# --------------------------------------------------
# Chunk documents
# --------------------------------------------------

print("✂️ Creating chunks...")


text_chunks = text_split(
    filter_data
)


print(
    f"✅ Chunks created: {len(text_chunks)}"
)



# --------------------------------------------------
# Embeddings
# --------------------------------------------------

print("🧠 Loading embeddings...")


embeddings = download_embeddings()


print("✅ Embeddings ready")



# --------------------------------------------------
# Pinecone
# --------------------------------------------------

pc = Pinecone(
    api_key=PINECONE_API_KEY
)


index_name = "football-knowledge-base-v2"



# --------------------------------------------------
# Create index only if missing
# --------------------------------------------------

if not pc.has_index(index_name):

    print("Creating Pinecone index...")


    pc.create_index(
        name=index_name,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )


    print("Waiting for index readiness...")


    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(5)


    print("✅ Index ready")


else:

    print(
        "✅ Existing Pinecone index found"
    )



# --------------------------------------------------
# Upload vectors in batches
# --------------------------------------------------

print("⬆️ Uploading vectors...")


batch_size = 100


for i in range(
    0,
    len(text_chunks),
    batch_size
):

    batch = text_chunks[
        i:i + batch_size
    ]


    print(
        f"Uploading batch {i//batch_size + 1} "
        f"/ {(len(text_chunks)//batch_size)+1}"
    )


    PineconeVectorStore.from_documents(
        documents=batch,
        index_name=index_name,
        embedding=embeddings
    )


print(
    "🎉 Football knowledge base upload completed!"
)