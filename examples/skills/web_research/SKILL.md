# Web Research

Conduct comprehensive web research and gather information from online sources.

## Overview

This skill enables effective web research through:
- Search engine queries (Google, Bing, DuckDuckGo)
- Web scraping and content extraction
- Dynamic content handling (JavaScript-rendered pages)
- Multi-source information synthesis
- Citation and source tracking

## Usage

### Search Engine Queries

```python
import requests
from bs4 import BeautifulSoup

def google_search(query: str, num_results: int = 10) -> list:
    """Perform Google search and return results"""
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    for g in soup.find_all('div', class_='g'):
        title = g.find('h3')
        link = g.find('a')
        if title and link:
            results.append({
                'title': title.get_text(),
                'link': link.get('href')
            })
    return results
```

### Web Scraping

```python
def scrape_article(url: str) -> dict:
    """Extract article content from URL"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract main content
    article = soup.find('article') or soup.find('main')

    return {
        'title': soup.find('h1').get_text() if soup.find('h1') else '',
        'content': article.get_text() if article else '',
        'url': url
    }
```

### Dynamic Content (Selenium)

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_dynamic_page(url: str) -> str:
    """Scrape JavaScript-rendered content"""
    driver = webdriver.Chrome()
    driver.get(url)

    # Wait for content to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "content"))
    )

    content = driver.find_element(By.CLASS_NAME, "content").text
    driver.quit()

    return content
```

### Multi-Source Research

```python
def research_topic(topic: str, num_sources: int = 5) -> dict:
    """Research a topic from multiple sources"""
    # 1. Search for sources
    search_results = google_search(topic, num_sources)

    # 2. Extract content from each source
    sources = []
    for result in search_results:
        try:
            content = scrape_article(result['link'])
            sources.append(content)
        except Exception as e:
            print(f"Failed to scrape {result['link']}: {e}")

    # 3. Synthesize information
    return {
        'topic': topic,
        'num_sources': len(sources),
        'sources': sources
    }
```

## Examples

See `resources/search_templates.json` for effective search query patterns.

## Dependencies

- requests: `pip install requests`
- beautifulsoup4: `pip install beautifulsoup4`
- selenium: `pip install selenium` (for dynamic content)
- Optional: `playwright` for modern browser automation

## Notes

- Always respect robots.txt and website terms of service
- Add rate limiting to avoid overwhelming servers
- Use appropriate User-Agent headers
- Consider using proxies for large-scale scraping
- Cache results to minimize redundant requests
- Validate and sanitize scraped data before use
