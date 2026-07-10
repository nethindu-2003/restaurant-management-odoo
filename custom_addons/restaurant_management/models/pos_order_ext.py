# -*- coding: utf-8 -*-

from odoo import fields, models, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    reservation_id = fields.Many2one(
        'restaurant.reservation',
        string='Linked Reservation',
        help="Linked reservation if this order is for a reserved table."
    )

    kitchen_state = fields.Selection([
        ('to_prepare', 'To Prepare'),
        ('preparing', 'Preparing'),
        ('prepared', 'Prepared'),
        ('served', 'Served')
    ], string='Kitchen Status', default='to_prepare', tracking=True)

    kitchen_order_details = fields.Html(
        string='Order Details',
        compute='_compute_kitchen_order_details',
        store=True,
    )

    @api.depends('lines', 'lines.product_id', 'lines.qty', 'lines.customer_note', 'lines.note')
    def _compute_kitchen_order_details(self):
        for order in self:
            details_html = []
            for line in order.lines:
                qty = int(line.qty) if line.qty and line.qty % 1 == 0 else (line.qty or 0)
                prod_name = line.product_id.name or 'Unknown Product'
                
                notes = []
                if line.customer_note:
                    notes.append(line.customer_note)
                if line.note:
                    notes.append(line.note)
                
                notes_str = f" <span style='color: #ef4444; font-size: 0.85em; font-weight: bold;'>({', '.join(notes)})</span>" if notes else ""
                
                details_html.append(
                    f"<div style='margin-bottom: 5px; font-size: 0.95rem; color: #f3f4f6; font-weight: 500;'>"
                    f"<strong style='color: #e2b04a;'>{qty}x</strong> {prod_name}{notes_str}"
                    f"</div>"
                )
            order.kitchen_order_details = "".join(details_html) if details_html else "<div style='color: #888;'>No items</div>"

    def action_kitchen_prepare(self):
        self.write({'kitchen_state': 'preparing'})
        for order in self:
            for line in order.lines:
                product = line.product_id
                if not product:
                    continue
                # Search for BoM of type 'normal' (Manufacture)
                bom = self.env['mrp.bom'].sudo()._bom_find(products=product)[product]
                if bom and bom.type == 'normal':
                    # Create Manufacturing Order
                    mo = self.env['mrp.production'].sudo().create({
                        'product_id': product.id,
                        'product_qty': line.qty,
                        'bom_id': bom.id,
                        'pos_order_id': order.id,
                    })
                    mo.action_confirm()

    def action_kitchen_ready(self):
        self.write({'kitchen_state': 'prepared'})
        for order in self:
            mos = self.env['mrp.production'].sudo().search([
                ('pos_order_id', '=', order.id),
                ('state', 'in', ['draft', 'confirmed', 'progress'])
            ])
            for mo in mos:
                if mo.state == 'draft':
                    mo.action_confirm()
                if not mo.qty_producing:
                    mo.qty_producing = mo.product_qty
                
                # Mark raw materials as consumed (picked) to ensure ingredients are deducted from inventory
                for move in mo.move_raw_ids:
                    if move.state not in ('done', 'cancel'):
                        move.quantity = move.product_uom_qty
                        if 'picked' in move._fields:
                            move.picked = True
                
                # Use context to skip the consumption warning wizard
                mo.with_context(skip_consumption=True).button_mark_done()

    def action_kitchen_serve(self):
        self.write({'kitchen_state': 'served'})
        for order in self:
            # Use sudo() to ensure picking is created regardless of current user permissions
            order.sudo()._create_order_picking()

    def _create_order_picking(self):
        self.ensure_one()
        # Defer picking validation until customer takes the order (kitchen_state == 'served')
        if self.kitchen_state != 'served':
            return
        super()._create_order_picking()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('kitchen_state'):
                vals['kitchen_state'] = 'to_prepare'
        orders = super().create(vals_list)
        for order in orders:
            if order.reservation_id:
                # Mark reservation as arrived if not already, and link it
                if order.reservation_id.state in ['draft', 'confirmed']:
                    order.reservation_id.action_arrive()
                order.reservation_id.pos_order_id = order.id
        return orders

    def write(self, vals):
        if 'kitchen_state' in vals and not vals.get('kitchen_state'):
            vals['kitchen_state'] = 'to_prepare'
        res = super().write(vals)
        for order in self:
            if 'state' in vals and vals['state'] in ['paid', 'done']:
                if order.reservation_id:
                    order.reservation_id.action_done()
        return res


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pos_order_id = fields.Many2one('pos.order', string='POS Order', readonly=True, index=True)


