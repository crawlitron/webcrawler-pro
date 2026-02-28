# API Reference - WebCrawler Pro

Base URL: `https://example.com/api` (production) | `http://localhost:8000` (local)

Interactive Swagger UI: `/api/docs` | ReDoc: `/api/redoc`

---

## Authentication

Currently the API is open (no auth required for self-hosted). Production deployments should be
protected by Traefik BasicAuth middleware or an API key header.

---

## Projects

### `GET /api/projects`
List all projects.

**Response 200:**
```json
[
  {
    "id": 1,
    "name": "My Website",
    "start_url": "https://example.com",
    "max_urls": 500,
    "last_crawl_status": "completed",
    "last_crawl_id": 3,
    "created_at": "2026-02-28T10:00:00Z"
  }
]
```

### `POST /api/projects`
Create a new project.

**Request body:**
```json
{
  "name": "My Website",
  "start_url": "https://example.com",
  "max_urls": 500
}
```

**Response 201:** Project object (see GET /api/projects)

### `GET /api/projects/{id}`
Get a single project by ID.

### `PUT /api/projects/{id}`
Update project name, start_url, or max_urls.

### `DELETE /api/projects/{id}`
Delete project and all associated crawl data.

---

## Crawls

### `POST /api/projects/{id}/crawls`
Start a new crawl for a project.

**Response 201:**
```json
{
  "id": 5,
  "project_id": 1,
  "status": "pending",
  "celery_task_id": "abc123-...",
  "total_urls": 0,
  "crawled_urls": 0,
  "failed_urls": 0,
  "critical_issues": 0,
  "warning_issues": 0,
  "info_issues": 0,
  "created_at": "2026-02-28T12:00:00Z"
}
```

### `GET /api/crawls/{id}`
Get crawl status and statistics. Poll this endpoint for real-time progress.

**Crawl statuses:** `pending` | `running` | `completed` | `failed` | `cancelled`

### `GET /api/projects/{id}/crawls`
List all crawls for a project (newest first).

### `POST /api/crawls/{id}/cancel`
Cancel a running crawl.

**Response 200:**
```json
{"message": "Crawl cancellation requested"}
```

---

## Pages

### `GET /api/crawls/{id}/pages`
List crawled pages with filtering and pagination.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 50, max: 200) |
| `status_code` | int | Filter by HTTP status code |
| `issue_type` | string | Filter pages with specific issue type |
| `search` | string | Search URL or title |

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "url": "https://example.com/page",
      "status_code": 200,
      "title": "Page Title",
      "meta_description": "Page description",
      "h1": "Main Heading",
      "word_count": 542,
      "response_time": 0.234,
      "internal_links_count": 12,
      "external_links_count": 3,
      "images_without_alt": 1,
      "is_indexable": true,
      "depth": 2,
      "issue_count": 2
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

---

## Issues

### `GET /api/crawls/{id}/issues`
List all SEO issues found during the crawl.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `severity` | string | `critical` / `warning` / `info` |
| `issue_type` | string | Filter by issue type slug |
| `page` | int | Page number |
| `page_size` | int | Items per page |

**Issue severity levels:**

| Severity | Color | Examples |
|----------|-------|---------|
| `critical` | Red | Missing title, broken links (5xx), duplicate titles |
| `warning` | Yellow | Short meta description, thin content (<300 words), missing OG tags |
| `info` | Blue | Schema.org present, Twitter Cards, keyword density |

**Common issue types:**

| Issue Type | Severity | Description |
|------------|----------|-------------|
| `missing_title` | critical | Page has no `<title>` tag |
| `duplicate_title` | critical | Same title on multiple pages |
| `missing_meta_description` | warning | No meta description |
| `missing_h1` | warning | No H1 heading |
| `duplicate_h1` | warning | Multiple H1 tags |
| `thin_content` | warning | Word count < 300 |
| `broken_link` | critical | HTTP 4xx/5xx response |
| `missing_alt` | warning | Images without alt text |
| `noindex` | info | Page has noindex meta tag |
| `missing_og_tags` | warning | Missing Open Graph tags |
| `has_schema_org` | info | Structured data detected |
| `slow_page` | warning | Response time > 3 seconds |
| `url_too_long` | warning | URL length > 100 characters |
| `url_has_special_chars` | warning | Uppercase, spaces, or special chars in URL |

---

## Analytics

### `GET /api/crawls/{id}/analytics/overview`
Returns comprehensive analytics summary for the crawl.

