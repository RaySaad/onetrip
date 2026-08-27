from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Carry the Fleet Expense vehicle onto the accounting expense line.

        Odoo 19's account_fleet module already provides account.move.line.vehicle_id.
        Expense-generated move lines contain expense_id, so this keeps Vehicle as a
        common accounting dimension without changing Odoo's native posting flow.
        """
        expense_ids = {
            vals.get('expense_id')
            for vals in vals_list
            if vals.get('expense_id') and not vals.get('vehicle_id')
        }
        expenses = {
            expense.id: expense
            for expense in self.env['hr.expense'].browse(expense_ids).exists()
        }

        for vals in vals_list:
            expense = expenses.get(vals.get('expense_id'))
            if expense and expense.is_fleet_expense and expense.vehicle_id and not vals.get('vehicle_id'):
                vals['vehicle_id'] = expense.vehicle_id.id

        return super().create(vals_list)
