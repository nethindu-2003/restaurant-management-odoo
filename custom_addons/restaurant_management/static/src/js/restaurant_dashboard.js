/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class RestaurantDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: null,
            lastUpdated: null,
            stats: {
                total_today: 0,
                confirmed_today: 0,
                arrived_today: 0,
                done_today: 0,
                active_kitchen_orders: 0,
                total_sales: 0.0,
                reservable_tables: 0,
                recent_reservations: [],
            },
        });

        this._refreshInterval = null;

        onMounted(async () => {
            await this.loadStats();
            // Auto-refresh every 30 seconds
            this._refreshInterval = setInterval(() => this.loadStats(), 30000);
        });

        onWillUnmount(() => {
            if (this._refreshInterval) {
                clearInterval(this._refreshInterval);
            }
        });
    }

    async loadStats() {
        this.state.loading = true;
        this.state.error = null;
        try {
            // @api.model method: call with empty positional args []
            const data = await this.orm.call(
                "restaurant.reservation",
                "get_dashboard_statistics",
                []
            );
            this.state.stats = data;
            this.state.lastUpdated = new Date().toLocaleTimeString();
        } catch (error) {
            console.error("Dashboard load failed:", error);
            this.state.error = "Failed to load dashboard data. Please refresh.";
            this.notification.add(
                "Dashboard refresh failed. Check your connection.",
                { type: "warning", sticky: false }
            );
        } finally {
            this.state.loading = false;
        }
    }

    formatCurrency(value) {
        return parseFloat(value || 0).toFixed(2);
    }

    getStateBadgeClass(state) {
        const map = {
            confirmed: "bg-success",
            draft:     "bg-info",
            arrived:   "bg-warning text-dark",
            done:      "bg-secondary",
            cancelled: "bg-danger",
        };
        return "badge " + (map[state] || "bg-secondary");
    }

    getStateLabel(state) {
        const map = {
            confirmed: "Confirmed",
            draft:     "Pending",
            arrived:   "Arrived",
            done:      "Done",
            cancelled: "Cancelled",
        };
        return map[state] || state;
    }

    // Quick-navigation actions
    openReservations() {
        this.action.doAction("restaurant_management.action_restaurant_reservation");
    }

    openKitchenQueue() {
        this.action.doAction("restaurant_management.action_kitchen_order_queue");
    }
}

RestaurantDashboard.template = "restaurant_management.RestaurantDashboard";
registry.category("actions").add("restaurant_management.dashboard", RestaurantDashboard);
export { RestaurantDashboard };
