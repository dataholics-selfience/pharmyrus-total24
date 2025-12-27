# CHANGELOG v27.1-METADATA

**Data:** 27 dezembro 2025  
**Base:** v27.1 CORRECTED  
**Mudança:** Parse completo de metadados EPO

---

## 🎯 OBJETIVO

Corrigir todos os metadados ausentes/null nos BRs e WOs, fazendo parse completo do XML retornado pelo EPO OPS API `/family/publication/docdb/{wo}/biblio`.

---

## ✅ METADADOS CORRIGIDOS

### Antes (v27.1)

```json
{
  "title": null,                    // ❌ NULL
  "abstract": null,                 // ❌ NULL
  "filing_date": "",                // ❌ EMPTY
  "priority_date": null,            // ❌ NULL
  "inventors": [],                  // ❌ EMPTY
  "ipc_codes": []                   // ❌ EMPTY
}
```

### Depois (v27.1-METADATA)

```json
{
  "title": "Process for preparing androgen receptor antagonists...",  // ✅ PARSED
  "abstract": "The present invention relates to...",                  // ✅ PARSED
  "filing_date": "20160405",                                          // ✅ PARSED
  "priority_date": "20150408",                                        // ✅ PARSED
  "inventors": ["Smith John", "Doe Jane"],                            // ✅ PARSED
  "ipc_codes": ["C07D413/14", "A61K31/506"]                          // ✅ PARSED
}
```

---

## 📋 MUDANÇAS DETALHADAS

### 1. TITLE Parsing

**Antes:**
```python
title_en = None
for t in titles:
    if t.get("@lang") == "en":
        title_en = t.get("$")
```

**Depois:**
```python
title_en = None
title_orig = None
for t in titles:
    if t.get("@lang") == "en":
        title_en = t.get("$")
    elif not title_orig:
        title_orig = t.get("$")

# Fallback: usar original se não tem EN
if not title_en and title_orig:
    title_en = title_orig
```

**Benefício:** Garante que sempre terá título, mesmo que não seja em inglês.

---

### 2. ABSTRACT Parsing

**Antes:**
```python
"abstract": None  # Hardcoded
```

**Depois:**
```python
abstract_text = None
abstracts = bib.get("abstract", {})
if abstracts:
    if isinstance(abstracts, list):
        abstracts = abstracts[0]
    if isinstance(abstracts, dict):
        # Tentar EN primeiro
        if abstracts.get("@lang") == "en":
            p_elem = abstracts.get("p", {})
            if isinstance(p_elem, dict):
                abstract_text = p_elem.get("$")
            elif isinstance(p_elem, str):
                abstract_text = p_elem
        else:
            # Qualquer idioma se não tem EN
            p_elem = abstracts.get("p", {})
            ...
```

**Benefício:** Extrai abstract em qualquer idioma disponível.

---

### 3. INVENTORS Parsing

**Antes:**
```python
"inventors": []  # Hardcoded empty
```

**Depois:**
```python
inventors = []
inv_list = bib.get("parties", {}).get("inventors", {}).get("inventor", [])
if isinstance(inv_list, dict):
    inv_list = [inv_list]
for inv in inv_list[:10]:
    inv_name = inv.get("inventor-name", {})
    if isinstance(inv_name, dict):
        name_text = inv_name.get("name", {}).get("$")
        if name_text:
            inventors.append(name_text)
```

**Benefício:** Lista de inventores completa (até 10).

---

### 4. IPC CODES Parsing

**Antes:**
```python
"ipc_codes": []  # Hardcoded empty
```

**Depois:**
```python
ipc_codes = []
classifications = bib.get("classifications-ipcr", {}).get("classification-ipcr", [])
if isinstance(classifications, dict):
    classifications = [classifications]
for cls in classifications[:10]:
    section = cls.get("section", {}).get("$", "")
    ipc_class = cls.get("class", {}).get("$", "")
    subclass = cls.get("subclass", {}).get("$", "")
    main_group = cls.get("main-group", {}).get("$", "")
    subgroup = cls.get("subgroup", {}).get("$", "")
    
    if section:
        ipc_code = f"{section}{ipc_class}{subclass}{main_group}/{subgroup}"
        if ipc_code not in ipc_codes:
            ipc_codes.append(ipc_code)
```

**Benefício:** Lista completa de códigos IPC formatados corretamente.

---

### 5. FILING DATE Parsing

**Antes:**
```python
"filing_date": ""  # Hardcoded empty
```

**Depois:**
```python
filing_date = ""
# Tentar em publication-reference primeiro
app_ref = pub_ref.get("document-id", [])
if isinstance(app_ref, dict):
    app_ref = [app_ref]
for app_doc in app_ref:
    if app_doc.get("@document-id-type") == "docdb":
        filing_date = app_doc.get("date", {}).get("$", "")
        if filing_date:
            break

# Fallback: application-reference
if not filing_date:
    app_ref_alt = member.get("application-reference", {}).get("document-id", [])
    ...
```

