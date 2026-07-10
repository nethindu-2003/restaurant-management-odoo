# Restaurant Management System for Odoo 19

A comprehensive, custom-built Restaurant Management module designed to extend Odoo's native Point of Sale (POS) and Restaurant capabilities. This module provides a complete workflow from customer table reservations to kitchen synchronization and automated inventory deduction based on dish recipes.

## 🌟 Key Features

### 1. Online Table Reservations
- Customers can book tables online via the Website Portal.
- Reservations are directly linked to physical POS Tables and Floors.
- Automated email confirmations sent to customers upon booking.
- Staff can easily manage reservations (Draft -> Confirmed -> Arrived -> Done).

### 2. Kitchen Display System (KDS)
- A dedicated Kitchen Queue interface for chefs to track incoming orders.
- Orders synchronize immediately when placed in the POS.
- Clear status tracking (`To Prepare`, `Preparing`, `Ready`, `Served`).
- Real-time display of special customer requests and item notes (e.g., "Extra Spicy").

### 3. Advanced Ingredient & Inventory Management
- **Admin-Only Access**: Securely restricted to authorized administrators.
- **Recipe Management**: Create a Bill of Materials (BOM) for any POS Product directly on the Product form. Map raw ingredients (e.g., Rice, Chicken) to finished dishes (e.g., Fried Rice).
- **Automated Deduction**: When a POS order is confirmed and Paid, the system silently deducts the exact raw ingredients used from the inventory in the background.
- **Low Stock Alerts**: Define minimum thresholds for ingredients. The system highlights ingredients in red when stock runs low, providing immediate visual warnings.

### 4. Interactive Admin Analytics Dashboard
- A sleek, OWL-powered dashboard built directly into the Odoo backend.
- Displays crucial statistics: Total Daily Revenue, Active Reservations, Current Kitchen Queue size, and Table Occupancy.
- Staff role is granted view access without encountering permission errors.

## 👥 Security Roles

The module introduces specialized security roles to ensure data integrity:
- **Restaurant Management / Staff**: Can manage reservations, view the dashboard, and process POS orders. Cannot see or modify ingredient inventory.
- **Restaurant Management / Admin**: Has full access to the module, including the configuration of raw ingredients, recipe management, and stock thresholds.

## ⚙️ Dependencies

This custom module relies on the following standard Odoo 19 modules:
- `base`
- `website`
- `point_of_sale`
- `pos_restaurant`
- `account`
- `mail`
- `portal`

## 🚀 Getting Started

### Installation
1. Place the `restaurant_management` folder inside your Odoo `addons` directory (or custom addons path).
2. Start the Odoo server.
3. Go to **Apps**, remove the `Apps` filter, search for `Restaurant Management`, and click **Activate**.


## 🛠 Tech Stack
- **Backend**: Python 3, Odoo ORM (Odoo 19)
- **Frontend**: XML, Odoo OWL framework, Bootstrap/SCSS
- **Database**: PostgreSQL
