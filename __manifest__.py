{
    'name': 'FNI Consulting Customizations',
    'version': '17.0.1.0.0',
    'summary': 'Custom patches and business logic for FNI Consulting',

    'author': 'CodeRomz',
    'website': "https://github.com/CodeRomz",
    'license': 'LGPL-3',

    'category': 'Custom',
    'depends': ['hr_timesheet_sheet', 'project_timesheet_time_control'],

    'data': [
        'security/ir.model.access.csv',
        'views/task_type_view.xml',
        'views/account_analytic_line_view.xml',
        'views/hr_timesheet_sheet_readonly.xml',
    ],
    'installable': True,
    'application': False,

}
