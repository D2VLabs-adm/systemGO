"""
Kaggle Dataset Downloader and Realistic Test Data Generator

Downloads real datasets from Kaggle for testing and generates
realistic audit scenario files with cross-references.

Requires: kaggle API credentials configured (~/.kaggle/kaggle.json)
Install: pip install kaggle
"""
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random
import logging

logger = logging.getLogger(__name__)


def download_sales_dataset(output_dir: Path) -> Path:
    """
    Download sales dataset from Kaggle or generate realistic synthetic data
    
    Returns: Path to Excel file with multi-tab structure
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    excel_path = output_dir / "sales_data_5years.xlsx"
    
    # Check if already exists
    if excel_path.exists():
        logger.info(f"Sales dataset already exists at {excel_path}")
        return excel_path
    
    logger.info("Generating realistic 5-year sales dataset...")
    
    # Try Kaggle first, fall back to synthetic generation
    try:
        return _download_from_kaggle(output_dir, excel_path)
    except Exception as e:
        logger.warning(f"Kaggle download failed: {e}. Generating synthetic data...")
        return _generate_synthetic_sales_data(excel_path)


def _download_from_kaggle(output_dir: Path, excel_path: Path) -> Path:
    """
    Attempt to download from Kaggle with quality validation
    
    Priority datasets (in order of relevance):
    1. talhabu/us-regional-sales-data - Multi-region, good time series
    2. kyanyoga/sample-sales-data - Classic sales dataset
    3. rohitsahoo/sales-forecasting - Time series focus
    """
    try:
        import kaggle
    except ImportError:
        raise ImportError("Kaggle package not installed. Run: pip install kaggle")
    
    # Datasets ranked by quality for our testing needs
    datasets_to_try = [
        {
            'name': "talhabu/us-regional-sales-data",
            'description': "US Regional Sales Data (best for multi-year, regional analysis)",
            'priority': 1
        },
        {
            'name': "kyanyoga/sample-sales-data", 
            'description': "Classic sales dataset (good product/category coverage)",
            'priority': 2
        },
        {
            'name': "rohitsahoo/sales-forecasting",
            'description': "Sales forecasting data (strong time series)",
            'priority': 3
        }
    ]
    
    validation_results = []
    
    for dataset_info in datasets_to_try:
        dataset = dataset_info['name']
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Attempting: {dataset}")
            logger.info(f"Description: {dataset_info['description']}")
            logger.info(f"Priority: {dataset_info['priority']}")
            logger.info(f"{'='*60}")
            
            # Download
            kaggle.api.dataset_download_files(dataset, path=str(output_dir), unzip=True)
            
            # Find and validate CSV files
            for file in output_dir.glob("*.csv"):
                logger.info(f"Found CSV: {file.name}")
                
                try:
                    df = pd.read_csv(file)
                    is_valid, reason = _validate_sales_dataset(df)
                    
                    if is_valid:
                        logger.info(f"✓ VALIDATION PASSED: {dataset}")
                        logger.info(f"  Converting to multi-tab Excel...")
                        result = _convert_to_multitab_excel(file, excel_path)
                        logger.info(f"✓ SUCCESS: Using Kaggle dataset '{dataset}'")
                        return result
                    else:
                        validation_results.append({
                            'dataset': dataset,
                            'file': file.name,
                            'valid': False,
                            'reason': reason
                        })
                        logger.warning(f"✗ Validation failed: {reason}")
                        
                except Exception as e:
                    logger.warning(f"Error processing {file.name}: {e}")
                    continue
            
            # Check for Excel files
            for file in output_dir.glob("*.xlsx"):
                logger.info(f"Found Excel: {file.name}")
                
                try:
                    excel_file = pd.ExcelFile(file)
                    df = pd.read_excel(file, sheet_name=excel_file.sheet_names[0])
                    is_valid, reason = _validate_sales_dataset(df)
                    
                    if is_valid:
                        logger.info(f"✓ VALIDATION PASSED: {dataset}")
                        result = _enhance_excel_with_tabs(file, excel_path)
                        logger.info(f"✓ SUCCESS: Using Kaggle dataset '{dataset}'")
                        return result
                    else:
                        validation_results.append({
                            'dataset': dataset,
                            'file': file.name,
                            'valid': False,
                            'reason': reason
                        })
                        logger.warning(f"✗ Validation failed: {reason}")
                        
                except Exception as e:
                    logger.warning(f"Error processing {file.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Failed to download {dataset}: {e}")
            validation_results.append({
                'dataset': dataset,
                'valid': False,
                'reason': f"Download failed: {e}"
            })
            continue
    
    # If we get here, all Kaggle attempts failed
    logger.warning("\n" + "="*60)
    logger.warning("ALL KAGGLE DATASETS FAILED VALIDATION")
    logger.warning("="*60)
    for result in validation_results:
        logger.warning(f"  {result['dataset']}: {result['reason']}")
    logger.warning("="*60)
    
    raise Exception("All Kaggle downloads failed validation. Will use synthetic data.")


def _validate_sales_dataset(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate that downloaded dataset meets our testing requirements
    
    Returns: (is_valid, reason)
    """
    required_characteristics = {
        'min_rows': 1000,
        'min_date_range_years': 2,
        'required_column_types': {
            'date': ['date', 'order date', 'order_date', 'transaction date', 'timestamp'],
            'region': ['region', 'area', 'territory', 'location', 'state'],
            'sales': ['sales', 'revenue', 'amount', 'total'],
            'profit': ['profit', 'margin', 'net', 'earnings'],
            'product': ['product', 'item', 'sku', 'product name'],
        }
    }
    
    # Check minimum rows
    if len(df) < required_characteristics['min_rows']:
        return False, f"Insufficient rows: {len(df)} < {required_characteristics['min_rows']}"
    
    # Check for required column types
    df_columns_lower = [col.lower() for col in df.columns]
    found_columns = {}
    
    for col_type, possible_names in required_characteristics['required_column_types'].items():
        found = False
        for possible_name in possible_names:
            if any(possible_name in col for col in df_columns_lower):
                found = True
                found_columns[col_type] = next(col for col in df.columns if possible_name in col.lower())
                break
        
        if not found:
            return False, f"Missing required column type: {col_type}"
    
    # Check date range
    if 'date' in found_columns:
        try:
            date_col = found_columns['date']
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            date_range = (df[date_col].max() - df[date_col].min()).days / 365.25
            
            if date_range < required_characteristics['min_date_range_years']:
                return False, f"Insufficient date range: {date_range:.1f} years < {required_characteristics['min_date_range_years']} years"
        except Exception as e:
            return False, f"Date parsing failed: {e}"
    
    # Check for excessive nulls (>50% in key columns)
    for col_type in ['sales', 'product']:
        if col_type in found_columns:
            col_name = found_columns[col_type]
            null_pct = (df[col_name].isna().sum() / len(df)) * 100
            if null_pct > 50:
                return False, f"Excessive nulls in {col_type}: {null_pct:.1f}%"
    
    # Check for reasonable value ranges (sales/revenue should be positive)
    if 'sales' in found_columns:
        col_name = found_columns['sales']
        if df[col_name].dtype in [np.float64, np.int64]:
            negative_pct = (df[col_name] < 0).sum() / len(df) * 100
            if negative_pct > 10:
                return False, f"Too many negative values in sales: {negative_pct:.1f}%"
    
    logger.info(f"✓ Dataset validated successfully")
    logger.info(f"  - Rows: {len(df):,}")
    logger.info(f"  - Date range: {date_range:.1f} years")
    logger.info(f"  - Found columns: {found_columns}")
    
    return True, "Valid"


