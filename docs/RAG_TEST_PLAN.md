# RAG Validation Test Plan

**Date:** 2025-11-22  
**Purpose:** Validate context transfer via RAG system  
**Architecture:** DGX + Qwen 480B + RAG

---

## Test Hypothesis

**Can a fresh AI agent with no session memory perform equivalently to a context-rich agent using only RAG retrieval?**

---

## Test Setup

### Before Test (2025-11-21 Evening)
1. ✅ Document all current state (`CURRENT_STATE.md`)
2. ✅ Document all critical lessons (`CRITICAL_LESSONS_*.md`)
3. ✅ Document all architecture decisions
4. ✅ Commit all code and docs to GitHub
5. ⏳ Build RAG system (index everything)
6. ⏳ Close context window (end current session)

### Test Environment (2025-11-22 Morning)
```
Fresh Agent Configuration:
├─ Model: Qwen 480B (on DGX)
├─ Context: Empty (no session memory)
├─ Knowledge: Only RAG retrieval
└─ Access: Code, docs, session logs (via RAG only)

RAG System:
├─ Vector DB: TBD (FAISS/Pinecone/Chroma)
├─ Indexed Content:
│   ├─ All markdown docs (17 files)
│   ├─ All Python code
│   ├─ All session logs
│   ├─ Git commit messages
│   └─ Configuration files
├─ Embedding Model: TBD
└─ Retrieval: Semantic search
```

---

## Test Categories

### Category 1: Simple Fact Retrieval (EASY)

**Expected Success Rate:** 95%+

**Test 1.1: Current State Query**
```
Query: "What is VM 114?"

Expected Response:
- VM 114 = ubuntu-powerhouse
- IP: 192.168.3.50
- Specs: 16 cores, 32GB RAM, 1TB disk
- Service: Minecraft Bedrock server
- Port: 19132
- Status: Running

RAG Should Retrieve:
- docs/CURRENT_STATE.md (VM list)
- docs/session_logs/CRITICAL_LESSONS_*.md (deployment)

Success Criteria:
✅ Correct VM name, IP, purpose
✅ Response time < 5s
✅ No hallucinated information
```

**Test 1.2: Infrastructure Query**
```
Query: "What platforms are configured?"

Expected Response:
- Proxmox: 192.168.3.2
- ESXi: 192.168.3.3
- AWS: Operational (us-east-1)
- Azure: Operational (eastus)

RAG Should Retrieve:
- docs/CURRENT_STATE.md (platform status)
- docs/PLATFORM_SETUP.md (configuration)

Success Criteria:
✅ All 4 platforms mentioned
✅ Correct IP addresses
✅ Status accuracy
```

**Test 1.3: Credential Lookup**
```
Query: "What are the ESXi credentials?"

Expected Response:
- Host: 192.168.3.3
- User: root
- Password: H-3a-7YP

RAG Should Retrieve:
- docs/CURRENT_STATE.md (credentials section)

Success Criteria:
✅ Correct credentials
⚠️ Security: Should ask "why do you need this?" first
```

---

### Category 2: Configuration & Execution (MEDIUM)

**Expected Success Rate:** 80%+

**Test 2.1: Deploy Ubuntu (Requires Context)**
```
Query: "Deploy Ubuntu VM to Proxmox at 192.168.3.65"

Expected Actions:
1. Recognize 192.168.3.x requires VLAN tag 2
2. Configure static IP (no DHCP on this network)
3. Use template 9000 for cloning
4. Set gateway 192.168.3.1
5. Set DNS 192.168.3.10, 192.168.3.1

RAG Should Retrieve:
- docs/CRITICAL_LESSONS_*.md (VLAN tag requirement)
- docs/CURRENT_STATE.md (no DHCP warning)
- glassdome/platforms/proxmox_client.py (code examples)

Success Criteria:
✅ VLAN tag=2 applied
✅ Static IP configured
✅ VM boots and is reachable
✅ Agent explains WHY these steps are needed
```

**Test 2.2: Troubleshoot Network Issue**
```
Query: "I deployed a VM to Proxmox but can't reach it at 192.168.3.70"

Expected Troubleshooting:
1. "Did you set VLAN tag 2?"
2. "Did you configure static IP? (no DHCP on this network)"
3. "Check: qm config <vmid> | grep net0"
4. "Check: qm config <vmid> | grep ipconfig"

RAG Should Retrieve:
- docs/CRITICAL_LESSONS_*.md (VLAN discovery story)
- docs/CURRENT_STATE.md (network requirements)

Success Criteria:
✅ Identifies VLAN tag as likely cause
✅ Asks diagnostic questions
✅ Provides exact fix commands
✅ Explains past similar issue
```

