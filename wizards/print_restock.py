import logging
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
    

class ProductPrinting(models.TransientModel):
    _name = "product.printing"
    printing_id = fields.Many2one("printer.wizard")
    product = fields.Many2one("product.product")
    qty = fields.Integer()
    lot = fields.Char()