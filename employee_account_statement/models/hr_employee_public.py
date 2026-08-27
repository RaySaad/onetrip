from odoo import api, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    @api.model
    def _account_statement_iqama_field_name(self):
        """Locate the Saudi National / IQAMA field without hard-coding Enterprise internals.

        Saudi payroll is an Enterprise localization and its field can move between
        employee/version models across releases. hr.employee delegates hr.version,
        so scanning hr.employee fields also covers delegated fields.
        """
        employee_model = self.env["hr.employee"]

        # Prefer a field whose label clearly identifies the Saudi National / IQAMA ID.
        for field_name, field in employee_model._fields.items():
            label = (field.string or "").lower().replace("_", " ")
            if (
                field.type in ("char", "text")
                and "iqama" in label
                and ("saudi" in label or "national" in label)
                and (field.store or field.search)
            ):
                return field_name

        # Defensive fallbacks for common/custom technical names.
        candidate_names = (
            "l10n_sa_identification_id",
            "l10n_sa_national_id",
            "saudi_national_id",
            "saudi_iqama_id",
            "iqama_id",
            "identification_id",
        )
        for field_name in candidate_names:
            field = employee_model._fields.get(field_name)
            if field and field.type in ("char", "text") and (field.store or field.search):
                return field_name
        return False

    @api.model
    def _account_statement_iqama_map(self, employee_ids):
        employee_ids = [int(employee_id) for employee_id in employee_ids if employee_id]
        if not employee_ids:
            return {}

        field_name = self._account_statement_iqama_field_name()
        if not field_name:
            return {employee_id: "" for employee_id in employee_ids}

        employees = self.env["hr.employee"].sudo().with_context(active_test=False).browse(employee_ids).exists()
        return {
            employee.id: (employee[field_name] or "")
            for employee in employees
        }

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        """Allow the accounting employee picker to search directly by IQAMA/ID.

        The behavior is enabled only when our accounting fields pass the
        ``account_employee_lookup`` context flag, so other employee dropdowns
        in Odoo keep their normal behavior.
        """
        domain = list(domain or [])
        results = super().name_search(name=name, domain=domain, operator=operator, limit=limit)
        if not self.env.context.get("account_employee_lookup"):
            return results

        ordered_ids = [employee_id for employee_id, _display_name in results]

        if name and (limit is None or len(ordered_ids) < limit):
            field_name = self._account_statement_iqama_field_name()
            if field_name:
                positive_operators = {"=", "ilike", "=ilike", "like", "=like"}
                iqama_operator = operator if operator in positive_operators else "ilike"
                remaining = None if limit is None else max(limit - len(ordered_ids), 0)
                if remaining is None or remaining > 0:
                    private_matches = (
                        self.env["hr.employee"]
                        .sudo()
                        .with_context(active_test=False)
                        .search([(field_name, iqama_operator, name)], limit=remaining or None)
                    )
                    if private_matches:
                        public_domain = domain + [("id", "in", private_matches.ids)]
                        public_matches = self.with_context(active_test=False).search(
                            public_domain,
                            limit=remaining or None,
                        )
                        for employee_id in public_matches.ids:
                            if employee_id not in ordered_ids:
                                ordered_ids.append(employee_id)

        if limit:
            ordered_ids = ordered_ids[:limit]

        employees = self.with_context(active_test=False).browse(ordered_ids).exists()
        employee_by_id = {employee.id: employee for employee in employees}
        iqama_by_id = self._account_statement_iqama_map(ordered_ids)

        formatted_results = []
        for employee_id in ordered_ids:
            employee = employee_by_id.get(employee_id)
            if not employee:
                continue
            iqama = iqama_by_id.get(employee_id) or ""
            label = employee.name or employee.display_name
            if iqama:
                label = f"{label} — {iqama}"
            formatted_results.append((employee.id, label))
        return formatted_results
