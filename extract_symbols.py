from PyPDF2 import PdfReader
import fitz  # PyMuPDF for image extraction
import os

# Path to PDF
pdf_path = "Finalized_Indian_army_Symbology_5.pdf"

# Output folder
output_folder = "extracted_symbols"
os.makedirs(output_folder, exist_ok=True)

# Open PDF with PyMuPDF
doc = fitz.open(pdf_path)
image_count = 0
image_files = []

for page_index in range(len(doc)):
    page = doc[page_index]
    images = page.get_images(full=True)
    
    for img_index, img in enumerate(images):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)
        
        # If image has alpha channel
        if pix.n - pix.alpha < 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        
        image_count += 1
        image_path = os.path.join(output_folder, f"page{page_index+1}_img{img_index+1}.png")
        pix.save(image_path)
        image_files.append(image_path)

image_count, image_files[:10]  # show first 10 extracted paths
