# Data Processor

Process, transform, and analyze structured data from various formats.

## Overview

This skill provides comprehensive data processing capabilities:
- CSV/Excel file reading and writing
- JSON data manipulation
- Data cleaning and validation
- Data transformation and aggregation
- Format conversion
- Data quality analysis

## Usage

### CSV Processing

```python
import pandas as pd

def process_csv(input_path: str, output_path: str) -> dict:
    """Read, process, and save CSV data"""
    # Read CSV
    df = pd.read_csv(input_path)

    # Basic cleaning
    df = df.drop_duplicates()
    df = df.dropna(subset=['important_column'])

    # Transformation
    df['new_column'] = df['col1'] + df['col2']

    # Save result
    df.to_csv(output_path, index=False)

    return {
        'rows_processed': len(df),
        'columns': list(df.columns),
        'output_file': output_path
    }
```

### JSON Processing

```python
import json

def process_json(input_path: str, transform_func=None) -> dict:
    """Read and transform JSON data"""
    with open(input_path, 'r') as f:
        data = json.load(f)

    # Apply transformation
    if transform_func:
        data = transform_func(data)

    return data

def flatten_json(nested_json: dict, prefix: str = '') -> dict:
    """Flatten nested JSON structure"""
    flattened = {}
    for key, value in nested_json.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_json(value, new_key))
        else:
            flattened[new_key] = value
    return flattened
```

### Data Aggregation

```python
def aggregate_data(df: pd.DataFrame, group_by: list, agg_funcs: dict) -> pd.DataFrame:
    """Aggregate data by specified columns"""
    # Example: group_by=['category'], agg_funcs={'sales': 'sum', 'quantity': 'mean'}
    result = df.groupby(group_by).agg(agg_funcs).reset_index()
    return result
```

### Data Merging

```python
def merge_datasets(df1: pd.DataFrame, df2: pd.DataFrame,
                  on: str, how: str = 'inner') -> pd.DataFrame:
    """Merge two datasets"""
    merged = pd.merge(df1, df2, on=on, how=how)
    return merged
```

### Data Validation

```python
def validate_data(df: pd.DataFrame, rules: dict) -> dict:
    """Validate data against rules"""
    validation_results = {
        'valid': True,
        'errors': []
    }

    # Check required columns
    if 'required_columns' in rules:
        missing = set(rules['required_columns']) - set(df.columns)
        if missing:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Missing columns: {missing}")

    # Check data types
    if 'data_types' in rules:
        for col, expected_type in rules['data_types'].items():
            if col in df.columns and df[col].dtype != expected_type:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Column {col} has type {df[col].dtype}, expected {expected_type}"
                )

    # Check value ranges
    if 'ranges' in rules:
        for col, (min_val, max_val) in rules['ranges'].items():
            if col in df.columns:
                invalid = df[(df[col] < min_val) | (df[col] > max_val)]
                if len(invalid) > 0:
                    validation_results['valid'] = False
                    validation_results['errors'].append(
                        f"Column {col} has {len(invalid)} values outside range [{min_val}, {max_val}]"
                    )

    return validation_results
```

### Format Conversion

```python
def convert_format(input_path: str, output_path: str,
                  input_format: str, output_format: str) -> bool:
    """Convert between data formats"""
    # Read input
    if input_format == 'csv':
        df = pd.read_csv(input_path)
    elif input_format == 'json':
        df = pd.read_json(input_path)
    elif input_format == 'excel':
        df = pd.read_excel(input_path)

    # Write output
    if output_format == 'csv':
        df.to_csv(output_path, index=False)
    elif output_format == 'json':
        df.to_json(output_path, orient='records', indent=2)
    elif output_format == 'excel':
        df.to_excel(output_path, index=False)

    return True
```

## Examples

See `resources/transformation_patterns.json` for common data transformation patterns.

## Dependencies

- pandas: `pip install pandas`
- openpyxl: `pip install openpyxl` (for Excel support)
- numpy: `pip install numpy` (usually included with pandas)

## Notes

- For large datasets (>1GB), consider using chunking: `pd.read_csv(file, chunksize=10000)`
- Use `dtype` parameter to optimize memory: `pd.read_csv(file, dtype={'col1': 'int32'})`
- Validate data early to catch issues before processing
- Always handle missing values explicitly
- Use `pd.to_datetime()` for date parsing
- Consider using `dask` for datasets that don't fit in memory
