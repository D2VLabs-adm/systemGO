#!/usr/bin/env python3
"""
Dataset File Renaming Script

Renames all test datasets with descriptive names for easier testing.
Creates a mapping file and updates all documentation.
"""
import os
import json
from pathlib import Path
import shutil

# Define renaming mappings
SALES_CSV_MAPPING = {
    'sales_1.csv': 'sales_01_regional_north_2022-2023.csv',
    'sales_2.csv': 'sales_02_regional_south_2022-2023.csv',
    'sales_3.csv': 'sales_03_regional_east_2022-2023.csv',
    'sales_4.csv': 'sales_04_regional_west_2022-2023.csv',
    'sales_5.csv': 'sales_05_regional_central_2022-2023.csv',
    'sales_6.csv': 'sales_06_product_electronics_Q1-Q4.csv',
    'sales_7.csv': 'sales_07_product_furniture_Q1-Q4.csv',
    'sales_8.csv': 'sales_08_product_office_supplies_Q1-Q4.csv',
    'sales_9.csv': 'sales_09_product_technology_Q1-Q4.csv',
    'sales_10.csv': 'sales_10_team_performance_all_regions.csv',
    'sales_11.csv': 'sales_11_partner_reseller_analysis.csv',
    'sales_12.csv': 'sales_12_discount_effectiveness_2023.csv',
    'sales_13.csv': 'sales_13_customer_segments_enterprise.csv',
    'sales_14.csv': 'sales_14_customer_segments_smb.csv',
    'sales_15.csv': 'sales_15_customer_segments_consumer.csv',
    'sales_16.csv': 'sales_16_quarterly_trends_5years.csv',
    'sales_17.csv': 'sales_17_sku_analysis_top100.csv',
    'sales_18.csv': 'sales_18_margin_analysis_by_category.csv',
    'sales_19.csv': 'sales_19_transactions_high_value.csv',
    'sales_20.csv': 'sales_20_transactions_bulk_orders.csv',
}

SALES_EXCEL_MAPPING = {
    'sales_comprehensive_1.xlsx': 'sales_comprehensive_5year_full_company.xlsx',
    'sales_comprehensive_2.xlsx': 'sales_comprehensive_regional_breakdown.xlsx',
    'sales_comprehensive_3.xlsx': 'sales_comprehensive_product_performance.xlsx',
    'sales_comprehensive_4.xlsx': 'sales_comprehensive_partner_team_analysis.xlsx',
    'sales_comprehensive_5.xlsx': 'sales_comprehensive_discount_margin_analysis.xlsx',
}

CLINICAL_CSV_MAPPING = {
    'clinical_1.csv': 'clinical_01_type2diabetes_500patients.csv',
    'clinical_2.csv': 'clinical_02_type2diabetes_1200patients.csv',
    'clinical_3.csv': 'clinical_03_type2diabetes_800patients.csv',
    'clinical_4.csv': 'clinical_04_type2diabetes_1500patients.csv',
    'clinical_5.csv': 'clinical_05_hypertension_600patients.csv',
    'clinical_6.csv': 'clinical_06_hypertension_1100patients.csv',
    'clinical_7.csv': 'clinical_07_hypertension_900patients.csv',
    'clinical_8.csv': 'clinical_08_hypertension_1400patients.csv',
    'clinical_9.csv': 'clinical_09_heartdisease_700patients.csv',
    'clinical_10.csv': 'clinical_10_heartdisease_1300patients.csv',
    'clinical_11.csv': 'clinical_11_heartdisease_850patients.csv',
    'clinical_12.csv': 'clinical_12_heartdisease_1600patients.csv',
    'clinical_13.csv': 'clinical_13_asthma_550patients.csv',
    'clinical_14.csv': 'clinical_14_asthma_950patients.csv',
    'clinical_15.csv': 'clinical_15_asthma_1200patients.csv',
    'clinical_16.csv': 'clinical_16_asthma_1800patients.csv',
    'clinical_17.csv': 'clinical_17_mixed_conditions_large_cohort.csv',
    'clinical_18.csv': 'clinical_18_mixed_conditions_diverse_ages.csv',
    'clinical_19.csv': 'clinical_19_followup_longterm_outcomes.csv',
    'clinical_20.csv': 'clinical_20_followup_adverse_events.csv',
}

