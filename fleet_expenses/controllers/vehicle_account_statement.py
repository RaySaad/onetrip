import io

from odoo import _, http
from odoo.http import content_disposition, request


class VehicleAccountStatementController(http.Controller):
    @http.route("/fleet_expenses/vehicle_statement/<int:wizard_id>/xlsx", type="http", auth="user")
    def download_xlsx(self, wizard_id, **kwargs):
        wizard = request.env["vehicle.account.statement.wizard"].browse(wizard_id).exists()
        if not wizard:
            return request.not_found()
        wizard.check_access("read")
        data = wizard._get_statement_data()
        try:
            import xlsxwriter
        except ImportError:
            return request.make_response("Python package xlsxwriter is required.", status=500)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        title = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#1F4E78"})
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        money = workbook.add_format({"num_format": "#,##0.00;[Red](#,##0.00)", "border": 1})
        cell = workbook.add_format({"border": 1})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1})

        def sheet(name, columns):
            ws = workbook.add_worksheet(name[:31])
            if request.env.lang.startswith("ar"):
                ws.right_to_left()
            ws.freeze_panes(1, 0)
            for col, label in enumerate(columns):
                ws.write(0, col, label, header)
                ws.set_column(col, col, max(13, min(32, len(label) + 4)))
            return ws

        ws = workbook.add_worksheet(_("Summary")[:31])
        if request.env.lang.startswith("ar"):
            ws.right_to_left()
        ws.set_column("A:A", 32); ws.set_column("B:B", 22)
        ws.write("A1", _("Vehicle Account Statement"), title)
        summary = [
            (_("Vehicle"), data["vehicle"].display_name), (_("Company"), data["company"].display_name),
            (_("Period"), _("%(date_from)s to %(date_to)s", date_from=data["date_from"], date_to=data["date_to"])), (_("Currency"), data["currency"].name),
            (_("Period Operating Expenses"), data["totals"]["period_operating"]), (_("Period Depreciation"), data["totals"]["period_depreciation"]),
            (_("Period Total Cost"), data["totals"]["period_total"]), (_("Lifetime Total Cost"), data["totals"]["lifetime_total"]),
            (_("Opening Odometer"), data["odometer"]["opening"]), (_("Closing Odometer"), data["odometer"]["closing"]),
            (_("Distance"), data["odometer"]["distance"]), (_("Total Cost / KM"), data["totals"]["total_cost_km"]),
        ]
        for row, (label, value) in enumerate(summary, 2):
            ws.write(row, 0, label, header); ws.write(row, 1, value, money if isinstance(value, (int, float)) else cell)

        ws = sheet(_("Assets & Depreciation"), [_('Current'), _('Asset'), _('Reference'), _('State'), _('Acquisition Date'), _('Original Value'), _('Salvage'), _('Depreciated'), _('Book Value'), _('Method')])
        for row, item in enumerate(data["assets"], 1):
            vals = [_('Yes') if item["active_current"] else "", item["name"], item["reference"], item["state"], item["acquisition_date"], item["original_value"], item["salvage_value"], item["depreciated_value"], item["book_value"], item["method"]]
            for col, value in enumerate(vals): ws.write(row, col, value, date_fmt if col == 4 else (money if col in (5, 6, 7, 8) else cell))

        ws = sheet(_("Expense Transactions"), [_('Date'), _('Entry'), _('Source Document'), _('Source'), _('Partner/Employee'), _('Account'), _('Category'), _('Label'), _('Debit'), _('Credit'), _('Balance')])
        for row, item in enumerate(data["transactions"], 1):
            vals = [item[k] for k in ("date", "entry", "source_document", "source", "partner", "account", "category", "label", "debit", "credit", "amount")]
            for col, value in enumerate(vals): ws.write(row, col, value, date_fmt if col == 0 else (money if col >= 8 else cell))

        ws = sheet(_("Expense Summary"), [_('Type'), _('Name'), _('Count'), _('Debit'), _('Credit'), _('Amount')])
        row = 1
        for item in data["category_summary"]:
            ws.write_row(row, 0, [_('Category'), item["name"], "", "", "", item["amount"]], cell); row += 1
        for item in data["account_summary"]:
            ws.write_row(row, 0, [_('GL Account'), item["name"], "", item["debit"], item["credit"], item["balance"]], cell); row += 1
        for item in data["source_summary"]:
            ws.write_row(row, 0, [_('Source'), item["name"], item["count"], "", "", item["amount"]], cell); row += 1

        ws = sheet(_("Service History"), [_('Date'), _('Service'), _('Vendor'), _('Odometer'), _('Cost (Informational)'), _('Notes')])
        for row, item in enumerate(data["services"], 1):
            vals = [item[k] for k in ("date", "service", "vendor", "odometer", "cost", "notes")]
            for col, value in enumerate(vals): ws.write(row, col, value, date_fmt if col == 0 else (money if col == 4 else cell))

        ws = sheet(_("Fuel"), [_('Metric'), _('Value')])
        fuel_rows = [(_("Total Liters"), data["fuel"]["liters"]), (_("Fuel Expense Amount"), data["fuel"]["cost"]), (_("Average Cost / Liter"), data["fuel"]["cost_per_liter"]), (_("Consumption L / 100 KM"), data["fuel"]["consumption_100km"]), (_("Fuel Cost / KM"), data["fuel"]["cost_per_km"])]
        for row, values in enumerate(fuel_rows, 1): ws.write_row(row, 0, values, cell)

        ws = sheet(_("Depreciation Schedule"), [_('Asset'), _('Date'), _('Entry'), _('State'), _('Amount')])
        for row, item in enumerate(data["depreciation_schedule"], 1):
            vals = [item[k] for k in ("asset", "date", "entry", "state", "amount")]
            for col, value in enumerate(vals): ws.write(row, col, value, date_fmt if col == 1 else (money if col == 4 else cell))

        workbook.close(); output.seek(0)
        filename = f"Vehicle_Account_Statement_{data['vehicle'].license_plate or data['vehicle'].id}.xlsx"
        return request.make_response(output.read(), headers=[("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("Content-Disposition", content_disposition(filename))])
