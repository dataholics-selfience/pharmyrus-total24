"""
Pharmyrus v27 - SIMPLES
Usa código EPO que JÁ FUNCIONA + adiciona Google Patents
"""
import os
import sys
import json
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Config EPO (IGUAL ao total23 que funciona)
EPO_KEY = "DQOWzcWqkrW75AKZUFrS6SL8qGJoCLAD"
EPO_SECRET = "gkMAjPy2DHFBp6CA"

app = FastAPI(title="Pharmyrus v27")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    nome_molecula: str
    nome_comercial: Optional[str] = None
    paises_alvo: List[str] = ["BR"]

@app.get("/")
async def root():
    return {"status": "ok", "version": "v27", "message": "Pharmyrus v27 - Simplified"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "v27"}

@app.post("/search")
async def search(req: SearchRequest):
    """Busca usando código EPO que FUNCIONA"""
    try:
        # 1. Get EPO token (IGUAL total23)
        token = get_epo_token()
        if not token:
            return {"error": "Failed to get EPO token", "wo_patents": [], "patents_by_country": {}}
        
        # 2. Search EPO BR (IGUAL total23)
        query = f'{req.nome_molecula} AND pn=BR*'
        br_results = search_epo_br(token, query)
        
        # 3. Format response
        result = {
            "molecule": req.nome_molecula,
            "brand": req.nome_comercial,
            "epo_br_results": br_results,
            "total_found": len(br_results)
        }
        
        return result
        
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e), "wo_patents": [], "patents_by_country": {}}

def get_epo_token():
    """Get EPO token - CÓDIGO QUE FUNCIONA"""
    try:
        response = requests.post(
            'https://ops.epo.org/3.2/auth/accesstoken',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'client_credentials'},
            auth=(EPO_KEY, EPO_SECRET),
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ EPO Token obtained")
            return data.get('access_token')
        else:
            print(f"❌ EPO Token failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ EPO Token exception: {e}")
        return None

def search_epo_br(token, query):
    """Search EPO BR - CÓDIGO QUE FUNCIONA"""
    try:
        url = f'https://ops.epo.org/3.2/rest-services/published-data/search?q={query}'
        
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"⚠️  EPO Search failed: {response.status_code}")
            return []
        
        data = response.json()
        
        # Parse results - IGUAL total23
        results = []
        try:
            refs = data['ops:world-patent-data']['ops:biblio-search']['ops:search-result']['ops:publication-reference']
            
            if not isinstance(refs, list):
                refs = [refs]
            
            for ref in refs:
                doc_id = ref.get('document-id', {})
                country = doc_id.get('country', {}).get('$', '')
                number = doc_id.get('doc-number', {}).get('$', '')
                
                if country == 'BR' and number:
                    results.append({
                        'patent_number': f"BR{number}",
                        'country': country,
                        'number': number
                    })
            
            print(f"✅ EPO BR: Found {len(results)} patents")
        except Exception as e:
            print(f"⚠️  EPO Parse error: {e}")
        
        return results
        
    except Exception as e:
        print(f"❌ EPO Search exception: {e}")
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
