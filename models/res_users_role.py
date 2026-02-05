from odoo import _, api, models
from odoo.exceptions import AccessError


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def _fni_is_access_rights_only(self):
        user = self.env.user
        return user.has_group("base.group_erp_manager") and not user.has_group(
            "base.group_system"
        )

    @api.model_create_multi
    def create(self, vals_list):
        if self._fni_is_access_rights_only():
            raise AccessError(_("You are not allowed to create roles."))
        return super().create(vals_list)

    def write(self, vals):
        if self._fni_is_access_rights_only():
            raise AccessError(_("You are not allowed to modify roles."))
        return super().write(vals)

    def unlink(self):
        if self._fni_is_access_rights_only():
            raise AccessError(_("You are not allowed to delete roles."))
        return super().unlink()
