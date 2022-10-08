
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HotelReservation(models.Model):
    _name = "hotel.reservation"
    _rec_name = "reservation_no"
    _description = "Reservation"
    _order = "reservation_no desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _compute_folio_id(self):
        for res in self:
            res.update({"no_of_folio": len(res.folios_ids.ids)})

    reservation_no = fields.Char("Reservacion N°", readonly=True, copy=False)
    date_order = fields.Datetime("Fecha de Registro",readonly=True,required=True,index=True,default=lambda self: fields.Datetime.now())
    warehouse_id = fields.Many2one("stock.warehouse","Hotel",readonly=True,required=True,default=1,states={"draft": [("readonly", False)]})
    partner_id = fields.Many2one("res.partner","Nombre del Huesped",readonly=True,required=True,states={"draft": [("readonly", False)]})
    pricelist_id = fields.Many2one("product.pricelist","Lista de Precio",required=True,readonly=True,states={"draft": [("readonly", False)]},
        help="Lista de precios para la reserva actual.")
    partner_invoice_id = fields.Many2one("res.partner","Dirección de Facturación",readonly=True,states={"draft": [("readonly", False)]},
        help="Dirección de facturación de la reserva actual.")
    partner_order_id = fields.Many2one("res.partner","Contacto para Pedidos",readonly=True,states={"draft": [("readonly", False)]},
        help="El nombre y dirección del contacto que solicitó el pedido o cotización.")
    partner_shipping_id = fields.Many2one("res.partner","Dirección de entrega",readonly=True,states={"draft": [("readonly", False)]},
        help="Dirección de entrega de la reserva actual.")
    checkin = fields.Datetime("Fecha prevista de llegada",required=True,readonly=True,states={"draft": [("readonly", False)]})
    checkout = fields.Datetime("Fecha prevista de salida",required=True,readonly=True,states={"draft": [("readonly", False)]})
    adults = fields.Integer("Adultos",readonly=True,states={"draft": [("readonly", False)]},help="Número de adultos que hay en la lista de invitados.")
    children = fields.Integer(u"Niños",readonly=True,states={"draft": [("readonly", False)]},help="Número de niños en la lista de invitados.")
    reservation_line_ids = fields.One2many("hotel_reservation.line","line_id","Línea de reserva",help="Detalles de reserva de habitación de hotel.",
        readonly=True,states={"draft": [("readonly", False)]})
    state = fields.Selection([("draft", "Borrador"),("confirm", "Confirmado"),("cancel", "Cancelado"),("done", "Hecho")],"Estado",readonly=True,default="draft")
    folios_ids = fields.Many2many("hotel.folio","hotel_folio_reservation_rel","order_id","invoice_id",string="Folio")
    no_of_folio = fields.Integer("N° de Folio", compute="_compute_folio_id")

    def unlink(self):
        for reserv_rec in self:
            if reserv_rec.state != "draft":
                raise ValidationError(_("Lo sentimos, ¡solo puedes eliminar la reserva cuando es borrador!"))
        return super(HotelReservation, self).unlink()

    def copy(self):
        ctx = dict(self._context) or {}
        ctx.update({"duplicate": True})
        return super(HotelReservation, self.with_context(ctx)).copy()

    @api.constrains("reservation_line_ids", "adults", "children")
    def check_reservation_rooms(self):
        """
        Este método se utiliza para validar el reservation_line_ids.
        """
        ctx = dict(self._context) or {}
        for reservation in self:
            cap = 0
            for rec in reservation.reservation_line_ids:
                if not rec.reserve:
                    raise ValidationError(_("Seleccione las habitaciones para reservar."))
                cap = sum(room.capacity for room in rec.reserve)
            if not ctx.get("duplicate"):
                if (reservation.adults + reservation.children) > cap:
                    raise ValidationError(_(
                            "Capacidad de la Habitacion excedida \n"
                            " Seleccione las habitaciones de acuerdo con su capacidad."
                        )
                    )
            if reservation.adults <= 0:
                raise ValidationError(_("El número de adultos debe ser un valor positivo."))

    @api.constrains("checkin", "checkout")
    def check_in_out_dates(self):
        """
        Cuando date_order es menor que la fecha de entrada o
        La fecha de salida debe ser mayor que la fecha de entrada.
        """
        if self.checkout and self.checkin:
            if self.checkin < self.date_order:
                raise ValidationError(
                    _(
                        """La fecha de entrada debe ser mayor que """
                        """la fecha actual."""
                    )
                )
            if self.checkout < self.checkin:
                raise ValidationError(
                    _(
                        """La fecha de salida debe ser mayor """
                        """que la fecha de entrada."""
                    )
                )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """
        Cuando cambie partner_id, se actualizará el partner_invoice_id,
        partner_shipping_id y pricelist_id de la reserva del hotel también
        """
        if not self.partner_id:
            self.update(
                {
                    "partner_invoice_id": False,
                    "partner_shipping_id": False,
                    "partner_order_id": False,
                }
            )
        else:
            addr = self.partner_id.address_get(["delivery", "invoice", "contact"])
            self.update(
                {
                    "partner_invoice_id": addr["invoice"],
                    "partner_shipping_id": addr["delivery"],
                    "partner_order_id": addr["contact"],
                    "pricelist_id": self.partner_id.property_product_pricelist.id,
                }
            )

    @api.model
    def create(self, vals):
        vals["reservation_no"] = (
            self.env["ir.sequence"].next_by_code("hotel.reservation") or "New"
        )
        return super(HotelReservation, self).create(vals)

    def check_overlap(self, date1, date2):
        delta = date2 - date1
        return {date1 + timedelta(days=i) for i in range(delta.days + 1)}

    def confirm_reservation(self):
        """
        Este método crea un nuevo conjunto de registros para la línea de reserva de habitaciones de hotel
        """
        reservation_line_obj = self.env["hotel.room.reservation.line"]
        vals = {}
        for reservation in self:
            reserv_checkin = reservation.checkin
            reserv_checkout = reservation.checkout
            room_bool = False
            for line_id in reservation.reservation_line_ids:
                for room in line_id.reserve:
                    if room.room_reservation_line_ids:
                        for reserv in room.room_reservation_line_ids.search(
                            [
                                ("status", "in", ("confirm", "done")),
                                ("room_id", "=", room.id),
                            ]
                        ):
                            check_in = reserv.check_in
                            check_out = reserv.check_out
                            if check_in <= reserv_checkin <= check_out:
                                room_bool = True
                            if check_in <= reserv_checkout <= check_out:
                                room_bool = True
                            if (reserv_checkin <= check_in and reserv_checkout >= check_out):
                                room_bool = True
                            r_checkin = (reservation.checkin).date()
                            r_checkout = (reservation.checkout).date()
                            check_intm = (reserv.check_in).date()
                            check_outtm = (reserv.check_out).date()
                            range1 = [r_checkin, r_checkout]
                            range2 = [check_intm, check_outtm]
                            overlap_dates = self.check_overlap(*range1) & self.check_overlap(*range2)
                            if room_bool:
                                raise ValidationError(
                                    _("Intentó confirmar la reserva con las habitaciones que ya estaban"
                                      "reservadas en este período de reserva. Las fechas superpuestas son %s") % overlap_dates
                                )
                            else:
                                self.state = "confirm"
                                vals = {
                                    "room_id": room.id,
                                    "check_in": reservation.checkin,
                                    "check_out": reservation.checkout,
                                    "state": "assigned",
                                    "reservation_id": reservation.id,
                                }
                                room.write({"isroom": False, "status": "occupied"})
                        else:
                            self.state = "confirm"
                            vals = {
                                "room_id": room.id,
                                "check_in": reservation.checkin,
                                "check_out": reservation.checkout,
                                "state": "assigned",
                                "reservation_id": reservation.id,
                            }
                            room.write({"isroom": False, "status": "occupied"})
                    else:
                        self.state = "confirm"
                        vals = {
                            "room_id": room.id,
                            "check_in": reservation.checkin,
                            "check_out": reservation.checkout,
                            "state": "assigned",
                            "reservation_id": reservation.id,
                        }
                        room.write({"isroom": False, "status": "occupied"})
                    reservation_line_obj.create(vals)
        return True

    def cancel_reservation(self):
        """
        Este método cancela el registro establecido para la línea de reserva de habitación de hotel
        """
        room_res_line_obj = self.env["hotel.room.reservation.line"]
        hotel_res_line_obj = self.env["hotel_reservation.line"]
        self.state = "cancel"
        room_reservation_line = room_res_line_obj.search([("reservation_id", "in", self.ids)])
        room_reservation_line.write({"state": "unassigned"})
        room_reservation_line.unlink()
        reservation_lines = hotel_res_line_obj.search([("line_id", "in", self.ids)])
        for reservation_line in reservation_lines:
            reservation_line.reserve.write({"isroom": True, "status": "available"})
        return True

    def set_to_draft_reservation(self):
        self.update({"state": "draft"})

    def action_send_reservation_mail(self):
        """
        Esta función abre una ventana para redactar un correo electrónico,
        mensaje de plantilla cargado de forma predeterminada.
        """
        self.ensure_one(), "Esto es para una sola identificación a la vez."
        template_id = self.env.ref("hotel_reservation.email_template_hotel_reservation").id
        compose_form_id = self.env.ref("mail.email_compose_message_wizard_form").id
        ctx = {
            "default_model": "hotel.reservation",
            "default_res_id": self.id,
            "default_use_template": bool(template_id),
            "default_template_id": template_id,
            "default_composition_mode": "comment",
            "force_send": True,
            "mark_so_as_sent": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
            "force_send": True,
        }

    @api.model
    def _reservation_reminder_24hrs(self):
        """
        Este método es para el planificador
        cada programador de 1 día llamará a este método para
        encontrar todas las reservas de mañana.
        """
        now_date = fields.Date.today()
        template_id = self.env.ref("hotel_reservation.mail_template_reservation_reminder_24hrs")
        for reserv_rec in self:
            checkin_date = reserv_rec.checkin
            difference = relativedelta(now_date, checkin_date)
            if (difference.days == -1 and reserv_rec.partner_id.email and reserv_rec.state == "confirm"):
                template_id.send_mail(reserv_rec.id, force_send=True)
        return True

    def create_folio(self):
        """
        Este método es para crear un nuevo folio de hotel.
        """
        hotel_folio_obj = self.env["hotel.folio"]
        for reservation in self:
            folio_lines = []
            checkin_date = reservation["checkin"]
            checkout_date = reservation["checkout"]
            duration_vals = self._onchange_check_dates(
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                duration=False,
            )
            duration = duration_vals.get("duration") or 0.0
            folio_vals = {
                "date_order": reservation.date_order,
                "warehouse_id": reservation.warehouse_id.id,
                "partner_id": reservation.partner_id.id,
                "pricelist_id": reservation.pricelist_id.id,
                "partner_invoice_id": reservation.partner_invoice_id.id,
                "partner_shipping_id": reservation.partner_shipping_id.id,
                "checkin_date": reservation.checkin,
                "checkout_date": reservation.checkout,
                "duration": duration,
                "reservation_id": reservation.id,
            }
            for line in reservation.reservation_line_ids:
                for r in line.reserve:
                    folio_lines.append((0,0,{
                                "checkin_date": checkin_date,
                                "checkout_date": checkout_date,
                                "product_id": r.product_id and r.product_id.id,
                                "name": reservation["reservation_no"],
                                "price_unit": r.list_price,
                                "product_uom_qty": duration,
                                "is_reserved": True}))
                    r.write({"status": "occupied", "isroom": False})
            folio_vals.update({"room_line_ids": folio_lines})
            folio = hotel_folio_obj.create(folio_vals)
            for rm_line in folio.room_line_ids:
                rm_line.product_id_change()
            self.write({"folios_ids": [(6, 0, folio.ids)], "state": "done"})
        return True

    def _onchange_check_dates(self, checkin_date=False, checkout_date=False, duration=False):
        """
        Este método da la duración entre el check-in y el check-out si
        el cliente se irá solo por una hora que se consideraría
        como un día entero. Si el cliente se registrará en el pago por más o igual
        horas, que se configuran en la empresa como horas adicionales a las
        ser considerado como días completos
        """
        value = {}
        configured_addition_hours = (self.warehouse_id.company_id.additional_hours)
        duration = 0
        if checkin_date and checkout_date:
            dur = checkout_date - checkin_date
            duration = dur.days + 1
            if configured_addition_hours > 0:
                additional_hours = abs(dur.seconds / 60)
                if additional_hours <= abs(configured_addition_hours * 60):
                    duration -= 1
        value.update({"duration": duration})
        return value

    def open_folio_view(self):
        folios = self.mapped("folios_ids")
        action = self.env.ref("hotel.open_hotel_folio1_form_tree_all").read()[0]
        if len(folios) > 1:
            action["domain"] = [("id", "in", folios.ids)]
        elif len(folios) == 1:
            action["views"] = [(self.env.ref("hotel.view_hotel_folio_form").id, "form")]
            action["res_id"] = folios.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action


