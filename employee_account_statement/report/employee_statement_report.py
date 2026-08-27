from odoo import api, models


class EmployeeStatementReport(models.AbstractModel):
    _name = "report.employee_account_statement.report_employee_statement"
    _description = "Employee Account Statement PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["employee.account.statement.wizard"].browse(docids)
        docs.ensure_one()
        return {
            "doc_ids": docids,
            "doc_model": "employee.account.statement.wizard",
            "docs": docs,
            "statement": docs._prepare_statement_data(),
        }
