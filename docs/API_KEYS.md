# API Keys Configuration for Glassdome

## Available API Keys

All API keys are configured in `~/.bashrc` and automatically available in the shell environment.

### AI/LLM Providers (Research Agent)

#### 1. OpenAI (GPT-4)
```bash
OPENAI_API_KEY=sk-proj-...
```
**Usage:** Primary LLM for Research Agent
- CVE analysis and understanding
- Exploitation procedure generation
- Structured output generation
**Models:** GPT-4 Turbo, GPT-4, GPT-3.5 Turbo

#### 2. Anthropic (Claude)
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```
**Usage:** Alternative/backup LLM for Research Agent
- Deep vulnerability analysis
- Complex procedure generation
- Long-context analysis (200K tokens)
**Models:** Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku

#### 3. X.AI (Grok)
```bash
XAI_API_KEY=xai-...
```
**Usage:** Optional LLM provider
- Real-time information (if needed)
- Alternative analysis perspective

#### 4. Perplexity
```bash
PERPLEXITY_API_KEY=pplx-...
```
**Usage:** Research and information gathering
- Finding recent CVE discussions
- Security blog analysis
- Technical documentation search

---

### Search & Data APIs (Exploit Finder)

#### 5. Google Custom Search
```bash
GOOGLE_SEARCH_API=AIzaSy...
GOOGLE_ENGINE_ID=30695a31b6d624f73
```
**Usage:** Web search for exploit research
- Finding PoC repositories
- Security advisories
- Technical articles

#### 6. RapidAPI
```bash
RAPIDAPI_KEY=3ef9be207emsh...
```
**Usage:** Access to various APIs through RapidAPI marketplace
- Potential for CVE data APIs
- Security tool integrations

---

### Proxmox & Infrastructure

#### 7. Proxmox API Token (from .env)
```bash
PROXMOX_HOST=192.168.3.2
PROXMOX_USER=apex@pve
PROXMOX_TOKEN_ID=apex@pve!glassdome-token
PROXMOX_TOKEN_SECRET=44fa1891-0b3f-487a-b1ea-0800284f79d9
```
**Usage:** VM deployment and management
**Status:** ✅ Working (deployed VM ID 100)

---

## Research Agent LLM Strategy

### Multi-Provider Support

The Research Agent will support multiple LLM providers with automatic fallback:

```python
# glassdome/ai/llm_client.py

class LLMClient:
    def __init__(self, provider: str = "auto"):
        """
        provider options:
        - "auto": Try OpenAI → Anthropic → XAI
        - "openai": GPT-4 (fast, expensive)
        - "anthropic": Claude (thorough, moderate cost)
        - "xai": Grok (real-time, experimental)
        - "perplexity": Research-focused
        """
        self.provider = self.select_provider(provider)
```

### Provider Selection Criteria

**For CVE Analysis (Phase 1):**
- **Primary:** OpenAI GPT-4 (fast, structured output)
- **Backup:** Anthropic Claude 3 Sonnet

**For Exploit Research (Phase 2):**
- **Primary:** Perplexity (designed for research)
- **Backup:** Google Search API

**For Procedure Generation (Phase 4):**
- **Primary:** Anthropic Claude 3 Opus (thorough, detailed)
- **Backup:** OpenAI GPT-4

**For Validation (Phase 5):**
- **Primary:** OpenAI GPT-3.5 Turbo (fast, cheap)

---

## Cost Optimization

### Estimated Costs per CVE Research

**Quick Research (10 minutes):**
- GPT-4: ~5,000 tokens input, ~2,000 tokens output = $0.15
- Google Search: 10 queries = $0.01
- **Total:** ~$0.16 per CVE

**Standard Research (30 minutes):**
- GPT-4: ~15,000 tokens input, ~5,000 tokens output = $0.45
- Claude 3: ~10,000 tokens input, ~3,000 tokens output = $0.30
- Google Search: 20 queries = $0.02
- Perplexity: 5 queries = $0.05
- **Total:** ~$0.82 per CVE

**Deep Research (1-2 hours):**
- Claude 3 Opus: ~50,000 tokens input, ~15,000 tokens output = $2.25
- GPT-4: ~20,000 tokens input, ~10,000 tokens output = $0.90
- Search APIs: $0.10
- **Total:** ~$3.25 per CVE

### Annual Cost Projection

**Scenario 1: Training Focus (100 CVEs/year)**
- 100 CVEs × $0.82 (standard) = $82/year
- **Very affordable**

**Scenario 2: Research Focus (500 CVEs/year)**
- 500 CVEs × $0.82 (standard) = $410/year
- **Still very affordable vs. $50K platforms**

**Scenario 3: Heavy Usage (1000 CVEs/year)**
- 1000 CVEs × $0.82 (standard) = $820/year
- **Fraction of proprietary platform costs**

### Cost Comparison

| Solution | Annual Cost | Notes |
|----------|-------------|-------|
| Cyber Range Platform | $50,000+ | Per-seat licensing, limited CVEs |
| Hack The Box Enterprise | $20,000+ | Curated content only |
| Manual Research (200 hrs) | $30,000+ | Security engineer at $150/hr |
| **Glassdome (1000 CVEs)** | **$820** | **Unlimited customization** |

**Savings: 98%+**

---

## API Usage Limits

### OpenAI
- **Rate Limit:** 10,000 requests/minute (Tier 5)
- **Token Limit:** 2M tokens/minute
- **Sufficient for:** Hundreds of concurrent research tasks

### Anthropic
- **Rate Limit:** 50 requests/minute
- **Token Limit:** 100K tokens/minute
- **Sufficient for:** Dozens of concurrent deep analyses

### Google Custom Search
- **Free Tier:** 100 queries/day
- **Paid:** 10,000 queries/day ($5/1000 queries)
- **Sufficient for:** 10-50 CVE researches/day

### Perplexity
- **Rate Limit:** 50 requests/minute
- **Sufficient for:** Research augmentation

---

## Environment Setup

### For Development (Local)

API keys are automatically loaded from `~/.bashrc`:

```bash
# Just activate the venv
cd /home/nomad/glassdome
source venv/bin/activate

