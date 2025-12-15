# PDF Analyzer

Extract and analyze information from PDF documents including text, tables, images, and metadata.

## Overview

This skill provides comprehensive PDF analysis capabilities:
- Text extraction from single or multi-page PDFs
- Table detection and extraction
- Metadata extraction (author, creation date, etc.)
- Image extraction
- Document structure analysis

## Usage

### Basic Text Extraction

```python
import PyPDF2

def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text
```

### Table Extraction

```python
import pdfplumber

def extract_tables(pdf_path: str) -> list:
    """Extract all tables from a PDF file"""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables
```

### Metadata Extraction

```python
def get_metadata(pdf_path: str) -> dict:
    """Extract PDF metadata"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        metadata = reader.metadata
        return {
            'title': metadata.get('/Title'),
            'author': metadata.get('/Author'),
            'subject': metadata.get('/Subject'),
            'creator': metadata.get('/Creator'),
            'producer': metadata.get('/Producer'),
            'creation_date': metadata.get('/CreationDate'),
            'num_pages': len(reader.pages)
        }
```

## Examples

See `resources/examples.json` for common use cases and patterns.

## Dependencies

- PyPDF2: `pip install PyPDF2`
- pdfplumber: `pip install pdfplumber`

## Notes

- For encrypted PDFs, use `reader.decrypt(password)` before extraction
- pdfplumber is better for complex layouts and tables
- PyPDF2 is faster for simple text extraction
- Consider memory usage for large PDF files
