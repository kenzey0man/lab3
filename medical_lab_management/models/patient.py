from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
import re


class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _description = 'Medical Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Patient Name', required=True, tracking=True)
    patient_id = fields.Char(string='Patient ID', readonly=True, copy=False, default=lambda self: _('New'))
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    age = fields.Char(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', required=True, tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)
    notes = fields.Text(string='Patient Notes')
    active = fields.Boolean(default=True, string='Active')
    
    # Related fields for invoices
    invoice_ids = fields.One2many('medical.invoice', 'patient_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            if record.date_of_birth:
                today = date.today()
                birth_date = record.date_of_birth
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                
                if age > 0:
                    record.age = f"{age} Years"
                else:
                    # Calculate months and days for children under 1 year
                    months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
                    if months > 0:
                        record.age = f"{months} Months"
                    else:
                        days = (today - birth_date).days
                        record.age = f"{days} Days"
            else:
                record.age = ""

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.model
    def create(self, vals):
        if vals.get('patient_id', _('New')) == _('New'):
            vals['patient_id'] = self.env['ir.sequence'].next_by_code('medical.patient') or _('New')
        return super(MedicalPatient, self).create(vals)

    @api.constrains('phone', 'mobile')
    def _check_phone_format(self):
        for record in self:
            if record.phone:
                if not re.match(r'^\+?[1-9]\d{1,14}$', record.phone.replace(' ', '')):
                    raise ValidationError(_('Phone number format is invalid. Use format: +9647711111111'))
            if record.mobile:
                if not re.match(r'^\+?[1-9]\d{1,14}$', record.mobile.replace(' ', '')):
                    raise ValidationError(_('Mobile number format is invalid. Use format: +9647722222222'))

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        for record in self:
            if record.date_of_birth and record.date_of_birth > date.today():
                raise ValidationError(_('Date of birth cannot be in the future.'))

    def action_view_invoices(self):
        """Smart button to view patient invoices"""
        return {
            'name': _('Patient Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'medical.invoice',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.patient_id} - {record.name}"
            result.append((record.id, name))
        return result