{
    "name": "Employee Account Statement",
    "version": "19.0.1.0.4",
    "category": "Accounting/Accounting",
    "summary": "Assign employees to journal items and print employee account statements",
    "description": """
Employee Account Statement for Odoo 19
======================================
* Employee field on Journal Items.
* Employee lookup by name or Saudi National / IQAMA ID.
* Employee Statement wizard under Accounting > Reporting.
* Posted-entry opening balance, period activity, running balance and closing balance.
* Professional PDF and XLSX exports including company logo, print user and print time.
""",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account",
        "hr",
        "l10n_sa_hr_payroll",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_line_views.xml",
        "wizard/employee_statement_wizard_views.xml",
        "report/employee_statement_report.xml",
    ],
    "installable": True,
    "application": False,
}
