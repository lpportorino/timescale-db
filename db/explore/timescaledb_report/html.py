"""
Functions for generating HTML reports.
"""

import logging
import markdown
import os
from datetime import datetime
from timescaledb_report.strings import get_string, get_config

logger = logging.getLogger(__name__)

def markdown_to_html(md_content, title=None):
    """Convert markdown content to HTML

    Args:
        md_content (str): Markdown content
        title (str, optional): HTML page title

    Returns:
        str: HTML content
    """
    # Get title from config if not provided
    if title is None:
        title = get_string("html.title", "TimescaleDB Report")

    # Convert markdown to HTML
    html_body = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.toc',
            'markdown.extensions.attr_list'
        ]
    )

    # Get CSS styles from config if available
    styles = get_config().get('html', {}).get('style', {})

    # Define CSS based on configuration or use defaults
    css = f"""
        body {{
            {styles.get('body', 'font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px;')}
        }}
        h1, h2, h3, h4 {{
            {styles.get('headings', 'color: #2c3e50; margin-top: 1.5em;')}
        }}
        h1 {{
            {styles.get('h1', 'border-bottom: 2px solid #3498db; padding-bottom: 10px;')}
        }}
        h2 {{
            {styles.get('h2', 'border-bottom: 1px solid #bdc3c7; padding-bottom: 5px;')}
        }}
        h3 {{
            {styles.get('h3', 'color: #16a085;')}
        }}
        table {{
            {styles.get('table', 'border-collapse: collapse; width: 100%; margin: 20px 0;')}
        }}
        th, td {{
            {styles.get('table_cell', 'padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd;')}
        }}
        th {{
            {styles.get('th', 'background-color: #f2f2f2; font-weight: bold;')}
        }}
        tr:hover {{
            {styles.get('tr_hover', 'background-color: #f5f5f5;')}
        }}
        code {{
            {styles.get('code', 'background-color: #f8f8f8; padding: 2px 5px; border-radius: 3px; font-family: Monaco, Consolas, "Courier New", monospace;')}
        }}
        pre {{
            {styles.get('pre', 'background-color: #f8f8f8; padding: 15px; border-radius: 5px; overflow-x: auto;')}
        }}
        .toc {{
            {styles.get('toc', 'background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;')}
        }}
        hr {{
            {styles.get('hr', 'border: 0; height: 1px; background-color: #ddd; margin: 30px 0;')}
        }}
        .check {{
            {styles.get('check', 'color: #27ae60; font-weight: bold;')}
        }}
        .x {{
            {styles.get('x', 'color: #e74c3c; font-weight: bold;')}
        }}
    """

    # Get footer text from config
    footer_text = get_string(
        "html.footer",
        "Generated on {date} by TimescaleDB Report Generator",
        date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # Create full HTML document with styling
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    {html_body.replace('✓', '<span class="check">✓</span>').replace('✗', '<span class="x">✗</span>')}
    <footer>
        <hr>
        <p><em>{footer_text}</em></p>
    </footer>
</body>
</html>
"""
    return html

def generate_html_report(md_file, html_file=None):
    """Generate an HTML report from a Markdown file

    Args:
        md_file (str): Path to markdown file
        html_file (str, optional): Path to output HTML file

    Returns:
        str: Path to output HTML file
    """
    if not html_file:
        # Default to same name but with .html extension
        html_file = os.path.splitext(md_file)[0] + '.html'

    # Read markdown content
    with open(md_file, 'r') as f:
        md_content = f.read()

    # Convert to HTML
    html_content = markdown_to_html(md_content)

    # Write HTML file
    with open(html_file, 'w') as f:
        f.write(html_content)

    # Log success message
    logger.info(get_string("log_messages.html_report_generated",
                           "HTML report generated: {file}",
                           file=html_file))

    return html_file
