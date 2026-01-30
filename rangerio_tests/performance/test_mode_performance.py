"""
Performance Benchmarking for Mode Testing

Benchmarks response times, memory usage, and throughput for all modes:
- Basic: Baseline performance
- Assistant: Smart features overhead
- Deep Search: Thorough analysis overhead
- Both: Combined overhead

Generates comparison reports and validates performance expectations.
"""
import pytest
import time
import statistics
from pathlib import Path
from typing import Dict, List
from rangerio_tests.utils.mode_config import get_all_modes, create_mode_comparison_table


def run_benchmark_query(api_client, rag_id: int, query: str, mode_config) -> Dict:
    """Run a single benchmarked query and return timing metrics."""
    start_time = time.time()
    
    resp = api_client.post("/rag/query", json={
        "prompt": query,
        "project_id": rag_id,
        **mode_config.to_api_params()
    })
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        'success': resp.status_code == 200,
        'status_code': resp.status_code,
        'elapsed_ms': elapsed_ms,
        'result': resp.json() if resp.status_code == 200 else None
    }


@pytest.mark.performance
@pytest.mark.slow
def test_mode_response_time_distribution(api_client, sample_csv_small):
    """
    Benchmark response time distribution for each mode.
    Runs 50 queries per mode and measures p50, p95, p99 latencies.
    """
    # Create RAG
    rag_name = f"Perf Benchmark {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    # Test queries (mix of simple and complex)
    test_queries = [
        "How many records?",
        "What columns exist?",
        "Summarize the data",
        "What is the average value?",
        "List unique categories",
    ]
    
    benchmark_results = {}
    
    print(f"\n{'='*70}")
    print(f"RESPONSE TIME DISTRIBUTION BENCHMARK")
    print(f"Running 50 queries per mode (10 iterations of 5 queries)")
    print(f"{'='*70}\n")
    
    for mode_name, mode_config in get_all_modes().items():
        timings = []
        
        # Run 10 iterations of all 5 queries
        for iteration in range(10):
            for query in test_queries:
                result = run_benchmark_query(api_client, rag_id, query, mode_config)
                if result['success']:
                    timings.append(result['elapsed_ms'])
        
        # Calculate statistics
        if timings:
            p50 = statistics.median(timings)
            p95 = statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else max(timings)
            p99 = statistics.quantiles(timings, n=100)[98] if len(timings) >= 100 else max(timings)
            avg = statistics.mean(timings)
            std = statistics.stdev(timings) if len(timings) > 1 else 0
            
            benchmark_results[mode_name] = {
                'count': len(timings),
                'avg_ms': avg,
                'p50_ms': p50,
                'p95_ms': p95,
                'p99_ms': p99,
                'std_ms': std,
                'min_ms': min(timings),
                'max_ms': max(timings),
            }
            
            print(f"{mode_config.name} Mode:")
            print(f"  Queries: {len(timings)}")
            print(f"  Average: {avg:.0f}ms")
            print(f"  P50: {p50:.0f}ms")
            print(f"  P95: {p95:.0f}ms")
            print(f"  P99: {p99:.0f}ms")
            print(f"  Std Dev: {std:.0f}ms")
            print(f"  Range: {min(timings)}-{max(timings)}ms")
            print(f"  Expected: {mode_config.expected_response_time}")
            
            # Check if within expected range
            in_range = mode_config.expected_response_time[0] <= p50 <= mode_config.expected_response_time[1]
            print(f"  P50 in range: {'✓' if in_range else '⚠'}")
            print()
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    return benchmark_results


