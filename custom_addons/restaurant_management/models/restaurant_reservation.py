# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError

class RestaurantReservation(models.Model):
    _name = 'restaurant.reservation'
    _description = 'Table Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reservation Ref',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True
    )
    table_id = fields.Many2one(
        'restaurant.table',
        string='Table',
        required=True,
        domain="[('is_reservable', '=', True)]",
        tracking=True
    )
    reservation_date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    start_time = fields.Float(
        string='Start Time',
        required=True,
        help="Start hour (e.g., 19.5 is 7:30 PM)",
        tracking=True
    )
    end_time = fields.Float(
        string='End Time',
        required=True,
        help="End hour (e.g., 21.0 is 9:00 PM)",
        tracking=True
    )
    guest_count = fields.Integer(
        string='Guests',
        required=True,
        default=2,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Customer Notes')
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        readonly=True,
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.reservation') or _('New')
        return super().create(vals_list)

    @api.constrains('table_id', 'reservation_date', 'start_time', 'end_time', 'guest_count')
    def _check_reservation_constraints(self):
        for rec in self:
            if rec.start_time >= rec.end_time:
                raise ValidationError(_("Start time must be before end time."))
            if rec.start_time < 0.0 or rec.end_time > 24.0:
                raise ValidationError(_("Times must be between 00:00 and 24:00."))
            if rec.guest_count <= 0:
                raise ValidationError(_("Number of guests must be greater than zero."))
            
            # Check capacity
            if rec.table_id and rec.guest_count > rec.table_id.seats:
                raise ValidationError(_(
                    "The selected table has a capacity of %s seats, which is less than the requested %s guests."
                ) % (rec.table_id.seats, rec.guest_count))

            # Overlap check
            overlap = self.search([
                ('id', '!=', rec.id),
                ('table_id', '=', rec.table_id.id),
                ('reservation_date', '=', rec.reservation_date),
                ('state', 'not in', ['cancelled']),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            if overlap:
                raise ValidationError(_(
                    "Table %s is already reserved during the selected time window on %s."
                ) % (rec.table_id.table_number, rec.reservation_date))

    def action_confirm(self):
        for rec in self:
            # Final overlap guard before confirming
            overlap = self.env['restaurant.reservation'].search([
                ('id', '!=', rec.id),
                ('table_id', '=', rec.table_id.id),
                ('reservation_date', '=', rec.reservation_date),
                ('state', 'not in', ['cancelled']),
                ('start_time', '<', rec.end_time),
                ('end_time', '>', rec.start_time),
            ])
            if overlap:
                raise ValidationError(_(
                    "Table %s is already booked during this time slot. Please choose a different table or time."
                ) % rec.table_id.table_number)
        self.write({'state': 'confirmed'})
        self._send_confirmation_email()

    def action_arrive(self):
        self.write({'state': 'arrived'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def _send_confirmation_email(self):
        """Send reservation confirmation email to the customer."""
        template = self.env.ref(
            'restaurant_management.email_template_reservation',
            raise_if_not_found=False
        )
        if not template:
            return

        # Auto-heal the template in the database to override noupdate=1 limitations
        try:
            # If the database template still uses old Jinja2 syntax, force rewrite to Odoo 19 QWeb syntax
            body = template.body_html or ''
            if '{{' in body or 'object.customer_id.name' in body:
                template.sudo().write({
                    'subject': 'Reservation Confirmation - {{ object.name }}',
                    'email_from': '{{ object.env.company.email or object.create_uid.email or "noreply@restaurant.com" }}',
                    'email_to': '{{ object.customer_id.email }}',
                    'partner_to': '{{ object.customer_id.id }}',
                    'body_html': """
<div style="font-family: Arial, sans-serif; font-size: 14px; max-width: 600px; margin: auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0;">
  <!-- Header -->
  <div style="background: linear-gradient(135deg, #1a1a2e, #0f3460); padding: 32px 24px; text-align: center;">
    <h1 style="color: #e2b04a; margin: 0; font-size: 1.6rem;">🍽️ Table Reservation Confirmed</h1>
    <p style="color: rgba(255,255,255,0.7); margin: 8px 0 0;">Thank you for choosing us!</p>
  </div>
  <!-- Greeting -->
  <div style="padding: 24px 24px 0;">
    <p style="color: #333; font-size: 1rem;">
      Hello <strong><t t-out="object.customer_id.name"/></strong>,
    </p>
    <p style="color: #555;">
      Your table reservation has been <strong style="color: #22c55e;">successfully confirmed!</strong>
      We look forward to welcoming you.
    </p>
  </div>
  <!-- Details Table -->
  <div style="padding: 16px 24px;">
    <table style="width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden;">
      <tr style="background: #f8f9fa;">
        <td style="padding: 12px 16px; font-weight: bold; color: #555; width: 38%; border-bottom: 1px solid #eee;">📋 Reservation Ref</td>
        <td style="padding: 12px 16px; color: #1a1a2e; font-weight: 700; border-bottom: 1px solid #eee;">
          <t t-out="object.name"/>
        </td>
      </tr>
      <tr>
        <td style="padding: 12px 16px; font-weight: bold; color: #555; border-bottom: 1px solid #eee;">📅 Date</td>
        <td style="padding: 12px 16px; color: #333; border-bottom: 1px solid #eee;">
          <t t-out="object.reservation_date"/>
        </td>
      </tr>
      <tr style="background: #f8f9fa;">
        <td style="padding: 12px 16px; font-weight: bold; color: #555; border-bottom: 1px solid #eee;">⏰ Time</td>
        <td style="padding: 12px 16px; color: #333; border-bottom: 1px solid #eee;">
          <t t-out="'%02d:%02d' % (int(object.start_time), int(round((object.start_time % 1) * 60)))"/>
          →
          <t t-out="'%02d:%02d' % (int(object.end_time), int(round((object.end_time % 1) * 60)))"/>
        </td>
      </tr>
      <tr>
        <td style="padding: 12px 16px; font-weight: bold; color: #555; border-bottom: 1px solid #eee;">🪑 Table</td>
        <td style="padding: 12px 16px; color: #333; border-bottom: 1px solid #eee;">
          Table <t t-out="object.table_id.table_number"/>
          <span style="color: #888; font-size: 0.85em;"> — <t t-out="object.table_id.floor_id.name or 'Main Floor'"/></span>
        </td>
      </tr>
      <tr style="background: #f8f9fa;">
        <td style="padding: 12px 16px; font-weight: bold; color: #555;">👥 Guests</td>
        <td style="padding: 12px 16px; color: #333;">
          <t t-out="object.guest_count"/> people
        </td>
      </tr>
    </table>
  </div>
  <!-- Notes -->
  <t t-if="object.notes">
    <div style="padding: 0 24px 16px;">
      <p style="color: #555; font-weight: bold; margin-bottom: 4px;">📝 Your Notes:</p>
      <p style="color: #666; background: #f8f9fa; padding: 12px; border-radius: 6px; margin: 0;">
        <t t-out="object.notes"/>
      </p>
    </div>
  </t>
  <!-- Footer -->
  <div style="background: #1a1a2e; padding: 24px; text-align: center; margin-top: 8px;">
    <p style="color: rgba(255,255,255,0.8); margin: 0 0 4px;">We look forward to serving you!</p>
    <p style="color: #e2b04a; font-weight: bold; margin: 0;">Restaurant Management Team</p>
  </div>
</div>
                    """
                })
        except Exception:
            pass

        for rec in self:
            if not rec.customer_id.email:
                rec.message_post(
                    body=_("Confirmation email could not be sent: customer has no email address."),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                continue
            try:
                # Pass email_to explicitly in email_values as a hard guarantee
                template.sudo().send_mail(
                    rec.id,
                    force_send=True,
                    raise_exception=True,
                    email_values={
                        'email_to': rec.customer_id.email,
                        'email_from': (
                            rec.env.company.email
                            or rec.create_uid.email
                            or 'noreply@restaurant.com'
                        ),
                    },
                )
                rec.message_post(
                    body=_("✅ Confirmation email sent to %s.") % rec.customer_id.email,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception as e:
                rec.message_post(
                    body=_("❌ Failed to send confirmation email: %s") % str(e),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )


    @api.model
    def get_dashboard_statistics(self):
        import datetime
        today = fields.Date.context_today(self)

        total_today = self.env['restaurant.reservation'].sudo().search_count([('reservation_date', '=', today)])
        confirmed_today = self.env['restaurant.reservation'].sudo().search_count([('reservation_date', '=', today), ('state', '=', 'confirmed')])
        arrived_today = self.env['restaurant.reservation'].sudo().search_count([('reservation_date', '=', today), ('state', '=', 'arrived')])
        done_today = self.env['restaurant.reservation'].sudo().search_count([('reservation_date', '=', today), ('state', '=', 'done')])

        # Active kitchen orders (orders not yet served and not cancelled)
        try:
            active_kitchen_orders = self.env['pos.order'].sudo().search_count([
                ('kitchen_state', 'not in', ['served', False]),
                ('state', 'not in', ['cancel', 'cancelled']),
            ])
        except Exception:
            active_kitchen_orders = 0

        # Today's POS sales
        start_of_today = datetime.datetime.combine(today, datetime.time.min)
        end_of_today = datetime.datetime.combine(today, datetime.time.max)
        try:
            pos_orders_today = self.env['pos.order'].sudo().search([
                ('date_order', '>=', start_of_today),
                ('date_order', '<=', end_of_today),
                ('state', 'in', ['paid', 'done', 'invoiced']),
            ])
            total_sales = sum(pos_orders_today.mapped('amount_total'))
        except Exception:
            total_sales = 0.0

        reservable_tables = self.env['restaurant.table'].sudo().search_count([('is_reservable', '=', True)])

        # 5 most recent reservations (any date, newest first)
        recent_reservations = []
        try:
            for r in self.env['restaurant.reservation'].sudo().search([], order='id desc', limit=5):
                recent_reservations.append({
                    'name': r.name,
                    'customer': r.customer_id.name or '—',
                    'table': r.table_id.display_name or '—',
                    'date': str(r.reservation_date),
                    'guests': r.guest_count,
                    'state': r.state,
                })
        except Exception:
            pass

        return {
            'total_today': total_today,
            'confirmed_today': confirmed_today,
            'arrived_today': arrived_today,
            'done_today': done_today,
            'active_kitchen_orders': active_kitchen_orders,
            'total_sales': round(total_sales, 2),
            'reservable_tables': reservable_tables,
            'recent_reservations': recent_reservations,
        }
