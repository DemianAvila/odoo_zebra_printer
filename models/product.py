# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_pos_ids = fields.One2many('parameter.product.pos', 'product_id', string="Parametros de Productos")


class ParameterProductPos(models.Model):
    _name = 'parameter.product.pos'
    _description = 'Parameter Product Pos'

    maximo = fields.Integer(string='Maximo')
    minimo = fields.Integer(string='Minimo')
    config_id = fields.Many2one("pos.config", string="Punto de Venta")
    product_id = fields.Many2one("product.template", string="Producto")