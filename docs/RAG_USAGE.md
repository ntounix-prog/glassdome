# RAG System Usage Guide

**Implementation:** Layer 3 (Confusion Resolver)  
**Status:** Operational  
**Last Updated:** 2025-11-22

---

## Overview

The RAG (Retrieval-Augmented Generation) system provides context-aware assistance to agents when they encounter confusion, errors, or uncertainty.

**Layer 3 Pattern:**
- Agents attempt tasks with base knowledge first
- RAG is consulted ONLY when confused/uncertain/error
- Provides relevant context from past sessions, docs, code
- Enables organic workflow evolution

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Agent (Qwen 480B)                       │
│  - Receives task                         │
│  - Attempts with base knowledge          │
│  - Monitors for confusion signals        │
└──────────────┬──────────────────────────┘
               │
               ▼ (Only when confused)
┌─────────────────────────────────────────┐
│  ConfusionDetector                       │
│  - Error occurred?                       │
│  - User corrected agent?                 │
│  - Historical question?                  │
│  - Low confidence?                       │
└──────────────┬──────────────────────────┘
               │
               ▼ (If confused = TRUE)
┌─────────────────────────────────────────┐
│  QueryEngine                             │
│  - Search 3091 indexed documents         │
│  - Return top 3-5 relevant chunks        │
│  - Include: docs, code, logs, commits    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Agent (with RAG context)                │
│  - Reviews relevant context              │
│  - Applies past learnings                │
│  - Resolves confusion                    │
│  - Continues task                        │
└─────────────────────────────────────────┘
```

---

## Indexed Knowledge

**Total:** 3,091 documents

### Breakdown:
- **2,767** markdown chunks (all documentation)
- **130** code chunks (functions/classes with docstrings)
- **109** session logs (including CRITICAL_LESSONS)
- **85** git commits (recent history with context)

### Sources:
- `docs/` - All markdown documentation
- `glassdome/` - Python code with docstrings
- `docs/session_logs/` - Session logs and critical lessons
- Git history - Commit messages and context

---

## Confusion Triggers (When RAG is Queried)

### 1. Error Encountered
```python
context = {
    "error_message": "VM failed to boot after 3 attempts"
}
# → RAG searches for similar errors and solutions
```

### 2. Historical Question
```python
context = {
    "user_message": "Why did VM 114 fail initially?"
}
# → RAG retrieves past events and decisions
```

### 3. Agent Uncertainty
```python
context = {
    "agent_response": "I'm not sure which VLAN tag to use"
}
# → RAG searches for relevant configuration patterns
```

### 4. User Correction
```python
context = {
    "user_message": "Actually, that's wrong. Credentials are in .env"
}
# → RAG searches for correct information
```

### 5. Low Confidence
```python
context = {
    "confidence_score": 0.4  # < 0.5 threshold
}
# → RAG provides validation context
```

### 6. Unknown Entity
```python
context = {
    "user_message": "What's the status of VM 114?"
}
# → RAG searches for VM-specific information
```

---

## Usage Examples

### Basic Usage (RAGHelper)

```python
from glassdome.knowledge import RAGHelper

helper = RAGHelper()

# Agent encounters error
context = {
    "error_message": "Connection refused to 192.168.3.50",
    "task": "deploy VM"
}

result = helper.consult_rag(context)

if result and result["should_use_rag"]:
    print(f"Consulting RAG: {result['reason']}")
    print(f"Priority: {result['priority']}")
    print(f"\n{result['context']}")
    
    # Agent uses context to resolve issue
```

### Direct Query (QueryEngine)

```python
from glassdome.knowledge import QueryEngine

engine = QueryEngine()

# Search for specific information
results = engine.search("VLAN configuration Proxmox", top_k=3)

for result in results:
    print(f"Source: {result['source']}")
    print(f"Similarity: {result['similarity']:.2f}")
    print(result['content'][:200])
```

### Error Search

```python
from glassdome.knowledge import RAGHelper

helper = RAGHelper()

# Search for similar past errors
error_context = helper.search_error("VM won't boot")
print(error_context)
# Returns: Similar errors from session logs with solutions
```

### Confusion Detection

```python
from glassdome.knowledge import ConfusionDetector

detector = ConfusionDetector()

context = {
    "user_message": "Why did VM 114 fail?",
    "agent_response": ""
}

decision = detector.should_query_rag(context)

if decision["should_query"]:
    print(f"Should query RAG: {decision['reason']}")
    print(f"Suggested query: {decision['query_suggestion']}")
    print(f"Priority: {decision['priority']}")
