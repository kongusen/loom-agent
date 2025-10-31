"""
Complete example demonstrating EmbeddingRetriever with Agent integration

This example shows:
1. Creating a custom domain adapter
2. Setting up an embedding retriever
3. Integrating with an Agent
4. Automatic context injection
"""

import asyncio
from typing import List

from loom import agent
from loom.retrieval import (
    EmbeddingRetriever,
    DomainAdapter,
    IndexStrategy,
    RetrievalConfig
)
from loom.core.context_retriever import ContextRetriever
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.retriever import FAISSVectorStore
from loom.interfaces.retriever import Document


# ============================================================================
# Step 1: Create a custom domain adapter for your data
# ============================================================================

class KnowledgeBaseDomainAdapter(DomainAdapter):
    """
    Example: Knowledge base adapter

    Adapts a simple knowledge base for retrieval.
    In practice, this could connect to:
    - SQL databases (for schema retrieval)
    - Code repositories (for code search)
    - Documentation sites (for docs search)
    - APIs (for endpoint discovery)
    """

    def __init__(self, knowledge_base: List[dict]):
        """
        Args:
            knowledge_base: List of dict with 'id', 'title', 'content', 'tags'
        """
        self.knowledge_base = {item['id']: item for item in knowledge_base}

    async def extract_documents(
        self,
        source=None,
        metadata_only: bool = False,
        **kwargs
    ) -> List[Document]:
        """Extract knowledge base articles as documents"""
        documents = []

        for item_id, item in self.knowledge_base.items():
            if metadata_only:
                # Lightweight version for lazy loading
                doc = Document(
                    doc_id=item_id,
                    content=f"{item['title']}: {item['content'][:100]}...",
                    metadata={
                        "title": item['title'],
                        "tags": item.get('tags', []),
                        "type": "metadata"
                    }
                )
            else:
                # Full article
                doc = Document(
                    doc_id=item_id,
                    content=f"{item['title']}\n\n{item['content']}",
                    metadata={
                        "title": item['title'],
                        "tags": item.get('tags', []),
                        "type": "full"
                    }
                )

            documents.append(doc)

        return documents

    async def load_document_details(
        self,
        document_id: str,
        **kwargs
    ) -> Document:
        """Lazy load full article"""
        item = self.knowledge_base[document_id]

        return Document(
            doc_id=document_id,
            content=f"{item['title']}\n\n{item['content']}",
            metadata={
                "title": item['title'],
                "tags": item.get('tags', []),
                "type": "full"
            }
        )

    def format_for_embedding(self, document: Document) -> str:
        """Format document for embedding generation"""
        # Include title and tags in embedding
        tags_str = ", ".join(document.metadata.get("tags", []))
        return f"{document.content}\nTags: {tags_str}"


# ============================================================================
# Step 2: Prepare your knowledge base
# ============================================================================

KNOWLEDGE_BASE = [
    {
        "id": "kb1",
        "title": "What is Loom?",
        "content": "Loom is an AI agent framework that provides a simple and powerful way to build AI agents with tool calling, RAG, and multi-agent capabilities. It supports multiple LLM providers including OpenAI, Anthropic, and local models.",
        "tags": ["overview", "introduction"]
    },
    {
        "id": "kb2",
        "title": "Creating an Agent",
        "content": "To create an agent, use the loom.agent() function. You can specify the LLM provider, model, and optional tools. Example: agent = loom.agent(provider='openai', model='gpt-4o')",
        "tags": ["api", "quickstart"]
    },
    {
        "id": "kb3",
        "title": "EmbeddingRetriever",
        "content": "EmbeddingRetriever provides semantic search using embeddings and vector stores. It supports lazy loading, caching, and custom domain adapters. You can use FAISS, Milvus, or Qdrant as backends.",
        "tags": ["retrieval", "rag"]
    },
    {
        "id": "kb4",
        "title": "Tool Calling",
        "content": "Agents can call tools to perform actions. Define tools using the BaseTool interface, and pass them to the agent. The agent will automatically decide when to call tools based on the user query.",
        "tags": ["tools", "advanced"]
    },
    {
        "id": "kb5",
        "title": "Domain Adapters",
        "content": "Domain adapters allow you to adapt any data source for retrieval. Implement the DomainAdapter interface to connect to databases, APIs, file systems, or any other data source.",
        "tags": ["retrieval", "customization"]
    },
]


# ============================================================================
# Step 3: Main example
# ============================================================================

