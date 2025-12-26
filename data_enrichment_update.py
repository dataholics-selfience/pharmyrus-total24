    async def run_all_enrichment(self, client: httpx.AsyncClient, molecule: str, brand: str = None) -> Dict:
        """
        Executa TODAS as fontes de enriquecimento em paralelo
        Incluindo: PubChem, OpenFDA, PubMed, FDA Orange Book
        """
        logger.info(f"🔍 ENRICHMENT: Starting comprehensive data extraction for {molecule}")
        
        # Executar em paralelo para velocidade
        await asyncio.gather(
            self.enrich_from_pubchem(client, molecule),
            self.enrich_from_openfda(client, molecule, brand),
            self.enrich_from_pubmed(client, molecule),
            self.enrich_from_fda_orangebook(client, molecule, brand),
            # drugbank comentado por ora (requer autenticação)
            # self.enrich_from_drugbank(client, molecule),
            return_exceptions=True
        )
        
        # Converter sets para lists
        result = {
            "synonyms": list(self.enriched_data["synonyms"])[:50],  # Top 50
            "dev_codes": list(self.enriched_data["dev_codes"])[:20],  # Top 20
            "cas_numbers": list(self.enriched_data["cas_numbers"]),
            "companies": list(self.enriched_data["companies"])[:30],  # Top 30
            "therapeutic_terms": list(self.enriched_data["therapeutic_terms"]),
            "chemical_formulas": list(self.enriched_data["chemical_formulas"]),
            "inchi": list(self.enriched_data["inchi"])[:5],
            "smiles": list(self.enriched_data["smiles"])[:5],
        }
        
        logger.info(f"✅ ENRICHMENT COMPLETE:")
        logger.info(f"   - Synonyms: {len(result['synonyms'])}")
        logger.info(f"   - Dev codes: {len(result['dev_codes'])}")
        logger.info(f"   - CAS numbers: {len(result['cas_numbers'])}")
        logger.info(f"   - Companies: {len(result['companies'])}")
        logger.info(f"   - Chemical data: {len(result['chemical_formulas'])} formulas, {len(result['inchi'])} InChI, {len(result['smiles'])} SMILES")
        
        return result
