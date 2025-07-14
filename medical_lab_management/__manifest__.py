{
    'name': 'Medical Lab Management',
    'version': '1.0.0',
    'category': 'Healthcare',
    'summary': 'Comprehensive Medical Laboratory Management System',
    'description': """
        Medical Lab Management System for Odoo 17
        
        Features:
        - Patient Management with auto-generated IDs
        - Invoice and Billing Management
        - Sample Collection and Tracking
        - Test Management with Multiple Result Types
        - Diagnosis and Result Recording
        - Report Printing and Signing
        - Barcode Generation and Printing
        - Workflow Management
        - User Permissions and Activity Logging
    """,
    'author': 'Medical Lab Management',
    'website': 'https://www.example.com',
    'depends': [
        'base',
        'mail',
        'account',
        'contacts',
        'product',
        'report_xlsx',
        'barcode',
        'web',
    ],
    'data': [
        'security/medical_lab_security.xml',
        'security/ir.model.access.csv',
        'data/medical_lab_data.xml',
        'views/patient_views.xml',
        'views/doctor_views.xml',
        'views/test_views.xml',
        'views/invoice_views.xml',
        'views/sample_views.xml',
        'views/diagnosis_views.xml',
        'views/printing_views.xml',
        'views/menu_views.xml',
        'reports/worksheet_report.xml',
        'reports/barcode_report.xml',
        'reports/receipt_report.xml',
        'reports/test_report.xml',
    ],
    'demo': [
        'demo/medical_lab_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'medical_lab_management/static/src/js/medical_lab.js',
            'medical_lab_management/static/src/css/medical_lab.css',
        ],
    },
}