def _convert_to_multitab_excel(csv_path: Path, output_path: Path) -> Path:
    """
    Convert downloaded CSV to multi-tab Excel with realistic structure
    Validates dataset before conversion.
    """
    df = pd.read_csv(csv_path)
    
    # Validate dataset meets our requirements
    is_valid, reason = _validate_sales_dataset(df)
    if not is_valid:
        logger.warning(f"Kaggle dataset validation failed: {reason}")
        logger.info("Falling back to synthetic data generation...")
        return _generate_synthetic_sales_data(output_path)
    
    # Create writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main sales transactions tab
        df.to_excel(writer, sheet_name='Sales Transactions', index=False)
        
        # Product catalog tab (unique products)
        if 'Product' in df.columns or 'Product Name' in df.columns:
            product_col = 'Product' if 'Product' in df.columns else 'Product Name'
            products = df[[product_col]].drop_duplicates()
            products.to_excel(writer, sheet_name='Product Catalog', index=False)
        
        # Regional data tab (aggregated by region)
        if 'Region' in df.columns:
            regional = df.groupby('Region').agg({
                df.columns[df.columns.str.contains('Sales|Revenue|Profit', case=False, na=False)][0]: ['sum', 'mean', 'count']
            }).reset_index()
            regional.to_excel(writer, sheet_name='Regional Data', index=False)
        
        # Sales team performance (if team data exists)
        if 'Sales Team' in df.columns or 'Salesperson' in df.columns:
            team_col = 'Sales Team' if 'Sales Team' in df.columns else 'Salesperson'
            performance = df.groupby(team_col).agg({
                df.columns[df.columns.str.contains('Sales|Revenue', case=False, na=False)][0]: 'sum'
            }).reset_index()
            performance.to_excel(writer, sheet_name='Sales Team Performance', index=False)
    
    logger.info(f"Created multi-tab Excel at {output_path}")
    return output_path


