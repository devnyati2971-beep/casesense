import weasyprint
from typing import List, Dict

def render_draft_to_pdf(title: str, sections_data: List[Dict]) -> bytes:
    """Blueprint §D21: Render draft version to PDF."""
    html_parts = [f"<h1>{title}</h1>"]
    
    for sec in sections_data:
        if sec.get("heading"):
            html_parts.append(f"<h2>{sec['heading']}</h2>")
        if sec.get("body"):
            # Simple HTML escaping for safety
            body_safe = (
                sec["body"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            html_parts.append(f"<p>{body_safe}</p>")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            @page {{
                size: A4;
                margin: 1in;
            }}
            body {{ 
                font-family: serif; 
                font-size: 12pt; 
                line-height: 1.6; 
            }}
            h1 {{ 
                text-align: center; 
                font-size: 16pt; 
                font-weight: bold; 
                text-transform: uppercase; 
                margin-bottom: 30pt;
            }}
            h2 {{ 
                font-size: 14pt; 
                font-weight: bold; 
                margin-top: 24pt; 
                margin-bottom: 12pt; 
            }}
            p {{ 
                margin-bottom: 12pt; 
                text-align: justify; 
            }}
        </style>
    </head>
    <body>
        {''.join(html_parts)}
    </body>
    </html>
    """
    
    # Render PDF bytes
    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
    return pdf_bytes