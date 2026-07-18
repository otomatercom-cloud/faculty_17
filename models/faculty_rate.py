from odoo import fields,models,api,_

class FacultyRates(models.Model):
    _name = 'faculty.rates'
    _description = "Faculty Rate"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "display_name"

    faculty_id = fields.Many2one('faculty.details', string="Faculty", required=1, tracking=1, domain=[('state', '=', 'hr_approved')])
    course_id = fields.Many2one('op.course', string="Course", required=1,tracking=1)
    subject_id = fields.Many2one('op.subject', string="Subject", required=1, tracking=1)
    salary_per_hour = fields.Float(string="Salary per Hr.", tracking=1)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)

    def _compute_display_name(self):
        for i in self:
            if i.faculty_id:
                i.display_name = i.faculty_id.name + " "  + 'Rates'
            else:
                i.display_name = 'Faculty Rates'

    def _recompute_linked_records(self):
        """Trigger recompute of subject_rate on all matching faculty.records."""
        for rate in self:
            records = self.env['faculty.records'].search([
                ('faculty_id', '=', rate.faculty_id.id),
                ('subject_id', '=', rate.subject_id.id),
                ('course_id', '=', rate.course_id.id),
            ])
            if records:
                records._compute_faculty_rate()
                # Persist the recomputed values since subject_rate is stored
                for rec in records:
                    rec.write({'subject_rate': rec.subject_rate})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_linked_records()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._recompute_linked_records()
        return res