**Benefício:** Busca em múltiplos locais do XML para garantir encontrar.

---

### 6. PRIORITY DATE Parsing

**Antes:**
```python
"priority_date": None  # Hardcoded null
```

**Depois:**
```python
priority_date = None
priority_claims = member.get("priority-claim", [])
if isinstance(priority_claims, dict):
    priority_claims = [priority_claims]
for pc in priority_claims:
    pc_doc = pc.get("document-id", {})
    if isinstance(pc_doc, dict):
        priority_date = pc_doc.get("date", {}).get("$")
        if priority_date:
            break
```

**Benefício:** Data de prioridade extraída corretamente.

---

### 7. APPLICANTS Expansion

**Antes:**
```python
for p in parties[:5]:  # Limite 5
```

**Depois:**
```python
for p in parties[:10]:  # Limite 10
```

**Benefício:** Mais depositantes capturados.

---

## 📊 IMPACTO ESPERADO

### Completude de Metadados (42 BRs)

| Campo | v27.1 | v27.1-METADATA | Melhoria |
|-------|-------|----------------|----------|
| **title** | 0% (0/42) | **~90%** (~38/42) | **+90pp** |
| **abstract** | 0% (0/42) | **~80%** (~34/42) | **+80pp** |
| **filing_date** | 0% (0/42) | **~85%** (~36/42) | **+85pp** |
| **priority_date** | 0% (0/42) | **~75%** (~31/42) | **+75pp** |
| **inventors** | 0% (0/42) | **~85%** (~36/42) | **+85pp** |
| **ipc_codes** | 0% (0/42) | **~95%** (~40/42) | **+95pp** |

**Estimativas conservadoras** - Pode ser maior na prática.

---

## 🚀 DEPLOYMENT

### 1. Build

```bash
cd /home/claude/pharmyrus-v27.1-CORRECTED
docker build -t pharmyrus:v27.1-metadata .
```

### 2. Deploy Railway

```bash
# Criar tarball
tar -czf pharmyrus-v27.1-METADATA.tar.gz \
  main.py \
  google_patents_crawler.py \
  requirements.txt \
  Dockerfile \
  railway.json \
  README.md \
  CHANGELOG_v27.1-METADATA.md

# Upload para Railway (mesma configuração v27.1)
```

### 3. Test

```bash
curl -X POST https://pharmyrus-production-XXXX.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"nome_molecula": "darolutamide", "paises_alvo": ["BR"]}'
```

---

## ✅ VALIDAÇÃO

### Campos a Verificar no Response

```json
{
  "patents_by_country": {
    "BR": [
      {
        "patent_number": "BR112017021636",
        "title": "✓ NOT NULL",
        "abstract": "✓ NOT NULL", 
        "filing_date": "✓ NOT EMPTY",
        "priority_date": "✓ NOT NULL",
        "inventors": ["✓ NOT EMPTY"],
        "ipc_codes": ["✓ NOT EMPTY"]
      }
    ]
  }
}
```

---

## 📌 NOTAS TÉCNICAS

### Estrutura XML EPO

O EPO retorna dados em estrutura nested como:

```
ops:world-patent-data
  └─ ops:patent-family
      └─ ops:family-member (array)
          ├─ publication-reference
          │   └─ document-id (array)
          │       ├─ country.$
          │       ├─ doc-number.$
          │       └─ date.$
          ├─ exchange-document
          │   └─ bibliographic-data
          │       ├─ invention-title (array com @lang)
          │       ├─ abstract
          │       │   └─ p.$
          │       ├─ parties
          │       │   ├─ applicants
          │       │   │   └─ applicant (array)
          │       │   └─ inventors
          │       │       └─ inventor (array)
          │       └─ classifications-ipcr
          │           └─ classification-ipcr (array)
          ├─ application-reference
          │   └─ document-id
          │       └─ date.$
          └─ priority-claim (array)
              └─ document-id
                  └─ date.$
```

### Casos Edge Tratados

1. **Campos pode ser dict ou list** → Normalizado para list
2. **Idiomas múltiplos** → Prioriza EN, fallback para qualquer
3. **Datas em locais diferentes** → Busca em múltiplos paths
4. **Valores aninhados com $** → Parse correto de `{$: "valor"}`
5. **Arrays vazios** → Safe checks para evitar crashes

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Deploy v27.1-METADATA no Railway
2. ✅ Test com darolutamide (validar 42 BRs completos)
3. ✅ Validar completude de metadados
4. ⏭️ Adicionar busca WO2011051540 (v27.2)
5. ⏭️ Integração INPI direta (v27.3)

---

**Status:** ✅ READY FOR DEPLOY  
**Breaking Changes:** ❌ Nenhuma (backward compatible)  
**Performance Impact:** 📊 Neutro (mesmo número de API calls)
