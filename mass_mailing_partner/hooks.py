# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    # ACTION 1: Match existing contacts
       _logger.info("Trying to match contacts to partner by email")

    matching_query = """
        UPDATE mailing_contact mc
        SET partner_id = rp.id
        FROM res_partner rp
        WHERE mc.email IS NOT NULL 
          AND rp.email IS NOT NULL
          AND LOWER(TRIM(mc.email)) = LOWER(TRIM(rp.email))
    """
    delete_older_tag_ids_query = """
        DELETE FROM mailing_contact_res_partner_category_rel
        WHERE mailing_contact_id IN (SELECT id FROM mailing_contact WHERE partner_id IS NOT NULL)
    """
    insert_tag_ids_query = """
        INSERT INTO mailing_contact_res_partner_category_rel (mailing_contact_id, res_partner_category_id)
        SELECT 
            mc.id,
            rprpcr.category_id
        FROM mailing_contact mc
        JOIN res_partner_res_partner_category_rel rprpcr ON mc.partner_id = rprpcr.partner_id
        WHERE mc.partner_id IS NOT NULL
    """

    env.cr.execute(matching_query)
    _logger.info("Mailing contacts updated: %d rows affected", env.cr.rowcount)

    env.cr.execute(delete_older_tag_ids_query)
    env.cr.execute(insert_tag_ids_query)

    # ACTION 2: Match existing statistics
    stat_model = env["mailing.trace"]
    stats = stat_model.search([("model", "!=", False), ("res_id", "!=", False)])
    _logger.info("Trying to link %d mass mailing statistics to partner", len(stats))
    stats.partner_link()
