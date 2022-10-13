import zpl 
import json
import os
import shutil
import fpdf
import requests
from PIL import Image
from io import BytesIO
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO

#READ THE FILE
file = open("/tmp/tickets.json", "r")
data = json.load(file)
file.close()

##STABLISH THE SIZE OF THE ZPL 
##l = zpl.Label(data["total_width"], data["total_height"])
pdf = fpdf.FPDF(unit="mm" ,format=(data["total_width"], data["total_height"]))
pdf.add_page()
pdf.set_auto_page_break(auto=False)
pdf.set_font('helvetica', size=5)
measures = open("/tmp/measures1.txt", "w")
counter = 0
for index, ticket in enumerate(data["tickets"]):
    w = int(ticket["origin"][0])
    h = int(ticket["origin"][1])
    #PRODUCT NAME
    #pdf.set_x(round(1, ticket["origin"][0]))
    #pdf.set_x(w+1000)    
    pdf.set_xy(x = w, y= h+.75)    
    #pdf.set_y(round(1, ticket["origin"][1]))
    #pdf.set_y(h+2)
    #pdf.set_y(counter)
    #if index%2==0 and index>0:
    #    counter+=13
    pdf.cell(txt = ticket["product"],
        w = data["partial_width"],
        h = data["partial_height"]/5,
        align = "C")
    rv = BytesIO()
    Code128(ticket["lot"], writer=ImageWriter()).write(rv)
    barcode = Image.open(rv)
    barcode_width = (data["partial_width"]/6)*2
    barcode_height = (data["partial_height"]/5)*4
    pdf.image(name = barcode,
        x = ((data["partial_width"]-barcode_width)/2)+w, 
        y = h+data["partial_height"]/5,
        w = barcode_width,
        h = barcode_height)


    


pdf.output("/tmp/label.pdf")


#    #CENTER
#    #center = (((l.width/2) - data["partial_height"])/2)+ticket["origin"][0]
#    #l.origin(center, ticket["origin"][1]+1)
#    #TEXT
#    #l.write_text(ticket["product"], char_height=2, char_width=2)
#    #l.endorigin()
#    #BARCODE
#    #center = (((l.width/2))/2)+ticket["origin"][0]
#    #with open(f"/tmp/barcode{index}.jpeg", "wb") as f:
#        Code128(ticket["lot"], writer=ImageWriter()).write(f)
#    barcode = Image.open(f"/tmp/barcode{index}.jpeg")
#    l.origin(center, ticket["origin"][1]+3)
#    l.write_graphic(barcode, 20)
#    l.endorigin()
#
##file = open("/tmp/zpl_label.zpl", "w")
##file.write(l.dumpZPL())
##file.close()
#
#zpl = l.dumpZPL()
#w = "{:.2f}".format(round(l.width/25.4, 2))  
#h = "{:.2f}".format(round(l.height/25.4, 2)) 
## adjust print density (8dpmm), label width (4 inches), label height (6 inches), and label index (0) as necessary
#url = f"http://api.labelary.com/v1/printers/12dpmm/labels/{h}x{w}/"
#open("/tmp/test.txt", "w").write(url)
#files = {'file' : zpl}
#headers = {'Accept' : 'application/pdf'} # omit this line to get PNG images back
#response = requests.post(url, headers = headers, files = files, stream = True)
#
#if response.status_code == 200:
#    response.raw.decode_content = True
#    with open('/tmp/label.pdf', 'wb') as out_file: # change file name for PNG images
#        shutil.copyfileobj(response.raw, out_file)
#
#
#
##error = subprocess.run([
##    "curl", "--request", "POST", 
##    f"http://api.labelary.com/v1/printers/12dpmm/labels/{l.width/25.4}x{l.height/25.4}/0/", 
##    "--form", "file=@/tmp/zpl_label.zpl", "--header", "\"Accept: application/pdf\"", ">", "/tmp/label.pdf"] )
#    #capture_output = True)
#
##file = open("/tmp/label.pdf", "w")
##file.write(str(error.stdout))
##file.close()
#