```

---

## Agent Integration Pattern

### Recommended Flow:

```python
class GlassdomeAgent:
    def __init__(self):
        self.rag = RAGHelper()
        
    def execute_task(self, user_message: str):
        # 1. Try with base knowledge
        try:
            result = self._attempt_task(user_message)
            
            # Success - no RAG needed
            return result
            
        except Exception as e:
            # 2. Error occurred - consult RAG
            context = {
                "error_message": str(e),
                "user_message": user_message,
                "task": self.current_task
            }
            
            rag_result = self.rag.consult_rag(context)
            
            if rag_result:
                # 3. Use RAG context to resolve
                print(f"Consulting knowledge base: {rag_result['reason']}")
                
                # Include RAG context in retry
                result = self._attempt_task_with_context(
                    user_message,
                    rag_context=rag_result['context']
                )
                
                return result
            else:
                # No RAG help available
                raise
    
    def handle_user_query(self, message: str):
        # Check if this triggers RAG
        context = {"user_message": message}
        rag_result = self.rag.consult_rag(context)
        
        if rag_result:
            # Historical/clarification question
            return self._respond_with_context(rag_result['context'])
        else:
            # Direct query
            return self._respond_directly(message)
```

---

## Rebuilding Index

When documentation/code changes significantly:

```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -m glassdome.knowledge.index_builder
```

This will:
1. Re-scan all docs, code, logs
2. Generate new embeddings
3. Rebuild FAISS index
4. Save to `.rag_index/`

**Rebuild triggers:**
- Major documentation updates
- New critical lessons added
- Significant code changes
- After each session (to index session logs)

---

## Testing RAG Quality

### Test Queries:

```python
from glassdome.knowledge import QueryEngine

engine = QueryEngine()

# Test 1: Specific fact
results = engine.search("What is VM 114?")
# Should return: Minecraft server, 192.168.3.50

# Test 2: Configuration pattern
results = engine.search("How to configure static IP on Proxmox")
# Should return: VLAN tag, ipconfig0 commands

# Test 3: Historical event
results = engine.search("Why did VM 114 fail initially?")
# Should return: VLAN discovery story

# Test 4: Error solution
results = engine.search_by_error("VM won't boot")
# Should return: Past boot failures and solutions
```

### Success Criteria:
- Relevant doc in top 3 results
- Similarity score > 0.5 for good matches
- Response time < 2 seconds
- No hallucinations (only returns indexed content)

---

## Performance

### Current Stats:
- **Index size:** 3,091 documents
- **Index file:** ~2MB (FAISS)
- **Metadata:** ~4MB (JSON)
- **Query time:** < 1s
- **Embedding model:** all-MiniLM-L6-v2 (384 dimensions)

### Scaling:
- Can handle 10K+ documents easily
- FAISS is very fast for this scale
- May need IVF index if > 100K documents
- Consider GPU acceleration for Qwen 480B embeddings

---

## Limitations & Future Enhancements

### Current Limitations:
1. **No multi-hop reasoning** (single query only)
2. **No re-ranking** (just similarity)
3. **No query rewriting** (uses query as-is)
4. **Fixed chunk size** (by markdown sections)
5. **No temporal weighting** (recent docs not prioritized)

### Planned Enhancements:
1. **Query expansion** - Rewrite query for better matches
2. **Re-ranking** - Use cross-encoder for better results
3. **Multi-hop** - Follow references between docs
4. **Hybrid search** - Combine semantic + keyword
5. **Confidence scoring** - Know when RAG is uncertain
6. **Interactive refinement** - Ask follow-up questions
7. **Graph RAG** - Link related concepts/entities

---

## Troubleshooting

### Issue: "RAG index not found"
```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -m glassdome.knowledge.index_builder
```

### Issue: "No relevant results"
- Check if docs indexed: `ls .rag_index/`
- Verify query phrasing
- Lower similarity threshold
- Rebuild index if docs changed

### Issue: "Slow queries"
- Check FAISS index loaded correctly
- Verify embedding model downloaded
- Consider GPU acceleration

### Issue: "Irrelevant results"
- Query too broad - be more specific
- Check confusion detection logic
- May need query rewriting

---

## Related Documents
- `docs/RAG_TEST_PLAN.md` - Validation test plan
- `docs/CURRENT_STATE.md` - System state snapshot
- `docs/COMMUNICATIONS_ARCHITECTURE.md` - Integration with Slack/Email
- `docs/ARCHITECTURE.md` - Overall system design

---

**RAG System Status:** ✅ Operational (Layer 3)  
**Next Evolution:** Monitor usage patterns, may drop to Layer 2 if beneficial  
**Last Indexed:** 2025-11-22

