# Pharmyrus v27 - Railway Deployment Guide

## 🚀 Quick Deploy (5 minutes)

### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init
git branch -M main

# Add remote (replace with your GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/pharmyrus-v27.git

# Add and commit all files
git add .
git commit -m "Pharmyrus v27: Initial deployment"

# Push to GitHub
git push -u origin main
```

### Step 2: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `pharmyrus-v27` repository
5. Railway will automatically:
   - Detect the Dockerfile
   - Build the image
   - Deploy the service
   - Assign a public URL

### Step 3: Verify Deployment

Once deployed, test the endpoints:

```bash
# Health check
curl https://your-app.up.railway.app/health

# Test search
curl -X POST https://your-app.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "nome_molecula": "aspirin",
    "paises_alvo": ["BR"]
  }'
```

---

## 📋 What Gets Deployed

### Docker Image
- **Base:** `mcr.microsoft.com/playwright/python:v1.48.0-jammy`
- **Chromium:** Pre-installed and ready
- **Size:** ~1.2GB (first build), ~100MB (rebuilds)
- **Build time:** ~3-5 minutes (first), ~30s (rebuilds)

### Environment
- **Python:** 3.11
- **Port:** 8080 (auto-configured by Railway)
- **Workers:** 1 (to avoid memory issues)
- **Memory:** ~300MB base, up to 1GB during crawling

### Proxies
All proxies are **hardcoded** from `config/proxies.py`:
- 6 ScrapingBee keys
- 5 Webshare keys
- 3 ProxyScrape keys
- **Total:** 14 premium proxies

**No environment variables needed!**

---

## 🧪 Testing After Deployment

### 1. Health Check
```bash
curl https://your-app.up.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "Pharmyrus v27",
  "total_proxies": 14,
  "supported_countries": 16
}
```

### 2. Countries List
```bash
curl https://your-app.up.railway.app/countries
```

### 3. Search Test (Quick)
```bash
curl -X POST https://your-app.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "nome_molecula": "aspirin",
    "nome_comercial": "Aspirin",
    "paises_alvo": ["BR"],
    "incluir_wo": true
  }'
```

**Note:** First search may take 3-6 minutes as it crawls Google.

### 4. Search Test (Benchmark - Darolutamide)
```bash
curl -X POST https://your-app.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "nome_molecula": "darolutamide",
    "nome_comercial": "Nubeqa",
    "paises_alvo": ["BR"],
    "incluir_wo": true
  }'
```

**Expected:** Find WO2011051540 (product patent) + 8 BR patents from Cortellis.

---

## 📊 Performance Expectations

### Layer 1: EPO OPS
- **Time:** 30-60 seconds
- **Rate limits:** None (official API)
- **Success rate:** 95%+

### Layer 2: Google Patents
- **Time:** 2-5 minutes
- **Rate limits:** Managed with 15-20s delays
- **Success rate:** 90%+ (with proxies)

### Total Per Search
- **Time:** 3-6 minutes
- **Memory:** Peak ~800MB
- **Cost:** Free tier covers ~10-20 searches/day

---

## 🐛 Troubleshooting

### Build Fails
**Problem:** Dockerfile build errors

**Solution:**
- Check Railway build logs
- Ensure Dockerfile uses official Playwright image
- Verify requirements.txt syntax

### Timeout Errors
**Problem:** Searches timing out

**Solution:**
- Google may be rate limiting
- Wait 5-10 minutes between searches
- Proxies will auto-rotate

### Empty Results
**Problem:** No WOs or BRs found

**Solution:**
- Check molecule name spelling
- Try with brand name too
- EPO layer may need API key refresh

### Memory Issues
**Problem:** Railway instance crashes

**Solution:**
- Railway Pro plan gives 8GB RAM
- Reduce workers to 1 (already configured)
- Limit concurrent searches

---

## 🔧 Configuration

### Proxies
Edit `config/proxies.py` to add/remove proxy keys.

### Countries
Add countries in `config/settings.py` → `SUPPORTED_COUNTRIES`.

### Delays
Adjust in `config/settings.py`:
- `GOOGLE_SEARCH_DELAY_MIN/MAX`
- `GOOGLE_PATENTS_DELAY_MIN/MAX`

---

## 📈 Monitoring

### Railway Dashboard
- View real-time logs
- Monitor memory/CPU usage
- Check request counts

### Health Endpoint
Call `/health` to verify service status.

### Logs
Railway automatically captures all logs. Check for:
- `✅` Success indicators
- `❌` Error messages
- `⚠️` Warnings

---

## 🚨 Important Notes

1. **First search is slow** (3-6 min) - this is normal
2. **Proxies rotate automatically** - no manual intervention
3. **Railway auto-deploys** on git push
4. **Free tier limits:** ~100 hours/month
5. **Pro tier recommended** for production use

---

## 📞 Support

If issues persist:
1. Check Railway build logs
2. Verify proxy keys are valid
3. Test locally with Docker first
4. Check GitHub repository for updates

---

**Ready to deploy?** Run `./deploy.sh` to start! 🚀