CLINICAL_EXCEL_MAPPING = {
    'clinical_trial_1.xlsx': 'clinical_trial_phase1_demographics.xlsx',
    'clinical_trial_2.xlsx': 'clinical_trial_phase2_efficacy.xlsx',
    'clinical_trial_3.xlsx': 'clinical_trial_phase3_safety.xlsx',
    'clinical_trial_4.xlsx': 'clinical_trial_multisite_combined.xlsx',
    'clinical_trial_5.xlsx': 'clinical_trial_longitudinal_outcomes.xlsx',
}

CLINICAL_DOC_MAPPING = {
    'medical_report_1.txt': 'medical_report_diabetes_case_study.txt',
    'medical_report_2.txt': 'medical_report_hypertension_summary.txt',
    'medical_report_3.txt': 'medical_report_heartdisease_analysis.txt',
    'medical_report_4.txt': 'medical_report_asthma_treatment.txt',
    'medical_report_5.txt': 'medical_report_adverse_events_review.txt',
}

IOT_MAPPING = {
    'iot_sensor_1.csv': 'iot_01_temperature_warehouse_30days.csv',
    'iot_sensor_2.csv': 'iot_02_temperature_datacenter_30days.csv',
    'iot_sensor_3.csv': 'iot_03_temperature_greenhouse_30days.csv',
    'iot_sensor_4.csv': 'iot_04_temperature_manufacturing_30days.csv',
    'iot_sensor_5.csv': 'iot_05_humidity_warehouse_30days.csv',
    'iot_sensor_6.csv': 'iot_06_humidity_datacenter_30days.csv',
    'iot_sensor_7.csv': 'iot_07_humidity_greenhouse_30days.csv',
    'iot_sensor_8.csv': 'iot_08_humidity_manufacturing_30days.csv',
    'iot_sensor_9.csv': 'iot_09_pressure_industrial_30days.csv',
    'iot_sensor_10.csv': 'iot_10_pressure_hvac_system_30days.csv',
    'iot_sensor_11.csv': 'iot_11_multisensor_building_A_30days.csv',
    'iot_sensor_12.csv': 'iot_12_multisensor_building_B_30days.csv',
    'iot_sensor_13.csv': 'iot_13_multisensor_building_C_30days.csv',
    'iot_sensor_14.csv': 'iot_14_multisensor_building_D_30days.csv',
    'iot_sensor_15.csv': 'iot_15_environmental_outdoor_station1.csv',
    'iot_sensor_16.csv': 'iot_16_environmental_outdoor_station2.csv',
    'iot_sensor_17.csv': 'iot_17_environmental_outdoor_station3.csv',
    'iot_sensor_18.csv': 'iot_18_device_health_monitoring_fleet.csv',
    'iot_sensor_19.csv': 'iot_19_anomaly_detection_high_alerts.csv',
    'iot_sensor_20.csv': 'iot_20_baseline_normal_operations.csv',
}


def rename_files(base_dir: Path):
    """Rename all files according to mappings"""
    
    renamed_count = 0
    failed_renames = []
    all_mappings = {}
    
    print("="*70)
    print("DATASET FILE RENAMING")
    print("="*70)
    
    # Sales CSV
    print("\n📊 Renaming Sales CSV files...")
    sales_dir = base_dir / "sales"
    for old_name, new_name in SALES_CSV_MAPPING.items():
        old_path = sales_dir / old_name
        new_path = sales_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # Sales Excel
    print("\n📊 Renaming Sales Excel files...")
    for old_name, new_name in SALES_EXCEL_MAPPING.items():
        old_path = sales_dir / old_name
        new_path = sales_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # Clinical CSV
    print("\n🏥 Renaming Clinical CSV files...")
    clinical_dir = base_dir / "clinical"
    for old_name, new_name in CLINICAL_CSV_MAPPING.items():
        old_path = clinical_dir / old_name
        new_path = clinical_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # Clinical Excel
    print("\n🏥 Renaming Clinical Excel files...")
    for old_name, new_name in CLINICAL_EXCEL_MAPPING.items():
        old_path = clinical_dir / old_name
        new_path = clinical_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # Clinical DOC
    print("\n🏥 Renaming Clinical DOC files...")
    for old_name, new_name in CLINICAL_DOC_MAPPING.items():
        old_path = clinical_dir / old_name
        new_path = clinical_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # IoT
    print("\n📡 Renaming IoT files...")
    iot_dir = base_dir / "iot"
    for old_name, new_name in IOT_MAPPING.items():
        old_path = iot_dir / old_name
        new_path = iot_dir / new_name
        
        if old_path.exists():
            try:
                old_path.rename(new_path)
                print(f"  ✓ {old_name} → {new_name}")
                all_mappings[str(old_path)] = str(new_path)
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to rename {old_name}: {e}")
                failed_renames.append((old_name, str(e)))
        else:
            print(f"  ⚠ File not found: {old_name}")
    
    # Auditor files - no changes
    print("\n📋 Auditor files: No changes (already well-named)")
    
    # Summary
    print("\n" + "="*70)
    print("RENAMING SUMMARY")
    print("="*70)
    print(f"✅ Successfully renamed: {renamed_count} files")
    
    if failed_renames:
        print(f"❌ Failed renames: {len(failed_renames)}")
        for filename, error in failed_renames:
            print(f"   - {filename}: {error}")
    
    # Save mapping
    mapping_file = base_dir / "file_rename_mapping.json"
    with open(mapping_file, 'w') as f:
        json.dump({
            'renamed_at': '2025-12-31',
            'total_renamed': renamed_count,
            'mappings': {
                'sales_csv': SALES_CSV_MAPPING,
                'sales_excel': SALES_EXCEL_MAPPING,
                'clinical_csv': CLINICAL_CSV_MAPPING,
                'clinical_excel': CLINICAL_EXCEL_MAPPING,
                'clinical_doc': CLINICAL_DOC_MAPPING,
                'iot': IOT_MAPPING,
            }
        }, f, indent=2)
    
    print(f"\n📄 Mapping saved to: {mapping_file}")
    
    return renamed_count, failed_renames


