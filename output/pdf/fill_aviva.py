import io, json, hashlib
from pathlib import Path
import fitz
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
src=Path(r'C:\Users\Admin\Downloads\F - Aviva - NFEE.pdf')
out=Path(r'D:\anonym\output\pdf\KUNAL_DAS_Aviva_01210020_NFE_prefilled.pdf')
buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(595.28,841.89))
c.setFillColorRGB(0.02,0.12,0.25)
def text(x,y,t,size=9):
 c.setFont('Helvetica',size); c.drawString(x,841.89-y,t)
def boxes(x,y,t,step=15.45,size=10):
 c.setFont('Helvetica',size)
 for j,ch in enumerate(t): c.drawCentredString(x+j*step,841.89-y,ch)
def tick(x,y):
 c.setStrokeColorRGB(0.02,0.12,0.25);c.setLineWidth(1.3)
 c.line(x-3,841.89-(y),x-1,841.89-(y+2));c.line(x-1,841.89-(y+2),x+4,841.89-(y-4))
boxes(78.5,193,'01210020')
boxes(318,193,'KUNAL DAS')
text(110,212,'isearch.xsolve@gmail.com',10)
boxes(426,212,'8617216163')
boxes(109,231,'AIIPD6525H')
text(350,231,'DOB (identification only): 29/05/1979',8)
tick(116.5,246)
tick(260.5,263) # User confirmed tax residence only in India.
tick(36,356)

text(174,375,'isearch.xsolve@gmail.com',9)
boxes(195,408,'8617216163')
boxes(195,424,'9830739230')
tick(36,721)
boxes(236.5,665,'KUNAL DAS')
boxes(204.5,689,'KOTAK MAHINDRA BANK')
boxes(220,704,'KOLKATA-GARIAHAT')
boxes(220,719,'5550559381')
boxes(204.5,734,'KKBK0006599',step=13.1,size=9)
tick(204.5,748)
c.showPage();c.showPage();c.save();buf.seek(0)
r=PdfReader(str(src));o=PdfReader(buf);w=PdfWriter()
for i,p in enumerate(r.pages):
 p.merge_page(o.pages[i]);w.add_page(p)
w.add_metadata({'/Title':'KUNAL DAS - Aviva NFE - Policy 01210020','/Subject':'Contact and bank update; unsigned; India-only tax residence confirmed'})
with out.open('wb') as f:w.write(f)
d=fitz.open(out)
for i,p in enumerate(d):p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(str(out.parent/f'aviva-filled-{i+1}.png'))
t='\n'.join(p.extract_text() or '' for p in PdfReader(str(out)).pages)
for v in ['01210020','isearch.xsolve@gmail.com','29/05/1979']: assert v in t.replace(' ', '').replace('\n',''),v
print(out)
print('SHA256',hashlib.sha256(out.read_bytes()).hexdigest())




