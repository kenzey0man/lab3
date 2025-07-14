from odoo import models, fields, api, _


class MedicalPrinting(models.Model):
    _name = 'medical.printing'
    _description = 'Medical Printing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Printing ID', readonly=True, copy=False, default=lambda self: _('New'))
    invoice_id = fields.Many2one('medical.invoice', string='Invoice', required=True, ondelete='cascade')
    
    # Patient Information
    patient_id = fields.Many2one(related='invoice_id.patient_id', string='Patient', store=True)
    patient_name = fields.Char(related='patient_id.name', string='Patient Name', store=True)
    patient_age = fields.Char(related='patient_id.age', string='Patient Age', store=True)
    patient_gender = fields.Selection(related='patient_id.gender', string='Patient Gender', store=True)
    
    # Printing Information
    print_date = fields.Datetime(string='Print Date', default=fields.Datetime.now, tracking=True)
    printed_by = fields.Many2one('res.users', string='Printed By', default=lambda self: self.env.user, tracking=True)
    signed_by = fields.Many2one('res.users', string='Signed By', tracking=True)
    signed_date = fields.Datetime(string='Signed Date', tracking=True)
    
    # Report Configuration
    report_type = fields.Selection([
        ('standard', 'Standard Report'),
        ('detailed', 'Detailed Report'),
        ('summary', 'Summary Report'),
        ('custom', 'Custom Report')
    ], string='Report Type', default='standard', tracking=True)
    
    include_header = fields.Boolean(string='Include Header', default=True)
    include_footer = fields.Boolean(string='Include Footer', default=True)
    include_logo = fields.Boolean(string='Include Logo', default=True)
    include_signature = fields.Boolean(string='Include Signature', default=True)
    
    # Printing Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('printing', 'Printing'),
        ('printed', 'Printed'),
        ('signed', 'Signed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)
    
    # Report Content
    report_content = fields.Html(string='Report Content')
    report_notes = fields.Text(string='Report Notes')
    
    # Related records
    diagnosis_ids = fields.One2many('medical.diagnosis', 'invoice_id', string='Diagnoses')
    test_count = fields.Integer(compute='_compute_test_count', string='Test Count')

    @api.depends('diagnosis_ids')
    def _compute_test_count(self):
        for record in self:
            record.test_count = len(record.diagnosis_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.printing') or _('New')
        return super(MedicalPrinting, self).create(vals)

    def action_start_printing(self):
        """Start printing process"""
        self.write({'state': 'printing'})

    def action_printed(self):
        """Mark as printed"""
        self.write({
            'state': 'printed',
            'print_date': fields.Datetime.now(),
            'printed_by': self.env.user.id
        })

    def action_sign(self):
        """Sign the report"""
        self.write({
            'state': 'signed',
            'signed_date': fields.Datetime.now(),
            'signed_by': self.env.user.id
        })

    def action_deliver(self):
        """Mark as delivered"""
        self.write({'state': 'delivered'})

    def action_cancel(self):
        """Cancel printing"""
        self.write({'state': 'cancelled'})

    def action_reset_pending(self):
        """Reset to pending"""
        self.write({'state': 'pending'})

    def generate_report_content(self):
        """Generate report content based on diagnoses"""
        content = f"""
        <div class="medical-report">
            <h2>Medical Laboratory Report</h2>
            <div class="patient-info">
                <p><strong>Patient Name:</strong> {self.patient_name}</p>
                <p><strong>Patient ID:</strong> {self.patient_id.patient_id}</p>
                <p><strong>Age:</strong> {self.patient_age}</p>
                <p><strong>Gender:</strong> {self.patient_gender}</p>
                <p><strong>Report Date:</strong> {self.print_date.strftime('%Y-%m-%d %H:%M') if self.print_date else ''}</p>
            </div>
            
            <div class="test-results">
                <h3>Test Results</h3>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>Result</th>
                            <th>Unit</th>
                            <th>Normal Range</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for diagnosis in self.diagnosis_ids:
            if diagnosis.state in ['completed', 'verified']:
                result_value = ''
                if diagnosis.test_result_type == 'selection':
                    result_value = diagnosis.selection_result or ''
                elif diagnosis.test_result_type == 'range':
                    result_value = str(diagnosis.numeric_result) if diagnosis.numeric_result is not None else ''
                elif diagnosis.test_result_type == 'quantitative':
                    result_value = str(diagnosis.quantitative_result) if diagnosis.quantitative_result is not None else ''
                elif diagnosis.test_result_type == 'descriptive':
                    result_value = diagnosis.descriptive_result or ''
                
                normal_range = ''
                if diagnosis.test_result_type == 'range':
                    if diagnosis.normal_range_min is not None and diagnosis.normal_range_max is not None:
                        normal_range = f"{diagnosis.normal_range_min} - {diagnosis.normal_range_max}"
                
                content += f"""
                    <tr>
                        <td>{diagnosis.test_name}</td>
                        <td>{result_value}</td>
                        <td>{diagnosis.test_unit or ''}</td>
                        <td>{normal_range}</td>
                        <td>{diagnosis.result_status or ''}</td>
                    </tr>
                """
        
        content += """
                    </tbody>
                </table>
            </div>
            
            <div class="signature-section">
                <p><strong>Printed By:</strong> {printed_by}</p>
                <p><strong>Signed By:</strong> {signed_by}</p>
            </div>
        </div>
        """.format(
            printed_by=self.printed_by.name if self.printed_by else '',
            signed_by=self.signed_by.name if self.signed_by else ''
        )
        
        self.report_content = content
        return content

    def print_report(self):
        """Print the report"""
        self.generate_report_content()
        return self.env.ref('medical_lab_management.action_test_report').report_action(self)