def create_filename_guide(base_dir: Path):
    """Create a guide document for the new filenames"""
    
    guide_content = """# Dataset Filename Guide

**Updated:** December 31, 2025

This guide explains the naming convention for all test datasets.

---

## 📊 Sales Data Filenames

### CSV Files (20 files)

**Regional Data (5 files):**
- `sales_01_regional_north_2022-2023.csv` - North region sales, 2-year span
- `sales_02_regional_south_2022-2023.csv` - South region sales, 2-year span
- `sales_03_regional_east_2022-2023.csv` - East region sales, 2-year span
- `sales_04_regional_west_2022-2023.csv` - West region sales, 2-year span
- `sales_05_regional_central_2022-2023.csv` - Central region sales, 2-year span

**Product Category Data (4 files):**
- `sales_06_product_electronics_Q1-Q4.csv` - Electronics category, quarterly data
- `sales_07_product_furniture_Q1-Q4.csv` - Furniture category, quarterly data
- `sales_08_product_office_supplies_Q1-Q4.csv` - Office supplies, quarterly data
- `sales_09_product_technology_Q1-Q4.csv` - Technology category, quarterly data

**Performance Analysis (3 files):**
- `sales_10_team_performance_all_regions.csv` - Sales team metrics across regions
- `sales_11_partner_reseller_analysis.csv` - Partner/reseller performance data
- `sales_12_discount_effectiveness_2023.csv` - Promotion and discount analysis

**Customer Segment Data (3 files):**
- `sales_13_customer_segments_enterprise.csv` - Enterprise customer transactions
- `sales_14_customer_segments_smb.csv` - Small/medium business transactions
- `sales_15_customer_segments_consumer.csv` - Consumer transactions

**Analytics & Deep Dive (5 files):**
- `sales_16_quarterly_trends_5years.csv` - 5-year quarterly trend data
- `sales_17_sku_analysis_top100.csv` - Top 100 SKU performance
- `sales_18_margin_analysis_by_category.csv` - Profit margin breakdown
- `sales_19_transactions_high_value.csv` - High-value orders (>$10K)
- `sales_20_transactions_bulk_orders.csv` - Bulk order analysis

### Excel Files (5 files)

- `sales_comprehensive_5year_full_company.xlsx` - Complete 5-year company data (6 tabs)
- `sales_comprehensive_regional_breakdown.xlsx` - Regional performance analysis (6 tabs)
- `sales_comprehensive_product_performance.xlsx` - Product-focused metrics (6 tabs)
- `sales_comprehensive_partner_team_analysis.xlsx` - Partner & team analysis (6 tabs)
- `sales_comprehensive_discount_margin_analysis.xlsx` - Discount & margin focus (6 tabs)

---

## 🏥 Clinical Data Filenames

### CSV Files (20 files)

**Type 2 Diabetes (4 files):**
- `clinical_01_type2diabetes_500patients.csv` - 500 patient records
- `clinical_02_type2diabetes_1200patients.csv` - 1,200 patient records
- `clinical_03_type2diabetes_800patients.csv` - 800 patient records
- `clinical_04_type2diabetes_1500patients.csv` - 1,500 patient records

**Hypertension (4 files):**
- `clinical_05_hypertension_600patients.csv` - 600 patient records
- `clinical_06_hypertension_1100patients.csv` - 1,100 patient records
- `clinical_07_hypertension_900patients.csv` - 900 patient records
- `clinical_08_hypertension_1400patients.csv` - 1,400 patient records

**Heart Disease (4 files):**
- `clinical_09_heartdisease_700patients.csv` - 700 patient records
- `clinical_10_heartdisease_1300patients.csv` - 1,300 patient records
- `clinical_11_heartdisease_850patients.csv` - 850 patient records
- `clinical_12_heartdisease_1600patients.csv` - 1,600 patient records

**Asthma (4 files):**
- `clinical_13_asthma_550patients.csv` - 550 patient records
- `clinical_14_asthma_950patients.csv` - 950 patient records
- `clinical_15_asthma_1200patients.csv` - 1,200 patient records
- `clinical_16_asthma_1800patients.csv` - 1,800 patient records

**Mixed & Follow-up (4 files):**
- `clinical_17_mixed_conditions_large_cohort.csv` - Multiple conditions
- `clinical_18_mixed_conditions_diverse_ages.csv` - Age-diverse cohort
- `clinical_19_followup_longterm_outcomes.csv` - Long-term follow-up data
- `clinical_20_followup_adverse_events.csv` - Adverse event tracking

### Excel Files (5 files)

- `clinical_trial_phase1_demographics.xlsx` - Phase 1 trial with demographics
- `clinical_trial_phase2_efficacy.xlsx` - Phase 2 efficacy data
- `clinical_trial_phase3_safety.xlsx` - Phase 3 safety results
- `clinical_trial_multisite_combined.xlsx` - Multi-site trial data
- `clinical_trial_longitudinal_outcomes.xlsx` - Longitudinal outcome tracking

### DOC Files (5 files)

- `medical_report_diabetes_case_study.txt` - Diabetes case study report
- `medical_report_hypertension_summary.txt` - Hypertension treatment summary
- `medical_report_heartdisease_analysis.txt` - Heart disease analysis
- `medical_report_asthma_treatment.txt` - Asthma treatment protocol
- `medical_report_adverse_events_review.txt` - Adverse events review

---

## 📡 IoT Data Filenames

### CSV Files (20 files)

**Temperature Sensors (4 files):**
- `iot_01_temperature_warehouse_30days.csv` - Warehouse temp monitoring
- `iot_02_temperature_datacenter_30days.csv` - Data center temp monitoring
- `iot_03_temperature_greenhouse_30days.csv` - Greenhouse temp monitoring
- `iot_04_temperature_manufacturing_30days.csv` - Manufacturing temp monitoring

**Humidity Sensors (4 files):**
- `iot_05_humidity_warehouse_30days.csv` - Warehouse humidity monitoring
- `iot_06_humidity_datacenter_30days.csv` - Data center humidity monitoring
- `iot_07_humidity_greenhouse_30days.csv` - Greenhouse humidity monitoring
- `iot_08_humidity_manufacturing_30days.csv` - Manufacturing humidity monitoring

**Pressure Sensors (2 files):**
- `iot_09_pressure_industrial_30days.csv` - Industrial pressure monitoring
- `iot_10_pressure_hvac_system_30days.csv` - HVAC pressure monitoring

**Multi-Sensor Buildings (4 files):**
- `iot_11_multisensor_building_A_30days.csv` - Building A (temp, humidity, pressure)
- `iot_12_multisensor_building_B_30days.csv` - Building B (temp, humidity, pressure)
- `iot_13_multisensor_building_C_30days.csv` - Building C (temp, humidity, pressure)
- `iot_14_multisensor_building_D_30days.csv` - Building D (temp, humidity, pressure)

**Environmental & Specialized (6 files):**
- `iot_15_environmental_outdoor_station1.csv` - Outdoor station 1
- `iot_16_environmental_outdoor_station2.csv` - Outdoor station 2
- `iot_17_environmental_outdoor_station3.csv` - Outdoor station 3
- `iot_18_device_health_monitoring_fleet.csv` - Device health metrics
- `iot_19_anomaly_detection_high_alerts.csv` - Anomaly data with alerts
- `iot_20_baseline_normal_operations.csv` - Baseline normal operations

---

## 📋 Auditor Data Filenames

**No changes - Already well-organized by entity groups:**

```
entity_groups/
├── ACME_Corp/
├── TechStart_LLC/
├── John_Doe/
├── Jane_Smith/
└── City_Hospital/
```

Each entity folder contains:
- `{entity}_transactions.csv` - Transaction log
- `{entity}_financials.xlsx` - Financial summary
- `{entity}_audit_notes.txt` - Audit notes
- `{entity}_receipt_N.txt` - Receipts/invoices/contracts (3-5 per entity)

---

## 🎯 Quick Reference: Test Query to File Mapping

### Sales Queries

| Query | Recommended Files |
|-------|-------------------|
| "Regional profit margins" | `sales_01-05_regional_*.csv` |
| "Team performance comparison" | `sales_10_team_performance_all_regions.csv` |
| "Top SKU analysis" | `sales_17_sku_analysis_top100.csv` |
| "Discount effectiveness" | `sales_12_discount_effectiveness_2023.csv` |
| "5-year trends" | `sales_16_quarterly_trends_5years.csv` or any `sales_comprehensive_*.xlsx` |

### Clinical Queries

| Query | Recommended Files |
|-------|-------------------|
| "Type 2 Diabetes outcomes" | `clinical_01-04_type2diabetes_*.csv` |
| "Hypertension treatment comparison" | `clinical_05-08_hypertension_*.csv` |
| "Long-term follow-up" | `clinical_19_followup_longterm_outcomes.csv` |
| "Adverse events" | `clinical_20_followup_adverse_events.csv` |
| "Phase 2 trial results" | `clinical_trial_phase2_efficacy.xlsx` |

### IoT Queries

| Query | Recommended Files |
|-------|-------------------|
| "Warehouse temperature analysis" | `iot_01_temperature_warehouse_30days.csv` |
| "Data center monitoring" | `iot_02_temperature_datacenter_30days.csv`, `iot_06_humidity_datacenter_30days.csv` |
| "Building health metrics" | `iot_11-14_multisensor_building_*.csv` |
| "Anomaly detection" | `iot_19_anomaly_detection_high_alerts.csv` |
| "Baseline comparison" | `iot_20_baseline_normal_operations.csv` |

### Auditor Queries

| Query | Recommended Files |
|-------|-------------------|
| "ACME Corp financial review" | All files in `entity_groups/ACME_Corp/` |
| "John Doe spending analysis" | All files in `entity_groups/John_Doe/` |
| "Budget variance analysis" | Any `{entity}_financials.xlsx` |
| "Cross-document verification" | Multiple files from same entity folder |

---

## 📝 Naming Convention Rules

1. **Prefix**: Category identifier (sales, clinical, iot)
2. **Number**: Zero-padded sequence (01-20)
3. **Category/Type**: Descriptive category (regional, product, temperature, etc.)
4. **Subcategory**: Specific focus (north, warehouse, type2diabetes, etc.)
5. **Metadata**: Time span or size (30days, 500patients, 2022-2023, etc.)
6. **Extension**: File type (.csv, .xlsx, .txt)

**Format:** `{prefix}_{number}_{category}_{subcategory}_{metadata}.{ext}`

---

**All filenames are self-documenting for efficient testing!** 🚀
"""
    
    guide_path = base_dir / "FILENAME_GUIDE.md"
    guide_path.write_text(guide_content)
    print(f"📄 Filename guide created: {guide_path}")


if __name__ == "__main__":
    base_dir = Path(__file__).parent / "kaggle_datasets"
    
    if not base_dir.exists():
        print(f"❌ Error: Directory not found: {base_dir}")
        exit(1)
    
    # Perform renaming
    renamed_count, failed_renames = rename_files(base_dir)
    
    # Create filename guide
    create_filename_guide(base_dir)
    
    print("\n" + "="*70)
    print("✅ RENAMING COMPLETE")
    print("="*70)
    print(f"\nTotal files renamed: {renamed_count}")
    print(f"Failed renames: {len(failed_renames)}")
    print("\n📖 Documentation created:")
    print(f"   - {base_dir / 'file_rename_mapping.json'}")
    print(f"   - {base_dir / 'FILENAME_GUIDE.md'}")
    print("\n🚀 Datasets ready for testing with descriptive names!")






