from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    is_fleet_expense = fields.Boolean(
        string='Fleet Expense',
        default=lambda self: bool(self.env.context.get('default_is_fleet_expense')),
        index=True,
        tracking=True,
        help='Enable this option when the expense belongs to a fleet vehicle.',
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle',
        index=True,
        tracking=True,
        check_company=True,
        help='Vehicle that incurred this expense.',
    )
    vehicle_odometer = fields.Float(
        string='Odometer',
        tracking=True,
        help='Vehicle odometer reading when the expense was incurred.',
    )
    fuel_liters = fields.Float(
        string='Fuel Quantity (L)',
        tracking=True,
        help='Optional fuel quantity in liters for fuel expenses.',
    )
    fuel_cost_per_liter = fields.Monetary(
        string='Cost / Liter',
        currency_field='currency_id',
        compute='_compute_fuel_cost_per_liter',
        store=True,
        help='Total expense amount divided by fuel quantity.',
    )

    @api.depends('total_amount_currency', 'fuel_liters')
    def _compute_fuel_cost_per_liter(self):
        for expense in self:
            expense.fuel_cost_per_liter = (
                expense.total_amount_currency / expense.fuel_liters
                if expense.fuel_liters
                else 0.0
            )

    def action_submit(self):
        missing_vehicle = self.filtered(lambda expense: expense.is_fleet_expense and not expense.vehicle_id)
        if missing_vehicle:
            raise ValidationError(_('A vehicle is required before submitting a Fleet Expense.'))
        return super().action_submit()

    @api.constrains('vehicle_odometer', 'fuel_liters')
    def _check_vehicle_values(self):
        for expense in self:
            if expense.vehicle_odometer < 0:
                raise ValidationError(_('Odometer cannot be negative.'))
            if expense.fuel_liters < 0:
                raise ValidationError(_('Fuel quantity cannot be negative.'))