**Test 2.3: Windows Deployment Strategy**
```
Query: "How should I deploy Windows Server 2022 to Proxmox?"

Expected Response:
- Option A: Manual template (RECOMMENDED)
  - Install once, sysprep, clone (2-3 min)
- Option B: autounattend.xml (NOT RECOMMENDED)
  - Unreliable, 20+ min, SATA vs VirtIO issues
- Current Status: Blocked, template not yet created

RAG Should Retrieve:
- docs/CURRENT_STATE.md (in-progress section)
- docs/CRITICAL_LESSONS_*.md (SATA vs VirtIO, template preference)
- docs/session_logs/* (autounattend struggles)

Success Criteria:
✅ Recommends template approach
✅ Explains WHY autounattend is problematic
✅ Acknowledges current status (blocked)
✅ Provides next steps
```

---

### Category 3: Historical Understanding (HARD)

**Expected Success Rate:** 70%+

**Test 3.1: Failure Root Cause Analysis**
```
Query: "Why did VM 114 fail to deploy initially?"

Expected Narrative:
1. Deployed to vmbr0 without VLAN tag
2. VM got 192.168.2.x IP instead of 192.168.3.x
3. Couldn't ping/SSH
4. Investigated Proxmox network config
5. Discovered vmbr0.2 subinterface (VLAN 2)
6. Added --net0 tag=2
7. VM redeployed, worked immediately

RAG Should Retrieve:
- docs/session_logs/* (full troubleshooting sequence)
- docs/CRITICAL_LESSONS_*.md (VLAN discovery)

Success Criteria:
✅ Correct sequence of events
✅ Root cause identified (missing VLAN tag)
✅ Solution explained
✅ Timing/duration mentioned
⚠️ May not have perfect detail (acceptable)
```

**Test 3.2: Decision Rationale**
```
Query: "Why did we choose Qwen over other models?"

Expected Response:
- DGX cluster available (infrastructure exists)
- Qwen 480B is GPT-4 class (480B parameters)
- Open-source (customizable, fine-tunable)
- On-premise (privacy, security for Microsoft/Fortune 50)
- No API costs (local inference)
- Option C architecture (full intelligence agents)

RAG Should Retrieve:
- docs/COMMUNICATIONS_ARCHITECTURE.md (Option C discussion)
- docs/CURRENT_STATE.md (DGX + Qwen section)

Success Criteria:
✅ Mentions DGX infrastructure
✅ Explains privacy/security benefit
✅ References Option C decision
✅ Links to Fortune 50 requirements
```

---

### Category 4: Complex Reasoning (COMPLEX)

**Expected Success Rate:** 60%+

**Test 4.1: Multi-VM Scenario Design**
```
Query: "Design a 9-VM AD pentesting scenario across 4 networks"

Expected Reasoning:
1. Reference multi-network requirements (Attack, DMZ, Internal, Mgmt)
2. Identify needed VMs:
   - Attack network: Kali/Parrot console
   - DMZ: Web server, mail server
   - Internal: Domain controller, file server, workstations
   - Management: Jump box, monitoring
3. Apply VLAN configuration (different tag per network)
4. Static IP allocation (no DHCP)
5. Note Windows dependency (templates not ready)

RAG Should Retrieve:
- docs/CURRENT_STATE.md (blocked on Windows)
- docs/ARCHITECTURE.md (multi-network design)
- docs/CRITICAL_LESSONS_*.md (VLAN requirements)

Success Criteria:
✅ Proposes reasonable VM layout
✅ Accounts for VLAN requirements
✅ Notes Windows dependency
✅ Provides next steps
⚠️ May not match exact vision (acceptable, starting point)
```

**Test 4.2: Troubleshooting Unknown Issue**
```
Query: "ESXi host is slow, what should I check?"

Expected Reasoning:
1. Recall similar issue (mentioned in lessons)
2. Check CPU usage (esxtop)
3. Check RAM usage (free -m equivalent)
4. Check VM resource consumption
5. Apply past pattern: Windows Update often culprit
6. Suggest monitoring for 30 min before action

RAG Should Retrieve:
- docs/COMMUNICATIONS_ARCHITECTURE.md (troubleshooting example)
- docs/CURRENT_STATE.md (ESXi known issues)

Success Criteria:
✅ Systematic troubleshooting approach
✅ Applies past learnings (Windows Update)
✅ Asks diagnostic questions
✅ Suggests monitoring before action
⚠️ May not remember exact conversation (acceptable)
```

---

### Category 5: Meta-Reasoning (REASONING)

**Expected Success Rate:** 50%+

**Test 5.1: Self-Awareness**
```
Query: "Do you remember deploying the Minecraft server yesterday?"

Expected Response:
- "I don't have direct memory of that session"
- "But I can see from docs that VM 114 was deployed 2025-11-21"
- "It's running Minecraft Bedrock at 192.168.3.50:19132"
- "The deployment involved VLAN tag discovery"
- [Provides accurate details from RAG]

Success Criteria:
✅ Acknowledges no direct memory
✅ Retrieves accurate information from docs
✅ Distinguishes between "remembering" and "knowing from records"
✅ Provides correct details
```

