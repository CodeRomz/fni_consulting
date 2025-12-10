{
    'name': 'FNI Consulting Customizations',
    'summary': 'Custom patches and business logic for FNI Consulting',

    'author': 'CodeRomz',
    'website': "https://github.com/CodeRomz",
    'license': 'LGPL-3',
    'version': '18.0.1.0.0',

    'category': 'Custom',
    'depends': ['hr_timesheet_sheet', 'project_timesheet_time_control', 'hr_holidays', 'survey'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank.xml',
        'reports/invoice_report_fni_template.xml',
        'reports/survey_report_fni_acknowledgement_template.xml',
        'reports/survey_report_action.xml',
        'reports/invoice_report_action.xml',
        'reports/external_layout_striped_header.xml',
        'reports/external_layout_striped_footer.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'fni_consulting/static/src/scss/firenor_style_backend.scss',
        ],
        'web.report_assets_pdf': [
            'fni_consulting/static/src/scss/invoice_report_fni.scss',
            'fni_consulting/static/src/scss/fni_style.scss',
        ],
    },

    'installable': True,
    'application': False,
}
