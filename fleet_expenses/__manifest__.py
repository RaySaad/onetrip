{
    'name': 'Fleet Expenses',
    'version': '19.0.1.0.1',
    'summary': 'Track employee and company-paid vehicle expenses by fleet vehicle',
    'description': """
Fleet Expenses
==============
Extends Odoo Expenses with vehicle-specific tracking while preserving Odoo's
native expense approval, reimbursement, accounting, and Fleet vendor-bill flow.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'category': 'Human Resources/Expenses',
    'depends': [
        'fleet',
        'hr_expense',
        'account_fleet',
    ],
    'data': [
        'views/hr_expense_views.xml',
        'views/fleet_expense_menus.xml',
    ],
    'application': True,
    'installable': True,
}