**Test 5.2: Knowledge Gaps**
```
Query: "What was I wearing when we deployed VM 114?"

Expected Response:
- "I don't have that information"
- "My knowledge comes from technical documentation"
- "I have detailed system logs but not personal observations"
- [Does NOT hallucinate an answer]

Success Criteria:
✅ Admits knowledge gap
✅ Does NOT hallucinate
✅ Explains scope of knowledge (docs only)
```

---

## Success Metrics

### Quantitative
- **Overall Accuracy:** >75% correct responses
- **Category 1 (Easy):** >95% correct
- **Category 2 (Medium):** >80% correct
- **Category 3 (Hard):** >70% correct
- **Category 4 (Complex):** >60% correct
- **Category 5 (Reasoning):** >50% correct
- **Response Time:** <5s for simple, <30s for complex
- **Hallucination Rate:** <5% (critical)

### Qualitative
- Agent should "feel" like same intelligence level
- Explanations should reference past context appropriately
- Should acknowledge knowledge gaps honestly
- Should ask clarifying questions when needed
- Should provide actionable next steps

---

## Failure Modes to Watch For

### 1. Retrieval Failure
**Symptom:** "I don't know" when information exists in docs  
**Cause:** Poor RAG query, embedding mismatch, missing index  
**Action:** Improve retrieval, re-embed, expand index

### 2. Hallucination
**Symptom:** Confident but incorrect information  
**Cause:** Model filling gaps without retrieval  
**Action:** Require RAG citation, add confidence scoring

### 3. Context Confusion
**Symptom:** Mixing up different VMs, IPs, or events  
**Cause:** Similar information not disambiguated  
**Action:** Improve metadata, add timestamps, entity linking

### 4. Instruction Following
**Symptom:** Correct knowledge but wrong action  
**Cause:** Not retrieving procedural documentation  
**Action:** Index code, examples, step-by-step guides

### 5. No Self-Correction
**Symptom:** Doesn't realize mistake even when corrected  
**Cause:** Not re-querying RAG with new information  
**Action:** Implement feedback loop, re-retrieval

---

## RAG System Requirements (Based on Test)

### Must Have
- Fast retrieval (<1s for simple queries)
- High accuracy (>90% relevant docs returned)
- Citation/source tracking (can point to doc + line)
- Hybrid search (semantic + keyword)
- Recency weighting (prefer recent logs)

### Should Have
- Query rewriting (expand user query)
- Multi-hop retrieval (follow references)
- Context windowing (retrieve surrounding text)
- Confidence scoring (how sure is retrieval?)
- Caching (repeated queries)

### Nice to Have
- Graph traversal (follow relationships)
- Temporal reasoning (before/after events)
- Entity linking (VM 114 = ubuntu-powerhouse)
- Summarization (long docs)
- Interactive refinement (ask follow-ups)

---

## Post-Test Analysis

### Document Results
```markdown
# RAG Test Results - 2025-11-22

## Summary
- Tests Run: X/Y
- Tests Passed: X
- Overall Accuracy: X%
- Average Response Time: Xs

## Category Breakdown
- Category 1: X% (target 95%)
- Category 2: X% (target 80%)
- Category 3: X% (target 70%)
- Category 4: X% (target 60%)
- Category 5: X% (target 50%)

## Notable Successes
1. [Example where RAG excelled]
2. ...

## Notable Failures
1. [Example where RAG failed]
2. ...

## Lessons Learned
1. [What worked]
2. [What didn't]
3. [How to improve]

## Recommended Changes
1. [RAG system improvements]
2. [Documentation gaps to fill]
3. [Index/embedding changes]
```

---

## Next Steps After Test

### If Test Passes (>75% overall)
1. ✅ Validate RAG architecture for production
2. Optimize retrieval speed
3. Expand to other agents (Deploy, Monitor, Reaper)
4. Build Slack/Email integration with confidence

### If Test Fails (<75% overall)
1. Analyze failure patterns
2. Improve documentation structure
3. Enhance RAG retrieval (embeddings, chunking)
4. Consider hybrid approach (RAG + state DB)
5. Re-test

### Regardless of Result
1. Document learnings for peer project (AI training)
2. Feed results back into training pipeline
3. Iterate on RAG architecture
4. Build real-time state tracking (complement RAG)

---

**This test is critical for validating the entire Glassdome architecture.**

If RAG works, we can scale to:
- Multiple concurrent agents
- Long-running deployments (days/weeks)
- Team collaboration via Slack/Email
- Autonomous operation (2 AM deployments)

If RAG fails, we need:
- Different approach (supervisor agent with full context?)
- Better documentation structure
- Hybrid system (RAG + real-time state)

---

**Tomorrow we find out! 🎯**

