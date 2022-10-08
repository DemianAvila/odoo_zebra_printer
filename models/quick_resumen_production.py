# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class QuickResumenProduction(models.TransientModel):
    _name = "quick.resumen.production"
    _description = "Quick Resumen Production"

    maximo = fields.Integer(string='Maximo')
    minimo = fields.Integer(string='Minimo')
    config_id = fields.Many2one("pos.config", string="Punto de Venta")
    product_id = fields.Many2one("product.template", string="Producto")
    # adults = fields.Integer("Adultos")

    # @api.onchange("check_out", "check_in")
    # def on_change_check_out(self):
    #     """
    #     Cuando cambie el pago o el registro, se comprobará si
    #     La fecha de salida debe ser mayor que la fecha de registro
    #     y actualizar el campo ficticio
    #     """
    #     if self.check_out and self.check_in:
    #         if self.check_out < self.check_in:
    #             raise ValidationError(_("La fecha de salida debe ser mayor que la fecha de registro."))
    #
    # @api.onchange("partner_id")
    # def _onchange_partner_id_res(self):
    #     """
    #     Cuando cambie partner_id, se actualizará el partner_invoice_id,
    #     partner_shipping_id y pricelist_id de la reserva del hotel también
    #     """
    #     if not self.partner_id:
    #         self.update(
    #             {
    #                 "partner_invoice_id": False,
    #                 "partner_shipping_id": False,
    #                 "partner_order_id": False,
    #             }
    #         )
    #     else:
    #         addr = self.partner_id.address_get(["delivery", "invoice", "contact"])
    #         self.update(
    #             {
    #                 "partner_invoice_id": addr["invoice"],
    #                 "partner_shipping_id": addr["delivery"],
    #                 "partner_order_id": addr["contact"],
    #                 "pricelist_id": self.partner_id.property_product_pricelist.id,
    #             }
    #         )
    #
    # @api.model
    # def default_get(self, fields):
    #     res = super(QuickResumenProduction, self).default_get(fields)
    #     keys = self._context.keys()
    #     if "date" in keys:
    #         res.update({"check_in": self._context["date"]})
    #     if "room_id" in keys:
    #         roomid = self._context["room_id"]
    #         res.update({"room_id": int(roomid)})
    #     return res

    # def room_reserve(self):
    #     """
    #     Este método crea un nuevo registro para hotel.reservation
    #     """
    #     hotel_res_obj = self.env["hotel.reservation"]
    #     for res in self:
    #         rec = hotel_res_obj.create(
    #             {
    #                 "partner_id": res.partner_id.id,
    #                 "partner_invoice_id": res.partner_invoice_id.id,
    #                 "partner_order_id": res.partner_order_id.id,
    #                 "partner_shipping_id": res.partner_shipping_id.id,
    #                 "checkin": res.check_in,
    #                 "checkout": res.check_out,
    #                 "warehouse_id": res.warehouse_id.id,
    #                 "pricelist_id": res.pricelist_id.id,
    #                 "adults": res.adults,
    #                 "reservation_line_ids": [(0,0,{
    #                             "reserve": [(6, 0, [res.room_id.id])],
    #                             "name": (res.room_id and res.room_id.name or "")})],
    #             }
    #         )
    #     return rec
