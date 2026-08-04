# Football Analytics RAG

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)](https://www.langchain.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-VectorDB-blueviolet.svg)](https://www.pinecone.io/)


## Overview

Football Analytics RAG is a Flask-based AI learning assistant designed to bridge the gap between technical data skills and football knowledge. The platform helps data analysts, data scientists, developers, and beginners with limited football backgrounds understand football analytics concepts, terminology, tactical ideas, and event data definitions.

By combining Retrieval-Augmented Generation (RAG) with a curated knowledge base, the system converts complex football analytics concepts into clear, accessible explanations tailored to different experience levels.

## Motivation

Football analytics exists at the intersection of two challenging domains:

- **Technical skills** - Data analysis, statistics, programming, and machine learning
- **Football knowledge** - Tactical understanding, terminology, positional play, and game dynamics

Many talented analysts possess strong technical skills but struggle with football-specific terminology and concepts. Conversely, football enthusiasts often want to understand analytical approaches but lack the technical framework. Football Analytics RAG addresses this gap by providing an intelligent assistant that explains football analytics concepts in context, making the field more accessible to both groups.

## Features

- **Conversational Assistant**: Interactive chat interface for asking football analytics questions
- **RAG-based Retrieval**: Contextually relevant knowledge retrieval from a curated knowledge base
- **Personalized Explanations**: Responses tailored to user experience level (beginner to advanced)
- **Football Terminology**: Clear explanations of football-specific terms and concepts
- **Tactical Analysis**: Understanding of formations, playing styles, and strategic concepts
- **Event Definitions**: Explanations of football data provider event types and metrics
- **Vector Search**: Semantic similarity search using Pinecone vector database
- **Session Management**: Maintains conversation context for follow-up questions
- **LangSmith Integration**: Comprehensive monitoring and tracing for debugging and optimization

## System Architecture

### RAG Pipeline Architecture

```mermaid
graph TD
    A[User Question] --> B[Flask Web Interface]
    B --> C[User Profile + Query Processing]
    C --> D[Embedding Generation]
    D --> E[Pinecone Vector Database]
    E --> F[Retrieved Football Knowledge]
    F --> G[LangChain Prompt Construction]
    G --> H[Large Language Model]
    H --> I[Generated Response]
