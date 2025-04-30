# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools


class AccountArVatLine(models.Model):
    """ Base model for new Argentine VAT reports. The idea is that these lines have all the necessary data and which any
    changes in odoo, this ones will be taken for this cube and then no changes will be needed in the reports that use
    this lines. A line is created for each accounting entry that is affected by VAT tax.

    Basically which it does is covert the accounting entries into columns depending on the information of the taxes and
    add some other fields """

    _inherit = "account.ar.vat.line"
    perc_iibb_tucuman = fields.Monetary(readonly=True, string='Perc. IIBB Tucumán', currency_field='company_currency_id')
    perc_iibb_salta = fields.Monetary(readonly=True, string='Perc. IIBB Salta', currency_field='company_currency_id')
    perc_iibb_jujuy = fields.Monetary(readonly=True, string='Perc. IIBB Jujuy', currency_field='company_currency_id')

    @api.model
    def _ar_vat_line_build_query(self, tables='account_move_line', where_clause='', where_params=None,
                                 column_group_key='', tax_types=('sale', 'purchase')):
        """Returns the SQL Select query fetching account_move_lines info in order to build the pivot view for the VAT summary.
        This method is also meant to be used outside this model, which is the reason why it gives the opportunity to
        provide a few parameters, for which the defaults are used in this model.

        The query is used to build the VAT book report"""
        if where_params is None:
            where_params = []

        query = f"""
                SELECT
                    %s AS column_group_key,
                    account_move.id,
                    (CASE WHEN lit.l10n_ar_afip_code = '80' THEN rp.vat ELSE NULL END) AS cuit,
                    art.name AS afip_responsibility_type_name,
                    rp.name AS partner_name,
                    COALESCE(nt.type_tax_use, bt.type_tax_use) AS tax_type,
                    account_move.id AS move_id,
                    account_move.move_type,
                    account_move.date,
                    account_move.invoice_date,
                    account_move.partner_id,
                    account_move.journal_id,
                    account_move.name AS move_name,
                    account_move.l10n_ar_afip_responsibility_type_id as afip_responsibility_type_id,
                    account_move.l10n_latam_document_type_id as document_type_id,
                    account_move.state,
                    account_move.company_id,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code in ('4', '5', '6', '8', '9') THEN account_move_line.balance ELSE 0 END) AS taxed,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code = '4' THEN account_move_line.balance ELSE 0 END) AS base_10,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code = '4' THEN account_move_line.balance ELSE 0 END) AS vat_10,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code = '5' THEN account_move_line.balance ELSE 0 END) AS base_21,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code = '5' THEN account_move_line.balance ELSE 0 END) AS vat_21,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code = '6' THEN account_move_line.balance ELSE 0 END) AS base_27,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code = '6' THEN account_move_line.balance ELSE 0 END) AS vat_27,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code = '8' THEN account_move_line.balance ELSE 0 END) AS base_5,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code = '8' THEN account_move_line.balance ELSE 0 END) AS vat_5,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code = '9' THEN account_move_line.balance ELSE 0 END) AS base_25,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code = '9' THEN account_move_line.balance ELSE 0 END) AS vat_25,
                    SUM(CASE WHEN btg.l10n_ar_vat_afip_code in ('0', '1', '2', '3', '7') THEN account_move_line.balance ELSE 0 END) AS not_taxed,
                    SUM(CASE WHEN ntg.l10n_ar_tribute_afip_code = '06' THEN account_move_line.balance ELSE 0 END) AS vat_per,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL and ntg.l10n_ar_tribute_afip_code = '07' THEN account_move_line.balance ELSE 0 END) AS perc_iibb,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL 
                             AND ntg.l10n_ar_tribute_afip_code = '07' 
                             AND ntg.name->>'es_AR' ILIKE '%%Perc IIBB Tucumán%%' THEN account_move_line.balance ELSE 0 END) AS perc_iibb_tucuman,
                             
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL 
                             AND ntg.l10n_ar_tribute_afip_code = '07' 
                             AND ntg.name->>'en_US' ILIKE '%%Perc IIBB Salta%%' THEN account_move_line.balance ELSE 0 END) AS perc_iibb_salta,
                             
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL 
                             AND ntg.l10n_ar_tribute_afip_code = '07' 
                             AND ntg.name->>'en_US' ILIKE '%%Perc IIBB Jujuy%%' THEN account_move_line.balance ELSE 0 END) AS perc_iibb_jujuy,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL and ntg.l10n_ar_tribute_afip_code = '09' THEN account_move_line.balance ELSE 0 END) AS perc_earnings,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL and ntg.l10n_ar_tribute_afip_code in ('03', '08') THEN account_move_line.balance ELSE 0 END) AS city_tax,
                    SUM(CASE WHEN ntg.l10n_ar_vat_afip_code is NULL and ntg.l10n_ar_tribute_afip_code in ('02', '04', '05', '99') THEN account_move_line.balance ELSE 0 END) AS other_taxes,
                    SUM(account_move_line.balance) AS total
                FROM
                    {tables}
                    JOIN
                        account_move ON account_move_line.move_id = account_move.id
                    LEFT JOIN
                        -- nt = net tax
                        account_tax AS nt ON account_move_line.tax_line_id = nt.id
                    LEFT JOIN
                        account_move_line_account_tax_rel AS amltr ON account_move_line.id = amltr.account_move_line_id
                    LEFT JOIN
                        -- bt = base tax
                        account_tax AS bt ON amltr.account_tax_id = bt.id
                    LEFT JOIN
                        account_tax_group AS btg ON btg.id = bt.tax_group_id
                    LEFT JOIN
                        account_tax_group AS ntg ON ntg.id = nt.tax_group_id
                    LEFT JOIN
                        res_partner AS rp ON rp.id = account_move.commercial_partner_id
                    LEFT JOIN
                        l10n_latam_identification_type AS lit ON rp.l10n_latam_identification_type_id = lit.id
                    LEFT JOIN
                        l10n_ar_afip_responsibility_type AS art ON account_move.l10n_ar_afip_responsibility_type_id = art.id
                WHERE
                    (account_move_line.tax_line_id is not NULL OR btg.l10n_ar_vat_afip_code is not NULL)
                    AND (nt.type_tax_use in %s OR bt.type_tax_use in %s)
                    {where_clause}
                GROUP BY
                    account_move.id, art.name, rp.id, lit.id,  COALESCE(nt.type_tax_use, bt.type_tax_use)
                ORDER BY
                    account_move.invoice_date, account_move.name"""
        return query, [column_group_key, tax_types, tax_types, *where_params]
