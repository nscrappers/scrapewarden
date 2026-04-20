# scrapewarden

> Rate-limiting and proxy rotation middleware for Python scraping frameworks like Scrapy and httpx.

---

## Installation

```bash
pip install scrapewarden
```

Or with optional Scrapy support:

```bash
pip install scrapewarden[scrapy]
```

---

## Usage

### With httpx

```python
import httpx
from scrapewarden import Warden

warden = Warden(
    proxies=["http://proxy1:8080", "http://proxy2:8080"],
    rate_limit=2.5,  # requests per second
)

with warden.client() as client:
    response = client.get("https://example.com")
    print(response.status_code)
```

### With Scrapy

Add `scrapewarden` to your Scrapy middleware settings:

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    "scrapewarden.scrapy.WardanMiddleware": 610,
}

SCRAPEWARDEN = {
    "proxies": ["http://proxy1:8080", "http://proxy2:8080"],
    "rate_limit": 2.5,
    "retry_on_block": True,
}
```

---

## Features

- 🔄 Automatic proxy rotation with configurable strategies
- ⏱️ Flexible rate limiting (global or per-domain)
- 🔁 Retry logic with backoff on blocked requests
- 🔌 Drop-in middleware for Scrapy and httpx

---

## License

This project is licensed under the [MIT License](LICENSE).