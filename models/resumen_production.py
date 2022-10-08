# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
from odoo import tools

_logger = logging.getLogger(__name__)
try:
    import pytz
except (ImportError, IOError) as err:
    _logger.debug(err)

class ResumenProductionAll(models.Model):
    _name = "resumen.production.all"
    _description = "Resumen Production All"
    _auto = False

    date_order = fields.Date('Fecha')
    product_id = fields.Many2one('product.product',string='Producto')
    config_id = fields.Many2one("pos.config", string="Punto de Venta")
    maximo = fields.Integer(string='Maximo')
    minimo = fields.Integer(string='Minimo')

    qty_ven = fields.Float('Cantidad Ventas')
    qty_revast = fields.Float(string='Cantidad a Reabastecer')

    company_id = fields.Many2one('res.company', string=u'Compañia')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr,self._table)
        self.env.cr.execute("""
		CREATE VIEW resumen_production_all AS (
		SELECT row_number() OVER () AS id, T.* FROM (
		select T1.date_order,
        pt.name,
        pp.id as product_id,
        ppp.config_id,
        ppp.maximo,
        ppp.minimo,
        coalesce(T1.qty_ven,0) as qty_ven,
        T1.company_id
		from (
			select to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text) as date_order,
				   prl.product_id,
				   sum(coalesce(prl.qty,0)) as qty_ven,
				   ps.config_id,
				   prl.company_id
			from pos_order_line as prl
			left join pos_order pr on pr.id=prl.order_id
			left join pos_session ps on ps.id=pr.session_id
			where prl.product_id is not null
			and pr.state not in ('draft','cancel')
			group by prl.product_id,to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text),ps.config_id,prl.company_id
			order by to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text),ps.config_id,prl.product_id
		) T1
		left join product_product pp on pp.id=T1.product_id
		left join product_template pt on pt.id=pp.product_tmpl_id
		left join parameter_product_pos ppp on (ppp.product_id= pt.id and ppp.config_id=T1.config_id)
		where ppp.product_id is not null
--		and T1.date_order between '%s' AND '%s'
--		and T1.company_id = %d
		)T
        )""")

