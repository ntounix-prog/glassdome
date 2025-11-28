# RAG Memory Improvement Plan

**Date:** November 24, 2024  
**Issue:** Agent's memory outside of today is dim - missing critical project context

---

## Problem Statement

The agent's weekly summary missed several critical aspects:
- ❌ Azure integration (fully implemented, 101 regions supported)
- ❌ .deb package maintenance (Glassdome is a Python package with `pyproject.toml`)
- ❌ Git operations and workflows
- ❌ Comprehensive Proxmox integrations (multi-instance, template migration, etc.)
- ❌ Project history and evolution

**Root Cause:** RAG system is not effectively retrieving historical knowledge, even though it's indexed.

---

## Current RAG Analysis

### What the RAG Knows (But Didn't Retrieve)

**Azure Integration:**
- ✅ `azure_client.py` exists (799 lines, fully implemented)
- ✅ Supports 101 Azure regions globally
- ✅ VM creation, resource group management
- ✅ Cloud-init support
- ✅ Tested: 2024-11-20
- ❌ **RAG similarity: 0.570-0.595** (too low, didn't surface)

**Debian Package:**
- ✅ `pyproject.toml` exists (proper Python package)
- ✅ `PACKAGE_GUIDE.md` documents package usage
- ✅ Installable with `pip install -e .`
- ✅ CLI commands: `glassdome serve`
- ❌ **RAG similarity: 0.461-0.491** (too low, didn't surface)

**Git Operations:**
- ✅ `GIT_SETUP.md` exists
- ✅ Git repository initialized
- ✅ GitHub integration
- ✅ Commit conventions documented
- ❌ **RAG similarity: 0.503-0.553** (marginal)

**Proxmox Integration:**
- ✅ Multi-instance support (pve01, pve02)
- ✅ Template migration tools
- ✅ Full CRUD operations
- ✅ Windows template deployment
- ✅ **RAG similarity: 0.610-0.652** (better, but still missed details)

---

## Solutions

### Solution 1: Pre-Query Context Gathering (Immediate)

**Problem:** Agent doesn't query RAG before writing summaries.

**Solution:** Create a "context gathering" step before important tasks.

```python
# Before writing summary, query RAG for:
1. All platform integrations (Azure, AWS, Proxmox, ESXi)
2. Package structure and deployment
3. Git workflows
4. Project history
5. Recent accomplishments
```

**Implementation:**
- Create `gather_context()` function
- Query RAG with multiple phrasings
- Aggregate results
- Use in summary generation

### Solution 2: Improve RAG Query Strategy (Short-term)

**Problem:** Single queries with low similarity thresholds miss important context.

**Solution:** Multi-query approach with different phrasings.

```python
# Instead of one query:
results = engine.search("What Azure capabilities exist?", top_k=3)

# Use multiple queries:
queries = [
    "What Azure integration and capabilities exist?",
    "Azure VM deployment and cloud-init",
    "Azure platform client implementation",
    "Multi-cloud deployment Azure",
]
results = []
for query in queries:
    results.extend(engine.search(query, top_k=2, min_similarity=0.3))
# Deduplicate and rank
```

### Solution 3: Create "Project Memory" Document (Medium-term)

**Problem:** Historical knowledge is scattered across many files.

**Solution:** Create a single "PROJECT_MEMORY.md" that gets updated regularly.

**Structure:**
```markdown
# Glassdome Project Memory

## Platform Integrations
- Azure: [summary with key facts]
- AWS: [summary]
- Proxmox: [summary]
- ESXi: [summary]

## Package Structure
- Python package with pyproject.toml
- Installable with pip install -e .
- CLI commands: glassdome serve

## Git Workflows
- Repository: github.com/ntounix/glassdome
- Branch strategy: [details]
- Commit conventions: [details]

## Project History
- Started: November 19, 2024
- Major milestones: [list]
```

**Update Strategy:**
- Update weekly (or after major changes)
- Include in RAG index
- Query this document first for summaries

### Solution 4: Improve RAG Indexing (Long-term)

**Problem:** Some documents may not be properly chunked or indexed.

**Solution:** 
1. **Re-index with better chunking:**
   - Smaller chunks for code files
   - Larger chunks for documentation
   - Overlap chunks for better context

2. **Add metadata:**
   - Document type (code, docs, logs)
   - Date created/updated
   - Importance level
   - Tags (platform, feature, etc.)

3. **Weighted retrieval:**
   - Prioritize recent documents
   - Boost importance of core docs
   - Penalize archived docs

### Solution 5: Create "Weekly Context" Document (Ongoing)

**Problem:** Agent loses context between sessions.

**Solution:** Create a weekly context document that summarizes:
- What was worked on
- What was built
- What was learned
- What's next

**Format:**
```markdown
# Weekly Context - Week of [Date]

## Work Completed
- [List of accomplishments]

## Code Changes
- [Key files modified/created]

## Learnings
- [New knowledge gained]

## Next Steps
- [Planned work]
```

**Usage:**
- Query this document first for weekly summaries
- Update at end of each week
- Include in RAG index

---

## Implementation Plan

### Phase 1: Immediate (Today)
1. ✅ Create `gather_context()` function
2. ✅ Update summary generation to use context gathering
3. ✅ Create `PROJECT_MEMORY.md` with current knowledge

### Phase 2: Short-term (This Week)
1. Implement multi-query RAG strategy
2. Create `WEEKLY_CONTEXT.md` template
3. Update RAG index with better chunking

### Phase 3: Medium-term (Next Week)
1. Re-index RAG with metadata
2. Implement weighted retrieval
3. Create automated context updates

### Phase 4: Long-term (Ongoing)
1. Weekly context document updates
2. Project memory document maintenance
3. Continuous RAG improvement

---

## Code Changes Needed

### 1. Context Gathering Function

```python
# glassdome/knowledge/context_gatherer.py
from glassdome.knowledge.query_engine import QueryEngine

class ContextGatherer:
    def __init__(self):
        self.engine = QueryEngine()
    
    def gather_project_context(self) -> Dict[str, List]:
        """Gather comprehensive project context from RAG"""
        context = {
            'platforms': [],
            'package': [],
            'git': [],
            'history': [],
            'recent': []
        }
        
        # Multi-query for each topic
        platform_queries = [
            "What Azure integration and capabilities exist?",
            "What AWS deployment features are implemented?",
            "What Proxmox integrations and features exist?",
            "What ESXi deployment capabilities are available?",
        ]
        
        for query in platform_queries:
            results = self.engine.search(query, top_k=3, min_similarity=0.3)
            context['platforms'].extend(results)
        
        # Similar for other topics...
        
        return context
```

### 2. Update Summary Generation

```python
# Before writing summary:
context = ContextGatherer().gather_project_context()

# Use context in summary:
- Check context['platforms'] for Azure/AWS/Proxmox/ESXi
- Check context['package'] for package structure
- Check context['git'] for git workflows
- Check context['history'] for project evolution
```

---

## Metrics for Success

1. **Coverage:** Weekly summaries include all major components
2. **Accuracy:** Information is correct and up-to-date
3. **Completeness:** No critical aspects are missed
4. **Consistency:** Similar queries return similar results

---

## Next Steps

1. **Immediate:** Create `PROJECT_MEMORY.md` with current knowledge
2. **Today:** Implement context gathering for summary generation
3. **This Week:** Create weekly context document template
4. **Ongoing:** Update project memory and weekly context regularly

---

*This plan addresses the root cause: RAG retrieval is not comprehensive enough for complex queries. The solution is multi-layered: better queries, better indexing, and better context management.*