def _enhance_excel_with_tabs(excel_path: Path, output_path: Path) -> Path:
    """
    Enhance existing Excel file with additional tabs if needed
    Validates dataset before using it.
    """
    # Read and validate
    excel_file = pd.ExcelFile(excel_path)
    df = pd.read_excel(excel_path, sheet_name=excel_file.sheet_names[0])
    
    # Validate dataset
    is_valid, reason = _validate_sales_dataset(df)
    if not is_valid:
        logger.warning(f"Kaggle Excel validation failed: {reason}")
        logger.info("Falling back to synthetic data generation...")
        return _generate_synthetic_sales_data(output_path)
    
    # If already has multiple tabs, just copy
    if len(excel_file.sheet_names) > 1:
        import shutil
        shutil.copy(excel_path, output_path)
        logger.info(f"Using Kaggle dataset with {len(excel_file.sheet_names)} tabs")
        return output_path
    
    # Otherwise, enhance it (add more tabs)
    logger.info("Enhancing Kaggle dataset with additional tabs...")
    return _convert_to_multitab_excel(excel_path, output_path)


def _generate_synthetic_sales_data(output_path: Path) -> Path:
    """
    Generate realistic 5-year sales dataset with multiple tabs
    """
    logger.info("Generating synthetic sales data (5 years, 10K transactions)...")
    
    # Set random seed for reproducibility
    np.random.seed(42)
    random.seed(42)
    
    # Generate date range (5 years)
    start_date = datetime(2019, 1, 1)
    end_date = datetime(2023, 12, 31)
    num_transactions = 10000
    
    dates = [start_date + timedelta(days=random.randint(0, (end_date - start_date).days)) 
             for _ in range(num_transactions)]
    
    # Define realistic dimensions
    regions = ['North', 'South', 'East', 'West', 'Central']
    products = [
        'Widget A', 'Widget B', 'Gadget X', 'Gadget Y', 'Doohickey Pro',
        'Thingamajig', 'Whatchamacallit', 'Gizmo Elite', 'Device Plus', 'Tool Master'
    ]
    categories = ['Electronics', 'Office Supplies', 'Furniture', 'Technology', 'Accessories']
    sales_teams = [f'Team {i}' for i in range(1, 11)]
    customer_segments = ['Enterprise', 'SMB', 'Consumer', 'Government']
    resellers = [f'Reseller {chr(65+i)}' for i in range(10)]
    
    # Generate main sales data
    data = {
        'Order ID': [f'ORD{str(i).zfill(6)}' for i in range(1, num_transactions + 1)],
        'Order Date': dates,
        'Region': np.random.choice(regions, num_transactions),
        'Sales Team': np.random.choice(sales_teams, num_transactions),
        'Product': np.random.choice(products, num_transactions),
        'Category': np.random.choice(categories, num_transactions),
        'Customer Segment': np.random.choice(customer_segments, num_transactions),
        'Reseller': np.random.choice(resellers, num_transactions),
        'Quantity': np.random.randint(1, 100, num_transactions),
        'Unit Price': np.random.uniform(10, 1000, num_transactions).round(2),
    }
    
    df = pd.DataFrame(data)
    
    # Calculate derived columns
    df['Revenue'] = (df['Quantity'] * df['Unit Price']).round(2)
    df['Discount %'] = np.random.uniform(0, 25, num_transactions).round(1)
    df['Discount Amount'] = (df['Revenue'] * df['Discount %'] / 100).round(2)
    df['Cost'] = (df['Revenue'] * np.random.uniform(0.4, 0.7, num_transactions)).round(2)
    df['Profit'] = (df['Revenue'] - df['Discount Amount'] - df['Cost']).round(2)
    df['Profit Margin %'] = ((df['Profit'] / df['Revenue']) * 100).round(2)
    
    # Introduce some missing values (20%)
    missing_indices = np.random.choice(df.index, size=int(len(df) * 0.2), replace=False)
    df.loc[missing_indices[:len(missing_indices)//3], 'Profit'] = np.nan
    df.loc[missing_indices[len(missing_indices)//3:2*len(missing_indices)//3], 'Profit Margin %'] = np.nan
    df.loc[missing_indices[2*len(missing_indices)//3:], 'Discount %'] = np.nan
    
    # Add sales targets (for team performance analysis)
    df['Target Achievement %'] = np.random.uniform(70, 150, num_transactions).round(1)
    
    # Create Excel with multiple tabs
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Tab 1: Sales Transactions
        df.to_excel(writer, sheet_name='Sales Transactions', index=False)
        
        # Tab 2: Product Catalog
        product_catalog = df[['Product', 'Category', 'Unit Price']].drop_duplicates()
        product_catalog['Supplier'] = np.random.choice(['Supplier A', 'Supplier B', 'Supplier C'], len(product_catalog))
        product_catalog.to_excel(writer, sheet_name='Product Catalog', index=False)
        
        # Tab 3: Regional Data (aggregated)
        regional = df.groupby('Region').agg({
            'Revenue': ['sum', 'mean', 'count'],
            'Profit': 'sum',
            'Profit Margin %': 'mean'
        }).reset_index()
        regional.columns = ['Region', 'Total Revenue', 'Avg Revenue', 'Transactions', 'Total Profit', 'Avg Margin %']
        regional.to_excel(writer, sheet_name='Regional Data', index=False)
        
        # Tab 4: Sales Team Performance
        team_perf = df.groupby('Sales Team').agg({
            'Revenue': 'sum',
            'Profit': 'sum',
            'Target Achievement %': 'mean',
            'Order ID': 'count'
        }).reset_index()
        team_perf.columns = ['Sales Team', 'Total Revenue', 'Total Profit', 'Avg Target Achievement %', 'Deals Closed']
        team_perf.to_excel(writer, sheet_name='Sales Team Performance', index=False)
    
    logger.info(f"Generated synthetic sales data at {output_path}")
    return output_path


def create_auditor_scenario(output_dir: Path) -> Dict[str, Path]:
    """
    Create realistic auditor scenario with mixed file types
    
    Returns: Dict with paths to all generated files
    """
    output_dir = Path(output_dir) / "auditor_scenario"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Creating auditor scenario files...")
    
    files = {}
    
    # 1. Excel: Financial Statements
    files['excel'] = _create_financial_statements(output_dir)
    
    # 2. PDF: Board Meeting Minutes
    files['pdf'] = _create_board_minutes(output_dir, files['excel'])
    
    # 3. DOCX: Audit Findings Draft
    files['docx'] = _create_audit_findings(output_dir, files['excel'])
    
    # 4. TXT: Email Thread
    files['txt'] = _create_email_thread(output_dir, files['excel'])
    
    logger.info(f"Created auditor scenario at {output_dir}")
    return files


def _create_financial_statements(output_dir: Path) -> Path:
    """
    Create Excel file with financial statements (multiple tabs)
    """
    excel_path = output_dir / "Financial_Statements_2023.xlsx"
    
    if excel_path.exists():
        return excel_path
    
    # Balance Sheet data
    balance_sheet = pd.DataFrame({
        'Account': [
            'Cash and Equivalents', 'Accounts Receivable', 'Inventory', 'Property & Equipment',
            'Total Assets', '', 'Accounts Payable', 'Long-term Debt', 'Total Liabilities',
            'Shareholders Equity', 'Total Liabilities & Equity'
        ],
        '2023': [1250000, 890000, 450000, 3200000, 5790000, None, 320000, 1800000, 2120000, 3670000, 5790000],
        '2022': [980000, 750000, 420000, 2900000, 5050000, None, 290000, 1600000, 1890000, 3160000, 5050000]
    })
    
    # Income Statement data
    income_statement = pd.DataFrame({
        'Line Item': [
            'Revenue', 'Cost of Goods Sold', 'Gross Profit', '',
            'Operating Expenses', 'Operating Income', '',
            'Interest Expense', 'Income Before Tax', 'Income Tax', 'Net Income'
        ],
        '2023': [8500000, 4250000, 4250000, None, 2100000, 2150000, None, 120000, 2030000, 609000, 1421000],
        '2022': [7200000, 3600000, 3600000, None, 1900000, 1700000, None, 110000, 1590000, 477000, 1113000]
    })
    
    # Cash Flow data
    cash_flow = pd.DataFrame({
        'Category': [
            'Operating Activities:', 'Net Income', 'Depreciation', 'Changes in Working Capital',
            'Net Cash from Operations', '',
            'Investing Activities:', 'Capital Expenditures', 'Equipment Purchases',
            'Net Cash from Investing', '',
            'Financing Activities:', 'Debt Proceeds', 'Debt Payments',
            'Net Cash from Financing', '',
            'Net Change in Cash'
        ],
        '2023': [None, 1421000, 350000, -120000, 1651000, None,
                 None, -450000, -180000, -630000, None,
                 None, 500000, -251000, 249000, None, 1270000],
        '2022': [None, 1113000, 320000, -95000, 1338000, None,
                 None, -380000, -150000, -530000, None,
                 None, 400000, -220000, 180000, None, 988000]
    })
    
    # Write to Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        balance_sheet.to_excel(writer, sheet_name='Balance Sheet', index=False)
        income_statement.to_excel(writer, sheet_name='Income Statement', index=False)
        cash_flow.to_excel(writer, sheet_name='Cash Flow', index=False)
    
    return excel_path


def _create_board_minutes(output_dir: Path, financial_path: Path) -> Path:
    """
    Create text-based PDF (board meeting minutes) with cross-references to financial data
    """
    pdf_path = output_dir / "Board_Meeting_Minutes_Q3_2023.txt"  # Using TXT as PDF placeholder
    
    if pdf_path.exists():
        return pdf_path
    
    content = """
BOARD MEETING MINUTES
Acme Corporation
Q3 2023 - September 15, 2023

ATTENDEES:
- John Smith, CEO
- Sarah Johnson, CFO
- Michael Brown, COO
- Emily Davis, Board Chair
- Robert Wilson, Board Member
- Jennifer Lee, Board Member

AGENDA:
1. Q3 Financial Review
2. Capital Expenditure Proposals
3. Debt Refinancing Discussion
4. New Equipment Purchases

---

1. Q3 FINANCIAL REVIEW

Sarah Johnson presented Q3 financial results:
- Revenue for Q3: $2,150,000 (up 15% YoY)
- Operating expenses: $520,000
- Net income projection for full year: $1,400,000

The Board noted strong revenue growth and approved continued investment in operations.

---

2. CAPITAL EXPENDITURE PROPOSALS

Michael Brown proposed three major capital expenditures for Q4:

a) Manufacturing Equipment Upgrade - $250,000
   - Approved unanimously (Vote: 6-0)
   - Expected to improve efficiency by 20%
   
b) New Warehouse Facility - $500,000
   - Approved (Vote: 5-1, Wilson dissenting)
   - Construction to begin Q1 2024
   
c) IT Infrastructure Modernization - $180,000
   - Tabled for further review
   - Requires additional cost-benefit analysis

TOTAL APPROVED CAPEX: $750,000

---

3. DEBT REFINANCING

Sarah Johnson presented debt refinancing proposal:
- Current long-term debt: $1,800,000
- Proposed new facility: $2,100,000
- Interest rate reduction from 6.5% to 5.2%
- Approved unanimously (Vote: 6-0)

---

4. NEW EQUIPMENT PURCHASES

Robert Wilson raised concerns about equipment purchases totaling $180,000 
that appeared in preliminary expense reports but were not reflected in 
the capital budget or cash flow projections.

Sarah Johnson noted these were approved by CEO under discretionary authority
(<$200K) and will be reflected in Q4 statements.

Board requested detailed report on all discretionary expenditures >$100K.

---

ACTION ITEMS:
1. CFO to provide detailed capex breakdown by month (Sarah Johnson, due Oct 1)
2. COO to submit warehouse construction timeline (Michael Brown, due Oct 15)
3. CFO to provide discretionary spending report (Sarah Johnson, due Sep 30)

Meeting adjourned at 4:30 PM.

Recorded by: Jane Martinez, Corporate Secretary
"""
    
    pdf_path.write_text(content)
    return pdf_path


def _create_audit_findings(output_dir: Path, financial_path: Path) -> Path:
    """
    Create DOCX-style audit findings (using TXT)
    """
    docx_path = output_dir / "Audit_Findings_Draft.txt"  # Using TXT as DOCX placeholder
    
    if docx_path.exists():
        return docx_path
    
    content = """
AUDIT FINDINGS - DRAFT
Acme Corporation - FY 2023
Prepared by: Anderson & Associates, CPAs
Date: October 5, 2023

---

EXECUTIVE SUMMARY

This report presents preliminary findings from our audit of Acme Corporation's 
financial statements for the fiscal year ending December 31, 2023.

Overall Assessment: SATISFACTORY with minor exceptions

---

FINDINGS REQUIRING MANAGEMENT RESPONSE

Finding 1: Capital Expenditure Documentation [MEDIUM PRIORITY]

During our review, we identified equipment purchases totaling $180,000 that:
- Were approved under CEO discretionary authority
- Lack complete supporting documentation
- Do not appear in the approved capital budget
- Are not reflected in Q3 cash flow statement

The expenditures include:
- CNC Machine: $95,000 (Invoice #INV-2023-0847, approved by J. Smith)
- Laser Cutter: $45,000 (Invoice #INV-2023-0923, approved by J. Smith)  
- Quality Control Equipment: $40,000 (Invoice #INV-2023-0956, approved by J. Smith)

TOTAL: $180,000

Management Response Required:
1. Provide purchase authorization documentation
2. Explain absence from cash flow projections
3. Reconcile with capital budget

---

Finding 2: Revenue Recognition Timing [LOW PRIORITY]

Board minutes reference Q3 revenue of $2,150,000, while Income Statement 
shows full-year revenue of $8,500,000 (implying Q3 actual was $2,125,000).

Difference: $25,000

This appears to be a timing difference related to one large customer order
recognized in different periods for management vs. GAAP reporting.

Recommendation: Clarify revenue recognition policies for board reporting.

---

Finding 3: Debt Refinancing Documentation [INFORMATIONAL]

Board approved debt refinancing from $1,800,000 to $2,100,000 on September 15.
As of October 5, loan documents are still pending final execution.

Current balance sheet shows $1,800,000 (unchanged).

No action required - transaction in progress.

---

TRANSACTIONS REQUIRING REVIEW

The following transactions have been flagged for management review:

1. Equipment Purchase #1 (Aug 15, 2023)
   - Amount: $95,000
   - Vendor: MachineWorks Inc.
   - Approver: John Smith (CEO)
   - Missing: Board approval for >$50K purchase
   
2. Equipment Purchase #2 (Sep 8, 2023)
   - Amount: $45,000  
   - Vendor: Laser Systems LLC
   - Approver: John Smith (CEO)
   - Missing: Competitive bid documentation
   
3. Consulting Fees (Jul-Sep 2023)
   - Amount: $75,000
   - Vendor: Strategic Advisors Group
   - Approver: Sarah Johnson (CFO)
   - Missing: Scope of work documentation

Board policy requires approval for expenditures >$50,000.

---

NEXT STEPS

1. Management response due: October 20, 2023
2. Follow-up review scheduled: November 1, 2023
3. Final audit report target: November 30, 2023

---

DRAFT - FOR INTERNAL USE ONLY
"""
    
    docx_path.write_text(content)
    return docx_path


def _create_email_thread(output_dir: Path, financial_path: Path) -> Path:
    """
    Create email thread discussing financial transactions
    """
    txt_path = output_dir / "Email_Thread.txt"
    
    if txt_path.exists():
        return txt_path
    
    content = """
EMAIL THREAD: Equipment Purchase Approvals
===========================================

From: Sarah Johnson <sarah.johnson@acmecorp.com>
To: John Smith <john.smith@acmecorp.com>
Date: August 10, 2023 2:15 PM
Subject: Urgent: CNC Machine Purchase Approval

John,

MachineWorks is offering a 15% discount if we commit by end of week.
The CNC machine we discussed is $95,000 (normally $112,000).

This is within your discretionary authority (<$100K) and critical for 
Q4 production ramp. Can you approve today so we don't miss the discount?

Invoice will be coded to Equipment CapEx.

Thanks,
Sarah

---

From: John Smith <john.smith@acmecorp.com>
To: Sarah Johnson <sarah.johnson@acmecorp.com>
Date: August 10, 2023 4:42 PM
Subject: RE: Urgent: CNC Machine Purchase Approval

Approved. Great deal!

However, I thought our policy required board approval for anything >$50K?
Should we run this by the board first, or document this as emergency approval?

John

---

From: Sarah Johnson <sarah.johnson@acmecorp.com>
To: John Smith <john.smith@acmecorp.com>
Date: August 10, 2023 5:03 PM
Subject: RE: Urgent: CNC Machine Purchase Approval

You're right about the policy, but your discretionary authority is up to $200K
per our updated bylaws (approved last year). 

I'll add a note to the board minutes for transparency. We'll disclose it at
the September meeting.

Processing the order now!
Sarah

---

From: Robert Wilson <robert.wilson@acmecorp.com>  
To: John Smith <john.smith@acmecorp.com>
Cc: Sarah Johnson <sarah.johnson@acmecorp.com>
Date: September 18, 2023 9:30 AM
Subject: Board Meeting Follow-up: Equipment Purchases

John & Sarah,

At last week's board meeting, you mentioned $180,000 in equipment purchases 
under CEO discretionary authority. Can you provide details?

I couldn't find these in the Q3 cash flow statement that was presented. 
Where are they reflected?

Also, if your discretionary authority is $200K, shouldn't purchases approaching
that limit be disclosed proactively to the board rather than after the fact?

Thanks,
Robert

---

From: Sarah Johnson <sarah.johnson@acmecorp.com>
To: Robert Wilson <robert.wilson@acmecorp.com>
Cc: John Smith <john.smith@acmecorp.com>
Date: September 18, 2023 2:15 PM
Subject: RE: Board Meeting Follow-up: Equipment Purchases

Robert,

Valid questions. Here's the breakdown:

1. CNC Machine: $95,000 (Aug 15 - Invoice INV-2023-0847)
2. Laser Cutter: $45,000 (Sep 8 - Invoice INV-2023-0923)
3. QC Equipment: $40,000 (Sep 12 - Invoice INV-2023-0956)

Total: $180,000

These weren't in the Q3 cash flow because:
- Aug/Sep purchases will be paid in Q4 (60-day terms)
- Accounting will reflect in Q4 cash flow

You're right about proactive disclosure. Going forward, we'll report any 
discretionary spending >$100K to the board monthly rather than quarterly.

I'll have the detailed report ready by Sep 30 as requested.

Sarah

---

From: Emily Davis <emily.davis@acmecorp.com>
To: Sarah Johnson <sarah.johnson@acmecorp.com>
Cc: John Smith <john.smith@acmecorp.com>, Robert Wilson <robert.wilson@acmecorp.com>
Date: September 19, 2023 10:45 AM
Subject: RE: Board Meeting Follow-up: Equipment Purchases

Sarah & John,

As Board Chair, I want to echo Robert's concerns but also recognize that
these purchases appear to be legitimate operational needs within policy.

For the discretionary spending report, please include:
- Full invoices and approvals
- Business justification
- Why each was time-sensitive/couldn't wait for board approval

This will help us refine our governance policies.

Emily Davis
Board Chair

---

END OF EMAIL THREAD
"""
    
    txt_path.write_text(content)
    return txt_path


if __name__ == "__main__":
    # Test the functions
    logging.basicConfig(level=logging.INFO)
    
    test_dir = Path("./test_data")
    
    print("Downloading/generating sales dataset...")
    sales_file = download_sales_dataset(test_dir)
    print(f"Sales data: {sales_file}")
    
    print("\nCreating auditor scenario...")
    auditor_files = create_auditor_scenario(test_dir)
    for file_type, path in auditor_files.items():
        print(f"{file_type.upper()}: {path}")

