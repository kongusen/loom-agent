"""
Domain Adapter Interface

Defines the interface for adapting domain-specific data to the retrieval system.
Users implement this interface to support their specific domains (Schema, Code, Docs, etc.)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from loom.interfaces.retriever import Document


class DomainAdapter(ABC):
    """
    Domain Adapter Interface

    Adapts domain-specific data to the generic Document format for retrieval.
    Users implement this interface to support any domain:
    - SQL Schema
    - Code repositories
    - Documentation
    - API specifications
    - etc.

    Example:
        class MySchemaDomainAdapter(DomainAdapter):
            async def extract_documents(self, source, **kwargs):
                tables = await self._get_tables()
                return [
                    Document(
                        doc_id=f"table_{table}",
                        content=f"Table: {table}",
                        metadata={"table": table}
                    )
                    for table in tables
                ]

            async def load_document_details(self, document_id):
                table_name = document_id.replace("table_", "")
                schema = await self._get_table_schema(table_name)
                return Document(
                    doc_id=document_id,
                    content=schema,
                    metadata={"table": table_name}
                )
    """

    @abstractmethod
    async def extract_documents(
        self,
        source: Any = None,
        metadata_only: bool = False,
        **kwargs
    ) -> List[Document]:
        """
        Extract documents from the data source

        Args:
            source: Data source (database connection, file path, etc.)
            metadata_only: If True, only extract lightweight metadata for lazy loading
            **kwargs: Domain-specific parameters

        Returns:
            List of documents

        Example:
            # Full documents
            docs = await adapter.extract_documents(source=db_connection)

            # Lightweight metadata only (for lazy loading)
            docs = await adapter.extract_documents(
                source=db_connection,
                metadata_only=True
            )
        """
        raise NotImplementedError

    @abstractmethod
    async def load_document_details(
        self,
        document_id: str,
        **kwargs
    ) -> Document:
        """
        Lazy load full document details

        Called when lazy loading is enabled and the full document is needed.

        Args:
            document_id: Document identifier
            **kwargs: Domain-specific parameters

        Returns:
            Full document with details

        Example:
            doc = await adapter.load_document_details("table_users")
        """
        raise NotImplementedError

    def format_for_embedding(self, document: Document) -> str:
        """
        Format document for embedding generation

        Override this method to customize how documents are formatted
        for embedding generation.

        Args:
            document: Document to format

        Returns:
            Formatted text for embedding

        Default implementation uses document.content
        """
        return document.content

    def should_index(self, document: Document) -> bool:
        """
        Determine if a document should be indexed

        Override this method to filter documents during indexing.

        Args:
            document: Document to check

        Returns:
            True if document should be indexed

        Default implementation indexes all documents
        """
        return True


class SimpleDomainAdapter(DomainAdapter):
    """
    Simple in-memory domain adapter

    Useful for testing and simple use cases where documents are
    already in memory.

    Example:
        documents = [
            Document(doc_id="1", content="Document 1"),
            Document(doc_id="2", content="Document 2"),
        ]

        adapter = SimpleDomainAdapter(documents)
        retriever = EmbeddingRetriever(
            embedding=...,
            vector_store=...,
            domain_adapter=adapter
        )
    """

    def __init__(self, documents: List[Document]):
        """
        Args:
            documents: List of documents to index
        """
        self.documents = {doc.doc_id: doc for doc in documents}

    async def extract_documents(
        self,
        source: Any = None,
        metadata_only: bool = False,
        **kwargs
    ) -> List[Document]:
        """Extract all documents"""
        if metadata_only:
            # Return lightweight versions
            return [
                Document(
                    doc_id=doc.doc_id,
                    content=doc.content[:100] + "..." if len(doc.content) > 100 else doc.content,
                    metadata=doc.metadata
                )
                for doc in self.documents.values()
            ]
        else:
            return list(self.documents.values())

    async def load_document_details(
        self,
        document_id: str,
        **kwargs
    ) -> Document:
        """Load full document"""
        if document_id not in self.documents:
            raise ValueError(f"Document not found: {document_id}")

        return self.documents[document_id]
