import base64
import io
import re
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_amount


class EmployeeAccountStatementWizard(models.TransientModel):
    _name = "employee.account.statement.wizard"
    _description = "Employee Account Statement"

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    employee_id = fields.Many2one(
        "hr.employee.public",
        string="Employee",
        required=True,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        domain="[('company_ids', 'parent_of', company_id)]",
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=_default_date_from,
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    excel_file = fields.Binary(readonly=True)
    excel_filename = fields.Char(readonly=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("Date From cannot be later than Date To."))

    @api.onchange("company_id")
    def _onchange_company_id(self):
        self.employee_id = False
        self.account_id = False

    def _get_private_employee(self):
        self.ensure_one()
        return self.env["hr.employee"].sudo().with_context(active_test=False).browse(self.employee_id.id).exists()

    def _get_iqama(self):
        self.ensure_one()
        iqama_map = self.env["hr.employee.public"]._account_statement_iqama_map([self.employee_id.id])
        return iqama_map.get(self.employee_id.id, "")

    def _base_line_domain(self):
        self.ensure_one()
        return [
            ("employee_id", "=", self.employee_id.id),
            ("account_id", "=", self.account_id.id),
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("display_type", "not in", ("line_section", "line_subsection", "line_note")),
        ]

    def _prepare_statement_data(self):
        self.ensure_one()
        self._check_dates()

        aml_model = self.env["account.move.line"]
        base_domain = self._base_line_domain()

        opening_lines = aml_model.search(base_domain + [("date", "<", self.date_from)])
        opening_balance = sum(opening_lines.mapped("balance"))

        period_lines = aml_model.search(
            base_domain + [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ],
            order="date asc, id asc",
        )

        running_balance = opening_balance
        lines = []
        total_debit = 0.0
        total_credit = 0.0
        currency = self.company_id.currency_id

        for line in period_lines:
            total_debit += line.debit
            total_credit += line.credit
            running_balance += line.debit - line.credit
            lines.append({
                "date": line.date,
                "date_label": line.date.strftime("%d/%m/%Y") if line.date else "",
                "journal": line.journal_id.code or line.journal_id.name or "",
                "entry": line.move_id.name or "",
                "reference": line.ref or line.move_id.ref or "",
                "description": line.name or "",
                "debit": line.debit,
                "credit": line.credit,
                "balance": running_balance,
                "debit_label": format_amount(self.env, line.debit, currency) if line.debit else "",
                "credit_label": format_amount(self.env, line.credit, currency) if line.credit else "",
                "balance_label": format_amount(self.env, running_balance, currency),
            })

        now_utc = fields.Datetime.now()
        local_now = fields.Datetime.context_timestamp(self, now_utc)
        closing_balance = opening_balance + total_debit - total_credit

        department_name = self.employee_id.department_id.display_name if self.employee_id.department_id else ""
        job_title = self.employee_id.job_title or ""

        return {
            "company": self.company_id,
            "employee": self.employee_id,
            "employee_name": self.employee_id.name or self.employee_id.display_name,
            "employee_iqama": self._get_iqama(),
            "department": department_name,
            "job_title": job_title,
            "account": self.account_id,
            "account_name": self.account_id.display_name,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "date_from_label": self.date_from.strftime("%d/%m/%Y"),
            "date_to_label": self.date_to.strftime("%d/%m/%Y"),
            "currency": currency,
            "currency_name": currency.name,
            "opening_balance": opening_balance,
            "period_debit": total_debit,
            "period_credit": total_credit,
            "closing_balance": closing_balance,
            "opening_balance_label": format_amount(self.env, opening_balance, currency),
            "period_debit_label": format_amount(self.env, total_debit, currency),
            "period_credit_label": format_amount(self.env, total_credit, currency),
            "closing_balance_label": format_amount(self.env, closing_balance, currency),
            "lines": lines,
            "printed_by": self.env.user.name,
            "printed_on": local_now.strftime("%d/%m/%Y %H:%M:%S"),
            "posted_only": True,
        }

    def action_print_pdf(self):
        self.ensure_one()
        self._check_dates()
        return self.env.ref("employee_account_statement.action_report_employee_statement").report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        data = self._prepare_statement_data()

        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError(_("The Python package 'XlsxWriter' is required to export Excel files.")) from exc

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet(_("Employee Statement")[:31])

        company = data["company"]
        currency = data["currency"]
        currency_format = f'#,##0.00 "{currency.symbol or currency.name}";[Red]-#,##0.00 "{currency.symbol or currency.name}"'

        fmt_title = workbook.add_format({
            "bold": True,
            "font_size": 18,
            "align": "center",
            "valign": "vcenter",
            "font_color": "#1F2937",
        })
        fmt_company = workbook.add_format({
            "bold": True,
            "font_size": 11,
            "align": "center",
            "font_color": "#6B7280",
        })
        fmt_section = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_color": "#FFFFFF",
            "bg_color": "#374151",
            "border": 1,
            "align": "left",
        })
        fmt_label = workbook.add_format({"bold": True, "font_color": "#4B5563", "border": 1, "bg_color": "#F3F4F6"})
        fmt_value = workbook.add_format({"border": 1, "font_color": "#111827"})
        fmt_header = workbook.add_format({
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#1F2937",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        fmt_text = workbook.add_format({"border": 1, "valign": "top"})
        fmt_date = workbook.add_format({"border": 1, "num_format": "dd/mm/yyyy", "align": "center"})
        fmt_money = workbook.add_format({"border": 1, "num_format": currency_format})
        fmt_money_bold = workbook.add_format({"border": 1, "num_format": currency_format, "bold": True})
        fmt_summary_label = workbook.add_format({"bold": True, "align": "right", "border": 1, "bg_color": "#F3F4F6"})
        fmt_summary_close = workbook.add_format({
            "bold": True,
            "font_size": 11,
            "align": "right",
            "border": 1,
            "bg_color": "#E5E7EB",
        })
        fmt_summary_close_money = workbook.add_format({
            "bold": True,
            "font_size": 11,
            "border": 1,
            "bg_color": "#E5E7EB",
            "num_format": currency_format,
        })
        fmt_note = workbook.add_format({"italic": True, "font_color": "#6B7280", "font_size": 9})

        worksheet.set_column("A:A", 12)
        worksheet.set_column("B:B", 11)
        worksheet.set_column("C:C", 18)
        worksheet.set_column("D:D", 20)
        worksheet.set_column("E:E", 38)
        worksheet.set_column("F:H", 17)
        worksheet.set_row(0, 30)
        worksheet.set_row(1, 24)

        if company.logo:
            try:
                logo_data = io.BytesIO(base64.b64decode(company.logo))
                worksheet.insert_image("A1", "company_logo.png", {
                    "image_data": logo_data,
                    "x_scale": 0.45,
                    "y_scale": 0.45,
                    "x_offset": 4,
                    "y_offset": 4,
                    "object_position": 1,
                })
            except Exception:
                # A malformed/unsupported logo must not block accounting export.
                pass

        worksheet.merge_range("C1:H2", _("EMPLOYEE STATEMENT"), fmt_title)
        worksheet.merge_range("C3:H3", company.name or "", fmt_company)

        worksheet.merge_range("A5:D5", _("EMPLOYEE INFORMATION"), fmt_section)
        worksheet.merge_range("E5:H5", _("STATEMENT INFORMATION"), fmt_section)

        employee_rows = [
            (_("Employee Name"), data["employee_name"]),
            (_("Saudi National / IQAMA ID"), data["employee_iqama"] or "-"),
            (_("Department"), data["department"] or "-"),
            (_("Job Title"), data["job_title"] or "-"),
        ]
        statement_rows = [
            (_("Account"), data["account_name"]),
            (_("Period"), f'{data["date_from_label"]} - {data["date_to_label"]}'),
            (_("Currency"), data["currency_name"]),
            (_("Entries"), _("Posted only")),
        ]

        for offset, (label, value) in enumerate(employee_rows, start=5):
            worksheet.write(offset, 0, label, fmt_label)
            worksheet.merge_range(offset, 1, offset, 3, value, fmt_value)
        for offset, (label, value) in enumerate(statement_rows, start=5):
            worksheet.write(offset, 4, label, fmt_label)
            worksheet.merge_range(offset, 5, offset, 7, value, fmt_value)

        header_row = 10
        headers = [
            _("Date"),
            _("Journal"),
            _("Journal Entry"),
            _("Reference"),
            _("Description"),
            _("Debit"),
            _("Credit"),
            _("Balance"),
        ]
        for col, header in enumerate(headers):
            worksheet.write(header_row, col, header, fmt_header)

        row = header_row + 1
        worksheet.merge_range(row, 0, row, 6, _("Opening Balance"), fmt_summary_label)
        worksheet.write_number(row, 7, data["opening_balance"], fmt_money_bold)
        row += 1

        for line in data["lines"]:
            if line["date"]:
                excel_date = datetime.combine(line["date"], time.min)
                worksheet.write_datetime(row, 0, excel_date, fmt_date)
            else:
                worksheet.write(row, 0, "", fmt_date)
            worksheet.write(row, 1, line["journal"], fmt_text)
            worksheet.write(row, 2, line["entry"], fmt_text)
            worksheet.write(row, 3, line["reference"], fmt_text)
            worksheet.write(row, 4, line["description"], fmt_text)
            worksheet.write_number(row, 5, line["debit"], fmt_money)
            worksheet.write_number(row, 6, line["credit"], fmt_money)
            worksheet.write_number(row, 7, line["balance"], fmt_money)
            row += 1

        row += 1
        summary_rows = [
            (_("Opening Balance"), data["opening_balance"], False),
            (_("Period Debit"), data["period_debit"], False),
            (_("Period Credit"), data["period_credit"], False),
            (_("Closing Balance"), data["closing_balance"], True),
        ]
        for label, amount, is_closing in summary_rows:
            label_fmt = fmt_summary_close if is_closing else fmt_summary_label
            amount_fmt = fmt_summary_close_money if is_closing else fmt_money_bold
            worksheet.merge_range(row, 5, row, 6, label, label_fmt)
            worksheet.write_number(row, 7, amount, amount_fmt)
            row += 1

        row += 1
        worksheet.merge_range(row, 0, row, 3, _("Printed By: %s") % data["printed_by"], fmt_note)
        worksheet.merge_range(row, 4, row, 7, _("Printed On: %s") % data["printed_on"], fmt_note)

        worksheet.freeze_panes(header_row + 1, 0)
        worksheet.autofilter(header_row, 0, max(row - 3, header_row), 7)
        worksheet.repeat_rows(0, header_row)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(0.35, 0.35, 0.5, 0.5)
        worksheet.set_footer(
            f'&L{company.name or ""}&C{_("Employee Statement")}&R{_("Page")} &P {_("of")} &N'
        )

        workbook.close()
        output.seek(0)

        safe_employee = re.sub(r"[^A-Za-z0-9_-]+", "_", data["employee_name"] or "employee").strip("_") or "employee"
        filename = f"Employee_Statement_{safe_employee}_{self.date_from}_{self.date_to}.xlsx"
        self.write({
            "excel_file": base64.b64encode(output.read()),
            "excel_filename": filename,
        })

        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model={self._name}&id={self.id}"
                f"&field=excel_file&filename_field=excel_filename&download=true"
            ),
            "target": "self",
        }
