from fpdf import FPDF

# Step 1: Read the full text
with open("summary_output.txt", "r", encoding="utf-8") as file:
    text = file.read()

# Step 2: Split every sentence as a bullet point
sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
bullet_points = ["- " + sentence.capitalize() for sentence in sentences]

# Step 3: Create PDF with all bullet points
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Bullet Point Summary", ln=True, align="C")
pdf.ln(10)

for point in bullet_points:
    pdf.multi_cell(0, 10, txt=point)

pdf.output("bullet1_output.pdf")
print("✅ PDF saved as: bullet_output.pdf")
