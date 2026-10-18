from collections import defaultdict
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class VehicleAccountStatementWizard(models.TransientModel):
    _name = "vehicle.account.statement.wizard"
    _description = "Vehicle Account Statement"

    vehicle_id = fields.Many2one("fleet.vehicle", required=True, check_company=True)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(month=1, day=1))
    date_to = fields.Date(required=True, default=fields.Date.today)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    posted_only = fields.Boolean(string="Posted Entries Only", default=True)
    include_service_history = fields.Boolean(string="Include Service History", default=True)
    include_depreciation_schedule = fields.Boolean(string="Include Depreciation Schedule", default=False)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_("Date From must be on or before Date To."))

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref("fleet_expenses.action_report_vehicle_account_statement").report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/fleet_expenses/vehicle_statement/{self.id}/xlsx",
            "target": "self",
        }

    @staticmethod
    def _first(record, names, default=False):
        for name in names:
            if name in record._fields:
                value = record[name]
                if value not in (False, None):
                    return value
        return default

    @staticmethod
    def _display(value):
        return value.display_name if hasattr(value, "display_name") else value or ""

    @staticmethod
    def _selection_label(record, field_name):
        value = record[field_name]
        return dict(record._fields[field_name]._description_selection(record.env)).get(value, value or "")

    def _asset_data(self, asset):
        original = float(self._first(asset, ["original_value", "value", "purchase_value"], 0.0))
        salvage = float(self._first(asset, ["salvage_value", "not_depreciable_value"], 0.0))
        book = float(self._first(asset, ["book_value", "value_residual"], 0.0))
        depreciated = max(original - book, 0.0)
        state = self._first(asset, ["state"], "")
        return {
            "id": asset.id,
            "name": asset.display_name,
            "reference": self._first(asset, ["code", "name"], ""),
            "state": self._selection_label(asset, "state"),
            "active_current": state in ("open", "paused", "draft") and bool(asset.active),
            "acquisition_date": self._first(asset, ["acquisition_date", "date"], False),
            "original_value": original,
            "salvage_value": salvage,
            "depreciable_value": original - salvage,
            "depreciated_value": depreciated,
            "book_value": book,
            "method": self._selection_label(asset, "method"),
            "account_asset": self._display(self._first(asset, ["account_asset_id", "account_id"], "")),
            "account_depreciation": self._display(self._first(asset, ["account_depreciation_id"], "")),
            "account_expense": self._display(self._first(asset, ["account_depreciation_expense_id"], "")),
        }

    def _depreciation_rows(self, assets):
        rows = []
        for asset in assets:
            moves = self.env["account.move"]
            for field_name in ("depreciation_move_ids", "account_move_ids", "move_ids"):
                field = asset._fields.get(field_name)
                if field and field.comodel_name == "account.move":
                    moves |= asset[field_name]
            for move in moves.sorted(lambda m: (m.date or fields.Date.today(), m.id)):
                if move.date and move.date > self.date_to:
                    continue
                amount = move.depreciation_value if "depreciation_value" in move._fields else sum(move.line_ids.mapped("debit"))
                rows.append({"asset": asset.display_name, "date": move.date, "entry": move.name, "state": self._selection_label(move, "state"), "amount": amount})
        return rows

    def _get_statement_data(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        line_domain = [
            ("vehicle_id", "=", vehicle.id),
            ("company_id", "=", self.company_id.id),
            ("date", "<=", self.date_to),
            ("account_id.account_type", "in", ["expense", "expense_depreciation", "expense_direct_cost"]),
        ]
        if self.posted_only:
            line_domain.append(("move_id.state", "=", "posted"))
        lifetime_lines = self.env["account.move.line"].search(line_domain, order="date,id")
        period_lines = lifetime_lines.filtered(lambda line: line.date >= self.date_from)

        # Asset depreciation is shown separately from operating expenses.
        operating = period_lines.filtered(lambda line: line.account_id.account_type != "expense_depreciation")
        lifetime_operating = lifetime_lines.filtered(lambda line: line.account_id.account_type != "expense_depreciation")
        depreciation = period_lines - operating
        lifetime_depreciation = lifetime_lines - lifetime_operating

        transactions = []
        by_account = defaultdict(lambda: {"debit": 0.0, "credit": 0.0, "balance": 0.0})
        by_category = defaultdict(float)
        by_source = defaultdict(lambda: {"count": 0, "amount": 0.0})
        for line in operating:
            source = _("Employee Expenses") if line.expense_id else (_("Vendor Bills") if line.move_id.move_type in ("in_invoice", "in_refund") else _("Other"))
            category = line.product_id.display_name if line.product_id else line.account_id.display_name
            amount = line.balance
            transactions.append({
                "date": line.date, "entry": line.move_id.name, "source_document": line.move_id.ref or "",
                "source": source, "partner": line.partner_id.display_name or "", "account": line.account_id.display_name,
                "category": category, "label": line.name or "", "debit": line.debit, "credit": line.credit, "amount": amount,
            })
            account = by_account[line.account_id.display_name]
            account["debit"] += line.debit; account["credit"] += line.credit; account["balance"] += amount
            by_category[category] += amount
            by_source[source]["count"] += 1; by_source[source]["amount"] += amount

        asset_model = self.env["account.asset"]
        assets = asset_model.search([("vehicle_id", "=", vehicle.id), ("company_id", "=", self.company_id.id)])
        asset_rows = [self._asset_data(asset) for asset in assets]
        asset_rows.sort(key=lambda row: (not row["active_current"], row["name"]))

        expense_domain = [("is_fleet_expense", "=", True), ("vehicle_id", "=", vehicle.id), ("date", ">=", self.date_from), ("date", "<=", self.date_to)]
        expenses = self.env["hr.expense"].search(expense_domain, order="date,id")
        accounted_expense_ids = set(period_lines.expense_id.ids)
        expenses = expenses.filtered(lambda expense: expense.id in accounted_expense_ids)
        fuel_expenses = expenses.filtered(lambda e: e.fuel_liters > 0)
        liters = sum(fuel_expenses.mapped("fuel_liters"))
        fuel_cost = sum(operating.filtered(lambda line: line.expense_id in fuel_expenses).mapped("balance"))

        odometers = self.env["fleet.vehicle.odometer"].search([("vehicle_id", "=", vehicle.id), ("date", "<=", self.date_to)], order="date,id")
        before = odometers.filtered(lambda o: o.date < self.date_from)
        during = odometers.filtered(lambda o: o.date >= self.date_from)
        opening_odo = before[-1].value if before else (during[0].value if during else 0.0)
        closing_odo = during[-1].value if during else (before[-1].value if before else 0.0)
        distance = max(closing_odo - opening_odo, 0.0)

        services = []
        if self.include_service_history:
            service_records = self.env["fleet.vehicle.log.services"].search([("vehicle_id", "=", vehicle.id), ("date", ">=", self.date_from), ("date", "<=", self.date_to)], order="date,id")
            for service in service_records:
                services.append({
                    "date": service.date, "service": self._display(self._first(service, ["service_type_id"], "")),
                    "vendor": self._display(self._first(service, ["vendor_id"], "")), "odometer": self._first(service, ["odometer"], 0.0),
                    "cost": self._first(service, ["amount", "cost"], 0.0), "notes": self._first(service, ["description", "notes"], ""),
                })

        period_operating = sum(operating.mapped("balance"))
        lifetime_operating_total = sum(lifetime_operating.mapped("balance"))
        period_depreciation = sum(depreciation.mapped("balance"))
        lifetime_depreciation_total = sum(lifetime_depreciation.mapped("balance"))
        return {
            "wizard": self, "vehicle": vehicle, "company": self.company_id, "currency": self.company_id.currency_id,
            "date_from": self.date_from, "date_to": self.date_to, "posted_only": self.posted_only,
            "assets": asset_rows, "asset_totals": {
                "original": sum(r["original_value"] for r in asset_rows), "salvage": sum(r["salvage_value"] for r in asset_rows),
                "depreciated": sum(r["depreciated_value"] for r in asset_rows), "book": sum(r["book_value"] for r in asset_rows),
            },
            "transactions": transactions,
            "category_summary": [{"name": k, "amount": v} for k, v in sorted(by_category.items())],
            "account_summary": [{"name": k, **v} for k, v in sorted(by_account.items())],
            "source_summary": [{"name": k, **v} for k, v in sorted(by_source.items())],
            "services": services, "depreciation_schedule": self._depreciation_rows(assets) if self.include_depreciation_schedule else [],
            "fuel": {"liters": liters, "cost": fuel_cost, "cost_per_liter": fuel_cost / liters if liters else 0.0, "consumption_100km": liters * 100 / distance if distance else 0.0, "cost_per_km": fuel_cost / distance if distance else 0.0},
            "odometer": {"opening": opening_odo, "closing": closing_odo, "distance": distance},
            "totals": {"period_operating": period_operating, "period_depreciation": period_depreciation, "period_total": period_operating + period_depreciation,
                "lifetime_operating": lifetime_operating_total, "lifetime_depreciation": lifetime_depreciation_total, "lifetime_total": lifetime_operating_total + lifetime_depreciation_total,
                "operating_cost_km": period_operating / distance if distance else 0.0, "total_cost_km": (period_operating + period_depreciation) / distance if distance else 0.0},
        }
