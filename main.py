"""
Pharmyrus v27 - Multi-Source Patent Search API
FastAPI application with EPO OPS + Google Patents crawling.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from orchestrator import PharmyrusOrchestrator
from config.settings import VERSION, SUPPORTED_COUNTRIES
from config.proxies import ProxyManager


# Pydantic models
class SearchRequest(BaseModel):
    nome_molecula: str = Field(..., description="Molecule name")
    nome_comercial: Optional[str] = Field(None, description="Brand name")
    paises_alvo: List[str] = Field(default=["BR"], description="Target countries")
    incluir_wo: bool = Field(default=True, description="Include WO patents")
    max_results: int = Field(default=200, description="Max results")


class HealthResponse(BaseModel):
    status: str
    version: str
    total_proxies: int
    supported_countries: int


# FastAPI app
app = FastAPI(
    title="Pharmyrus v27",
    description="Multi-source pharmaceutical patent search API",
    version="27.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = PharmyrusOrchestrator()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Pharmyrus v27 - Multi-Source Patent Search API",
        "version": VERSION,
        "endpoints": {
            "search": "POST /search",
            "health": "GET /health",
            "countries": "GET /countries"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint."""
    proxy_manager = ProxyManager()
    
    return HealthResponse(
        status="healthy",
        version=VERSION,
        total_proxies=proxy_manager.get_total_proxies(),
        supported_countries=len(SUPPORTED_COUNTRIES)
    )


@app.get("/countries", tags=["Info"])
async def get_countries():
    """Get list of supported countries."""
    return {
        "supported_countries": SUPPORTED_COUNTRIES,
        "total": len(SUPPORTED_COUNTRIES)
    }


@app.post("/search", tags=["Search"])
async def search_patents(request: SearchRequest):
    """
    Search for pharmaceutical patents.
    
    Combines EPO OPS (fast) + Google Patents (comprehensive) for maximum coverage.
    """
    try:
        # Validate countries
        invalid_countries = [
            c for c in request.paises_alvo
            if c not in SUPPORTED_COUNTRIES
        ]
        
        if invalid_countries:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid countries: {', '.join(invalid_countries)}"
            )
        
        # Execute search
        results = await orchestrator.search(
            molecule_name=request.nome_molecula,
            brand_name=request.nome_comercial,
            target_countries=request.paises_alvo
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )
