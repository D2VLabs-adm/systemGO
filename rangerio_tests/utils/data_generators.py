"""
Test data generators for creating fixture files
"""
from faker import Faker
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
import json


fake = Faker()


def generate_csv_with_pii(num_rows: int = 1000) -> pd.DataFrame:
    """
    Generate CSV with realistic PII for detection testing
    
    Args:
        num_rows: Number of rows to generate
        
    Returns:
        DataFrame with PII data
    """
    data = {
        'id': range(1, num_rows + 1),
        'name': [fake.name() for _ in range(num_rows)],
        'email': [fake.email() for _ in range(num_rows)],
        'ssn': [fake.ssn() for _ in range(num_rows)],
        'phone': [fake.phone_number() for _ in range(num_rows)],
        'credit_card': [fake.credit_card_number() for _ in range(num_rows)],
        'age': [fake.random_int(18, 80) for _ in range(num_rows)],
        'salary': [fake.random_int(30000, 150000) for _ in range(num_rows)],
        'address': [fake.address().replace('\n', ', ') for _ in range(num_rows)],
        'company': [fake.company() for _ in range(num_rows)],
    }
    return pd.DataFrame(data)


def generate_small_csv(num_rows: int = 100) -> pd.DataFrame:
    """
    Generate small CSV for basic testing
    
    Args:
        num_rows: Number of rows to generate
        
    Returns:
        DataFrame with test data
    """
    categories = ['A', 'B', 'C', 'D']
    data = {
        'id': range(1, num_rows + 1),
        'name': [f"Person_{i}" for i in range(1, num_rows + 1)],
        'email': [f"user{i}@example.com" for i in range(1, num_rows + 1)],
        'age': np.random.randint(18, 80, num_rows),
        'salary': np.random.randint(30000, 150000, num_rows),
        'category': np.random.choice(categories, num_rows),
        'score': np.random.uniform(0, 100, num_rows).round(2),
        'active': np.random.choice([True, False], num_rows),
        'join_date': pd.date_range('2020-01-01', periods=num_rows, freq='D')
    }
    return pd.DataFrame(data)


def generate_large_dataset(num_rows: int = 50000) -> pd.DataFrame:
    """
    Generate large CSV for performance testing
    
    Args:
        num_rows: Number of rows to generate
        
    Returns:
        DataFrame with large dataset
    """
    categories = ['Electronics', 'Clothing', 'Food', 'Books', 'Home', 'Sports']
    regions = ['North', 'South', 'East', 'West', 'Central']
    
    data = {
        'transaction_id': range(1, num_rows + 1),
        'customer_id': np.random.randint(1, 10000, num_rows),
        'product_id': np.random.randint(1, 1000, num_rows),
        'category': np.random.choice(categories, num_rows),
        'region': np.random.choice(regions, num_rows),
        'quantity': np.random.randint(1, 10, num_rows),
        'price': np.random.uniform(10, 1000, num_rows).round(2),
        'discount': np.random.uniform(0, 0.3, num_rows).round(2),
        'revenue': 0,  # Will calculate
        'timestamp': pd.date_range('2023-01-01', periods=num_rows, freq='30s')
    }
    
    df = pd.DataFrame(data)
    df['revenue'] = (df['price'] * df['quantity'] * (1 - df['discount'])).round(2)
    return df


def generate_messy_categories() -> pd.DataFrame:
    """
    Generate data with messy categorical values for normalization testing
    
    Returns:
        DataFrame with inconsistent categories
    """
    countries = [
        'USA', 'U.S.A.', 'United States', 'US', 'usa', 'United States of America',
        'UK', 'U.K.', 'United Kingdom', 'Great Britain', 'England',
        'Canada', 'CAN', 'ca', 'CANADA',
        'Germany', 'DE', 'deutschland', 'GERMANY',
        'France', 'FR', 'france', 'FRANCE'
    ]
    
    statuses = [
        'active', 'Active', 'ACTIVE', 'Active ',
        'inactive', 'Inactive', 'INACTIVE', 'not active',
        'pending', 'Pending', 'PENDING', 'in progress'
    ]
    
    num_rows = 500
    data = {
        'id': range(1, num_rows + 1),
        'name': [fake.name() for _ in range(num_rows)],
        'country': np.random.choice(countries, num_rows),
        'status': np.random.choice(statuses, num_rows),
        'value': np.random.randint(1, 1000, num_rows)
    }
    return pd.DataFrame(data)


def generate_excel_with_tabs() -> Dict[str, pd.DataFrame]:
    """
    Generate Excel workbook data with multiple sheets
    
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    return {
        'Sales': generate_large_dataset(1000),
        'Customers': generate_csv_with_pii(500),
        'Products': pd.DataFrame({
            'product_id': range(1, 101),
            'product_name': [f"Product {i}" for i in range(1, 101)],
            'category': np.random.choice(['A', 'B', 'C'], 100),
            'price': np.random.uniform(10, 500, 100).round(2)
        }),
        'Summary': pd.DataFrame({
            'metric': ['Total Sales', 'Total Customers', 'Avg Order Value'],
            'value': [1250000, 5000, 250.50]
        })
    }


def generate_json_data() -> List[Dict]:
    """
    Generate JSON test data
    
    Returns:
        List of dictionaries for JSON export
    """
    data = []
    for i in range(1, 201):
        record = {
            'id': i,
            'name': fake.name(),
            'email': fake.email(),
            'address': {
                'street': fake.street_address(),
                'city': fake.city(),
                'state': fake.state_abbr(),
                'zip': fake.postcode()
            },
            'orders': [
                {
                    'order_id': f"ORD-{i}-{j}",
                    'amount': round(np.random.uniform(10, 500), 2),
                    'date': fake.date_between(start_date='-1y', end_date='today').isoformat()
                }
                for j in range(1, np.random.randint(1, 6))
            ],
            'metadata': {
                'created': fake.date_time_this_year().isoformat(),
                'last_login': fake.date_time_this_month().isoformat()
            }
        }
        data.append(record)
    return data


def generate_all_fixtures(output_dir: Path):
    """
    Generate all test fixture files
    
    Args:
        output_dir: Base directory for fixtures (should be fixtures/test_data/)
    """
    print("Generating test fixtures...")
    
    # Create subdirectories
    (output_dir / 'csv').mkdir(parents=True, exist_ok=True)
    (output_dir / 'excel').mkdir(parents=True, exist_ok=True)
    (output_dir / 'json').mkdir(parents=True, exist_ok=True)
    (output_dir / 'pdf').mkdir(parents=True, exist_ok=True)
    (output_dir / 'docx').mkdir(parents=True, exist_ok=True)
    
    # Generate CSV files
    print("  Generating CSV files...")
    small_df = generate_small_csv(100)
    small_df.to_csv(output_dir / 'csv' / 'small_100rows.csv', index=False)
    
    pii_df = generate_csv_with_pii(1000)
    pii_df.to_csv(output_dir / 'csv' / 'pii_data.csv', index=False)
    
    large_df = generate_large_dataset(50000)
    large_df.to_csv(output_dir / 'csv' / 'large_50krows.csv', index=False)
    
    messy_df = generate_messy_categories()
    messy_df.to_csv(output_dir / 'csv' / 'categories_messy.csv', index=False)
    
    # Generate Excel file
    print("  Generating Excel file...")
    excel_data = generate_excel_with_tabs()
    with pd.ExcelWriter(output_dir / 'excel' / 'multi_sheet.xlsx') as writer:
        for sheet_name, df in excel_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Generate JSON file
    print("  Generating JSON file...")
    json_data = generate_json_data()
    with open(output_dir / 'json' / 'data.json', 'w') as f:
        json.dump(json_data, f, indent=2)
    
    # Generate Parquet file
    print("  Generating Parquet file...")
    large_df.to_parquet(output_dir / 'csv' / 'data.parquet')
    
    # Create placeholder files for PDF and DOCX
    print("  Creating placeholder files for PDF and DOCX...")
    (output_dir / 'pdf' / 'sample_document.pdf').touch()
    (output_dir / 'docx' / 'sample_document.docx').touch()
    
    print(f"✅ Test fixtures generated in {output_dir}")
    print(f"   - CSV: 4 files ({small_df.shape[0]} + {pii_df.shape[0]} + {large_df.shape[0]} + {messy_df.shape[0]} rows)")
    print(f"   - Excel: 1 file with {len(excel_data)} sheets")
    print(f"   - JSON: 1 file with {len(json_data)} records")
    print(f"   - Parquet: 1 file")
    print(f"   - PDF/DOCX: Placeholder files (add real documents manually)")


if __name__ == "__main__":
    from rangerio_tests.config import config
    generate_all_fixtures(config.TEST_DATA_DIR)








