{
    'name': 'FNI Consulting Customizations',
    'version': '17.0.1.0.0',
    'summary': 'Custom patches and business logic for FNI Consulting',
    'author': 'FNI IT Team',
    'category': 'Custom',
    'depends': ['hr_timesheet', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/task_type_view.xml',
        'views/account_analytic_line_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
