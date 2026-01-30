"""
Review validation results from HTML interactive reports

This script parses the exported JSON and provides:
1. Summary statistics
2. Detailed feedback extraction
3. Analysis for AI review
"""
import json
from pathlib import Path
from typing import Dict, Any


def review_validation_results(results_file: Path) -> Dict[str, Any]:
    """
    Parse and summarize validation results for AI review
    
    Args:
        results_file: Path to validation_results_*.json file
    
    Returns:
        Structured summary of human validation
    """
    with open(results_file) as f:
        data = json.load(f)
    
    summary = {
        "report_id": data["report_id"],
        "generated_at": data["generated_at"],
        "total_items": data["total_items"],
        "validated_items": data["validated_items"],
        "validation_rate": f"{(data['validated_items']/data['total_items']*100):.1f}%",
        "accurate_count": 0,
        "partial_count": 0,
        "inaccurate_count": 0,
        "not_validated_count": 0,
        "items_with_notes": 0,
        "by_type": {},
        "detailed_feedback": []
    }
    
    # Analyze each response
    for item_id, response in data["responses"].items():
        choice = response["choice"]
        item_type = response["item_type"]
        
        # Count by choice
        if choice == "accurate":
            summary["accurate_count"] += 1
        elif choice == "partial":
            summary["partial_count"] += 1
        elif choice == "inaccurate":
            summary["inaccurate_count"] += 1
        else:
            summary["not_validated_count"] += 1
        
        # Count by type
        if item_type not in summary["by_type"]:
            summary["by_type"][item_type] = {
                "total": 0,
                "accurate": 0,
                "partial": 0,
                "inaccurate": 0
            }
        summary["by_type"][item_type]["total"] += 1
        if choice in ["accurate", "partial", "inaccurate"]:
            summary["by_type"][item_type][choice] += 1
        
        # Collect detailed feedback
        if response["notes"]:
            summary["items_with_notes"] += 1
            summary["detailed_feedback"].append({
                "item_id": response["item_id"],
                "item_type": response["item_type"],
                "choice": response["choice"],
                "notes": response["notes"],
                "timestamp": response["timestamp"]
            })
    
    return summary


def print_summary(summary: Dict[str, Any]):
    """
    Print formatted summary of validation results
    """
    print("\n" + "="*70)
    print("📊 VALIDATION RESULTS SUMMARY")
    print("="*70)
    
    print(f"\n📁 Report ID: {summary['report_id']}")
    print(f"📅 Generated: {summary['generated_at']}")
    
    print(f"\n📈 Overall Statistics:")
    print(f"   Total Items: {summary['total_items']}")
    print(f"   Validated: {summary['validated_items']} ({summary['validation_rate']})")
    print(f"   Not Validated: {summary['not_validated_count']}")
    
    print(f"\n✅ Accuracy Breakdown:")
    print(f"   ✅ Accurate: {summary['accurate_count']}")
    print(f"   ⚠️  Partially Accurate: {summary['partial_count']}")
    print(f"   ❌ Inaccurate/Hallucination: {summary['inaccurate_count']}")
    
    if summary['by_type']:
        print(f"\n📊 By Item Type:")
        for item_type, stats in summary['by_type'].items():
            accuracy_rate = (stats['accurate'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"   {item_type}:")
            print(f"      Total: {stats['total']}")
            print(f"      Accurate: {stats['accurate']} ({accuracy_rate:.1f}%)")
            print(f"      Partial: {stats['partial']}")
            print(f"      Inaccurate: {stats['inaccurate']}")
    
    print(f"\n📝 Items with Notes: {summary['items_with_notes']}")
    
    if summary['detailed_feedback']:
        print(f"\n💬 Detailed Feedback:")
        for feedback in summary['detailed_feedback']:
            print(f"\n   Item #{feedback['item_id']} ({feedback['item_type']}):")
            print(f"   Choice: {feedback['choice']}")
            print(f"   Notes: {feedback['notes'][:200]}{'...' if len(feedback['notes']) > 200 else ''}")
    
    print("\n" + "="*70)


def analyze_quality_patterns(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze patterns in validation to identify issues
    """
    patterns = {
        "hallucination_rate": 0.0,
        "partial_accuracy_rate": 0.0,
        "full_accuracy_rate": 0.0,
        "common_issues": [],
        "strengths": []
    }
    
    total_validated = summary["validated_items"]
    if total_validated > 0:
        patterns["hallucination_rate"] = (summary["inaccurate_count"] / total_validated) * 100
        patterns["partial_accuracy_rate"] = (summary["partial_count"] / total_validated) * 100
        patterns["full_accuracy_rate"] = (summary["accurate_count"] / total_validated) * 100
    
    # Analyze notes for common issues
    issue_keywords = {
        "hallucination": ["hallucinated", "fabricated", "made up", "not in context"],
        "incomplete": ["missing", "incomplete", "partial", "could be better"],
        "context_quality": ["context", "retrieval", "chunks", "sources"],
        "formatting": ["format", "structure", "presentation"],
    }
    
    for feedback in summary["detailed_feedback"]:
        notes_lower = feedback["notes"].lower()
        for issue_type, keywords in issue_keywords.items():
            if any(keyword in notes_lower for keyword in keywords):
                patterns["common_issues"].append({
                    "type": issue_type,
                    "item_id": feedback["item_id"],
                    "excerpt": feedback["notes"][:100]
                })
    
    # Identify strengths
    if patterns["full_accuracy_rate"] > 70:
        patterns["strengths"].append("High accuracy rate (>70%)")
    if summary["inaccurate_count"] == 0:
        patterns["strengths"].append("No hallucinations detected")
    if patterns["hallucination_rate"] < 10:
        patterns["strengths"].append("Low hallucination rate (<10%)")
    
    return patterns


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python review_validation_results.py <results_file.json>")
        print("\nExample:")
        print("  python review_validation_results.py validation_results_20251229_171710.json")
        sys.exit(1)
    
    results_file = Path(sys.argv[1])
    
    if not results_file.exists():
        print(f"❌ Error: File not found: {results_file}")
        sys.exit(1)
    
    # Parse and summarize
    summary = review_validation_results(results_file)
    print_summary(summary)
    
    # Analyze patterns
    patterns = analyze_quality_patterns(summary)
    
    print("\n" + "="*70)
    print("🔍 QUALITY PATTERN ANALYSIS")
    print("="*70)
    print(f"\n📊 Accuracy Rates:")
    print(f"   Full Accuracy: {patterns['full_accuracy_rate']:.1f}%")
    print(f"   Partial Accuracy: {patterns['partial_accuracy_rate']:.1f}%")
    print(f"   Hallucination Rate: {patterns['hallucination_rate']:.1f}%")
    
    if patterns["strengths"]:
        print(f"\n✅ Strengths:")
        for strength in patterns["strengths"]:
            print(f"   • {strength}")
    
    if patterns["common_issues"]:
        print(f"\n⚠️  Common Issues Found:")
        issue_types = {}
        for issue in patterns["common_issues"]:
            issue_types[issue["type"]] = issue_types.get(issue["type"], 0) + 1
        for issue_type, count in issue_types.items():
            print(f"   • {issue_type}: {count} occurrences")
    
    print("\n" + "="*70)
    
    # Save analysis
    analysis_file = results_file.parent / f"analysis_{results_file.stem}.json"
    with open(analysis_file, 'w') as f:
        json.dump({
            "summary": summary,
            "patterns": patterns
        }, f, indent=2)
    
    print(f"\n✅ Analysis saved to: {analysis_file}")








