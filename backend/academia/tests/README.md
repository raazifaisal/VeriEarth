# Performance Benchmark Tests

This directory contains performance benchmarking tests for the VeriEarth API.

## Running the Benchmark

### Prerequisites

1. Ensure the backend is running:
   ```bash
   docker compose up -d backend
   ```

2. Ensure Redis is running (for cache hit tests):
   ```bash
   docker compose up -d redis
   ```

3. Install test dependencies:
   ```bash
   pip install requests
   ```

### Running the Benchmark

```bash
# From backend directory
python3 tests/performance_benchmark.py

# Or with custom configuration
API_BASE_URL=http://localhost:8000 \
TEST_ORG_ID=ecfc141e-2e55-4670-bb8e-9e8813b02866 \
python3 tests/performance_benchmark.py
```

### Output

Results are saved to `tests/performance_results.json` with detailed timing information for:

- **Data Ingestion**: Facilities, routes, shipments import times
- **EO Backfill**: Environmental data enrichment times
- **KG Sync**: Neo4j knowledge graph synchronization times
- **KG Analytics**: All graph analytics operations (betweenness, pagerank, communities, shortest path, EO hotspots)
- **PrefixSpan**: Frequent pattern mining times
- **Cache Performance**: Cache miss vs cache hit comparisons with speedup metrics

### JSON Structure

The output JSON includes:

- **Metadata**: Test configuration and timestamp
- **Timings**: Individual response times for each endpoint
- **Cache Analysis**: Cache miss (first call) vs cache hit (subsequent calls) comparison
- **Summary**: Aggregated statistics including average speedup

### For Research Papers

The JSON output can be directly used in research papers to:
- Compare cache miss vs cache hit performance
- Document response time improvements from caching
- Analyze endpoint performance characteristics
- Generate performance charts and tables

