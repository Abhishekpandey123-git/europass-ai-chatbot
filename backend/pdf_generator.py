import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from backend.schema import EuropassCV

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def generate_pdf_from_cv(cv_data: EuropassCV) -> bytes:
    """
    Takes the structured CV data, converts it to a standard dictionary,
    injects it into the HTML template, and renders it to a PDF using WeasyPrint.
    """
    template = env.get_template("europass_template.html")
    
    # FIX: Convert Pydantic model to a standard dictionary so Jinja2 maps keys perfectly
    if hasattr(cv_data, "model_dump"):
        cv_dict = cv_data.model_dump()
    else:
        cv_dict = cv_data.dict() # For older Pydantic versions
        
    html_out = template.render(cv=cv_dict)
    pdf_bytes = HTML(string=html_out).write_pdf()
    return pdf_bytes