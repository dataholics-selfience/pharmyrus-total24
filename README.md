# Pharmyrus v27 - Multi-Source Patent Search API

API for pharmaceutical patent search combining EPO OPS + Google Patents crawling.

## Features

- **Layer 1: EPO OPS** - Fast official API search
- **Layer 2: Google Patents** - Comprehensive web crawling with Playwright
- **Multi-country support** - BR, US, JP, EP, CN, and 15+ countries
- **Stealth crawling** - Anti-detection with proxy rotation
- **Automatic WO discovery** - Finds WO patents from molecule name alone
- **BR/Country mapping** - Maps WOs to target countries automatically

## Architecture

```
EPO OPS (fast) → Google Patents (comprehensive) → Deduplicate → Final Results
```

## Quick Deploy to Railway

1. Clone this repo
2. Push to GitHub
3. Connect to Railway
4. Deploy!

No environment variables needed - proxies hardcoded for immediate use.

## API Endpoints

### POST /search
Search patents for a molecule in multiple countries.

**Request:**
```json
{
  "nome_molecula": "darolutamide",
  "nome_comercial": "Nubeqa",
  "paises_alvo": ["BR", "US", "JP"],
  "incluir_wo": true,
  "max_results": 200
}
```

**Response:**
```json
{
  "metadata": {
    "molecule": "darolutamide",
    "version": "Pharmyrus v27",
    "elapsed_seconds": 180.5
  },
  "summary": {
    "total_wos": 185,
    "total_patents": 45,
    "by_country": {"BR": 25, "US": 12, "JP": 8}
  },
  "wo_patents": ["WO2011051540", ...],
  "patents_by_country": {...}
}
```

### GET /health
Health check endpoint.

## Development

```bash
# Local test
uvicorn main:app --reload --port 8080

# Test search
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{"nome_molecula": "aspirin", "paises_alvo": ["BR"]}'
```

## Performance

- EPO Layer: ~30-60 seconds
- Google Patents Layer: ~2-5 minutes
- Total: ~3-6 minutes per molecule

## Version History

- v27: Added Google Patents crawling layer
- v26: EPO OPS only (baseline)
