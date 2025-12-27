"""
Fallback translation using OpenAI GPT-4o-mini if Grok fails
"""

async def translate_with_openai(molecule_name: str, openai_api_key: str) -> str:
    """Fallback: OpenAI GPT-4o-mini translation"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a pharmaceutical terminology expert. Translate drug molecule names from English to Brazilian Portuguese. Return ONLY the translated name, nothing else."
                        },
                        {
                            "role": "user",
                            "content": f"Translate to Portuguese: {molecule_name}"
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 20
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                translated = data["choices"][0]["message"]["content"].strip()
                print(f"   ✅ OpenAI translated: {molecule_name} → {translated}")
                return translated
            else:
                return molecule_name
    except Exception as e:
        print(f"   ⚠️  OpenAI failed: {e}")
        return molecule_name
