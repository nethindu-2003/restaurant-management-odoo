# -*- coding: utf-8 -*-

from odoo import fields, models

class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    is_reservable = fields.Boolean(
        string='Reservable',
        default=False,
        help="If checked, this table can be booked online by customers."
    )
    reservation_ids = fields.One2many(
        'restaurant.reservation',
        'table_id',
        string='Reservations'
    )
