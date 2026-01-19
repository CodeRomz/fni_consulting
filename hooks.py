def post_init_hook(env):
    layout = env.ref("web.external_layout_striped", raise_if_not_found=False)
    if not layout:
        return
    companies = env["res.company"].search([("external_report_layout_id", "=", False)])
    if companies:
        companies.write({"external_report_layout_id": layout.id})
