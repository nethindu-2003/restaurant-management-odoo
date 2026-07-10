# -*- coding: utf-8 -*-
{
    'name': 'Restaurant Management',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Online Reservations, structured POS billing, KDS and Admin Dashboard',
    'description': """
Restaurant Management System:
- Handles customer table bookings online via Website Portal
- Links reservations directly to POS tables and POS orders
- Displays kitchen order preparation queue (KDS)
- Interactive Admin Analytics Dashboard
    """,
    'depends': [
        'base',
        'website',
        'point_of_sale',
        'pos_restaurant',
        'account',
        'mail',
        'portal',
        'mrp',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'data/reservation_sequence.xml',
        'data/mail_template_data.xml',
        'views/restaurant_table_views.xml',
        'views/reservation_views.xml',
        'views/pos_order_views.xml',
        'views/kitchen_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        'views/website_reservation_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'restaurant_management/static/src/js/restaurant_dashboard.js',
            'restaurant_management/static/src/xml/restaurant_dashboard.xml',
            'restaurant_management/static/src/scss/restaurant.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
