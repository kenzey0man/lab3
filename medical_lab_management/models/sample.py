from odoo import models, fields, api, _


class MedicalSample(models.Model):
    _name = 'medical.sample'
    _description = 'Medical Sample'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Sample ID', readonly=True, copy=False, default=lambda self: _('New'))
    invoice_id = fields.Many2one('medical.invoice', string='Invoice', required=True, ondelete='cascade')
    barcode = fields.Char(related='invoice_id.barcode', string='Barcode', store=True)
    
    # Patient Information
    patient_id = fields.Many2one(related='invoice_id.patient_id', string='Patient', store=True)
    patient_name = fields.Char(related='patient_id.name', string='Patient Name', store=True)
    patient_age = fields.Char(related='patient_id.age', string='Patient Age', store=True)
    patient_gender = fields.Selection(related='patient_id.gender', string='Patient Gender', store=True)
    
    # Sample Information
    sample_type = fields.Char(string='Sample Type', required=True)
    collection_date = fields.Datetime(string='Collection Date', default=fields.Datetime.now, tracking=True)
    collected_by = fields.Many2one('res.users', string='Collected By', default=lambda self: self.env.user, tracking=True)
    
    # Sample Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('collected', 'Collected'),
        ('sent_to_lab', 'Sent to Lab'),
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)
    
    # Sample Details
    volume = fields.Float(string='Volume (ml)')
    color = fields.Char(string='Color')
    appearance = fields.Text(string='Appearance')
    notes = fields.Text(string='Sample Notes')
    
    # Tests to be performed
    test_ids = fields.Many2many('medical.test', string='Tests to Perform')
    test_count = fields.Integer(compute='_compute_test_count', string='Test Count')
    
    # Related records
    diagnosis_ids = fields.One2many('medical.diagnosis', 'sample_id', string='Diagnoses')

    @api.depends('test_ids')
    def _compute_test_count(self):
        for record in self:
            record.test_count = len(record.test_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.sample') or _('New')
        return super(MedicalSample, self).create(vals)

    def action_collect(self):
        """Mark sample as collected"""
        self.write({
            'state': 'collected',
            'collection_date': fields.Datetime.now(),
            'collected_by': self.env.user.id
        })

    def action_send_to_lab(self):
        """Mark sample as sent to lab"""
        self.write({'state': 'sent_to_lab'})

    def action_receive(self):
        """Mark sample as received"""
        self.write({'state': 'received'})

    def action_processing(self):
        """Mark sample as processing"""
        self.write({'state': 'processing'})

    def action_complete(self):
        """Mark sample as completed"""
        self.write({'state': 'completed'})

    def action_cancel(self):
        """Cancel sample"""
        self.write({'state': 'cancelled'})

    def action_reset_pending(self):
        """Reset to pending"""
        self.write({'state': 'pending'})

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Update sample type and tests based on invoice"""
        if self.invoice_id:
            # Get unique sample types from invoice tests
            sample_types = self.invoice_id.line_ids.mapped('test_id.sample_type')
            if sample_types:
                self.sample_type = ', '.join(set(sample_types))
            
            # Get tests from invoice
            tests = self.invoice_id.line_ids.mapped('test_id')
            self.test_ids = [(6, 0, tests.ids)]