class HotelReservationLine(models.Model):
    _name = "hotel_reservation.line"
    _description = "Reservation Line"

    name = fields.Char("Nombre")
    line_id = fields.Many2one("hotel.reservation")
    reserve = fields.Many2many("hotel.room","hotel_reservation_line_room_rel","hotel_reservation_line_id","room_id",
        domain="[('isroom','=',True),('categ_id','=',categ_id)]")
    categ_id = fields.Many2one("hotel.room.type", "Tipo de Habitacion")

    @api.onchange("categ_id")
    def _onchange_categ(self):
        """
        Cuando cambia categ_id, el checkin y checkout son
        lleno o no si no, entonces levante la advertencia
        """
        if not self.line_id.checkin:
            raise ValidationError(
                _(
                    """Antes de elegir una habitación, \n debes"""
                    """seleccione una fecha de entrada o una fecha de salida"""
                    """en el formulario de reserva."""
                )
            )
        hotel_room_ids = self.env["hotel.room"].search([("room_categ_id", "=", self.categ_id.id)])
        room_ids = []
        for room in hotel_room_ids:
            assigned = False
            for line in room.room_reservation_line_ids:
                if line.status != "cancel":
                    if (self.line_id.checkin <= line.check_in <= self.line_id.checkout) or (self.line_id.checkin <= line.check_out <= self.line_id.checkout):
                        assigned = True
                    elif (line.check_in <= self.line_id.checkin <= line.check_out) or (line.check_in <= self.line_id.checkout <= line.check_out):
                        assigned = True
            for rm_line in room.room_line_ids:
                if rm_line.status != "cancel":
                    if (
                        self.line_id.checkin
                        <= rm_line.check_in
                        <= self.line_id.checkout
                    ) or (
                        self.line_id.checkin
                        <= rm_line.check_out
                        <= self.line_id.checkout
                    ):
                        assigned = True
                    elif (
                        rm_line.check_in
                        <= self.line_id.checkin
                        <= rm_line.check_out
                    ) or (
                        rm_line.check_in
                        <= self.line_id.checkout
                        <= rm_line.check_out
                    ):
                        assigned = True
            if not assigned:
                room_ids.append(room.id)
        domain = {"reserve": [("id", "in", room_ids)]}
        return {"domain": domain}

    def unlink(self):
        hotel_room_reserv_line_obj = self.env["hotel.room.reservation.line"]
        for reserv_rec in self:
            for rec in reserv_rec.reserve:
                lines = hotel_room_reserv_line_obj.search([("room_id", "=", rec.id),("reservation_id", "=", reserv_rec.line_id.id)])
                if lines:
                    rec.write({"isroom": True, "status": "available"})
                    lines.unlink()
        return super(HotelReservationLine, self).unlink()


class HotelRoomReservationLine(models.Model):
    _name = "hotel.room.reservation.line"
    _description = "Hotel Room Reservation"
    _rec_name = "room_id"

    room_id = fields.Many2one("hotel.room", string="Habitacion")
    check_in = fields.Datetime("Fecha de Ingreso", required=True)
    check_out = fields.Datetime("Fecha de Salida", required=True)
    state = fields.Selection([("assigned", "Asignado"), ("unassigned", "Sin Asignar")], "Estado de la Habitacion")
    reservation_id = fields.Many2one("hotel.reservation", "Reservacion")
    status = fields.Selection(string="Estado", related="reservation_id.state")
