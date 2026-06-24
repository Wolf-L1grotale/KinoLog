import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
        # Try mobile API or different endpoint
        tests = [
            'https://kinorium.com/api/movie/116780/',
            'https://kinorium.com/handlers/movie?id=116780',
            'https://m.kinorium.com/116780/',
        ]
        for url in tests:
            try:
                r = await c.get(url, headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36', 'Accept': 'application/json, text/html'})
                text = r.content.decode('utf-8', errors='replace')
                print(f'{url}: {r.status_code} len={len(text)}')
                if len(text) < 2000:
                    print(f'  Content: {text[:500]}')
                else:
                    # Check if it has actual content
                    has_title = 'Matrix' in text or 'Матрица' in text or 'matrix' in text.lower()
                    print(f'  Has film data: {has_title}')
                    # Save first one to file
                    if len(text) > 5000:
                        with open('test_mobile.txt', 'w', encoding='utf-8') as f:
                            f.write(text[:20000])
            except Exception as e:
                print(f'{url}: ERROR {e}')

asyncio.run(test())