**Response 200:**
```json
{
  "crawl_id": 5,
  "status": "completed",
  "total_pages": 248,
  "crawled_urls": 241,
  "failed_urls": 7,
  "critical_issues": 12,
  "warning_issues": 34,
  "info_issues": 89,
  "total_issues": 135,
  "avg_response_time_ms": 387,
  "avg_word_count": 612,
  "indexable_pages": 235,
  "noindex_pages": 6,
  "slow_pages": 3,
  "images_missing_alt": 18,
  "total_internal_links": 1842,
  "total_external_links": 203,
  "status_distribution": {
    "2xx": 235,
    "3xx": 6,
    "4xx": 5,
    "5xx": 2
  }
}
```

### `GET /api/crawls/{id}/analytics/top-issues?limit=10`
Returns top N most frequent issues sorted by count.

**Response 200:**
```json
[
  {
    "issue_type": "missing_meta_description",
    "severity": "warning",
    "count": 45,
    "label": "Missing Meta Description"
  }
]
```

### `GET /api/crawls/{id}/analytics/response-times`
Response time distribution histogram with percentiles.

**Response 200:**
```json
{
  "avg": 0.387,
  "p50": 0.312,
  "p90": 0.891,
  "p95": 1.234,
  "buckets": [
    {"range": "0-200ms", "count": 87},
    {"range": "200-500ms", "count": 112},
    {"range": "500ms-1s", "count": 31},
    {"range": "1s-2s", "count": 8},
    {"range": ">2s", "count": 3}
  ]
}
```

### `GET /api/crawls/{id}/analytics/issues-by-type`
Issues grouped and counted by type and severity.

### `GET /api/crawls/{id}/analytics/status-distribution`
HTTP status code distribution across all crawled URLs.

---

## Links

### `GET /api/crawls/{id}/links`
List all links found during the crawl.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `link_type` | string | `internal` or `external` |
| `nofollow` | bool | Filter nofollow links |
| `page` | int | Page number |
| `page_size` | int | Items per page (default: 50) |

**Response 200:**
```json
{
  "items": [
    {
      "source_url": "https://example.com/page",
      "target_url": "https://example.com/other",
      "anchor_text": "Learn more",
      "link_type": "internal",
      "nofollow": false,
      "status_code": 200
    }
  ],
  "total": 1842,
  "page": 1,
  "page_size": 50,
  "total_pages": 37
}
```

---

## Exports

### `GET /api/crawls/{id}/export/csv`
Download crawl results as CSV file.

### `GET /api/crawls/{id}/export/json`
Download crawl results as JSON file.

### `GET /api/crawls/{id}/export/sitemap`
Generate and download sitemap.xml from crawled indexable URLs.

**Response headers:**
```
Content-Type: application/xml
Content-Disposition: attachment; filename=sitemap.xml
```

**Sample response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2026-02-28</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

---

## Sitemap (via Analytics)

### `GET /api/crawls/{id}/sitemap`
Alternative endpoint returning sitemap.xml (same as export/sitemap).

---

## Error Responses

All errors return a JSON body:

```json
{
  "detail": "Project not found"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request - invalid input |
| 404 | Not Found - resource does not exist |
| 409 | Conflict - crawl already running |
| 422 | Unprocessable Entity - validation error |
| 500 | Internal Server Error |

---

## SDK / Code Examples

### Python

```python
import httpx, time

BASE = 'http://localhost:8000'

# Create project
project = httpx.post(f'{BASE}/api/projects', json={
    'name': 'My Site', 'start_url': 'https://example.com', 'max_urls': 500
}).json()

# Start crawl
crawl = httpx.post(f'{BASE}/api/projects/{project["id"]}/crawls').json()

# Poll until complete
while crawl['status'] not in ('completed', 'failed', 'cancelled'):
    time.sleep(5)
    crawl = httpx.get(f'{BASE}/api/crawls/{crawl["id"]}').json()
    print(f'Progress: {crawl["crawled_urls"]}/{crawl["total_urls"]}')

# Get analytics
overview = httpx.get(f'{BASE}/api/crawls/{crawl["id"]}/analytics/overview').json()
print(f'Issues: {overview["critical_issues"]} critical, {overview["warning_issues"]} warnings')
```

### curl

```bash
# List projects
curl https://example.com/api/projects

# Start crawl
curl -X POST https://example.com/api/projects/1/crawls

# Get crawl status
curl https://example.com/api/crawls/5

# Download sitemap
curl -o sitemap.xml https://example.com/api/crawls/5/export/sitemap

# Download JSON export
curl -o results.json https://example.com/api/crawls/5/export/json
```
