# Tool: search-documents

Search across indexed documents to find relevant content.

## Parameters

| Name | Description |
|------|-------------|
| query | The search query |
| limit | How many results to return |
| filters | Filter criteria for narrowing results |
| include_content | Whether to include full document content |

## Description

This tool searches through a collection of documents and returns matching results. It supports keyword search and can filter by various criteria. Use it when you need to find information in the document store.

## Examples

### Basic search

```json
{
  "query": "quarterly revenue projections",
  "limit": 10
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "doc-4821",
      "title": "Q3 Financial Summary",
      "score": 0.87,
      "snippet": "...projected revenue growth of 12% year-over-year..."
    },
    {
      "id": "doc-1193",
      "title": "Annual Planning Document",
      "score": 0.72,
      "snippet": "...revenue targets for the upcoming fiscal quarter..."
    }
  ]
}
```

### Filtered search

```json
{
  "query": "deployment checklist",
  "limit": 5,
  "filters": {
    "category": "engineering",
    "updated_after": "2025-01-01"
  }
}
```