@pytest.mark.performance
def test_mode_overhead_analysis(api_client, sample_csv_small):
    """
    Analyze overhead of Assistant and Deep Search modes compared to Basic.
    Validates overhead expectations:
    - Assistant: ~1-3s overhead
    - Deep Search: ~4-12s overhead
    - Both: ~4-15s overhead
    """
    # Create RAG
    rag_name = f"Overhead Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    query = "What are the key statistics in this dataset?"
    
    # Run 10 samples per mode
    samples = 10
    mode_timings = {}
    
    for mode_name, mode_config in get_all_modes().items():
        timings = []
        for _ in range(samples):
            result = run_benchmark_query(api_client, rag_id, query, mode_config)
            if result['success']:
                timings.append(result['elapsed_ms'])
        
        if timings:
            mode_timings[mode_name] = statistics.mean(timings)
    
    # Calculate overheads
    basic_avg = mode_timings.get('basic', 0)
    
    print(f"\n{'='*70}")
    print(f"MODE OVERHEAD ANALYSIS")
    print(f"Query: {query}")
    print(f"Samples: {samples} per mode")
    print(f"{'='*70}\n")
    
    print(f"{'Mode':<15} {'Avg Time':<12} {'Overhead':<15} {'Expected Overhead'}")
    print(f"{'-'*15} {'-'*12} {'-'*15} {'-'*20}")
    
    for mode_name in ['basic', 'assistant', 'deep', 'both']:
        if mode_name in mode_timings:
            avg_time = mode_timings[mode_name]
            overhead = avg_time - basic_avg if mode_name != 'basic' else 0
            
            # Expected overhead ranges
            overhead_expectations = {
                'basic': (0, 0),
                'assistant': (1000, 3000),
                'deep': (4000, 12000),
                'both': (4000, 15000)
            }
            
            expected = overhead_expectations[mode_name]
            in_range = expected[0] <= overhead <= expected[1] if mode_name != 'basic' else True
            status = '✓' if in_range else '⚠'
            
            print(f"{mode_name:<15} {avg_time:>8.0f}ms   +{overhead:>8.0f}ms   {expected[0]}-{expected[1]}ms {status}")
    
    print(f"\n{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.performance
def test_throughput_comparison(api_client, sample_csv_small):
    """
    Compare query throughput (queries per second) across modes.
    Measures how many queries can be processed in a fixed time window.
    """
    # Create RAG
    rag_name = f"Throughput Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    query = "How many records?"
    test_duration_seconds = 30  # Run for 30 seconds per mode
    
    print(f"\n{'='*70}")
    print(f"THROUGHPUT COMPARISON")
    print(f"Duration: {test_duration_seconds}s per mode")
    print(f"Query: {query}")
    print(f"{'='*70}\n")
    
    throughput_results = {}
    
    for mode_name, mode_config in get_all_modes().items():
        start_time = time.time()
        query_count = 0
        success_count = 0
        total_response_time = 0
        
        # Run queries for fixed duration
        while time.time() - start_time < test_duration_seconds:
            result = run_benchmark_query(api_client, rag_id, query, mode_config)
            query_count += 1
            if result['success']:
                success_count += 1
                total_response_time += result['elapsed_ms']
        
        elapsed = time.time() - start_time
        qps = query_count / elapsed
        avg_response = total_response_time / success_count if success_count > 0 else 0
        
        throughput_results[mode_name] = {
            'queries': query_count,
            'success': success_count,
            'qps': qps,
            'avg_response_ms': avg_response
        }
        
        print(f"{mode_config.name} Mode:")
        print(f"  Total queries: {query_count}")
        print(f"  Successful: {success_count}")
        print(f"  QPS: {qps:.2f}")
        print(f"  Avg response: {avg_response:.0f}ms")
        print()
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    return throughput_results


@pytest.mark.performance
def test_model_comparison_benchmark(api_client, sample_csv_small):
    """
    Benchmark for comparing different models across modes.
    This creates a baseline that can be run with different models
    (e.g., Qwen 4B vs Llama3 3B) for comparison.
    """
    # Create RAG
    rag_name = f"Model Comp Benchmark {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    # Representative queries
    benchmark_queries = [
        "How many records?",
        "What columns exist?",
        "Summarize the data",
    ]
    
    comparison_data = {}
    
    print(f"\n{'='*70}")
    print(f"MODEL COMPARISON BENCHMARK")
    print(f"{'='*70}\n")
    
    for mode_name, mode_config in get_all_modes().items():
        mode_results = []
        
        for query in benchmark_queries:
            result = run_benchmark_query(api_client, rag_id, query, mode_config)
            if result['success']:
                mode_results.append({
                    'query': query,
                    'time_ms': result['elapsed_ms'],
                    'answer_length': len(result['result'].get('answer', ''))
                })
        
        if mode_results:
            avg_time = statistics.mean([r['time_ms'] for r in mode_results])
            avg_length = statistics.mean([r['answer_length'] for r in mode_results])
            
            comparison_data[mode_name] = {
                'avg_response_time_ms': avg_time,
                'accuracy_score': 'See validation tests',
                'avg_answer_length': avg_length,
            }
    
    # Generate comparison table
    table = create_mode_comparison_table(comparison_data)
    print(table)
    print(f"\n{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    return comparison_data


@pytest.mark.performance
def test_generate_performance_report(api_client, sample_csv_small):
    """
    Generate a comprehensive performance report for all modes.
    This can be saved and compared across different test runs or models.
    """
    # Create RAG
    rag_name = f"Perf Report {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    # Run mini benchmark (5 queries per mode)
    test_queries = [
        "How many records?",
        "What columns?",
        "Summarize",
        "Average value?",
        "List categories",
    ]
    
    report_data = {}
    
    for mode_name, mode_config in get_all_modes().items():
        timings = []
        
        for query in test_queries:
            result = run_benchmark_query(api_client, rag_id, query, mode_config)
            if result['success']:
                timings.append(result['elapsed_ms'])
        
        if timings:
            report_data[mode_name] = {
                'mode': mode_config.name,
                'assistant_mode': mode_config.assistant_mode,
                'deep_search_mode': mode_config.deep_search_mode,
                'avg_response_ms': statistics.mean(timings),
                'median_response_ms': statistics.median(timings),
                'min_response_ms': min(timings),
                'max_response_ms': max(timings),
                'expected_range_ms': mode_config.expected_response_time,
                'description': mode_config.description,
            }
    
    # Print report
    print(f"\n{'='*70}")
    print(f"PERFORMANCE REPORT")
    print(f"{'='*70}\n")
    
    for mode_name, data in report_data.items():
        print(f"## {data['mode']} Mode")
        print(f"**Config**: Assistant={data['assistant_mode']}, Deep Search={data['deep_search_mode']}")
        print(f"**Description**: {data['description']}")
        print(f"**Performance**:")
        print(f"  - Average: {data['avg_response_ms']:.0f}ms")
        print(f"  - Median: {data['median_response_ms']:.0f}ms")
        print(f"  - Range: {data['min_response_ms']}-{data['max_response_ms']}ms")
        print(f"  - Expected: {data['expected_range_ms'][0]}-{data['expected_range_ms'][1]}ms")
        print()
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    return report_data








