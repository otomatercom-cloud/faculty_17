from odoo import models, api

class OpBatch(models.Model):
    _inherit = 'op.batch'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        if self.env.context.get('allow_all_batches'):
            # Bypasses the global record rules for op.batch when allow_all_batches is in the context
            return super(OpBatch, self.sudo())._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
        return super(OpBatch, self)._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
