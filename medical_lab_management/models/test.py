from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MedicalTest(models.Model):
    _name = 'medical.test'
    _description = 'Medical Test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Test Name', required=True, tracking=True)
    shortcut = fields.Char(string='Shortcut', tracking=True)
    unit = fields.Char(string='Unit')
    sample_type = fields.Char(string='Sample Type')
    category_id = fields.Many2one('medical.test.category', string='Category', tracking=True)
    department_id = fields.Many2one('medical.department', string='Department', tracking=True)
    machine_id = fields.Many2one('medical.machine', string='Machine', tracking=True)
    
    # Result Type Configuration
    result_type = fields.Selection([
        ('selection', 'Selection Type'),
        ('range', 'Range Type'),
        ('quantitative', 'Quantitative Type'),
        ('descriptive', 'Descriptive Type')
    ], string='Result Type', required=True, default='range', tracking=True)
    
    # Selection Type Options
    selection_options = fields.Text(string='Selection Options', 
                                   help='Enter options separated by commas (e.g., Negative,Positive or A+,A-,B+,B-,AB+,AB-,O+,O-)')
    
    # Range Type Configuration
    universal_range = fields.Boolean(string='Universal Range', default=True)
    normal_range_min = fields.Float(string='Normal Range Min')
    normal_range_max = fields.Float(string='Normal Range Max')
    
    # Demographic-based ranges
    demographic_ranges = fields.One2many('medical.test.range', 'test_id', string='Demographic Ranges')
    
    # Report Style
    report_style = fields.Selection([
        ('table', 'Table Format'),
        ('custom', 'Custom Template')
    ], string='Report Style', default='table', tracking=True)
    
    # Sorting and Grouping
    sort_order = fields.Integer(string='Sort Order', default=10)
    group_by_category = fields.Boolean(string='Group by Category', default=True)
    single_page_output = fields.Boolean(string='Single Page Output', default=False)
    
    # Pricing
    price = fields.Float(string='Price', tracking=True)
    price_list_ids = fields.Many2many('medical.price.list', string='Price Lists')
    
    # Package Support
    package_ids = fields.Many2many('medical.test.package', string='Test Packages')
    
    # Status
    active = fields.Boolean(default=True, string='Active')
    
    # Related fields
    invoice_line_ids = fields.One2many('medical.invoice.line', 'test_id', string='Invoice Lines')
    result_ids = fields.One2many('medical.test.result', 'test_id', string='Results')

    @api.constrains('normal_range_min', 'normal_range_max')
    def _check_range_values(self):
        for record in self:
            if record.result_type == 'range' and record.universal_range:
                if record.normal_range_min and record.normal_range_max:
                    if record.normal_range_min >= record.normal_range_max:
                        raise ValidationError(_('Minimum range value must be less than maximum range value.'))

    def get_normal_range(self, gender=None, age_years=None):
        """Get normal range based on demographics"""
        if self.result_type != 'range':
            return None
            
        if self.universal_range:
            return {
                'min': self.normal_range_min,
                'max': self.normal_range_max
            }
        
        # Find matching demographic range
        for range_record in self.demographic_ranges:
            if range_record.matches_demographics(gender, age_years):
                return {
                    'min': range_record.min_value,
                    'max': range_record.max_value
                }
        return None

    def get_selection_options_list(self):
        """Get selection options as a list"""
        if self.result_type == 'selection' and self.selection_options:
            return [opt.strip() for opt in self.selection_options.split(',')]
        return []


class MedicalTestCategory(models.Model):
    _name = 'medical.test.category'
    _description = 'Medical Test Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('medical.test.category', string='Parent Category')
    child_ids = fields.One2many('medical.test.category', 'parent_id', string='Child Categories')
    test_ids = fields.One2many('medical.test', 'category_id', string='Tests')
    active = fields.Boolean(default=True, string='Active')


class MedicalDepartment(models.Model):
    _name = 'medical.department'
    _description = 'Medical Department'
    _order = 'name'

    name = fields.Char(string='Department Name', required=True)
    code = fields.Char(string='Department Code')
    description = fields.Text(string='Description')
    test_ids = fields.One2many('medical.test', 'department_id', string='Tests')
    active = fields.Boolean(default=True, string='Active')


class MedicalMachine(models.Model):
    _name = 'medical.machine'
    _description = 'Medical Machine'
    _order = 'name'

    name = fields.Char(string='Machine Name', required=True)
    model = fields.Char(string='Model')
    manufacturer = fields.Char(string='Manufacturer')
    serial_number = fields.Char(string='Serial Number')
    test_ids = fields.One2many('medical.test', 'machine_id', string='Tests')
    active = fields.Boolean(default=True, string='Active')


class MedicalTestRange(models.Model):
    _name = 'medical.test.range'
    _description = 'Medical Test Range'

    test_id = fields.Many2one('medical.test', string='Test', required=True, ondelete='cascade')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('both', 'Both')
    ], string='Gender', default='both')
    age_min = fields.Integer(string='Age Min (Years)')
    age_max = fields.Integer(string='Age Max (Years)')
    min_value = fields.Float(string='Min Value', required=True)
    max_value = fields.Float(string='Max Value', required=True)
    description = fields.Char(string='Description')

    def matches_demographics(self, gender, age_years):
        """Check if this range matches the given demographics"""
        if not age_years:
            return False
            
        # Check gender
        if self.gender != 'both' and gender and self.gender != gender:
            return False
            
        # Check age range
        if self.age_min and age_years < self.age_min:
            return False
        if self.age_max and age_years > self.age_max:
            return False
            
        return True


class MedicalPriceList(models.Model):
    _name = 'medical.price.list'
    _description = 'Medical Price List'
    _order = 'name'

    name = fields.Char(string='Price List Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True, string='Active')
    test_price_ids = fields.One2many('medical.test.price', 'price_list_id', string='Test Prices')


class MedicalTestPrice(models.Model):
    _name = 'medical.test.price'
    _description = 'Medical Test Price'

    price_list_id = fields.Many2one('medical.price.list', string='Price List', required=True, ondelete='cascade')
    test_id = fields.Many2one('medical.test', string='Test', required=True)
    price = fields.Float(string='Price', required=True)


class MedicalTestPackage(models.Model):
    _name = 'medical.test.package'
    _description = 'Medical Test Package'
    _order = 'name'

    name = fields.Char(string='Package Name', required=True)
    description = fields.Text(string='Description')
    test_ids = fields.Many2many('medical.test', string='Tests')
    price = fields.Float(string='Package Price', compute='_compute_package_price', store=True)
    active = fields.Boolean(default=True, string='Active')

    @api.depends('test_ids.price')
    def _compute_package_price(self):
        for record in self:
            record.price = sum(record.test_ids.mapped('price'))