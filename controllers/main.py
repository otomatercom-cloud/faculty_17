import base64
from odoo import http
from odoo.http import request

class FacultyController(http.Controller):

    @http.route('/faculty/registration', type='http', auth="public", website=True)
    def faculty_registration_form(self, **kw):
        return request.render('faculty_17.portal_faculty_create_form', {})

    @http.route('/faculty/registration/submit', type='http', auth="public", website=True, methods=['POST'])
    def faculty_registration_submit(self, **post):
        # Extract files
        aadhar_file = request.httprequest.files.get('aadhar_card')
        pan_file = request.httprequest.files.get('pan_card')

        aadhar_data = base64.b64encode(aadhar_file.read()) if aadhar_file else False
        pan_data = base64.b64encode(pan_file.read()) if pan_file else False
        
        aadhar_filename = aadhar_file.filename if aadhar_file else ''
        pan_filename = pan_file.filename if pan_file else ''

        val = {
            'first_name': post.get('first_name'),
            'last_name': post.get('last_name'),
            'email': post.get('email'),
            'mobile': post.get('mobile'),
            'bank_name': post.get('bank_name'),
            'account_no': post.get('account_no'),
            'ifsc_code': post.get('ifsc_code'),
            'pan_no': post.get('pan_no'),
            'gst_no': post.get('gst_no'),
            'aad_no': post.get('aad_no'),
            'account_holder_name': post.get('account_holder_name'),
            'qualification': post.get('qualification'),
            'gender': post.get('gender'),
            'aadhar_card': aadhar_data,
            'aadhar_filename': aadhar_filename,
            'pan_card': pan_data,
            'pan_filename': pan_filename,
            'state': 'draft',
        }
        
        faculty = request.env['faculty.details'].sudo().create(val)
        
        return request.render('faculty_17.portal_faculty_create_success', {
            'faculty': faculty
        })
