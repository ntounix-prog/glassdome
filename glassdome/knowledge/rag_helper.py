"""
RAG Helper - Simple interface for agents

Layer 3 Usage Pattern:
1. Agent attempts task with base knowledge
2. If confused/error -> call consult_rag()
3. Agent uses RAG context to resolve confusion
4. Continue with task
"""

from typing import Dict, Any, Optional
from glassdome.knowledge.query_engine import QueryEngine
from glassdome.knowledge.confusion_detector import ConfusionDetector


class RAGHelper:
    """Simple interface for agents to consult RAG when confused"""
    
    def __init__(self):
        self.query_engine = QueryEngine()
        self.detector = ConfusionDetector()
        
    def consult_rag(
        self,
        context: Dict[str, Any],
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Consult RAG for help (Layer 3 pattern)
        
        Args:
            context: Current situation
                - user_message: What user said
                - agent_response: What agent is about to say
                - error_message: Any error that occurred
                - confidence_score: Agent's confidence (0-1)
                - task: Current task being attempted
            force: Force RAG query regardless of confusion detection
            
        Returns:
            {
                "should_use_rag": bool,
                "reason": str,
                "context": str,  # Formatted context from RAG
                "sources": List[str]  # Source documents
            }
            or None if no RAG needed
        """
        # Check if RAG is needed
        if force:
            decision = {"should_query": True, "reason": "Forced", "query_suggestion": context.get("user_message", ""), "priority": "high"}
        else:
            decision = self.detector.should_query_rag(context)
        
        if not decision["should_query"]:
            return None
        
        # Query RAG
        query = decision["query_suggestion"]
        results = self.query_engine.search(query, top_k=3)
        
        if not results:
            return {
                "should_use_rag": True,
                "reason": decision["reason"],
                "context": "No relevant context found in knowledge base.",
                "sources": []
            }
        
        # Format context
        context_parts = []
        context_parts.append("=== RELEVANT CONTEXT FROM KNOWLEDGE BASE ===\n")
        context_parts.append(f"Query: {query}")
        context_parts.append(f"Reason: {decision['reason']}\n")
        
        sources = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[Source {i}: {result['source']} - Similarity: {result['similarity']:.2f}]")
            context_parts.append(result['content'][:400] + "..." if len(result['content']) > 400 else result['content'])
            sources.append(result['source'])
        
        context_parts.append("\n=== END CONTEXT ===")
        
        return {
            "should_use_rag": True,
            "reason": decision["reason"],
            "priority": decision["priority"],
            "context": "\n".join(context_parts),
            "sources": sources
        }
    
    def quick_search(self, query: str, top_k: int = 3) -> str:
        """Quick search for specific information"""
        results = self.query_engine.search(query, top_k=top_k)
        
        if not results:
            return "No relevant information found."
        
        parts = []
        for r in results:
            parts.append(f"[{r['source']}]\n{r['content'][:300]}...\n")
        
        return "\n".join(parts)
    
    def search_error(self, error_message: str) -> str:
        """Search for similar errors and solutions"""
        results = self.query_engine.search_by_error(error_message, top_k=3)
        
        if not results:
            return "No similar errors found in knowledge base."
        
        parts = ["=== SIMILAR PAST ERRORS ===\n"]
        for i, r in enumerate(results, 1):
            parts.append(f"\n{i}. From {r['source']} (similarity: {r['similarity']:.2f})")
            parts.append(r['content'][:400] + "...")
        
        return "\n".join(parts)


# Example usage
if __name__ == "__main__":
    helper = RAGHelper()
    
    print("=" * 70)
    print("RAG HELPER TEST")
    print("=" * 70)
    
    # Scenario 1: Agent encounters error
    print("\n1. Agent encounters error:")
    context = {
        "error_message": "VM won't boot - no bootable device",
        "task": "deploy Windows to Proxmox"
    }
    result = helper.consult_rag(context)
    if result:
        print(f"   Should use RAG: {result['should_use_rag']}")
        print(f"   Reason: {result['reason']}")
        print(f"   Priority: {result['priority']}")
        print(f"   Sources: {result['sources']}")
    
    # Scenario 2: User asks historical question
    print("\n2. User asks historical question:")
    context = {
        "user_message": "Why did VM 114 deployment fail initially?",
        "agent_response": ""
    }
    result = helper.consult_rag(context)
    if result:
        print(f"   Should use RAG: {result['should_use_rag']}")
        print(f"   Reason: {result['reason']}")
        print(f"   Found {len(result['sources'])} sources")
    
    # Scenario 3: Agent confident (no RAG needed)
    print("\n3. Agent is confident (no RAG needed):")
    context = {
        "user_message": "Deploy Ubuntu to Proxmox",
        "agent_response": "Deploying Ubuntu now...",
        "confidence_score": 0.95
    }
    result = helper.consult_rag(context)
    print(f"   Should use RAG: {result is not None}")
    if result is None:
        print("   ✓ Agent proceeds without RAG consultation")
    
    print("\n" + "=" * 70)

