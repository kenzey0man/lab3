from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MedicalDiagnosis(models.Model):
    _name = 'medical.diagnosis'
    _description = 'Medical Diagnosis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Diagnosis ID', readonly=True, copy=False, default=lambda self: _('New'))
    invoice_id = fields.Many2one('medical.invoice', string='Invoice', required=True, ondelete='cascade')
    sample_id = fields.Many2one('medical.sample', string='Sample', ondelete='cascade')
    
    # Patient Information
    patient_id = fields.Many2one(related='invoice_id.patient_id', string='Patient', store=True)
    patient_name = fields.Char(related='patient_id.name', string='Patient Name', store=True)
    patient_age = fields.Char(related='patient_id.age', string='Patient Age', store=True)
    patient_gender = fields.Selection(related='patient_id.gender', string='Patient Gender', store=True)
    
    # Test Information
    test_id = fields.Many2one('medical.test', string='Test', required=True)
    test_name = fields.Char(related='test_id.name', string='Test Name', store=True)
    test_shortcut = fields.Char(related='test_id.shortcut', string='Shortcut', store=True)
    test_unit = fields.Char(related='test_id.unit', string='Unit', store=True)
    test_result_type = fields.Selection(related='test_id.result_type', string='Result Type', store=True)
    
    # Diagnosis Information
    diagnosis_date = fields.Datetime(string='Diagnosis Date', default=fields.Datetime.now, tracking=True)
    diagnosed_by = fields.Many2one('res.users', string='Diagnosed By', default=lambda self: self.env.user, tracking=True)
    verified_by = fields.Many2one('res.users', string='Verified By', tracking=True)
    
    # Result Values based on Test Type
    # Selection Type Results
    selection_result = fields.Selection(selection='_get_selection_options', string='Selection Result')
    
    # Range Type Results
    numeric_result = fields.Float(string='Numeric Result')
    normal_range_min = fields.Float(related='test_id.normal_range_min', string='Normal Range Min')
    normal_range_max = fields.Float(related='test_id.normal_range_max', string='Normal Range Max')
    
    # Quantitative Type Results
    quantitative_result = fields.Float(string='Quantitative Result')
    
    # Descriptive Type Results
    descriptive_result = fields.Text(string='Descriptive Result')
    
    # Result Status
    result_status = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
        ('low', 'Low'),
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('abnormal', 'Abnormal'),
        ('critical', 'Critical')
    ], string='Result Status', compute='_compute_result_status', store=True)
    
    # Diagnosis Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)
    
    # Notes and Comments
    diagnosis_notes = fields.Text(string='Diagnosis Notes')
    verification_notes = fields.Text(string='Verification Notes')
    
    # Related records
    result_ids = fields.One2many('medical.test.result', 'diagnosis_id', string='Detailed Results')

    def _get_selection_options(self):
        """Get selection options for the test"""
        if self.test_id and self.test_id.result_type == 'selection':
            options = self.test_id.get_selection_options_list()
            return [(opt, opt) for opt in options]
        return []

    @api.depends('numeric_result', 'selection_result', 'quantitative_result', 'test_id')
    def _compute_result_status(self):
        for record in self:
            if record.test_id.result_type == 'selection':
                if record.selection_result:
                    if 'positive' in record.selection_result.lower():
                        record.result_status = 'positive'
                    elif 'negative' in record.selection_result.lower():
                        record.result_status = 'negative'
                    else:
                        record.result_status = 'normal'
                else:
                    record.result_status = False
                    
            elif record.test_id.result_type == 'range':
                if record.numeric_result is not None:
                    normal_range = record.test_id.get_normal_range(record.patient_gender, self._get_age_years())
                    if normal_range:
                        if record.numeric_result < normal_range['min']:
                            record.result_status = 'low'
                        elif record.numeric_result > normal_range['max']:
                            record.result_status = 'high'
                        else:
                            record.result_status = 'normal'
                    else:
                        record.result_status = 'normal'
                else:
                    record.result_status = False
                    
            elif record.test_id.result_type == 'quantitative':
                if record.quantitative_result is not None:
                    record.result_status = 'normal'
                else:
                    record.result_status = False
                    
            elif record.test_id.result_type == 'descriptive':
                if record.descriptive_result:
                    record.result_status = 'normal'
                else:
                    record.result_status = False

    def _get_age_years(self):
        """Get patient age in years"""
        if self.patient_id and self.patient_id.date_of_birth:
            from datetime import date
            today = date.today()
            birth_date = self.patient_id.date_of_birth
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        return None

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.diagnosis') or _('New')
        return super(MedicalDiagnosis, self).create(vals)

    def action_start_diagnosis(self):
        """Start diagnosis process"""
        self.write({'state': 'in_progress'})

    def action_complete_diagnosis(self):
        """Complete diagnosis"""
        self.write({
            'state': 'completed',
            'diagnosis_date': fields.Datetime.now(),
            'diagnosed_by': self.env.user.id
        })

    def action_verify(self):
        """Verify diagnosis"""
        self.write({
            'state': 'verified',
            'verified_by': self.env.user.id
        })

    def action_cancel(self):
        """Cancel diagnosis"""
        self.write({'state': 'cancelled'})

    def action_reset_pending(self):
        """Reset to pending"""
        self.write({'state': 'pending'})

    @api.onchange('test_id')
    def _onchange_test_id(self):
        """Update fields based on test selection"""
        if self.test_id:
            # Clear previous results
            self.selection_result = False
            self.numeric_result = False
            self.quantitative_result = False
            self.descriptive_result = False


class MedicalTestResult(models.Model):
    _name = 'medical.test.result'
    _description = 'Medical Test Result'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    diagnosis_id = fields.Many2one('medical.diagnosis', string='Diagnosis', required=True, ondelete='cascade')
    test_id = fields.Many2one(related='diagnosis_id.test_id', string='Test', store=True)
    
    # Result Information
    parameter_name = fields.Char(string='Parameter Name', required=True)
    result_value = fields.Char(string='Result Value', required=True)
    unit = fields.Char(string='Unit')
    normal_range = fields.Char(string='Normal Range')
    result_status = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
        ('low', 'Low'),
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('abnormal', 'Abnormal')
    ], string='Status')
    
    # Additional Information
    notes = fields.Text(string='Notes')
    performed_by = fields.Many2one('res.users', string='Performed By', default=lambda self: self.env.user)
    performed_date = fields.Datetime(string='Performed Date', default=fields.Datetime.now)