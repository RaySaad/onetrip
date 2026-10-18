# Fleet Expenses for Odoo 19 Enterprise

Version 19.0.2.0.3 is built directly from the working 19.0.1.0.1 source. It preserves every V1 field and XML identifier and adds a bilingual Vehicle Account Statement under **Fleet Expenses > Reporting** with PDF and Excel exports.

Financial totals use accounting move lines carrying the native `vehicle_id`. Fleet service history is informational and is never added again, preventing double counting. Asset reporting reuses Odoo 19's native `account.asset.vehicle_id` relationship.

Install by extracting the ZIP into a custom addons directory, updating the Apps list, and installing/upgrading **Fleet Expenses**. Requires Odoo 19 Enterprise modules Expenses, Fleet, Accounting/Fleet, and Assets. Excel export requires the `xlsxwriter` Python package included with standard Odoo distributions.
