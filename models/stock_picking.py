# -*- encoding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging
log = logging.getLogger(__name__)

# class StockMove(models.Model):
# 	_inherit = 'stock.move'
#
# 	def get_despatch_product_name(self):
# 		return self.product_id.display_name

class StockPicking(models.Model):
	_inherit = 'stock.picking'

	config_id = fields.Many2one("pos.config", string="Punto de Venta")

	def _get_sql(self,date,config_id):
		# print("fecha",(date-relativedelta(days=1)).strftime('%Y/%m/%d'))
		sql = """
        select T1.date_order,
        pt.name,
        pt.uom_id,
        pp.id as product_id,
        ppp.config_id,
        ppp.maximo,
        ppp.minimo,
        coalesce(T1.qty_ven,0) as qty_ven,
        CASE
            WHEN coalesce(T1.qty_ven,0) >= ppp.minimo THEN coalesce(T1.qty_ven,0)
            ELSE 0
        END AS qty_revast,
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
		and T1.date_order = '%s'
		and ppp.config_id= %d
		and T1.company_id = %d
        """% ( (date-relativedelta(days=1)).strftime('%Y/%m/%d'),
			   int(config_id),
			   self.env.company.id
			   )
		# print("sql",sql)
		return sql

	def insert(self):
		# self.move_ids_without_package.unlink()
		self.env.cr.execute(self._get_sql(self.scheduled_date,self.config_id))
		res_productos = self.env.cr.dictfetchall()
		# print("res_productos",res_productos)
		if len(res_productos)==0:
			raise UserError('No se encontro ningun producto a Reabastecer para el %s.' % self.scheduled_date.strftime('%d-%m-%Y'))
		vals = []
		for product in res_productos:
			if product['qty_revast']!=0:
				val = {
					'product_id': product['product_id'],
					'product_uom': product['uom_id'],
					'product_uom_qty': product['qty_revast'],
					'picking_id': self.id,
					'name': product['name'],
					'picking_type_id':self.picking_type_id.id,
					'location_id':self.picking_type_id.default_location_src_id.id,
					'location_dest_id':self.picking_type_id.default_location_dest_id.id,
				}
				vals.append(val)
		# print("vals",vals)
		self.env['stock.move'].create(vals)
