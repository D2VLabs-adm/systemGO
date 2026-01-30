#!/usr/bin/env python3
"""
Compare RangerIO Benchmark Results

Usage:
    # Compare two models
    python compare_benchmarks.py --models qwen3-4b llama-3-2-3b --mode basic
    
    # Show performance trend
    python compare_benchmarks.py --trend --model qwen3-4b --test test_mode_response_time_distribution
    
    # Generate full report
    python compare_benchmarks.py --report
"""
import argparse
import sys
from pathlib import Path
from rangerio_tests.utils.benchmark_db import BenchmarkDatabase


def compare_models_cli(args):
    """Compare two or more models."""
    db = BenchmarkDatabase()
    
    if len(args.models) < 2:
        print("❌ Need at least 2 models to compare")
        return 1
    
    print(f"\n{'='*70}")
    print(f"📊 Comparing Models: {', '.join(args.models)}")
    print(f"Mode: {args.mode}")
    print(f"{'='*70}\n")
    
    comparison = db.compare_models(args.models[0], args.models[1], mode=args.mode)
    
    if not comparison:
        print("⚠️  No benchmark data found for these models")
        return 1
    
    # Print comparison table
    print(f"{'Test':<40} {'Model 1':<20} {'Model 2':<20} {'Difference'}")
    print(f"{'-'*40} {'-'*20} {'-'*20} {'-'*15}")
    
    for test_name, models_data in comparison.items():
        model1_data = models_data.get(args.models[0], {})
        model2_data = models_data.get(args.models[1], {})
        
        # Compare avg_response_ms if available
        if 'avg_response_ms' in model1_data and 'avg_response_ms' in model2_data:
            m1_avg = model1_data['avg_response_ms']['mean']
            m2_avg = model2_data['avg_response_ms']['mean']
            diff = m2_avg - m1_avg
            diff_pct = (diff / m1_avg) * 100 if m1_avg > 0 else 0
            
            print(f"{test_name[:38]:<40} {m1_avg:>8.0f}ms         {m2_avg:>8.0f}ms         {diff:>+6.0f}ms ({diff_pct:>+5.1f}%)")
    
    print(f"\n{'='*70}\n")
    return 0


def show_trend_cli(args):
    """Show performance trend over time."""
    db = BenchmarkDatabase()
    
    print(f"\n{'='*70}")
    print(f"📈 Performance Trend")
    print(f"Model: {args.model}")
    print(f"Test: {args.test}")
    print(f"Metric: {args.metric}")
    print(f"{'='*70}\n")
    
    trend = db.get_performance_trend(args.model, args.mode, args.test, args.metric)
    
    if not trend:
        print("⚠️  No trend data found")
        return 1
    
    print(f"{'Timestamp':<25} {'Value'}")
    print(f"{'-'*25} {'-'*15}")
    
    for point in trend:
        print(f"{point['timestamp']:<25} {point['value']:>10.2f}")
    
    print(f"\n📊 Summary:")
    values = [p['value'] for p in trend]
    print(f"  First:  {values[0]:.2f}")
    print(f"  Latest: {values[-1]:.2f}")
    print(f"  Change: {values[-1] - values[0]:+.2f} ({((values[-1] - values[0]) / values[0] * 100):+.1f}%)")
    print(f"\n{'='*70}\n")
    
    return 0


def generate_report_cli(args):
    """Generate full comparison report."""
    db = BenchmarkDatabase()
    
    output_file = args.output or f"reports/benchmarks/comparison_report_{Path().cwd().stem}.md"
    
    print(f"\n🔄 Generating benchmark comparison report...")
    report = db.generate_comparison_report(output_file)
    
    print(report)
    print(f"\n💾 Report saved to: {output_file}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="RangerIO Benchmark Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Compare models command
    compare_parser = subparsers.add_parser('compare', help='Compare two models')
    compare_parser.add_argument('--models', nargs='+', required=True, help='Models to compare')
    compare_parser.add_argument('--mode', default='basic', help='Mode to compare (default: basic)')
    
    # Trend command
    trend_parser = subparsers.add_parser('trend', help='Show performance trend')
    trend_parser.add_argument('--model', required=True, help='Model name')
    trend_parser.add_argument('--test', required=True, help='Test name')
    trend_parser.add_argument('--metric', default='avg_response_ms', help='Metric to trend (default: avg_response_ms)')
    trend_parser.add_argument('--mode', default='basic', help='Mode (default: basic)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate full comparison report')
    report_parser.add_argument('--output', help='Output file path')
    
    # Fallback for simple usage
    parser.add_argument('--models', nargs='+', help='Models to compare')
    parser.add_argument('--mode', default='basic', help='Mode to compare')
    parser.add_argument('--trend', action='store_true', help='Show trend')
    parser.add_argument('--model', help='Model for trend')
    parser.add_argument('--test', help='Test for trend')
    parser.add_argument('--metric', default='avg_response_ms', help='Metric for trend')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--output', help='Output file')
    
    args = parser.parse_args()
    
    # Handle subcommands
    if args.command == 'compare':
        return compare_models_cli(args)
    elif args.command == 'trend':
        return show_trend_cli(args)
    elif args.command == 'report':
        return generate_report_cli(args)
    
    # Handle legacy flags
    if args.trend and args.model and args.test:
        return show_trend_cli(args)
    elif args.report:
        return generate_report_cli(args)
    elif args.models and len(args.models) >= 2:
        return compare_models_cli(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())