class ResumenProduction(models.Model):
    _name = "resumen.production"
    _description = "Resumen Production"

    name = fields.Char("Resumen de reserva", default="Resumen de reserva")
    date_from = fields.Date("Hasta", default=lambda self: self._context.get('date', fields.Date.context_today(self))- relativedelta(days=6))
    date_to = fields.Date("Fecha Desde", default=fields.Date.context_today)
    config_id = fields.Many2one("pos.config", string="Punto de Venta")
    summary_header = fields.Text("Encabezado de resumen")
    product_summary = fields.Text("Resumen de la habitación")

    def _get_sql_product(self):
        sql = """         
         select pt.name,
        pt.id as product_id,
        ppp.config_id,
        ppp.maximo,
        ppp.minimo,
        T1.company_id
		from (
			select prl.product_id,
				   sum(coalesce(prl.qty,0)) as qty_ven,
				   ps.config_id,
				   prl.company_id
			from pos_order_line as prl
			left join pos_order pr on pr.id=prl.order_id
			left join pos_session ps on ps.id=pr.session_id
			where prl.product_id is not null
			and pr.state not in ('draft','cancel')
			group by prl.product_id,ps.config_id,prl.company_id
			order by ps.config_id,prl.product_id
		) T1
		left join product_product pp on pp.id=T1.product_id
		left join product_template pt on pt.id=pp.product_tmpl_id
		left join parameter_product_pos ppp on (ppp.product_id= pt.id and ppp.config_id=T1.config_id)
		where ppp.product_id is not null
        """
        return sql

    def _get_sql(self,product_id,config_id,date_from,date_to):
        sql = """         
        select T1.date_order,
        pt.name,
        pt.id as product_id,
        ppp.config_id,
        ppp.maximo,
        ppp.minimo,
        coalesce(T1.qty_ven,0) as qty_ven,
        T1.company_id
		from (
			select to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text) as date_order,
				   prl.product_id,
				   sum(coalesce(prl.qty,0)) as qty_ven,
				   ps.config_id,
				   prl.company_id
			from pos_order_line as prl
			left join pos_order pr on pr.id=prl.order_id
			left join pos_session ps on ps.id=pr.session_id
			where prl.product_id is not null
			and pr.state not in ('draft','cancel')
			group by prl.product_id,to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text),ps.config_id,prl.company_id
			order by to_char(pr.date_order::TIMESTAMP - '5 hr'::INTERVAL , 'yyyy/mm/dd'::text),ps.config_id,prl.product_id
		) T1
		left join product_product pp on pp.id=T1.product_id
		left join product_template pt on pt.id=pp.product_tmpl_id
		left join parameter_product_pos ppp on (ppp.product_id= pt.id and ppp.config_id=T1.config_id)
		where ppp.product_id is not null
		and pt.id= %d
		and ppp.config_id= %d
		and T1.date_order between '%s' AND '%s'
		and T1.company_id = %d
        """% ( int(product_id),
			int(config_id),
			date_from.strftime('%Y/%m/%d'),
			date_to.strftime('%Y/%m/%d'),
			self.env.company.id
			)
        return sql

    @api.onchange("date_from", "date_to","config_id")
    def get_product_summary(self):
        res = {}
        all_detail = []
        date_range_list = []
        main_header = []
        summary_header_list = ["Productos","Maximos","Minimos"]
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_("La fecha de salida debe ser mayor que la fecha de registro."))
            d_frm_obj = self.date_from
            d_to_obj = self.date_to
            temp_date = d_frm_obj
            while temp_date <= d_to_obj:
                val = ""
                val = (
                    str(temp_date.strftime("%a"))
                    + " "
                    + str(temp_date.strftime("%b"))
                    + " "
                    + str(temp_date.strftime("%d"))
                )
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime(dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            summary_header_list.append("Reabastecer para %s" % (self.date_to+relativedelta(days=1)).strftime('%d-%m-%Y'))
            self.env.cr.execute(self._get_sql_product())
            product_ids = self.env.cr.dictfetchall()
            # print(product_ids)
            all_product_detail = []
            for product in product_ids:
                if product['config_id']==self.config_id.id:
                    product_detail = {}
                    room_list_stats = []
                    product_detail.update(
                        {
                            "name": product['name'] or "",
                            "maximo": product['maximo'] or "",
                            "minimo": product['minimo'] or "",
                        })
                    # print("product",product)
                    # print("date_range_list",date_range_list)
                    memoria=[]
                    for chk_date in date_range_list:
                        chk_date=datetime.strptime(str(chk_date), '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d')
                        self.env.cr.execute(self._get_sql(product['product_id'],product['config_id'],self.date_from,self.date_to))
                        product_qty_ids = self.env.cr.dictfetchall()
                        # print("product_qty_ids",product_qty_ids)
                        for product_qty in product_qty_ids:
                            if product_qty['date_order'] == self.date_to.strftime('%Y/%m/%d') and product_qty['qty_ven']>=product_qty['minimo']:
                                # print("self.date_to",self.date_to.strftime('%Y/%m/%d'))
                                product_detail.update(
                                {
                                    "qty_revast": product_qty['qty_ven'] or "",
                                })
                            if product_qty['date_order'] == chk_date:
                                # print("product_qty",product_qty)
                                # print("chk_date if",product_qty['date_order'])
                                room_list_stats.append(
                                    {
                                        "color": "Verde",
                                        "qty": product_qty['qty_ven'],
                                        "date": chk_date,
                                        "product_id": product_qty['product_id'] or "",
                                    })
                                memoria.append(product_qty['date_order'])
                            else:
                                # print("memoria else",memoria)
                                if chk_date not in memoria and product_qty['date_order'] not in memoria:
                                    # print("chk_date else",chk_date)
                                    room_list_stats.append(
                                        {
                                            "color": "Rojo",
                                            "qty": 0,
                                            "date": chk_date,
                                            "product_id": product_qty['product_id'] or "",
                                        })
                                    memoria.append(chk_date)
                                else:
                                    continue
                        if chk_date not in memoria:
                            # print("chk_date if fuera bucle",chk_date)
                            room_list_stats.append(
                                {
                                    "color": "Rojo",
                                    "qty": 0,
                                    "date": chk_date,
                                    "product_id": product['product_id'] or "",
                                })
                            memoria.append(chk_date)
                        product_detail.update({"value": room_list_stats})
                    all_product_detail.append(product_detail)
            main_header.append({"header": summary_header_list})
            self.summary_header = str(main_header)
            self.product_summary = str(all_product_detail)
        return res
