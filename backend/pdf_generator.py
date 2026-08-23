import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from backend.schema import EuropassCV

# Setup Jinja2 to look in your templates directory
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def generate_pdf_from_cv(cv_data: EuropassCV) -> bytes:
    """
    Takes the structured CV data, injects it into the HTML template, 
    and renders it to a PDF using WeasyPrint. Returns PDF bytes.
    """
    # 1. Load the HTML template
    template = env.get_template("europass_template.html")
    
    # 2. Render the template with the Pydantic data
    html_out = template.render(cv=cv_data)
    
    # 3. Convert HTML to PDF using WeasyPrint
    pdf_bytes = HTML(string=html_out).write_pdf()
    
    return pdf_bytes