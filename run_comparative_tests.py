"""
Model Comparative Test Runner
Run full test suite with different models and compare results

Usage:
    python run_comparative_tests.py --models phi-3-mini zephyr-7b --compare
"""
import argparse
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
import pandas as pd


class ModelComparativeRunner:
    """
    Orchestrates comparative testing across different LLM models
    """
    
    def __init__(self, output_dir: str = "reports/comparisons"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def run_full_suite(self, model_config: dict) -> dict:
        """
        Run complete test suite with specified model
        
        Args:
            model_config: Dict with 'name', 'backend', 'model_path', etc.
            
        Returns:
            Test results and metrics
        """
        model_name = model_config['name']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n{'='*80}")
        print(f"🚀 Running Full Test Suite with Model: {model_name}")
        print(f"{'='*80}\n")
        
        # Set environment variables for model
        os.environ['TEST_MODEL_NAME'] = model_config['name']
        os.environ['TEST_MODEL_PATH'] = model_config.get('model_path', '')
        
        results = {
            'model': model_config,
            'timestamp': timestamp,
            'tests': {}
        }
        
        # Run pytest
        cmd = [
            "pytest",
            "rangerio_tests/",
            "-v",
            f"--html=reports/html/{model_name}_{timestamp}.html",
            "--self-contained-html",
            "-m", "not slow"  # Skip slow tests for comparison
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            results['tests']['exit_code'] = result.returncode
            results['tests']['passed'] = result.returncode == 0
        except subprocess.TimeoutExpired:
            results['tests']['exit_code'] = -1
            results['tests']['passed'] = False
            results['tests']['error'] = 'Timeout after 30 minutes'
        
        self.results[model_name] = results
        return results
    
    def compare_models(self, model_names: list = None) -> pd.DataFrame:
        """
        Generate comparison report between models
        
        Args:
            model_names: List of model names to compare
            
        Returns:
            DataFrame with comparison metrics
        """
        if not model_names:
            model_names = list(self.results.keys())
        
        if len(model_names) < 2:
            print("⚠️  Need at least 2 models to compare")
            return None
        
        print(f"\n{'='*80}")
        print(f"📊 Generating Comparison Report")
        print(f"{'='*80}\n")
        
        comparison_data = []
        for model_name in model_names:
            if model_name not in self.results:
                continue
            
            results = self.results[model_name]
            row = {
                'Model': model_name,
                'Tests Passed': '✅' if results['tests'].get('passed') else '❌',
                'Timestamp': results['timestamp']
            }
            comparison_data.append(row)
        
        df = pd.DataFrame(comparison_data)
        
        # Save comparison
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.output_dir / f"comparison_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"\n📊 Comparison Report:")
        print(df.to_string(index=False))
        print(f"\n💾 Saved to: {csv_path}")
        
        return df


def main():
    parser = argparse.ArgumentParser(
        description="RangerIO Comparative Model Testing"
    )
    
    parser.add_argument(
        '--models',
        nargs='+',
        required=True,
        help='Model names to test'
    )
    
    parser.add_argument(
        '--model-configs',
        type=str,
        default='model_configs.json',
        help='Path to model configurations JSON'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Generate comparison report after testing'
    )
    
    args = parser.parse_args()
    
    runner = ModelComparativeRunner()
    
    # Load model configs
    if Path(args.model_configs).exists():
        with open(args.model_configs) as f:
            model_configs = json.load(f)
    else:
        # Default configs
        model_configs = {
            name: {'name': name, 'backend': 'llama.cpp'}
            for name in args.models
        }
    
    # Run tests for each model
    for model_name in args.models:
        if model_name not in model_configs:
            print(f"⚠️  No configuration found for {model_name}")
            continue
        
        try:
            runner.run_full_suite(model_configs[model_name])
        except Exception as e:
            print(f"❌ Error testing {model_name}: {e}")
    
    # Generate comparison
    if args.compare:
        runner.compare_models(args.models)
    
    print("\n✅ All done!")


if __name__ == "__main__":
    main()








