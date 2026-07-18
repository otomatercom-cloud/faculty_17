{
    'name': 'Faculty',
    'version': '1.0.0',
    'summary': 'faculty expenses',
    'description': """
        this module for faculty class hours records submission.
    """,
    'author': 'Ajesh',
    'website': 'https://www.yourwebsite.com',
    'category': 'Specific Category',
    'license': 'LGPL-3',
    'depends': [
        'base',  # List of module dependencies
        'mail', 'web', 'hr', 'openeducat_core','logic_base_17', 'website'
        # Add other module dependencies here
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/faculty_details.xml',# Access rights
        'views/class_record.xml',
        'views/user.xml',
        'views/subject_stnd_hr.xml',
        'views/faculty_rates.xml',
        'views/rejection.xml',
        'views/lock_day.xml',
        'data/activity.xml',
        'views/portal_templates.xml',

    ],
    'assets': {
        'web.assets_backend': [

            '/faculty_17/static/src/css/style.css',

        ],
    },

    'installable': True,  # Whether the module can be installed
    'application': True,  # Set to True if it's an application module
    'auto_install': False,  # Automatically install if dependencies are met

}
