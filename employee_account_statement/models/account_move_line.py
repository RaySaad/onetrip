from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    employee_id = fields.Many2one(
        "hr.employee.public",
        string="Employee",
        index=True,
        ondelete="set null",
        check_company=True,
        help="Employee related to this journal item, for example an employee loan or advance.",
    )
