"""
Benchmark Results Persistence Layer

Saves and compares benchmark results across:
- Different test runs (track performance over time)
- Different models (Qwen 4B vs Llama3 3B vs others)
- Different configurations (Basic, Assistant, Deep Search, Both modes)

Results are stored in JSON format for easy comparison and trending.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import statistics


class BenchmarkDatabase:
    """Manages saving and retrieving benchmark results."""
    
    def __init__(self, db_dir: str = "reports/benchmarks"):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_file = self.db_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.index_file = self.db_dir / "index.json"
        
    def save_benchmark_result(
        self,
        test_name: str,
        mode: str,
        model: str,
        metrics: Dict,
        metadata: Optional[Dict] = None
    ):
        """Save a single benchmark result."""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_name': test_name,
            'mode': mode,
            'model': model,
            'metrics': metrics,
            'metadata': metadata or {}
        }
        
        # Append to current run file
        if self.current_run_file.exists():
            with open(self.current_run_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'run_id': self.current_run_file.stem, 'results': []}
        
        data['results'].append(result)
        
        with open(self.current_run_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Update index
        self._update_index(result)
        
        return result
    
    def _update_index(self, result: Dict):
        """Update the benchmark index for quick lookups."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {
                'runs': [],
                'models': set(),
                'modes': set(),
                'tests': set()
            }
        
        # Update index metadata
        run_id = self.current_run_file.stem
        if run_id not in index['runs']:
            index['runs'].append(run_id)
        
        index['models'] = list(set(index.get('models', [])) | {result['model']})
        index['modes'] = list(set(index.get('modes', [])) | {result['mode']})
        index['tests'] = list(set(index.get('tests', [])) | {result['test_name']})
        
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    def get_all_runs(self) -> List[Dict]:
        """Get all benchmark runs."""
        runs = []
        for file in sorted(self.db_dir.glob("benchmark_*.json")):
            with open(file, 'r') as f:
                runs.append(json.load(f))
        return runs
    
    def compare_models(self, model1: str, model2: str, mode: str = 'basic') -> Dict:
        """Compare two models across all tests."""
        runs = self.get_all_runs()
        
        model1_results = []
        model2_results = []
        
        for run in runs:
            for result in run['results']:
                if result['mode'] == mode:
                    if result['model'] == model1:
                        model1_results.append(result)
                    elif result['model'] == model2:
                        model2_results.append(result)
        
        # Aggregate by test
        comparison = {}
        for test_name in set([r['test_name'] for r in model1_results + model2_results]):
            m1_metrics = [r['metrics'] for r in model1_results if r['test_name'] == test_name]
            m2_metrics = [r['metrics'] for r in model2_results if r['test_name'] == test_name]
            
            if m1_metrics and m2_metrics:
                comparison[test_name] = {
                    model1: self._aggregate_metrics(m1_metrics),
                    model2: self._aggregate_metrics(m2_metrics)
                }
        
        return comparison
    
    def _aggregate_metrics(self, metrics_list: List[Dict]) -> Dict:
        """Aggregate metrics across multiple runs."""
        if not metrics_list:
            return {}
        
        aggregated = {}
        for key in metrics_list[0].keys():
            values = [m[key] for m in metrics_list if key in m and isinstance(m[key], (int, float))]
            if values:
                aggregated[key] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'count': len(values)
                }
        
        return aggregated
    
    def get_performance_trend(self, model: str, mode: str, test_name: str, metric: str) -> List[Dict]:
        """Get performance trend over time for a specific metric."""
        runs = self.get_all_runs()
        
        trend = []
        for run in runs:
            for result in run['results']:
                if (result['model'] == model and 
                    result['mode'] == mode and 
                    result['test_name'] == test_name and
                    metric in result['metrics']):
                    
                    trend.append({
                        'timestamp': result['timestamp'],
                        'value': result['metrics'][metric]
                    })
        
        return sorted(trend, key=lambda x: x['timestamp'])
    
    def generate_comparison_report(self, output_file: Optional[str] = None) -> str:
        """Generate a human-readable comparison report."""
        runs = self.get_all_runs()
        
        if not runs:
            return "No benchmark data available."
        
        report_lines = [
            "# RangerIO Benchmark Comparison Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Runs: {len(runs)}",
            "",
            "## Summary by Model",
            ""
        ]
        
        # Group by model
        models = {}
        for run in runs:
            for result in run['results']:
                model = result['model']
                if model not in models:
                    models[model] = []
                models[model].append(result)
        
        for model, results in models.items():
            report_lines.append(f"### {model}")
            report_lines.append(f"Total tests: {len(results)}")
            
            # Average response time by mode
            mode_times = {}
            for result in results:
                mode = result['mode']
                if 'avg_response_ms' in result['metrics']:
                    if mode not in mode_times:
                        mode_times[mode] = []
                    mode_times[mode].append(result['metrics']['avg_response_ms'])
            
            report_lines.append("\n**Average Response Time by Mode:**")
            for mode, times in sorted(mode_times.items()):
                avg = statistics.mean(times)
                report_lines.append(f"- {mode}: {avg:.0f}ms (n={len(times)})")
            
            report_lines.append("")
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
        
        return report


# Global instance
_db = None

def get_benchmark_db() -> BenchmarkDatabase:
    """Get or create the global benchmark database instance."""
    global _db
    if _db is None:
        _db = BenchmarkDatabase()
    return _db


def save_benchmark(test_name: str, mode: str, model: str, metrics: Dict, metadata: Optional[Dict] = None):
    """Convenience function to save a benchmark result."""
    db = get_benchmark_db()
    return db.save_benchmark_result(test_name, mode, model, metrics, metadata)






