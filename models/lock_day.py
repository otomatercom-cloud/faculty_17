from odoo import fields, models, api, _

class RecordsLockingDay(models.Model):
    _name = 'faculty.lock.config'
    _description = 'Lock Day'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'lock_day'

    lock_day = fields.Integer(string="Lock Day", default=21)