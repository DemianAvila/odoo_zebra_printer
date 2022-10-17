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
import re
import cairosvg

#READ THE FILE
file = open("/tmp/tickets.json", "r")
data = json.load(file)
file.close()

##STABLISH THE SIZE OF THE ZPL 
##l = zpl.Label(data["total_width"], data["total_height"])
pdf = fpdf.FPDF(unit="mm" ,format=(data["total_width"], data["partial_height"]))

pdf.set_auto_page_break(auto=False)
pdf.set_font('helvetica', size=4.5)
measures = open("/tmp/measures1.txt", "w")
counter = 0
for index, ticket in enumerate(data["tickets"]):

    #w = int(ticket["origin"][0])
    if index%2==0:
        w = 0
        pdf.add_page()
    else:
        w = 40
    h = 0
    #h = int(ticket["origin"][1])
    #PRODUCT NAME
    #pdf.set_x(round(1, ticket["origin"][0]))
    #pdf.set_x(w+1000)    
    pdf.set_xy(x = w, y= h+1.5)    
    #pdf.set_y(round(1, ticket["origin"][1]))
    #pdf.set_y(h+2)
    #pdf.set_y(counter)
    #if index%2==0 and index>0:
    #    counter+=13
    pdf.multi_cell(txt = ticket["product"],
        w = data["partial_width"],
        h = data["partial_height"]/5,
        align = "C")
    barcode_width = (data["partial_width"]/2.5)*2
    barcode_height = (data["partial_height"]/5)*3
    #base = BaseWriter()

    writer=ImageWriter()
    rv = BytesIO()
    Code128(ticket["lot"], writer).write(rv, 
        options = {
            "module_width":0.03, 
            "module_height":1,
            "quiet_zone": .5,
            "dpi": 300,
            "write_text": False
            }
        )

    image = Image.open(rv)
    w1, h1 = image.size
    crop_img = image.crop((0,9,w1,h1-9))
    crop_img.save("/tmp/crop.png", format="png") 
    open("/tmp/sizes.txt", "w").write(f"{w1}     {h1}\n")
    #png_scaled = BytesIO()
    #with open("/tmp/ticket.svg", "wb") as f:
    #Code128(ticket["lot"], writer).write(rv)

    #cairosvg.svg2png(bytestring = rv.getvalue(), 
    #    scale = .25,
    #    write_to = png_scaled)
        #output_width = barcode_width*3.7795275591 , 
        #output_height = barcode_height*3.7795275591 ,
        #write_to = png_scaled)

    #crop_img.save(rv, ) 
    #with open("/tmp/out.png", "wb") as outfile:
    # Copy the BytesIO stream to the output file
    #    outfile.write(rv.getbuffer())
     
    """
    f.close()
    f = open("/tmp/ticket.svg", "r")
    svg_error = f.readlines()
    svg_error = list(
        filter(
            lambda x: not re.search(.*<rect width="100%" height="100%" style="fill:white"/>.*,x),
            svg_error
        )
    ) 
    svg_error = list(
        map(
            lambda x: x.replace("mm", ""),
            svg_error
        )
    )
    f.close()
    f = open("/tmp/ticket.svg", "w")
    f.writelines(svg_error)
    f.close()
    """
    

    #barcode = Image.open(rv)
    pdf.image(name = crop_img,
        x = ((data["partial_width"]-barcode_width)/2)+w, 
        y = (h+data["partial_height"]/5)+1.6)
        #y = (h+data["partial_height"]/5)+2,
        #w = barcode_width,
        #h = barcode_height)

    pdf.set_xy(x = w, y= h+9.5)    
    pdf.cell(txt = ticket["lot"],
        w = data["partial_width"],
        h = data["partial_height"]/5,
        align = "C")


    


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
