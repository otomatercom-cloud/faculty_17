from odoo import fields,models,api,_

class InheritFaculty(models.Model):
    _inherit = 'res.users'

    faculty = fields.Boolean(string="Faculty")
