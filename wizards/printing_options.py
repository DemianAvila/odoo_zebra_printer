from odoo import fields, models, api
import logging
import math
import json
import sys
import datetime
import subprocess
import os
from base64 import b64encode

class PrintingOptions(models.TransientModel):
    _name = "printing_options.wizard"
    _description = "Printing Options"

    """
    available_printers = fields.One2many('available_printers', 
        'printing_id', 
        string='Available printers')
    """
    
    bar_codes = fields.One2many('bar_codes', 
        'printing_id', 
        string='field_name')

    error = fields.Boolean(default=False)
    error_message = fields.Char()

    date_tickets = fields.Date()
    qty = fields.Integer()

    def get_printable(self):
        #TRY TO GET PRINTABLE
        try:
            printable = {
                "status": 1,
                "printable": b64encode(open("/tmp/label.png", "rb").read())
            }
            return printable
        except:
            return {
                "status": 0
            }

    @api.onchange('date_tickets')
    def get_tickets(self):
        #ERASE VALUES
        values = []
        for code in self.bar_codes:
            values.append((2, code.id))
        self.bar_codes = values
        #SEARCH VALUES 
        #production = self.env['mrp.production'].search([])
        if self.date_tickets:
            production_4_day = self.env['production.order'].search([])
            #FILTER THE NAME
            production_4_day = list(
                filter(
                    lambda x: self.date_tickets.strftime("%Y-%m-%d") in x.name,
                    production_4_day
                )
            )
        else:
            return None
        if len(production_4_day)==0:
            return None
        production = production_4_day[0].slip_ids

        values = []
        for product in production:
            #CHECK IF DATE OF PRODUCTION CORRESPONDS WITH THE PASSED DATE
            if not self.date_tickets:
                break
            if (self.date_tickets.day == product.date_planned_start.day and 
                self.date_tickets.month == product.date_planned_start.month and
                self.date_tickets.year == product.date_planned_start.year):
                #GET THE LOT NAME ACCORDING TO DATE
                

                values.append((0,0,({
                    "date_prod": product.date_planned_start,
                    "product_id": product.product_id.id,
                    "choose_print": True,
                    "printing_id": self.id, 
                    "qty": product.product_qty,
                    "lot": 
                })))

        self.bar_codes = values

            


    def print_tickets(self):
        image_data = {}
        #GET THE TICKETS
        #tickets = self.env['resumen.production.all'].search([])  
        #THE WIDTH OF THE ELEMENT IS EQUIVALENT OF TWO TICKETS OF 80mm
        selected_bar_codes = list(
            filter(lambda x: x.choose_print,
                self.bar_codes)
        )
        image_data["partial_width"] = 80
        image_data["total_width"] = image_data["partial_width"]*2
        #THE HEIGHT OF THE ELEMENT IS EQUIVALENT OF 12.7mm OF THE 
        #TOTAL OF TICKETS /2 UP ROUNDED IF NOT EVEN
        image_data["partial_heigh"] = 12.7
        image_data["total_heigh"] = math.ceil((image_data["partial_heigh"]*len(selected_bar_codes))/2)
        #INITIALIZE THE IMAGE
        #l = zpl.Label(total_width, total_heigh)
        #ITERATE OVER THE TICKETS
        
        image_data["tickets"] = []
        for index, ticket in enumerate(selected_bar_codes):
            data = {}
            #GET DATE OF THE PRODUCTION
            date_order = ticket.date_prod
            #GET ID OF PRODUCT
            product_id = ticket.product_id.id
            #SEARCH BARCODE
            bar_code = self.env['product.product'].search(
                [('id', '=', product_id)],
                limit=1
            ).barcode
            #GET PRODUCT NAME
            product_name = self.env['product.template'].search(
                [('id', '=', product_id)],
                limit =1
            ).name
                     
            if index%2==0:
                data["origin"] = [0, image_data["partial_heigh"]*(index/2)]
                prev_height = image_data["partial_heigh"]*(index/2)
            else:
                data["origin"] = (image_data["partial_width"], 
                    prev_height)
            data.update({
                'date_order':date_order.strftime("%d/%m/%Y"),
                'product_id': product_id,
                'bar_code': bar_code,
                'product_name': product_name
            })
            image_data["tickets"].append(data)
        
        
        #WRITE INFO ON FILE
        file = open('/tmp/file_data.json', 'w')
        file.write(json.dumps(image_data))
        file.close()

        #RUN SUBPROCESS
        path = os.path.dirname(os.path.abspath(__file__))
        try:
            subprocess.check_output(["python3", os.path.join(path, "get_image.py")])
        except subprocess.CalledProcessError as e:
            logging.warning("-------------ERROR-------------")
            logging.warning(e.output)
            logging.warning(e)
        
        return {
            'res_model': 'printing_options.wizard',
            'type': 'ir.actions.client',
            'tag': 'detect_print',
            'destroy': True
            }


class BarCodes(models.TransientModel):
    _name = "bar_codes"
    date_prod = fields.Datetime("Production date")
    product_id = fields.Many2one('product.product' ,"Product name")
    #qty = fields.Integer("Product quantity")
    choose_print = fields.Boolean("Choose this printer")
    printing_id = fields.Many2one("printing_options.wizard")

"""
class AvailablePrinters(models.TransientModel):
    _name = "available_printers"
    printer = fields.Char("Printer name")
    choose = fields.Boolean("Choose this printer")
    printing_id = fields.Many2one("printing_options.wizard")
"""