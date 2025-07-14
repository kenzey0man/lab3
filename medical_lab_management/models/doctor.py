from odoo import models, fields, api, _


class MedicalDoctor(models.Model):
    _inherit = 'res.partner'
    _description = 'Medical Doctor'

    is_doctor = fields.Boolean(string='Is Doctor', default=False)
    specialization = fields.Char(string='Specialization')
    license_number = fields.Char(string='License Number')
    medical_center = fields.Char(string='Medical Center')
    
    # Related fields for invoices
    referral_invoice_ids = fields.One2many('medical.invoice', 'referral_doctor_id', string='Referral Invoices')
    referral_invoice_count = fields.Integer(compute='_compute_referral_invoice_count', string='Referral Count')

    @api.depends('referral_invoice_ids')
    def _compute_referral_invoice_count(self):
        for record in self:
            record.referral_invoice_count = len(record.referral_invoice_ids)

    def action_view_referrals(self):
        """Smart button to view doctor referrals"""
        return {
            'name': _('Doctor Referrals'),
            'type': 'ir.actions.act_window',
            'res_model': 'medical.invoice',
            'view_mode': 'tree,form',
            'domain': [('referral_doctor_id', '=', self.id)],
            'context': {'default_referral_doctor_id': self.id},
        }

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Search doctors by name or specialization"""
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|',
                     ('name', operator, name),
                     ('specialization', operator, name),
                     ('medical_center', operator, name),
                     ('license_number', operator, name)]
        domain += [('is_doctor', '=', True)]
        return self.search(domain + args, limit=limit).name_get()