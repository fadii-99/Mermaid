import markdown2
from tabula import read_pdf
from tabulate import tabulate
import re
import fitz
import pdfplumber

ALLOWED_EXTENSIONS = {'pdf'}


def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_tables_with_tabula(pdf_path):
    tables = read_pdf(pdf_path, pages="all", multiple_tables=True)
    return tables

def format_table_as_text(tables):
    formatted_tables = []
    for table in tables:
        formatted_tables.append(tabulate(table, tablefmt="grid"))
    return formatted_tables

def deduplicate_tables(tables):
    unique_tables = []
    seen_rows = set()
    for table in tables:
        rows = table.split("\n")
        first_three_rows = "\n".join(rows[:3])
        if first_three_rows not in seen_rows:
            seen_rows.add(first_three_rows)
            unique_tables.append(table)
    return unique_tables

def parse_markdown_table(table: str):
    """
    Parse a markdown table and return structured data.

    Args:
        table (str): The markdown table as a string.

    Returns:
        dict: A dictionary with 'headers' and 'rows'.
    """
    lines = table.strip().split('\n')
    
    headers = [header.strip() for header in lines[0].split('|') if header.strip()]
    
    rows = []
    current_row = {}
    
    for line in lines[2:]:
        if line.startswith('|---') or not line.strip():
            continue
        
        columns = [col.strip() for col in line.split('|')[1:-1]]
        
        columns = [col if col.lower() != 'nan' else '' for col in columns]
        
        if columns[0] == '':
            current_row[headers[2]] += ' ' + columns[2]  
        else:
            if current_row:
                rows.append(current_row)
            
            current_row = {headers[i]: columns[i] for i in range(len(headers))}
    
    if current_row:
        rows.append(current_row)
    
    return {'headers': headers, 'rows': rows}

def parse_assessment_tables(assessment_text):
    tables = []
    summaries = []
    current_table = None

    row_pattern = r"\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|"
    current_summary = []
    in_summary_section = False

    for line in assessment_text.splitlines():
        line = line.strip()

        if line.startswith("###") and not line.lower().startswith("### summary"):
            if in_summary_section:
                summaries.append(" ".join(current_summary).strip())
                current_summary = []
                in_summary_section = False

            if current_table:
                tables.append(current_table)
            current_table = {"title": line.replace("###", "").strip(), "rows": []}

        elif line.startswith("| Category") or line.startswith("|---"):
            continue

        elif current_table and re.match(row_pattern, line):
            if all(col.strip("- ") == "" for col in line.split("|")):
                continue

            match = re.match(row_pattern, line)
            category, score, percentile, description = [item.strip() for item in match.groups()]
            current_table["rows"].append({
                "category": category,
                "score": score,
                "percentile": percentile,
                "description": description
            })

        elif line.lower().startswith("### summary"):
            if current_table:
                tables.append(current_table)
                current_table = None
            in_summary_section = True

        elif in_summary_section:
            if line.startswith("###"):
                summaries.append(" ".join(current_summary).strip())
                current_summary = []
                in_summary_section = False
            else:
                current_summary.append(line)

    if current_table:
        tables.append(current_table)
    if in_summary_section and current_summary:
        summaries.append(" ".join(current_summary).strip())

    return {"tables": tables, "summaries": summaries}




def format_report_content(report_content):
    report_content = report_content.replace("  ", "  \n")  
    return markdown2.markdown(report_content)