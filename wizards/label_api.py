import zpl 
import json
import os
from PIL import Image
from io import BytesIO
from barcode import Code128
from barcode.writer import ImageWriter

#READ THE FILE
file = open("/tmp/tickets.json", "r")
data = json.load(file)
file.close()

#STABLISH THE SIZE OF THE ZPL 
l = zpl.Label(data["total_width"], data["total_height"])
for index, ticket in enumerate(data["tickets"]):
    #CENTER
    center = (((l.width/2) - data["partial_height"])/2)+ticket["origin"][0]
    l.origin(center, ticket["origin"][1]+1)
    #TEXT
    l.write_text(ticket["product"], char_height=2, char_width=2)
    l.endorigin()
    #BARCODE
    barcode = Image.open(f"/tmp/barcode{index}.jpeg")
    center = (((l.width/2))/2)+ticket["origin"][0]
    with open(f"/tmp/barcode{index}.jpeg", "wb") as f:
        Code128(ticket["lot"], writer=ImageWriter()).write(f)
    l.origin(center, ticket["origin"][1]+3)
    l.write_graphic(barcode, 20)
    l.endorigin()

file = open("/tmp/zpl_label.txt", "w")
file.write(l.dumpZPL())
file.close()
