# -*- coding: utf-8 -*-

import datetime
from odoo import http, _
# pyrefly: ignore [missing-import]
from odoo.http import request
from odoo.addons.web.controllers.home import Home

class RestaurantReservationPortal(http.Controller):

    # ============================================================
    # /products — Restaurant Menu Page
    # ============================================================
    @http.route(['/products', '/products/category/<int:categ_id>'],
                type='http', auth='public', website=True)
    def products_page(self, categ_id=None, search='', **kw):
        """Show POS products grouped by category as the restaurant menu."""

        # Fetch all POS categories
        all_categories = request.env['pos.category'].sudo().search([], order='sequence, name')

        # Base domain: only products marked as available in POS
        domain = [('available_in_pos', '=', True), ('sale_ok', '=', True)]

        # Filter by category if requested
        active_categ = None
        if categ_id:
            active_categ = request.env['pos.category'].sudo().browse(categ_id)
            if active_categ.exists():
                domain += [('pos_categ_ids', 'in', [categ_id])]

        # Apply search keyword
        if search:
            domain += [('name', 'ilike', search)]

        products = request.env['product.template'].sudo().search(
            domain, order='pos_sequence, name'
        )

        # Group products by their first POS category
        grouped = {}
        uncategorised = []
        for prod in products:
            if prod.pos_categ_ids:
                cat = prod.pos_categ_ids[0]
                grouped.setdefault(cat, []).append(prod)
            else:
                uncategorised.append(prod)

        values = {
            'all_categories': all_categories,
            'active_categ': active_categ,
            'grouped_products': grouped,
            'uncategorised_products': uncategorised,
            'search': search,
            'page_name': 'products',
        }
        return request.render('restaurant_management.restaurant_products_page', values)

    def _get_time_options(self):
        """Returns half-hour slots for selection"""
        options = []
        for hour in range(11, 23): # 11 AM to 10 PM start times
            options.append((float(hour), f"{hour:02d}:00"))
            options.append((float(hour) + 0.5, f"{hour:02d}:30"))
        return options

    def _get_duration_options(self):
        return [
            (1.0, "1 Hour"),
            (1.5, "1.5 Hours"),
            (2.0, "2 Hours"),
            (2.5, "2.5 Hours"),
            (3.0, "3 Hours"),
        ]

    @http.route(['/reservation'], type='http', auth="user", website=True)
    def reservation_page(self, **post):
        # Extract query parameters
        date_str = post.get('date')
        start_time_str = post.get('start_time')
        duration_str = post.get('duration')
        guest_count_str = post.get('guest_count')

        tables = []
        error_msg = None
        past_time_error = False
        searched = False

        if date_str and start_time_str and duration_str and guest_count_str:
            try:
                int(guest_count_str)  # validate guest count is an integer
                start_time = float(start_time_str)
                duration = float(duration_str)
                end_time = start_time + duration

                # Parse date
                date_val = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

                # ---- Server-side past date/time validation ----
                now = datetime.datetime.now()
                today = now.date()
                current_hour = now.hour + now.minute / 60.0
                if date_val < today or (date_val == today and start_time <= current_hour):
                    past_time_error = True
                else:
                    searched = True
                    # Find reserved table IDs for the given slot
                    overlapping_reservations = request.env['restaurant.reservation'].sudo().search([
                        ('reservation_date', '=', date_val),
                        ('state', 'not in', ['cancelled']),
                        ('start_time', '<', end_time),
                        ('end_time', '>', start_time),
                    ])
                    reserved_table_ids = overlapping_reservations.mapped('table_id.id')

                    # Find available tables (do not filter by individual seats >= guest_count, allowing multi-table booking)
                    tables = request.env['restaurant.table'].sudo().search([
                        ('is_reservable', '=', True),
                        ('id', 'not in', reserved_table_ids)
                    ])

            except Exception:
                error_msg = _("Invalid search input. Please try again.")

        values = {
            'time_options': self._get_time_options(),
            'duration_options': self._get_duration_options(),
            'date': date_str or datetime.date.today().strftime('%Y-%m-%d'),
            'start_time': float(start_time_str or 12.0),
            'duration': float(duration_str or 1.5),
            'guest_count': int(guest_count_str or 2),
            'tables': tables,
            'searched': searched,
            'error_msg': error_msg,
            'past_time_error': past_time_error,
            'page_name': 'reservation',
        }
        return request.render("restaurant_management.reservation_booking_page", values)

    @http.route(['/reservation/book'], type='http', auth="user", methods=['POST'], website=True)
    def submit_reservation(self, **post):
        name = post.get('customer_name')
        email = post.get('customer_email')
        phone = post.get('customer_phone')
        date_str = post.get('date')
        start_time_str = post.get('start_time')
        duration_str = post.get('duration')
        guest_count_str = post.get('guest_count')
        notes = post.get('notes')

        # Retrieve table IDs (can be multiple)
        table_ids_raw = request.httprequest.form.getlist('table_ids') or request.httprequest.form.getlist('table_id') or post.get('table_ids') or post.get('table_id')
        if isinstance(table_ids_raw, str):
            table_ids = [int(x) for x in table_ids_raw.split(',') if x.strip().isdigit()]
        elif isinstance(table_ids_raw, list):
            table_ids = [int(x) for x in table_ids_raw if str(x).isdigit()]
        else:
            try:
                table_ids = [int(table_ids_raw)] if table_ids_raw else []
            except (TypeError, ValueError):
                table_ids = []

        if not (name and email and phone and table_ids and date_str and start_time_str and duration_str and guest_count_str):
            return request.redirect('/reservation?error=missing_fields')

        try:
            guest_count = int(guest_count_str)
            start_time = float(start_time_str)
            duration = float(duration_str)
            end_time = start_time + duration
            date_val = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

            # Server-side past date/time guard (prevent bypass of frontend check)
            now = datetime.datetime.now()
            today = now.date()
            current_hour = now.hour + now.minute / 60.0
            if date_val < today or (date_val == today and start_time <= current_hour):
                return request.redirect('/reservation?past_time=1')

            # Fetch the selected tables
            tables = request.env['restaurant.table'].sudo().browse(table_ids)
            if not tables:
                return request.redirect('/reservation?error=invalid_tables')

            # 1. Create or Find ResPartner (customer)
            partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                })
            else:
                # Update phone if not set or different
                if not partner.phone or partner.phone != phone:
                    partner.sudo().write({'phone': phone})

            # Distribute guest count across tables to respect individual capacity constraints
            # Ensure every table has at least 1 guest
            distribution = {t.id: 1 for t in tables}
            remaining = guest_count - len(tables)

            # Sort tables by remaining capacity descending
            sorted_tables = sorted(tables, key=lambda t: t.seats, reverse=True)
            for t in sorted_tables:
                if remaining <= 0:
                    break
                additional = min(t.seats - 1, remaining)
                distribution[t.id] += additional
                remaining -= additional

            # If there's still remaining guests, put them in the largest table (will trigger capacity constraint failure if exceeded)
            if remaining > 0 and sorted_tables:
                distribution[sorted_tables[0].id] += remaining

            # 2. Create the reservations (one per selected table)
            reservations = request.env['restaurant.reservation'].sudo()
            for t in tables:
                res = request.env['restaurant.reservation'].sudo().create({
                    'customer_id': partner.id,
                    'table_id': t.id,
                    'reservation_date': date_val,
                    'start_time': start_time,
                    'end_time': end_time,
                    'guest_count': distribution[t.id],
                    'notes': notes,
                    'state': 'draft',
                })
                # Auto-confirm and send email
                res.action_confirm()
                reservations |= res

            return request.render("restaurant_management.reservation_success_page", {
                'reservations': reservations,
                'reservation': reservations[0] if reservations else False, # backwards compatibility
                'start_time_str': next((opt[1] for opt in self._get_time_options() if opt[0] == start_time), ""),
                'end_time_str': next((opt[1] for opt in self._get_time_options() if opt[0] == end_time), f"{int(end_time):02d}:{int((end_time%1)*60):02d}"),
            })

        except Exception:
            return request.redirect('/reservation?error=failed_creation')


