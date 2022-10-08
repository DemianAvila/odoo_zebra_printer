# -*- coding: utf-8 -*-
{
    "name": "Gestion de Produccion Panificadora",
    "version": "13.0.1.0.0",
    "author": "Giovani Alire",
    "category": "Panificadora",
    "summary": "controla y gestiona los procesos de producción",
    "depends": ["point_of_sale", "stock", "mrp"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/stock_picking_view.xml",
        "views/resumen_production.xml",
        "views/production_order.xml",
        'views/product.xml',
        "views/assets.xml",
    ],
    "qweb": ["static/src/xml/hotel_room_summary.xml"],
    "external_dependencies": {"python": ["dateutil"]},
    "installable": True,
}