# Keys are already in environment
echo $OPENAI_API_KEY  # Works!
```

### For Docker (Containerized)

Pass environment variables to containers:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - XAI_API_KEY=${XAI_API_KEY}
      - PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}
```

Run with:
```bash
# Inherit from shell environment
docker-compose up
```

### For Production

**Option 1: Environment Variables (Current)**
- Keys in `~/.bashrc` on server
- Secure, not in git
- ✅ Current approach

**Option 2: Secrets Manager (Future)**
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Encrypted at rest
- Audit logging

---

## Testing API Access

### Quick Test Script

```python
# test_api_keys.py

import os
import openai
import anthropic

def test_openai():
    """Test OpenAI API access."""
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API works!'"}],
            max_tokens=10
        )
        print("✅ OpenAI API: Working")
        return True
    except Exception as e:
        print(f"❌ OpenAI API: {e}")
        return False

def test_anthropic():
    """Test Anthropic API access."""
    try:
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'API works!'"}]
        )
        print("✅ Anthropic API: Working")
        return True
    except Exception as e:
        print(f"❌ Anthropic API: {e}")
        return False

if __name__ == "__main__":
    print("Testing API Keys...\n")
    test_openai()
    test_anthropic()
```

Run:
```bash
cd /home/nomad/glassdome
source venv/bin/activate
python test_api_keys.py
```

---

## Security Best Practices

### ✅ Current Security (Good)
- Keys in `~/.bashrc` (not in git) ✅
- `env.example` has placeholders only ✅
- `.gitignore` excludes `.env` files ✅

### 🔒 Additional Recommendations

1. **Restrict Key Permissions**
   ```bash
   chmod 600 ~/.bashrc
   ```

2. **Use Read-Only Keys (where possible)**
   - OpenAI: Can't restrict (unfortunately)
   - Anthropic: Can't restrict
   - Proxmox: ✅ Already using token (not root password)

3. **Monitor Usage**
   - OpenAI: Check usage at platform.openai.com
   - Anthropic: Check at console.anthropic.com
   - Set up billing alerts

4. **Rotate Keys Periodically**
   - Quarterly rotation recommended
   - Especially after team changes

5. **Rate Limiting**
   - Implement app-level rate limiting
   - Prevent runaway costs
   - Protect against abuse

---

## Tomorrow's Implementation

### Phase 1: LLM Client (Morning)

**File:** `glassdome/ai/llm_client.py`

```python
import os
import openai
import anthropic

class LLMClient:
    def __init__(self, provider="openai"):
        self.provider = provider
        
        if provider == "openai":
            self.client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
        elif provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
    
    async def analyze_cve(self, cve_data: dict):
        """Analyze CVE using LLM."""
        # Implementation tomorrow
        pass
```

### Required Packages

Add to `requirements.txt`:
```
openai>=1.0.0
anthropic>=0.7.0
google-api-python-client>=2.0.0
```

Install:
```bash
cd /home/nomad/glassdome
source venv/bin/activate
pip install openai anthropic google-api-python-client
```

---

## Summary

**You have everything needed for the Research Agent!** 🎉

### Available APIs
- ✅ OpenAI GPT-4 (primary LLM)
- ✅ Anthropic Claude (backup LLM)
- ✅ Perplexity (research)
- ✅ Google Search (exploit finding)
- ✅ Multiple other options

### Cost Projections
- Standard CVE research: $0.82
- 1000 CVEs/year: $820
- **98% cheaper than alternatives**

### Security
- ✅ Keys in `~/.bashrc` (not in git)
- ✅ Environment variables pattern
- ✅ Ready for containers

**Tomorrow: Build the Research Agent using these APIs!** 🚀