class CustomHome(Home):

    def _login_redirect(self, uid, redirect=None):
        """Custom post-login redirection based on roles"""
        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)
            if user.has_group('restaurant_management.group_restaurant_admin'):
                return redirect or '/odoo?action=restaurant_management.action_restaurant_dashboard'
            elif user.has_group('restaurant_management.group_restaurant_staff'):
                # Staff go directly to POS — no backend redirect to avoid loops
                return redirect or '/pos/web'
            elif user.has_group('base.group_portal'):
                return redirect or '/reservation'
        return super()._login_redirect(uid, redirect=redirect)

    @http.route()
    def web_client(self, s_action=None, **kw):
        """Enforce role-based access to Odoo backend"""
        if request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid)

            # 1. Portal Customers cannot access backend at all
            if user.has_group('base.group_portal'):
                return request.redirect('/reservation')

            # 2. Admins auto-directed to analytics dashboard if no action requested
            if user.has_group('restaurant_management.group_restaurant_admin'):
                if not s_action and not kw.get('action') and not kw.get('menu_id'):
                    return request.redirect('/odoo?action=restaurant_management.action_restaurant_dashboard')

            # NOTE: Staff are NOT blocked here — /pos/web redirects internally
            # to /odoo/action-pos_menu which would cause an infinite loop if we
            # intercept it. Odoo's native POS group security already blocks
            # non-POS users from accessing POS. Staff can only see POS screens.

        return super().web_client(s_action=s_action, **kw)

