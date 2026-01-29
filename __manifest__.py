{
    'name': 'FNI Consulting Customizations',
    'summary': 'Custom patches and business logic for FNI Consulting',
    'description': '',

    'author': 'CodeRomz',
    'website': "https://github.com/CodeRomz",
    'license': 'LGPL-3',
    'version': '18.0.1.1.0',

    'category': 'Custom',
    'depends': ['calendar',
                'hr_timesheet',
                'hr_timesheet_sheet',
                'project_timesheet_time_control',
                'hr_holidays',
                'survey',
                'account',
                'hr_timesheet_task_domain',
                'hr_timesheet_task_required',
                'hr_timesheet_time_type',
                'project_timesheet_holidays',
                'hr_timesheet_sheet_autodraft',
                ],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_bank.xml',
        'views/hr_timesheet_sheet_readonly.xml',
        'views/res_config_settings_timesheet_sheet_reminder.xml',
        'views/hr_employee_timesheet_reminder.xml',
        'views/inv_report_override.xml',
        'views/calendar_event_views.xml',
        'wizard/calendar_event_timesheet_wizard.xml',
        'reports/fni_paperformat.xml',
        'reports/invoice_report_fni_template.xml',
        'reports/survey_report_fni_acknowledgement_template.xml',
        'reports/survey_report_action.xml',
        'reports/invoice_report_action.xml',
        'reports/external_layout_striped_header.xml',
        'reports/external_layout_striped_footer.xml',
        'data/report_layout_defaults.xml',
        'data/mail_template_timesheet_sheet_reminder.xml',
        'data/ir_cron_timesheet_sheet_reminder.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'fni_consulting/static/src/scss/firenor_style_backend.scss',
            'fni_consulting/static/src/xml/calendar_popover_timesheet.xml',
            'fni_consulting/static/src/js/calendar_popover_timesheet_patch.js',
        ],
        'web.report_assets_pdf': [
            'fni_consulting/static/src/scss/invoice_report_fni.scss',
            'fni_consulting/static/src/scss/fni_style.scss',
        ],
    },

    'post_init_hook': 'post_init_hook',

    'installable': True,
    'application': False,
}
