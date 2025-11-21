"""
Glassdome Knowledge System (RAG)

Layer 3 Implementation: Confusion Resolver
- Agents query RAG only when confused/uncertain/error
- Provides context, past solutions, lessons learned
- Enables organic workflow evolution

Components:
- index_builder: Create vector embeddings from docs/code/logs
- query_engine: Search for relevant context
- confusion_detector: Determine when RAG is needed
"""

from glassdome.knowledge.query_engine import QueryEngine
from glassdome.knowledge.confusion_detector import ConfusionDetector
from glassdome.knowledge.rag_helper import RAGHelper

__all__ = ["QueryEngine", "ConfusionDetector", "RAGHelper"]

