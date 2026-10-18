from odoo import api, models


class VehicleAccountStatementReport(models.AbstractModel):
    _name = "report.fleet_expenses.vehicle_account_statement_document"
    _description = "Vehicle Account Statement PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["vehicle.account.statement.wizard"].browse(docids)
        return {"doc_ids": docids, "doc_model": docs._name, "docs": docs, "statements": [wizard._get_statement_data() for wizard in docs]}
