from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader
)

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_core.documents import Document

from typing import List
import os


# --------------------------------------------------
# Load PDF files with category metadata
# --------------------------------------------------

def load_pdf_file(data):

    documents = []

    for category in os.listdir(data):

        category_path = os.path.join(data, category)

        # Only process folders
        if os.path.isdir(category_path):

            loader = DirectoryLoader(
                category_path,
                glob="*.pdf",
                loader_cls=PyPDFLoader
            )

            docs = loader.load()

            for doc in docs:

                doc.metadata.update(
                    {
                        "category": category,
                        "source": os.path.basename(
                            doc.metadata.get("source", "")
                        )
                    }
                )

            documents.extend(docs)

    return documents



# --------------------------------------------------
# Filter document metadata
# --------------------------------------------------

def filter_to_minimal_docs(
    docs: List[Document]
) -> List[Document]:

    minimal_docs = []

    for doc in docs:

        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "source": doc.metadata.get("source"),
                    "category": doc.metadata.get("category")
                }
            )
        )

    return minimal_docs



# --------------------------------------------------
# Split documents into chunks
# --------------------------------------------------

def text_split(extracted_data):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    text_chunks = text_splitter.split_documents(
        extracted_data
    )

    return text_chunks



# --------------------------------------------------
# Download HuggingFace embeddings
# --------------------------------------------------

def download_embeddings():

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return embeddings