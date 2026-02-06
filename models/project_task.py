from odoo import api, models, Command


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                if not vals.get("user_ids"):
                    vals["user_ids"] = [Command.set([self.env.user.id])]
        return super().create(vals_list)
