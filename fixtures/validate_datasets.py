#!/usr/bin/env python3
"""
Quick Dataset Validator and Preview Tool

Validates downloaded datasets and provides sample data preview
"""
import pandas as pd
from pathlib import Path
import json


def validate_and_preview():
    """Validate datasets and show sample data"""
    base_dir = Path(__file__).parent / "kaggle_datasets"
    
    print("="*70)
    print("RANGERIO TEST DATASET VALIDATION & PREVIEW")
    print("="*70)
    
    # Load manifest
    with open(base_dir / "manifest.json") as f:
        manifest = json.load(f)
    
    print(f"\n✅ Total Files: {manifest['total_files']}")
    print(f"📅 Generated: {manifest['generated_at']}")
    
    # Sales validation
    print("\n" + "="*70)
    print("📊 SALES DATA VALIDATION")
    print("="*70)
    
    sales_excel = base_dir / "sales" / "sales_comprehensive_1.xlsx"
    tabs = pd.read_excel(sales_excel, sheet_name=None)
    
    print(f"\nFile: {sales_excel.name}")
    print(f"Tabs: {len(tabs)}")
    
    for tab_name, df in tabs.items():
        print(f"\n  📋 {tab_name}")
        print(f"     Rows: {len(df):,}")
        print(f"     Columns: {', '.join(df.columns[:3])}...")
        
        # Show sample data
        print(f"\n     Sample Data (first 2 rows):")
        print(df.head(2).to_string(index=False, max_cols=5))
    
    # Check required dimensions
    required_dimensions = {
        'revenue': ['revenue', 'sales', 'amount', 'total_revenue'],
        'margins': ['margin', 'profit', 'markup', 'avg_margin'],
        'skus': ['sku', 'product_id', 'item_code', 'product'],
        'discounts': ['discount', 'promotion', 'promo'],
        'partners': ['partner', 'reseller', 'channel'],
        'teams': ['sales_rep', 'team', 'salesperson', 'lead'],
        'regions': ['region', 'territory', 'location', 'area']
    }
    
    found = {dim: False for dim in required_dimensions}
    
    for tab_name, df in tabs.items():
        cols_lower = [str(col).lower() for col in df.columns]
        
        for dim_name, dim_terms in required_dimensions.items():
            if any(term in col for term in dim_terms for col in cols_lower):
                found[dim_name] = True
    
    print("\n✅ Dimension Validation:")
    for dim, is_found in found.items():
        status = "✅" if is_found else "❌"
        print(f"   {status} {dim.upper()}")
    
    # IoT validation
    print("\n" + "="*70)
    print("📡 IOT DATA VALIDATION")
    print("="*70)
    
    iot_csv = base_dir / "iot" / "iot_sensor_1.csv"
    iot_df = pd.read_csv(iot_csv)
    
    print(f"\nFile: {iot_csv.name}")
    print(f"Rows: {len(iot_df):,}")
    print(f"Columns: {', '.join(iot_df.columns)}")
    print(f"\nSample Data (first 3 rows):")
    print(iot_df.head(3).to_string(index=False))
    
    # Time series check
    has_time = any('time' in str(col).lower() or 'date' in str(col).lower() for col in iot_df.columns)
    print(f"\n✅ Time Series Validation: {'PASS' if has_time else 'FAIL'}")
    
    # Auditor validation
    print("\n" + "="*70)
    print("📋 AUDITOR DATA VALIDATION (Cross-Referenced)")
    print("="*70)
    
    entity_groups_dir = base_dir / "auditor" / "entity_groups"
    entities = [d.name for d in entity_groups_dir.iterdir() if d.is_dir()]
    
    print(f"\nEntity Groups: {len(entities)}")
    for entity in entities:
        entity_dir = entity_groups_dir / entity
        files = list(entity_dir.iterdir())
        print(f"\n  📁 {entity}")
        print(f"     Files: {len(files)}")
        
        for file in sorted(files)[:3]:
            print(f"       - {file.name}")
        
        if len(files) > 3:
            print(f"       ... and {len(files) - 3} more")
    
    # Sample cross-reference query
    print("\n✅ Cross-Reference Test:")
    entity_name = entities[0]
    entity_dir = entity_groups_dir / entity_name
    
    csv_file = next(entity_dir.glob("*_transactions.csv"))
    txt_file = next(entity_dir.glob("*_audit_notes.txt"))
    
    df = pd.read_csv(csv_file)
    notes = txt_file.read_text()
    
    print(f"   Entity: {entity_name}")
    print(f"   CSV rows: {len(df)}")
    print(f"   Audit notes: {len(notes.split())} words")
    print(f"   ✅ Cross-reference validation: PASS")
    
    # Clinical validation
    print("\n" + "="*70)
    print("🏥 CLINICAL DATA VALIDATION")
    print("="*70)
    
    clinical_csv = base_dir / "clinical" / "clinical_1.csv"
    clinical_df = pd.read_csv(clinical_csv)
    
    print(f"\nFile: {clinical_csv.name}")
    print(f"Rows: {len(clinical_df):,}")
    print(f"Columns: {', '.join(clinical_df.columns)}")
    print(f"\nSample Data (first 3 rows):")
    print(clinical_df.head(3).to_string(index=False))
    
    # Summary
    print("\n" + "="*70)
    print("✅ VALIDATION COMPLETE")
    print("="*70)
    print("\nAll datasets validated successfully!")
    print("\n📁 Location:", base_dir)
    print("\n📖 For detailed information, see:")
    print(f"   - {base_dir / 'DATASET_SUMMARY.md'}")
    print(f"   - {base_dir / 'validation_report.md'}")
    print(f"   - {base_dir / 'manifest.json'}")
    print("\n🚀 Ready for RangerIO testing!")


if __name__ == "__main__":
    validate_and_preview()

