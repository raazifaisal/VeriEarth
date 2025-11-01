#!/usr/bin/env python3
"""
Performance benchmark test suite for VeriEarth API endpoints.
Measures response times for data ingestion, EO backfill, KG sync, analytics operations, and PrefixSpan.
Tests both cache misses (first call) and cache hits (subsequent calls).

Output: JSON file with detailed timing results for research paper inclusion.
"""

import time
import json
import requests
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ORG_ID = "e02777c6-8055-428c-bb68-ed5e5b8f24ac"  # Raazi Faisal's Organization
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data_small"
OUTPUT_FILE = Path(__file__).parent / "performance_results.json"

# Test configuration
RUNS_PER_ENDPOINT = 3  # Number of runs to average (first is cache miss, rest are cache hits)


class PerformanceBenchmark:
    """Benchmark suite for API response time measurement."""
    
    def __init__(self, base_url: str, org_id: str):
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.csrf_token = None
        self.results: Dict[str, Any] = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "base_url": base_url,
                "org_id": org_id,
                "test_config": {
                    "runs_per_endpoint": RUNS_PER_ENDPOINT,
                    "cache_testing": True
                }
            },
            "data_ingestion": {},
            "eo_backfill": {},
            "kg_sync": {},
            "kg_analytics": {},
            "prefixspan": {},
            "summary": {}
        }
        # Get CSRF token
        self._get_csrf_token()
    
    def _get_csrf_token(self) -> None:
        """Fetch CSRF token from the API."""
        try:
            response = requests.get(f"{self.base_url}/csrf-token", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.csrf_token = data.get("csrf_token")
                print(f"✓ CSRF token obtained")
            else:
                print(f"⚠ Failed to get CSRF token: {response.status_code}")
        except Exception as e:
            print(f"⚠ Failed to get CSRF token: {e}")
    
    def measure_endpoint(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Measure response time for an API endpoint.
        Returns dict with timing, status, and cache status.
        """
        url = f"{self.base_url}{endpoint}"
        label = label or endpoint
        
        timings = []
        status_codes = []
        cache_statuses = []
        
        # Add CSRF token to headers for POST requests
        if method.upper() == "POST" and self.csrf_token:
            if headers is None:
                headers = {}
            headers["X-CSRF-Token"] = self.csrf_token
        
        for run in range(RUNS_PER_ENDPOINT):
            start_time = time.perf_counter()
            
            try:
                if method.upper() == "GET":
                    response = requests.get(url, params=params, headers=headers, timeout=300)
                elif method.upper() == "POST":
                    # Handle multipart form data (for file uploads)
                    if files and data:
                        response = requests.post(url, params=params, files=files, data=data, headers=headers, timeout=300)
                    elif files:
                        response = requests.post(url, params=params, files=files, headers=headers, timeout=300)
                    elif data:
                        # Check if data is form data (tuple format) or JSON
                        if isinstance(data, dict) and any(isinstance(v, tuple) for v in data.values()):
                            response = requests.post(url, params=params, data=data, headers=headers, timeout=300)
                        else:
                            response = requests.post(url, params=params, json=data, headers=headers, timeout=300)
                    else:
                        response = requests.post(url, params=params, headers=headers, timeout=300)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                elapsed = time.perf_counter() - start_time
                timings.append(elapsed * 1000)  # Convert to milliseconds
                status_codes.append(response.status_code)
                
                # Detect cache hit (faster response, typically <100ms for cache hits vs >1000ms for misses)
                # First run is typically cache miss, subsequent are cache hits
                is_cache_hit = run > 0 and elapsed < 0.5  # If <500ms, likely cached
                cache_statuses.append("cache_hit" if is_cache_hit else "cache_miss")
                
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                timings.append(elapsed * 1000)
                status_codes.append(0)
                cache_statuses.append("error")
                print(f"  ⚠ Run {run+1} failed: {e}")
        
        avg_time = sum(timings) / len(timings)
        cache_miss_time = timings[0] if len(timings) > 0 else None
        cache_hit_times = [t for i, t in enumerate(timings) if i > 0]
        cache_hit_avg = sum(cache_hit_times) / len(cache_hit_times) if cache_hit_times else None
        
        return {
            "label": label,
            "endpoint": endpoint,
            "method": method,
            "runs": RUNS_PER_ENDPOINT,
            "timings_ms": timings,
            "avg_response_time_ms": round(avg_time, 2),
            "cache_miss_time_ms": round(cache_miss_time, 2) if cache_miss_time else None,
            "cache_hit_times_ms": [round(t, 2) for t in cache_hit_times],
            "cache_hit_avg_ms": round(cache_hit_avg, 2) if cache_hit_avg else None,
            "speedup": round(cache_miss_time / cache_hit_avg, 2) if cache_miss_time and cache_hit_avg else None,
            "status_codes": status_codes,
            "cache_statuses": cache_statuses,
            "success_rate": sum(1 for sc in status_codes if 200 <= sc < 300) / len(status_codes) if status_codes else 0
        }
    
    def measure_file_upload_endpoint(
        self,
        endpoint: str,
        file_path: Path,
        form_fields: Dict[str, str],
        label: str
    ) -> Dict[str, Any]:
        """Measure file upload endpoint - runs only once (ingestion doesn't use caching)."""
        url = f"{self.base_url}{endpoint}"
        
        # Add CSRF token to headers
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        
        start_time = time.perf_counter()
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "text/csv")}
                response = requests.post(url, files=files, data=form_fields, headers=headers, timeout=300)
            
            elapsed = time.perf_counter() - start_time
            timing_ms = elapsed * 1000
            status_code = response.status_code
            success = 200 <= status_code < 300
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            timing_ms = elapsed * 1000
            status_code = 0
            success = False
            print(f"  ⚠ Upload failed: {e}")
        
        return {
            "label": label,
            "endpoint": endpoint,
            "method": "POST",
            "runs": 1,
            "timings_ms": [round(timing_ms, 2)],
            "avg_response_time_ms": round(timing_ms, 2),
            "status_code": status_code,
            "success": success,
            "note": "Ingestion endpoints run once (data persistence, not cacheable)"
        }
    
    def test_data_ingestion(self) -> None:
        """Test data ingestion endpoints - uploads all CSV files from test_data_small."""
        print("\n📦 Testing Data Ingestion...")
        
        # Map CSV files to entity types (order matters - dependencies first)
        entity_files = [
            ("suppliers", "suppliers.csv"),
            ("facilities", "facilities.csv"),
            ("products", "products.csv"),
            ("purchase_orders", "purchase_orders.csv"),
            ("routes", "routes.csv"),
            ("shipments", "shipments.csv"),
        ]
        
        for entity_type, filename in entity_files:
            file_path = TEST_DATA_DIR / filename
            if file_path.exists():
                print(f"  Testing {entity_type} ingestion...")
                result = self.measure_file_upload_endpoint(
                    "/api/ingestion/import",
                    file_path,
                    {"entity": entity_type, "org_id": self.org_id},
                    f"ingestion_{entity_type}"
                )
                self.results["data_ingestion"][entity_type] = result
            else:
                print(f"  ⚠ {filename} not found, skipping {entity_type}")
    
    def test_eo_backfill(self) -> None:
        """Test EO backfill endpoint."""
        print("\n🌍 Testing EO Backfill...")
        result = self.measure_endpoint(
            "POST",
            f"/api/supply-chain/organizations/{self.org_id}/eo/backfill",
            label="eo_backfill"
        )
        self.results["eo_backfill"] = {"eo_backfill": result}
    
    def test_kg_sync(self) -> None:
        """Test KG sync endpoint."""
        print("\n🔄 Testing KG Sync...")
        result = self.measure_endpoint(
            "POST",
            f"/api/kg/organizations/{self.org_id}/sync",
            params={"phase": 1},
            label="kg_sync_phase1"
        )
        self.results["kg_sync"]["phase1"] = result
    
    def test_kg_analytics(self) -> None:
        """Test all KG analytics endpoints."""
        print("\n📊 Testing KG Analytics...")
        
        # Build graphs first
        print("  Building graphs...")
        build_result = self.measure_endpoint(
            "POST",
            "/api/kg/analytics/graphs/build",
            params={"org_id": self.org_id},
            label="build_graphs"
        )
        self.results["kg_analytics"]["build_graphs"] = build_result
        
        # Facilities analytics
        print("  Testing facilities betweenness...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/facilities/betweenness",
            params={"org_id": self.org_id, "limit": 15},
            label="facilities_betweenness"
        )
        self.results["kg_analytics"]["facilities_betweenness"] = result
        
        print("  Testing facilities pagerank...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/facilities/pagerank",
            params={"org_id": self.org_id, "limit": 15},
            label="facilities_pagerank"
        )
        self.results["kg_analytics"]["facilities_pagerank"] = result
        
        print("  Testing facilities communities...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/facilities/communities",
            params={"org_id": self.org_id},
            label="facilities_communities"
        )
        self.results["kg_analytics"]["facilities_communities"] = result
        
        # Routes analytics
        print("  Testing routes betweenness...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/routes/betweenness",
            params={"org_id": self.org_id, "limit": 15},
            label="routes_betweenness"
        )
        self.results["kg_analytics"]["routes_betweenness"] = result
        
        print("  Testing routes pagerank...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/routes/pagerank",
            params={"org_id": self.org_id, "limit": 15},
            label="routes_pagerank"
        )
        self.results["kg_analytics"]["routes_pagerank"] = result
        
        print("  Testing routes communities...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/routes/communities",
            params={"org_id": self.org_id},
            label="routes_communities"
        )
        self.results["kg_analytics"]["routes_communities"] = result
        
        # Shortest path
        print("  Testing shortest path...")
        result = self.measure_endpoint(
            "POST",
            "/api/kg/analytics/shortest-path",
            params={"org_id": self.org_id, "srcNode": "F001", "dstNode": "F002", "weight": "emission"},
            label="shortest_path_emission"
        )
        self.results["kg_analytics"]["shortest_path_emission"] = result
        
        # EO hotspots
        print("  Testing EO hotspots...")
        result = self.measure_endpoint(
            "GET",
            "/api/kg/analytics/eo/hotspots",
            params={"org_id": self.org_id, "limit": 20},
            label="eo_hotspots"
        )
        self.results["kg_analytics"]["eo_hotspots"] = result
    
    def test_prefixspan(self) -> None:
        """Test PrefixSpan pattern mining."""
        print("\n🔍 Testing PrefixSpan...")
        result = self.measure_endpoint(
            "POST",
            "/api/kg/analytics/sequences/prefixspan",
            params={
                "org_id": self.org_id,
                "min_support": 5,
                "max_len": 5,
                "top_k": 50
            },
            label="prefixspan_mining"
        )
        self.results["prefixspan"] = {"prefixspan_mining": result}
    
    def calculate_summary(self) -> None:
        """Calculate summary statistics."""
        print("\n📈 Calculating summary statistics...")
        
        all_cache_misses = []
        all_cache_hits = []
        all_speedups = []
        
        def extract_timings(results_dict: Dict, prefix: str = ""):
            for key, value in results_dict.items():
                if isinstance(value, dict):
                    if "cache_miss_time_ms" in value and value["cache_miss_time_ms"]:
                        all_cache_misses.append({
                            "endpoint": f"{prefix}{key}",
                            "time_ms": value["cache_miss_time_ms"]
                        })
                    if "cache_hit_avg_ms" in value and value["cache_hit_avg_ms"]:
                        all_cache_hits.append({
                            "endpoint": f"{prefix}{key}",
                            "time_ms": value["cache_hit_avg_ms"]
                        })
                    if "speedup" in value and value["speedup"]:
                        all_speedups.append(value["speedup"])
                    # Recurse for nested dicts
                    extract_timings(value, f"{prefix}{key}.")
        
        extract_timings(self.results["data_ingestion"])
        if self.results.get("eo_backfill"):
            extract_timings({"eo_backfill": self.results["eo_backfill"]})
        extract_timings(self.results["kg_analytics"])
        if self.results.get("prefixspan"):
            extract_timings(self.results["prefixspan"])
        
        self.results["summary"] = {
            "total_endpoints_tested": len(all_cache_misses),
            "cache_performance": {
                "avg_cache_miss_ms": round(sum(t["time_ms"] for t in all_cache_misses) / len(all_cache_misses), 2) if all_cache_misses else None,
                "avg_cache_hit_ms": round(sum(t["time_ms"] for t in all_cache_hits) / len(all_cache_hits), 2) if all_cache_hits else None,
                "avg_speedup": round(sum(all_speedups) / len(all_speedups), 2) if all_speedups else None,
                "max_speedup": round(max(all_speedups), 2) if all_speedups else None,
                "min_speedup": round(min(all_speedups), 2) if all_speedups else None,
            },
            "cache_miss_times": all_cache_misses,
            "cache_hit_times": all_cache_hits
        }
    
    def save_results(self) -> None:
        """Save results to JSON file."""
        output_file = OUTPUT_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print(f"   Total size: {output_file.stat().st_size / 1024:.2f} KB")
    
    def print_summary(self) -> None:
        """Print summary of results."""
        print("\n" + "="*60)
        print("📊 PERFORMANCE BENCHMARK SUMMARY")
        print("="*60)
        
        summary = self.results["summary"]
        cache_perf = summary.get("cache_performance", {})
        
        print(f"\nTotal Endpoints Tested: {summary.get('total_endpoints_tested', 0)}")
        print(f"\nCache Performance:")
        print(f"  Average Cache Miss: {cache_perf.get('avg_cache_miss_ms', 'N/A')} ms")
        print(f"  Average Cache Hit:  {cache_perf.get('avg_cache_hit_ms', 'N/A')} ms")
        print(f"  Average Speedup:    {cache_perf.get('avg_speedup', 'N/A')}x")
        print(f"  Max Speedup:        {cache_perf.get('max_speedup', 'N/A')}x")
        print(f"  Min Speedup:        {cache_perf.get('min_speedup', 'N/A')}x")
    
    def run_all(self) -> None:
        """Run all benchmark tests."""
        print(f"\n🚀 Starting Performance Benchmark")
        print(f"   Base URL: {self.base_url}")
        print(f"   Org ID: {self.org_id}")
        print(f"   Runs per endpoint: {RUNS_PER_ENDPOINT}")
        
        try:
            # Test endpoints
            self.test_data_ingestion()
            self.test_eo_backfill()
            self.test_kg_sync()
            self.test_kg_analytics()
            self.test_prefixspan()
            
            # Calculate summary
            self.calculate_summary()
            
            # Save results
            self.save_results()
            
            # Print summary
            self.print_summary()
            
            print("\n✅ Benchmark completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    benchmark = PerformanceBenchmark(BASE_URL, ORG_ID)
    benchmark.run_all()


if __name__ == "__main__":
    main()

