from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader
)

from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_core.documents import Document

from typing import List



# --------------------------------------------------
# Load PDF files
# --------------------------------------------------

def load_pdf_file(data):

    loader = DirectoryLoader(
        data,
        glob="*.pdf",
        loader_cls=PyPDFLoader
    )

    documents = loader.load()

    return documents



# --------------------------------------------------
# Filter document metadata
# --------------------------------------------------

def filter_to_minimal_docs(
    docs: List[Document]
) -> List[Document]:

    """
    Keeps only useful metadata and page content.
    """

    minimal_docs = []

    for doc in docs:

        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={
                    "source": doc.metadata.get("source")
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
        chunk_overlap=20
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