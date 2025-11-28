"""
Query Engine module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
except ImportError:
    print("WARNING: sentence-transformers or faiss not installed")

from glassdome.core.paths import PROJECT_ROOT, RAG_INDEX_DIR


class QueryEngine:
    """Query RAG knowledge base"""
    
    def __init__(self, index_path: str = None, project_root: str = None):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.index_path = Path(index_path) if index_path else RAG_INDEX_DIR
        
        # Load index and metadata
        self._load_index()
        self._load_metadata()
        
    def _load_index(self):
        """Load FAISS index"""
        index_file = self.index_path / "faiss.index"
        
        if not index_file.exists():
            raise FileNotFoundError(
                f"RAG index not found at {index_file}. "
                f"Run 'python -m glassdome.knowledge.index_builder' first."
            )
        
        self.index = faiss.read_index(str(index_file))
        print(f"✅ Loaded FAISS index ({self.index.ntotal} vectors)")
        
    def _load_metadata(self):
        """Load document metadata"""
        metadata_file = self.index_path / "metadata.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata not found at {metadata_file}")
        
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            self.documents = data['documents']
            self.model_name = data['model_name']
            self.dimension = data['dimension']
        
        # Load embedding model
        print(f"Loading embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        
        print(f"✅ Loaded {len(self.documents)} documents")
        
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents
        
        Args:
            query: Search query (natural language)
            top_k: Number of results to return
            filter_type: Filter by document type (markdown, code, session_log, git_commit)
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of relevant documents with scores
        """
        # Generate query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Search FAISS index
        distances, indices = self.index.search(query_embedding, top_k * 2)  # Get more, filter later
        
        # Format results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # No more results
                break
            
            doc = self.documents[idx]
            
            # Filter by type if specified
            if filter_type and doc['type'] != filter_type:
                continue
            
            # Convert L2 distance to similarity score (0-1)
            # Lower distance = higher similarity
            similarity = 1 / (1 + dist)
            
            if similarity < min_similarity:
                continue
            
            results.append({
                'content': doc['content'],
                'source': doc['source'],
                'type': doc['type'],
                'metadata': doc['metadata'],
                'similarity': float(similarity),
                'distance': float(dist)
            })
            
            if len(results) >= top_k:
                break
        
        return results
    
    def search_by_error(self, error_message: str, top_k: int = 3) -> List[Dict]:
        """
        Search for similar errors and their solutions
        
        Focuses on session logs and code that might explain the error.
        """
        # Search session logs first (likely to have error context)
        log_results = self.search(
            query=f"Error: {error_message}",
            top_k=top_k,
            filter_type="session_log"
        )
        
        # Also search code for related functionality
        code_results = self.search(
            query=error_message,
            top_k=top_k // 2,
            filter_type="code"
        )
        
        # Combine and sort by similarity
        all_results = log_results + code_results
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_results[:top_k]
    
    def search_by_concept(self, concept: str, top_k: int = 5) -> List[Dict]:
        """
        Search for information about a concept or pattern
        
        Example: "VLAN configuration", "Windows deployment", "static IP"
        """
        # Search all types, prioritize documentation and session logs
        doc_results = self.search(
            query=concept,
            top_k=top_k,
            filter_type="markdown"
        )
        
        log_results = self.search(
            query=concept,
            top_k=top_k,
            filter_type="session_log"
        )
        
        # Combine
        all_results = doc_results + log_results
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_results[:top_k]
    
    def search_by_vm(self, vm_id: str, top_k: int = 5) -> List[Dict]:
        """
        Search for information about a specific VM
        
        Example: "VM 114", "ubuntu-powerhouse"
        """
        query = f"VM {vm_id}"
        
        # Search session logs and current state
        results = self.search(query, top_k=top_k)
        
        # Filter for high relevance
        return [r for r in results if r['similarity'] > 0.3]
    
    def get_context_for_task(self, task_description: str, top_k: int = 3) -> str:
        """
        Get relevant context for a task as formatted text
        
        Returns a string suitable for including in an AI prompt.
        """
        results = self.search(task_description, top_k=top_k)
        
        if not results:
            return "No relevant context found in knowledge base."
        
        context_parts = []
        context_parts.append("=== RELEVANT CONTEXT FROM KNOWLEDGE BASE ===\n")
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[Source {i}: {result['source']}]")
            context_parts.append(f"[Similarity: {result['similarity']:.2f}]")
            context_parts.append(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
            context_parts.append("")
        
        context_parts.append("=== END CONTEXT ===")
        
        return "\n".join(context_parts)


if __name__ == "__main__":
    # Quick test
    engine = QueryEngine()
    
    print("\n" + "="*70)
    print("TEST QUERIES")
    print("="*70)
    
    # Test 1: VM query
    print("\n1. Search for 'VM 114':")
    results = engine.search("VM 114", top_k=3)
    for r in results:
        print(f"   - {r['source']} (similarity: {r['similarity']:.2f})")
        print(f"     {r['content'][:100]}...")
    
    # Test 2: Concept query
    print("\n2. Search for 'VLAN configuration':")
    results = engine.search("VLAN configuration Proxmox", top_k=3)
    for r in results:
        print(f"   - {r['source']} (similarity: {r['similarity']:.2f})")
        print(f"     {r['content'][:100]}...")
    
    # Test 3: Error query
    print("\n3. Search for 'VM won't boot':")
    results = engine.search_by_error("VM won't boot", top_k=3)
    for r in results:
        print(f"   - {r['source']} (similarity: {r['similarity']:.2f})")
        print(f"     Type: {r['type']}")

