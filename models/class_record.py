from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, time
import logging

_logger = logging.getLogger(__name__)


class FacultyClassRecords(models.Model):
    _name = 'faculty.records'
    _description = 'Faculty Records'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'id desc'

    faculty_id = fields.Many2one('faculty.details', string="Faculty", required=1, domain=[('state', '=', 'hr_approved')])
    branch_id = fields.Many2one('op.branch', string="Branch", tracking=1)
    month_of_record = fields.Selection([
        ('january', 'January'), ('february', 'February'),
        ('march', 'March'), ('april', 'April'),
        ('may', 'May'), ('june', 'June'), ('july', 'July'), ('august', 'August'),
        ('september', 'September'), ('october', 'October'), ('november', 'November'),
        ('december', 'December')],
        string='Month of Record', copy=False,
        required=True,
        default=lambda self: fields.Date.today().strftime('%B').lower())
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    # state = fields.Selection([('draft','Draft'), ('head_approval','Head Approval'), ('accounts_approval','Accounts Approval'),('done','Done'), ('rejected','Rejected'), ('paid','Paid')], string="Status", tracking=1, default='draft')
    year_of_record = fields.Selection([('2023', '2023'), ('2024', '2024'), ('2025', '2025'), ('2026','2026')], string='Year of Record', default=lambda self: str(fields.Date.today().year))
    branch_head_id = fields.Many2one('res.users', string="Branch Head", required=1)
    batch_id = fields.Many2one('op.batch', string="Batch", domain="[('branch', '=', branch_id)]", tracking=1)
    course_id = fields.Many2one('op.course', string="Course", tracking=1)
    subject_id = fields.Many2one('op.subject', string="Subject", tracking=1)
    class_ids = fields.One2many('class.records', 'class_id', string="Classes")
    standard_hours = fields.Float(string="Standard Hours", compute='_compute_standard_hours', store=1)
    total_duration = fields.Float(string="Total Duration", compute="_compute_total_net_hour", store=1)
    balance_standard_hour = fields.Float(string="Balance Standard Hours", compute="_compute_balance_hours", store=1)
    subject_rate = fields.Float(string="Subject Rate", compute="_compute_faculty_rate", store=1)
    gross_payable = fields.Float(string="Gross Payable", compute="_compute_gross_payable", store=1)
    net_payable = fields.Float(string="Net Payable", compute="_compute_net_payable", store=1)
    extra_hour = fields.Float(string="Approved Extra Hour", tracking=1)
    total_this_sub_hrs = fields.Float(string="Class Hours Till Now", compute="_compute_balance_hours", store=1)
    actual_extra_hr = fields.Float(string="Actual Extra Hr.", compute='_compute_balance_hours', store=1)
    extra_hour_reason = fields.Char(string="Extra Hr. Reason", tracking=1)
    extra_hour_active = fields.Boolean(string="Extra Hour Active", compute="_compute_balance_hours", store=1)
    extra_hour_payment = fields.Float(string="Extra Hour Payment", compute="_compute_total_gross_plus_extra_hour_payable", store=1)
    tds_amount = fields.Float(string="TDS Amount", compute="_compute_tds_amount", store=1)
    advance_amount = fields.Float(string="Advance Amount")
    extra_amount_and_gross_amount = fields.Float(string="Gross + Extra Amount", compute="_compute_total_gross_plus_extra_hour_payable", store=1)
    gst_amount = fields.Float(string="GST Amount", compute="_compute_gst_amount", store=1)
    gst_amount_added_gross = fields.Float(string="Added GST to Gross Amount", compute='_compute_gst_amount', store=1)
    rejected_reason = fields.Text(string="Rejected Reason")
    rejected_person = fields.Many2one('res.users', string="Rejected Person")
    rejected_date = fields.Date(string="Rejected Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('branch_approval', 'Head Approval'),
        ('academic_head_approval', 'Academic Head Approval'),  # New State
        ('accounts_approval', 'Accounts Approval'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ], string="Status", tracking=1, default='draft')

    def _compute_display_name(self):
        for i in self:
            if i.faculty_id and i.month_of_record:
                i.display_name = i.faculty_id.name + " " + i.month_of_record + " " + 'Record'
            else:
                i.display_name = 'Faculty Record'

    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        if self.batch_id and self.batch_id.course_id:
            self.course_id = self.batch_id.course_id  # Optional: auto-set course

    @api.onchange('course_id')
    def _onchange_course_id(self):
        # Restrict the Subject list to subjects that belong to the selected Course,
        # and drop any previously chosen subject that no longer matches.
        if self.course_id:
            if self.subject_id and self.subject_id.course_id != self.course_id:
                self.subject_id = False
            return {'domain': {'subject_id': [('course_id', '=', self.course_id.id)]}}
        else:
            self.subject_id = False
            return {'domain': {'subject_id': []}}

    @api.depends('standard_hours', 'total_duration', 'batch_id', 'course_id', 'branch_id', 'subject_id')
    def _compute_balance_hours(self):
        for rec in self:
            rec.balance_standard_hour = rec.standard_hours or 0.0
            rec.total_this_sub_hrs = 0.0
            rec.extra_hour_active = False
            rec.actual_extra_hr = 0.0
            # rec.extra_hour = 0.0

            opening_hour = 0.0

            # Check if subject_id is linked to op.subject and has active_add_on
            if rec.subject_id:
                subject_record = self.env['op.subject'].sudo().search([('id', '=', rec.subject_id.id), ('course_id', '=', rec.course_id.id),], limit=1)
                if subject_record and subject_record.active_add_on:
                    opening_hour = subject_record.opening_hour or 0.0

            if rec.batch_id and rec.course_id and rec.branch_id and rec.subject_id:
                domain = [
                    ('batch_id', '=', rec.batch_id.id),
                    ('course_id', '=', rec.course_id.id),
                    ('branch_id', '=', rec.branch_id.id),
                    ('subject_id', '=', rec.subject_id.id),
                    ('state', '!=', 'rejected'),
                ]
                if rec.id:
                    domain.append(('id', '!=', rec.id))

                matched_records = self.env['faculty.records'].sudo().search(domain)
                total_taken_hours = sum(m.total_duration for m in matched_records)

                rec.total_this_sub_hrs = total_taken_hours + rec.total_duration + opening_hour
            else:
                rec.total_this_sub_hrs = rec.total_duration + opening_hour

            rec.balance_standard_hour = rec.standard_hours - rec.total_this_sub_hrs
            rec.extra_hour_active = rec.total_this_sub_hrs > rec.standard_hours

            rec.actual_extra_hr = (
                rec.total_this_sub_hrs - rec.standard_hours
                if rec.extra_hour_active else 0.0
            )

    @api.depends('gross_payable', 'faculty_id.tax_active')
    def _compute_gst_amount(self):
        for rec in self:
            if rec.faculty_id.tax_active:
                gst = rec.gross_payable * 0.18
                rec.gst_amount = rec.gross_payable + gst
                rec.gst_amount_added_gross = gst
            else:
                rec.gst_amount = rec.gross_payable
                rec.gst_amount_added_gross = 0.0

    @api.depends('extra_amount_and_gross_amount')
    def _compute_tds_amount(self):
        for rec in self:
            rec.tds_amount = rec.extra_amount_and_gross_amount * 0.10

    @api.depends('faculty_id', 'subject_id', 'course_id')
    def _compute_faculty_rate(self):
        for rec in self:
            rec.subject_rate = 0  # Default
            rate = self.env['faculty.rates'].search([
                ('faculty_id', '=', rec.faculty_id.id),
                ('subject_id', '=', rec.subject_id.id),
                ('course_id', '=', rec.course_id.id)
            ], limit=1)
            if rate:
                rec.subject_rate = rate.salary_per_hour

    @api.depends('faculty_id','batch_id','course_id','subject_id')
    def _compute_standard_hours(self):
        for rec in self:
            rec.standard_hours = 0.0  # Default value
            if rec.course_id and rec.subject_id:
                subject = self.env['op.subject'].sudo().search([
                    ('course_id', '=', rec.course_id.id),
                    ('id', '=', rec.subject_id.id)
                ], limit=1)
                if subject:
                    rec.standard_hours = subject.standard_hour

    @api.depends('gst_amount', 'extra_hour_payment', 'tds_amount', 'advance_amount')
    def _compute_net_payable(self):
        for rec in self:
            rec.net_payable = rec.gst_amount + rec.extra_hour_payment - rec.tds_amount - rec.advance_amount

    @api.depends('subject_rate', 'total_duration', 'actual_extra_hr')
    def _compute_gross_payable(self):
        for rec in self:
            if rec.actual_extra_hr != 0:
                regular_hours = rec.total_duration - rec.actual_extra_hr
                if regular_hours > 0:
                    rec.gross_payable = regular_hours * rec.subject_rate
                else:
                    rec.gross_payable = 0.0
            else:
                rec.gross_payable = rec.subject_rate * rec.total_duration

    @api.depends('gross_payable', 'extra_hour', 'subject_rate')
    def _compute_total_gross_plus_extra_hour_payable(self):
        for rec in self:
            if rec.extra_hour == 0:
                rec.extra_hour_payment = 0.0
                rec.extra_amount_and_gross_amount = rec.gross_payable
            else:
                rec.extra_hour_payment = rec.extra_hour * rec.subject_rate
                rec.extra_amount_and_gross_amount = rec.gross_payable + (rec.extra_hour * rec.subject_rate)

    # def act_submit(self):
    #     today = date.today()
    #     current_month = today.strftime("%B").lower()  # e.g., "july"
    #     print(current_month, 'curr')
    #     for rec in self:
    #         config = self.env['faculty.lock.config'].search([], limit=1, order='id desc')
    #         lock_day = config.lock_day if config else 21
    #         if rec.is_unlocked_by_admin != True:
    #             if rec.month_of_record == current_month:
    #                 print('yes')
    #                 # Get lock_day from config
    #                 # default fallback
    #
    #                 if today.day > lock_day:
    #                     raise UserError(
    #                         _("You cannot submit this record. Submissions are locked after day %s of this month.") % lock_day)
    #                 else:
    #                     rec.state = 'head_approval'
    #                     rec.activity_schedule('faculty_17.mail_activity_faculty_records', user_id=rec.branch_head_id.id,
    #                                           note=f' A new faculty record has been assigned to you by {rec.create_uid.name}. Please review and take necessary action.')
    #             else:
    #                 raise UserError(
    #                     _("You cannot submit this record. Submissions are locked after day %s of this month.") % lock_day)
    #
    #         else:
    #             print("is locked")
    #             rec.state = 'head_approval'
    #             rec.activity_schedule('faculty_17.mail_activity_faculty_records', user_id=rec.branch_head_id.id,
    #                                   note=f'A new faculty record has been assigned to you by {rec.create_uid.name}. Please review and take necessary action.')
    #     # self.state = 'head_approval'

    def act_submit(self):
        today = fields.Date.today()
        current_month = today.strftime("%B").lower()
        for rec in self:
            config = self.env['faculty.lock.config'].search([], limit=1, order='id desc')
            lock_day = config.lock_day if config else 21

            if not rec.is_unlocked_by_admin:
                if rec.month_of_record != current_month or today.day > lock_day:
                    raise UserError(
                        _("You cannot submit this record. Submissions are locked after day %s of this month.") % lock_day)

            rec.state = 'branch_approval'
            # Bypass SMTP error
            try:
                rec.with_context(mail_activity_quick_update=True).activity_schedule(
                    'faculty_17.mail_activity_faculty_records',
                    user_id=rec.branch_head_id.id,
                    note=f'A new faculty record has been assigned to you by {rec.create_uid.name}.'
                )
            except Exception as e:
                _logger.warning("Mail server disconnected. Activity created without email: %s", e)

    @api.depends('class_ids', 'class_ids.net_hour')
    def _compute_total_net_hour(self):
        for rec in self:
            if rec.class_ids:
                rec.total_duration = sum(class_rec.net_hour or 0 for class_rec in rec.class_ids)
            else:
                rec.total_duration = 0.0

    def act_return_to_draft(self):
        self.state = 'draft'

    def act_branch_approval(self):
        """Moves record from Branch Head to Faculty Academic Head"""
        for rec in self:
            rec.activity_feedback(['faculty_17.mail_activity_faculty_records'])
            rec.state = 'academic_head_approval'

            try:
                academic_heads = self.env.ref('faculty_17.group_faculty_academic_head').users
                for user in academic_heads:
                    rec.with_context(mail_activity_quick_update=True).activity_schedule(
                        'faculty_17.mail_activity_faculty_records',
                        user_id=user.id,
                        note=f'Branch Head approved. Awaiting Academic Head review for {rec.display_name}.'
                    )
            except Exception as e:
                _logger.warning("Mail server disconnected during Branch Approval: %s", e)

    def act_academic_head_approval(self):
        """Moves record from Faculty Academic Head to Accounts"""
        for rec in self:
            rec.activity_feedback(['faculty_17.mail_activity_faculty_records'])
            rec.state = 'accounts_approval'

            try:
                accounts_users = self.env.ref('faculty_17.group_faculty_accounts_team').users
                for user in accounts_users:
                    rec.with_context(mail_activity_quick_update=True).activity_schedule(
                        'faculty_17.mail_activity_faculty_records',
                        user_id=user.id,
                        note=f'Academic Head approved. Awaiting Accounts Approval for {rec.display_name}.'
                    )
            except Exception as e:
                _logger.warning("Mail server disconnected during Academic Approval: %s", e)

    # Helper method to clear activities (ensure this exists in your class)
    def activity_feedback(self, activity_xml_ids):
        for rec in self:
            try:
                activity_type = self.env.ref(activity_xml_ids[0])
                activities = rec.activity_ids.filtered(lambda a: a.activity_type_id.id == activity_type.id)
                activities.action_feedback(feedback='Approved')
            except Exception as e:
                _logger.error("Error clearing activities: %s", e)

    # # Modify this function to send to Academic Head instead of Accounts
    # def act_head_approval(self):
    #     activity_id = self.env['mail.activity'].search(
    #         [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
    #             'activity_type_id', '=', self.env.ref('faculty_17.mail_activity_faculty_records').id)])
    #     if activity_id:
    #         activity_id.action_feedback(feedback='Head Approved')
    #
    #     # Notify Academic Heads
    #     users = self.env.ref('faculty_17.group_faculty_academic_head').users
    #     for j in users:
    #         self.activity_schedule('faculty_17.mail_activity_faculty_records', user_id=j.id,
    #                                note=f'New faculty record needs Academic Head approval.')
    #
    #     self.state = 'academic_head_approval'

    # def act_head_approval(self):
    #     activity_id = self.env['mail.activity'].search(
    #         [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
    #             'activity_type_id', '=', self.env.ref('faculty_17.mail_activity_faculty_records').id)])
    #     if activity_id:
    #         activity_id.action_feedback(feedback='Head Approved')
    #     users = self.env.ref('faculty_17.group_faculty_accounts_team').users
    #     for j in users:
    #         self.activity_schedule('faculty_17.mail_activity_faculty_records', user_id=j.id,
    #                               note=f' A new faculty record has been assigned to you by {self.create_uid.name}. Please review and take necessary action.')
    #
    #     self.state = 'accounts_approval'

    def act_accounts_approval(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('faculty_17.mail_activity_faculty_records').id)])
        if activity_id:
            activity_id.action_feedback(feedback='Accounts Approved')
        self.state = 'done'

    # # Add this new function for Academic Head action
    # def act_academic_head_approval(self):
    #     activity_id = self.env['mail.activity'].search(
    #         [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
    #             'activity_type_id', '=', self.env.ref('faculty_17.mail_activity_faculty_records').id)])
    #     if activity_id:
    #         activity_id.action_feedback(feedback='Academic Head Approved')
    #
    #     # Notify Accounts Team
    #     users = self.env.ref('faculty_17.group_faculty_accounts_team').users
    #     for j in users:
    #         self.activity_schedule('faculty_17.mail_activity_faculty_records', user_id=j.id,
    #                                note=f'Academic Head approved. Please review for Accounts.')
    #
    #     self.state = 'accounts_approval'

    def act_paid(self):
        self.state = 'paid'

    def act_reject(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Rejection'),
                'res_model': 'reject.reason',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_record_id': self.id}, }

    is_unlocked_by_admin = fields.Boolean(string="Unlocked This Record", default=False)

    def action_unlock_record(self):
        for rec in self:
            rec.is_unlocked_by_admin = True


class ClassRecords(models.Model):
    _name = 'class.records'
    _description = 'Class Records'

    date = fields.Date(string="Date", required=1)
    start_time = fields.Float(string="Start Time", widget="float_time", required=1)
    end_time = fields.Float(string="End Time", widget="float_time", required=1)
    topic = fields.Char(string="Topic")
    break_reason = fields.Char(string="Break Reason")
    break_time = fields.Float(string="Break Time", widget="float_time")
    net_hour = fields.Float(string="Net Hour", widget="float_time", compute='_compute_total_net_hours', store=1)
    class_id = fields.Many2one('faculty.records', string="Class")
    standard_hours = fields.Float(string="Standard Hours")

    # @api.depends('start_time','end_time','break_time')
    # def _compute_total_net_hours(self):
    #     for i in self:
    #         if i.end_time and i.start_time:
    #             if i.break_time:
    #                 i.net_hour = i.end_time - i.start_time - i.break_time
    #             else:
    #                 i.net_hour = i.end_time - i.start_time

    @api.depends('start_time', 'end_time', 'break_time')
    def _compute_total_net_hours(self):
        for i in self:
            if i.start_time and i.end_time:
                # 1. Calculate Gross Duration
                duration = i.end_time - i.start_time
                if duration < 0: duration += 24.0

                # 2. Convert Break Time (e.g., 1.15 -> 1.25)
                # This separates the hours from the "minutes"
                break_hours = int(i.break_time)
                break_minutes = (i.break_time - break_hours) * 100
                # Convert minutes to a true decimal (15/60 = 0.25)
                actual_break_decimal = break_hours + (break_minutes / 60.0)

                # 3. Final Calculation
                i.net_hour = duration - actual_break_decimal
            else:
                i.net_hour = 0.0


