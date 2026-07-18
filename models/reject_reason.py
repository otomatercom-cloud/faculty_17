from odoo import fields, models
from datetime import date, datetime, time

class RejectReason(models.TransientModel):
    _name = 'reject.reason'
    _description = "Reject Wizard"

    record_id = fields.Many2one('faculty.records', string="Record")
    rejected_reason = fields.Text(string="Rejected Reason", required=1)

    def reject(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.record_id.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('faculty_17.mail_activity_faculty_records').id)])
        if activity_id:
            activity_id.action_feedback(feedback='rejected')
        for rec in self:
            rec.record_id.state = 'rejected'
            rec.record_id.rejected_person = self.env.user
            rec.record_id.rejected_date = date.today()
            rec.record_id.rejected_reason = rec.rejected_reason
