from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta


class MedicalInvoice(models.Model):
    _name = 'medical.invoice'
    _description = 'Medical Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Invoice ID', readonly=True, copy=False, default=lambda self: _('New'))
    barcode = fields.Char(string='Barcode ID', readonly=True, copy=False, default=lambda self: _('New'))
    
    # Patient Information
    patient_id = fields.Many2one('medical.patient', string='Patient', required=True, tracking=True)
    patient_name = fields.Char(related='patient_id.name', string='Patient Name', store=True)
    patient_age = fields.Char(related='patient_id.age', string='Patient Age', store=True)
    patient_gender = fields.Selection(related='patient_id.gender', string='Patient Gender', store=True)
    
    # Doctor Information
    referral_doctor_id = fields.Many2one('res.partner', string='Referral Doctor', 
                                        domain=[('is_doctor', '=', True)], tracking=True)
    
    # Financial Information
    subtotal = fields.Float(string='Subtotal', compute='_compute_amounts', store=True)
    discount = fields.Float(string='Discount', default=0.0, tracking=True)
    total = fields.Float(string='Total', compute='_compute_amounts', store=True)
    amount_paid = fields.Float(string='Amount Paid', default=0.0, tracking=True)
    amount_due = fields.Float(string='Amount Due', compute='_compute_amounts', store=True)
    
    # Dates
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.today, tracking=True)
    due_date = fields.Date(string='Due Date', compute='_compute_due_date', store=True)
    
    # Notes and Status
    visit_notes = fields.Text(string='Visit Notes', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sample_collected', 'Sample Collected'),
        ('diagnosis', 'Diagnosis'),
        ('printing', 'Printing'),
        ('signed', 'Signed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # User Information
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    
    # Related Records
    line_ids = fields.One2many('medical.invoice.line', 'invoice_id', string='Invoice Lines')
    sample_ids = fields.One2many('medical.sample', 'invoice_id', string='Samples')
    diagnosis_ids = fields.One2many('medical.diagnosis', 'invoice_id', string='Diagnoses')
    
    # Computed Fields
    test_count = fields.Integer(compute='_compute_test_count', string='Test Count')
    sample_count = fields.Integer(compute='_compute_sample_count', string='Sample Count')
    diagnosis_count = fields.Integer(compute='_compute_diagnosis_count', string='Diagnosis Count')
    
    # Activities tracking
    activities = fields.Text(string='Activities', compute='_compute_activities', store=True)

    @api.depends('line_ids.price_subtotal')
    def _compute_amounts(self):
        for record in self:
            record.subtotal = sum(record.line_ids.mapped('price_subtotal'))
            record.total = record.subtotal - record.discount
            record.amount_due = record.total - record.amount_paid

    @api.depends('invoice_date')
    def _compute_due_date(self):
        for record in self:
            if record.invoice_date:
                # Default due date is 7 days from invoice date
                record.due_date = record.invoice_date + timedelta(days=7)
            else:
                record.due_date = False

    @api.depends('line_ids')
    def _compute_test_count(self):
        for record in self:
            record.test_count = len(record.line_ids)

    @api.depends('sample_ids')
    def _compute_sample_count(self):
        for record in self:
            record.sample_count = len(record.sample_ids)

    @api.depends('diagnosis_ids')
    def _compute_diagnosis_count(self):
        for record in self:
            record.diagnosis_count = len(record.diagnosis_ids)

    @api.depends('state', 'create_date', 'user_id')
    def _compute_activities(self):
        for record in self:
            activities = []
            if record.create_date:
                activities.append(f"Created on {record.create_date.strftime('%Y-%m-%d %H:%M')} by {record.user_id.name}")
            if record.state != 'draft':
                activities.append(f"Status: {dict(record._fields['state'].selection).get(record.state)}")
            record.activities = '\n'.join(activities)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.invoice') or _('New')
        if vals.get('barcode', _('New')) == _('New'):
            vals['barcode'] = self.env['ir.sequence'].next_by_code('medical.barcode') or _('New')
        return super(MedicalInvoice, self).create(vals)

    def action_confirm(self):
        """Confirm the invoice"""
        self.write({'state': 'confirmed'})

    def action_collect_sample(self):
        """Move to sample collection"""
        self.write({'state': 'sample_collected'})

    def action_start_diagnosis(self):
        """Move to diagnosis"""
        self.write({'state': 'diagnosis'})

    def action_printing(self):
        """Move to printing"""
        self.write({'state': 'printing'})

    def action_sign(self):
        """Move to signed"""
        self.write({'state': 'signed'})

    def action_done(self):
        """Complete the invoice"""
        self.write({'state': 'done'})

    def action_cancel(self):
        """Cancel the invoice"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def print_worksheet(self):
        """Print worksheet"""
        return self.env.ref('medical_lab_management.action_worksheet_report').report_action(self)

    def print_barcode(self):
        """Print barcode sticker"""
        return self.env.ref('medical_lab_management.action_barcode_report').report_action(self)

    def print_receipt(self):
        """Print receipt"""
        return self.env.ref('medical_lab_management.action_receipt_report').report_action(self)

    def print_test_report(self):
        """Print test report"""
        return self.env.ref('medical_lab_management.action_test_report').report_action(self)


class MedicalInvoiceLine(models.Model):
    _name = 'medical.invoice.line'
    _description = 'Medical Invoice Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    invoice_id = fields.Many2one('medical.invoice', string='Invoice', required=True, ondelete='cascade')
    
    # Test Information
    test_id = fields.Many2one('medical.test', string='Test', required=True)
    test_name = fields.Char(related='test_id.name', string='Test Name', store=True)
    test_shortcut = fields.Char(related='test_id.shortcut', string='Shortcut', store=True)
    test_unit = fields.Char(related='test_id.unit', string='Unit', store=True)
    
    # Pricing
    price_unit = fields.Float(string='Unit Price', required=True, default=0.0)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sample_collected', 'Sample Collected'),
        ('diagnosis', 'Diagnosis'),
        ('printing', 'Printing'),
        ('signed', 'Signed'),
        ('done', 'Done')
    ], string='Status', default='pending', tracking=True)
    
    # Results
    result_value = fields.Char(string='Result Value')
    result_status = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
        ('low', 'Low'),
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('abnormal', 'Abnormal')
    ], string='Result Status')
    result_notes = fields.Text(string='Result Notes')
    
    # Users involved
    collected_by = fields.Many2one('res.users', string='Collected By')
    diagnosed_by = fields.Many2one('res.users', string='Diagnosed By')
    printed_by = fields.Many2one('res.users', string='Printed By')
    signed_by = fields.Many2one('res.users', string='Signed By')

    @api.depends('price_unit')
    def _compute_subtotal(self):
        for record in self:
            record.price_subtotal = record.price_unit

    @api.onchange('test_id')
    def _onchange_test_id(self):
        if self.test_id:
            self.price_unit = self.test_id.price

    def action_sample_collected(self):
        """Mark sample as collected"""
        self.write({
            'state': 'sample_collected',
            'collected_by': self.env.user.id
        })

    def action_diagnosis(self):
        """Mark as in diagnosis"""
        self.write({
            'state': 'diagnosis',
            'diagnosed_by': self.env.user.id
        })

    def action_printing(self):
        """Mark as in printing"""
        self.write({
            'state': 'printing',
            'printed_by': self.env.user.id
        })

    def action_signed(self):
        """Mark as signed"""
        self.write({
            'state': 'signed',
            'signed_by': self.env.user.id
        })

    def action_done(self):
        """Mark as done"""
        self.write({'state': 'done'})