async def main():
    print("=" * 80)
    print("EmbeddingRetriever + Agent Integration Example")
    print("=" * 80)
    print()

    # -------------------------------------------------------------------------
    # Setup: Create the retrieval pipeline
    # -------------------------------------------------------------------------

    print("[1/5] Creating domain adapter...")
    adapter = KnowledgeBaseDomainAdapter(KNOWLEDGE_BASE)

    print("[2/5] Creating embedding retriever...")
    retriever = EmbeddingRetriever(
        embedding=OpenAIEmbedding(
            model="text-embedding-3-small",
            # api_key="your-openai-api-key"  # Set via OPENAI_API_KEY env var
        ),
        vector_store=FAISSVectorStore(dimension=1536),
        domain_adapter=adapter,
        config=RetrievalConfig(
            index_strategy=IndexStrategy.LAZY,  # Fast initialization
            top_k=3,                             # Return top 3 results
            similarity_threshold=0.5,            # Filter low relevance
            enable_cache=True                    # Cache embeddings
        )
    )

    print("[3/5] Initializing retriever...")
    await retriever.initialize()

    stats = retriever.get_stats()
    print(f"   ✓ Indexed {stats['indexed_documents']} documents")
    print()

    # -------------------------------------------------------------------------
    # Test 1: Direct retrieval (without agent)
    # -------------------------------------------------------------------------

    print("[4/5] Testing direct retrieval...")
    print()

    query = "How do I create an agent?"
    print(f"Query: {query}")
    print()

    results = await retriever.retrieve(query, top_k=2)

    print("Results:")
    for i, doc in enumerate(results, 1):
        print(f"  [{i}] Score: {doc.score:.3f}")
        print(f"      Title: {doc.metadata['title']}")
        print(f"      Content: {doc.content[:100]}...")
        print()

    # -------------------------------------------------------------------------
    # Test 2: Integration with Agent (automatic context injection)
    # -------------------------------------------------------------------------

    print("[5/5] Testing agent integration...")
    print()

    # Wrap retriever in ContextRetriever
    context_retriever = ContextRetriever(
        retriever=retriever,
        top_k=3,
        auto_retrieve=True  # Automatically inject relevant context
    )

    # Create agent with context retriever
    my_agent = agent(
        provider="openai",
        model="gpt-4o-mini",
        context_retriever=context_retriever
    )

    # Query the agent
    query = "What is Loom and how do I use it?"
    print(f"User: {query}")
    print()

    # The agent will automatically:
    # 1. Retrieve relevant documents (kb1, kb2, kb3)
    # 2. Inject them as context
    # 3. Generate response based on retrieved knowledge

    response = await my_agent.ainvoke(query)

    print(f"Agent: {response}")
    print()

    # -------------------------------------------------------------------------
    # Check cache statistics
    # -------------------------------------------------------------------------

    stats = retriever.get_stats()
    print("Retrieval Statistics:")
    print(f"  - Indexed documents: {stats['indexed_documents']}")
    print(f"  - Embedding cache size: {stats['embedding_cache_size']}")
    print(f"  - Document cache size: {stats['document_cache_size']}")
    print()

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    print("✓ Example completed successfully!")
    print()
    print("Key Takeaways:")
    print("1. Domain adapters make it easy to connect any data source")
    print("2. Lazy loading enables fast initialization and low memory usage")
    print("3. ContextRetriever automatically injects relevant context")
    print("4. The agent receives context without any manual prompting")
    print()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())


"""
Expected Output:
================================================================================
EmbeddingRetriever + Agent Integration Example
================================================================================

[1/5] Creating domain adapter...
[2/5] Creating embedding retriever...
[3/5] Initializing retriever...
   ✓ Indexed 5 documents

[4/5] Testing direct retrieval...

Query: How do I create an agent?

Results:
  [1] Score: 0.892
      Title: Creating an Agent
      Content: Creating an Agent

To create an agent, use the loom.agent() function. You can specify the LLM...

  [2] Score: 0.745
      Title: What is Loom?
      Content: What is Loom?

Loom is an AI agent framework that provides a simple and powerful way to...

[5/5] Testing agent integration...

User: What is Loom and how do I use it?

Agent: Loom is an AI agent framework that provides a simple way to build AI
agents with tool calling, RAG, and multi-agent capabilities. To use it, you
can create an agent using loom.agent(provider='openai', model='gpt-4o').
The framework supports multiple LLM providers including OpenAI, Anthropic,
and local models.

Retrieval Statistics:
  - Indexed documents: 5
  - Embedding cache size: 2
  - Document cache size: 3

✓ Example completed successfully!

Key Takeaways:
1. Domain adapters make it easy to connect any data source
2. Lazy loading enables fast initialization and low memory usage
3. ContextRetriever automatically injects relevant context
4. The agent receives context without any manual prompting
"""
