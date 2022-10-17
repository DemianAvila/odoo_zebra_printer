import logging
import math
import json
import os
import subprocess
import base64
from odoo import fields, models, api

def filter_lots_by_date(list_elem, prod):
    logging.warning("------------------------")
    logging.warning(prod)
    logging.warning("------------------------")
    if list_elem.create_date.day != prod.date_planned_start.day:
        return False
    if list_elem.create_date.month != prod.date_planned_start.month:
        return False
    if list_elem.create_date.year != prod.date_planned_start.year:
        return False
    
    return True

class PrinterWizard(models.TransientModel):
    _name = "printer.wizard"
    
    production_order = fields.Many2one("production.order")
    products = fields.One2many("product.printing", "printing_id")

    def get_labels(self):
        file = open("/tmp/label.pdf", "rb")
        data = file.read()
        file.close()
        return {
            "file": base64.b64encode(data)
        }
        

    @api.onchange("production_order")
    def get_products(self):
        if not self.production_order:
            for product in self.products:
                product.printing_id = False
            return None
        else:
            for product in self.products:
                product.printing_id = False
            for product in self.production_order.slip_ids:
                #GET LOT
                lots = self.env["stock.production.lot"].search([
                    ("product_id", "=", product.product_id.id)
                ])
                
                lots = list(
                    filter(
                        lambda x: filter_lots_by_date(x, product),
                        lots
                    )
                )
                self.env["product.printing"].create({
                    "printing_id": self.id,
                    "product": product.product_id.id,
                    "qty": int(product.product_qty),
                    "lot": lots[0].lot_name
                })
    
    def print_labels(self):
        tickets = {}
        #SET THE MEASURES OF THE PDF
        #WIDTH
        tickets["partial_width"] = 40
        tickets["total_width"] = tickets["partial_width"]*2
        #HEIGHT
        tickets["partial_height"] = 12.7
        tickets["tickets"] = []
        counter = 0
        #ITERATE ALL OVER THE LABELS
        for index, product in enumerate(self.products):
            for i in range(product.qty):
                ticket = {}
                #IF counter EVEN
                if counter%2==0:
                    #ORIGIN 0 IN WIDTH AND HEIGHT IN PARTIAL
                    ticket["origin"] = [0,
                        tickets["partial_height"]*(math.floor((counter)/2))]
                else:
                    #ORIGIN 80 IN WIDTH AND HEIGHT IN PARTIAL
                    ticket["origin"] = [80, 
                        tickets["partial_height"]*(math.floor((counter)/2))]

                ticket["product"] = f"[{product.product.default_code}] {product.product.name}"
                ticket["lot"] = product.lot
                tickets["tickets"].append(ticket)
                counter += 1

        tickets["total_height"] = tickets["partial_height"]*(math.ceil(counter/2))

        
        #WRITE INFO IN JSON FILE
        data = json.dumps(tickets)
        file = open("/tmp/tickets.json", "w")
        file.write(data)
        file.close()

        #EXCECUTE PYTHON SCRIPT FOR LABELS
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, "label_api.py")

        error = subprocess.run(["python3", path], capture_output = True)
        file = open("/tmp/error.txt", "w")
        file.write(str(f"{path} {error.stderr}"))
        file.close()

        res = {
            'type': 'ir.actions.client',
            'name':'Print label',
            'tag':'print_label',
        }
        return res


            
            

            

class ProductPrinting(models.TransientModel):
    _name = "product.printing"
    printing_id = fields.Many2one("printer.wizard")
    product = fields.Many2one("product.product")
    qty = fields.Integer()
    lot = fields.Char()
