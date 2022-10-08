# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

# class stock_production_lot(models.Model):
# 	_inherit = 'stock.production.lot'
#
# 	name = fields.Char('Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
# 		required=True, help="Unique Lot/Serial Number")

class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	production_id = fields.Many2one("production.order", string="Orden produccion")
	qty_revast = fields.Float(string='Cantidad a Reabastecer',digits=(64,2))
	move_check = fields.Boolean(string='Alerta', track_visibility='always', compute='_get_move_check')

	@api.depends('state')
	def _get_move_check(self):
		for line in self:
			if line.state=='done':
				line.move_check=True
			else:
				line.move_check=False

class ProductionOrder(models.Model):
	_name = 'production.order'
	_description = 'Production Order'
	_rec_name = 'name'

	@api.model
	def _get_default_picking_type(self):
		company_id = self.env.context.get('default_company_id', self.env.company.id)
		return self.env['stock.picking.type'].search([
			('code', '=', 'mrp_operation'),
			('warehouse_id.company_id', '=', company_id),
		], limit=1).id

	name = fields.Char(string=u'Nombre',copy=False, default='/', readonly=True)
	# config_id = fields.Many2one("pos.config", string="Punto de Venta")
	date = fields.Date(string='Fecha',default=fields.Date.context_today)
	company_id = fields.Many2one('res.company', string=u'Compañía', readonly=True, default=lambda self: self.env.company)

	state = fields.Selection([
		('draft', 'Borrador'),
		('confirm', 'En proceso'),
		('done', 'Finalizado'),
		('cancel', 'Cancelado'),
	], 'Estados', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)

	picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        default=_get_default_picking_type, required=True, check_company=True)

	production_count = fields.Integer(compute='_compute_production_count')
	slip_ids = fields.One2many('mrp.production', 'production_id', string='Ordenes de Produccion')

	@api.model
	def create(self, vals):
		if vals.get('name','/') == '/':
			vals['name']= "Produccion del dia %s" % vals.get('date')
		result = super(ProductionOrder,self).create(vals)
		return result

	def _compute_production_count(self):
		for production in self:
			production.production_count = len(production.slip_ids)

	def action_open_productions(self):
		self.ensure_one()
		return {
			"type": "ir.actions.act_window",
			"res_model": "mrp.production",
			"views": [[False, "tree"], [False, "form"]],
			"domain": [['id', 'in', self.slip_ids.ids]],
			"name": "Ordenes de Produccion",
		}

	def action_production_draft(self):
		self.slip_ids.unlink()
		self.write({'state': 'draft'})

	def action_production_cancel(self):
		self.write({'state': 'cancel'})

	def action_production_done(self):
		self.write({'state': 'done'})

	def unlink(self):
		for reg in self:
			if reg.state not in ('draft','cancel'):
				raise UserError("No puede eliminar un Presupuesto que ya esta Confirmado.")
		return super(ProductionOrder, self).unlink()

	def _get_sql(self,date):
		sql = """
		select  T2.date_order,T2.product_id,
        sum(coalesce(T2.qty_ven,0)) as qty_ven,
        sum(coalesce(T2.qty_revast,0)) as qty_revast,T2.company_id   
		from (         
        select T1.date_order,
        pt.name,
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
		and T1.company_id = %d
		)T2
		group by T2.date_order,T2.product_id,T2.company_id
        """% ( (date-relativedelta(days=1)).strftime('%Y/%m/%d'),
			   self.env.company.id
			   )
		return sql

	def get_production_confirm(self):
		for record in self:
			self.env.cr.execute(self._get_sql(self.date))
			res_productos = self.env.cr.dictfetchall()
			# print(res_productos)
			if len(res_productos)==0:
				raise UserError('No se encontro ningun producto a Reabastecer para el %s.' % record.date.strftime('%d-%m-%Y'))
			for product in res_productos:
				product_id = self.env['product.product'].search([('id','=',product['product_id'])],limit=1)
				bom = self.env['mrp.bom']._bom_find(product=product_id, picking_type=record.picking_type_id, company_id=record.company_id.id, bom_type='normal')
				if product['qty_revast']>0:
					data={
						'production_id': record.id,
						'product_id': product['product_id'],
						'qty_revast':product['qty_revast'],
						'product_qty':1,
						'product_uom_id': bom.product_uom_id.id,
						'bom_id': bom.id,
					}
					# print("data",data)
					self.env['mrp.production'].create(data)
			record.state = 'confirm'
		return {
			'effect': {
				'fadeout': 'slow',
				'message': "Generacion exitosa",
				'type': 'rainbow_man',
			}
		}