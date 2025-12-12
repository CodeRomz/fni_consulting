{
    'name': 'FNI Consulting Customizations',
    'summary': 'Custom patches and business logic for FNI Consulting',
    'Description': '',

    'author': 'CodeRomz',
    'website': "https://github.com/CodeRomz",
    'license': 'LGPL-3',
    'version': '18.0.1.0.0',

    'category': 'Custom',
    'depends': ['hr_timesheet_sheet',
                'project_timesheet_time_control',
                'hr_holidays', 'survey', 'account',
                'hr_timesheet_task_domain',
                'hr_timesheet_task_required',
                'hr_timesheet_time_type',
                'project_timesheet_holidays',
                ],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank.xml',
        'views/res_config_settings.xml',
        'views/hr_timesheet_sheet_readonly.xml',
        'views/inv_report_override.xml',
        'reports/fni_paperformat.xml',
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
