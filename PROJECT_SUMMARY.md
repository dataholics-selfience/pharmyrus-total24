# Pharmyrus v27 - Project Summary

## 🎯 Objective
Create a **generic, agnostic** pharmaceutical patent search system that:
- Finds WO and country-specific patents **automatically** from molecule name alone
- Combines EPO OPS (fast) + Google Patents (comprehensive)
- Achieves 100% Cortellis benchmark coverage
- Works for any molecule, any country (BR, US, JP, etc.)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Pharmyrus v27 Orchestrator                  │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
  ┌───────▼─────────┐           ┌────────▼─────────────┐
  │  Layer 1: EPO   │           │ Layer 2: Google      │
  │     OPS         │           │   Patents            │
  └───────┬─────────┘           └────────┬─────────────┘
          │                               │
          │   Fast (30-60s)              │  Comprehensive (2-5min)
          │   Official API               │  Web Crawling
          │                               │
          └───────────────┬───────────────┘
                          │
                  ┌───────▼──────────┐
                  │  Deduplicator    │
                  │  & Merger        │
                  └───────┬──────────┘
                          │
                  ┌───────▼──────────┐
                  │  Final Results   │
                  └──────────────────┘
```

## 📁 Project Structure

```
pharmyrus-v27/
├── main.py                          # FastAPI application
├── orchestrator.py                  # Coordinates layers
├── config/
│   ├── __init__.py
│   ├── proxies.py                   # 14 premium proxies
│   └── settings.py                  # Configuration
├── layers/
│   ├── __init__.py
│   ├── epo_layer.py                 # EPO OPS integration
│   └── google_patents_layer.py      # Google Patents orchestration
├── google_patents/
│   ├── __init__.py
│   ├── stealth_browser.py           # Playwright + stealth
│   ├── wo_searcher.py               # Strategy 1: WO search
│   ├── br_family_extractor.py       # Strategy 2: Family extraction (TODO)
│   └── br_direct_searcher.py        # Strategy 3: Direct search (TODO)
├── utils/
│   ├── __init__.py
│   ├── deduplicator.py              # Remove duplicates
│   └── merger.py                    # Merge EPO + Google results
├── Dockerfile                        # Railway-ready
├── requirements.txt
├── railway.json
├── deploy.sh
├── README.md
├── DEPLOYMENT.md
└── PROJECT_SUMMARY.md
```

## 🔑 Key Features

### 1. Generic Discovery
- **No hardcoded patents** - discovers everything from molecule name
- Uses PubChem for synonyms/dev codes
- Systematic WO search across year ranges
- Family-based country mapping

### 2. Dual-Layer Architecture
- **Layer 1 (EPO):** Fast, reliable, official API
- **Layer 2 (Google):** Comprehensive, finds missing patents
- Automatic deduplication and merging

### 3. Stealth Crawling
- Playwright with anti-detection
- 14 premium proxies (ScrapingBee, Webshare, ProxyScrape)
- Human-like delays (15-20s)
- Automatic proxy rotation

### 4. Railway-Ready
- Official Playwright Docker image
- Zero configuration needed
- Auto-deploy on git push
- Health checks included

## 🎯 Current Status (Phase 1)

### ✅ Implemented
- [x] Project structure
- [x] Configuration system
- [x] Proxy management (14 proxies)
- [x] Stealth browser (Playwright)
- [x] WO Searcher (Strategy 1)
- [x] EPO Layer (placeholder)
- [x] Google Patents Layer (partial)
- [x] Orchestrator
- [x] Deduplicator
- [x] Merger
- [x] FastAPI endpoints
- [x] Railway deployment config
- [x] Documentation

### 🚧 TODO (Next Phases)
- [ ] Complete EPO layer implementation
- [ ] BR Family Extractor (Strategy 2)
- [ ] BR Direct Searcher (Strategy 3)
- [ ] Metadata extraction
- [ ] Multi-country support
- [ ] Error recovery
- [ ] Performance optimization

## 📊 Expected Performance

### Benchmark: Darolutamide
**Target (Cortellis):**
- 8 BR patents
- 7 unique WO patents

**Expected with v27:**
- 8+ BR patents (100% coverage)
- 7+ WO patents (100% coverage)
- Additional WOs found by Google layer
- Total: 30+ BRs, 200+ WOs

### Timing
- EPO Layer: 30-60s
- Google Layer: 2-5min
- **Total:** 3-6min per molecule

## 🔧 Technical Highlights

### Stealth Browser
- Playwright v1.48.0
- playwright-stealth for anti-detection
- Custom User-Agent (Chrome 134)
- Realistic viewport (1920x1080)
- Human scrolling behavior

### Proxy Strategy
- **Priority 1:** ScrapingBee (6 keys) - best for Google
- **Priority 2:** Webshare (5 keys) - residential IPs
- **Priority 3:** ProxyScrape (3 keys) - fallback
- Automatic rotation on each request
- No rate limit issues

### WO Search
- Multiple query strategies
- Year range targeting (2000-2025)
- Dev code combinations
- Regex extraction: `WO\d{4}\d{6}`
- Normalization and deduplication

## 🚀 Deployment

### Railway
```bash
# 1. Push to GitHub
git remote add origin <your-repo>
git push -u origin main

# 2. Connect to Railway
# - New Project → Deploy from GitHub
# - Select repository
# - Railway auto-detects Dockerfile

# 3. Deployed!
# URL: https://pharmyrus-v27-production.up.railway.app
```

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run locally
uvicorn main:app --reload --port 8080

# Test
curl http://localhost:8080/health
```

## 📈 Next Steps

1. **Deploy Phase 1** to Railway
2. **Test with Darolutamide** benchmark
3. **Implement Strategy 2** (BR Family Extraction)
4. **Implement Strategy 3** (BR Direct Search)
5. **Validate 100% Cortellis coverage**
6. **Optimize performance**
7. **Production ready!**

---

**Status:** Ready for Railway deployment 🚀
**Version:** v27 Phase 1
**Date:** 2024-12-26
