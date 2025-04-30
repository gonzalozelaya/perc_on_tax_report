# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.float_utils import float_split_str

from collections import defaultdict, OrderedDict
import re
import zipfile
import io


class ArgentinianReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_ar.tax.report.handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
    # dict of the form {move_id: {column_group_key: {expression_label: value}}}
    move_info_dict = {}

    # dict of the form {column_group_key: total_value}
    total_values_dict = {}

    # Every key/expression_label that is a number (and should be rendered like one)
    number_keys = ['taxed', 'not_taxed', 'vat_25', 'vat_5', 'vat_10', 'vat_21', 'vat_27', 'vat_per', 'perc_iibb', 'perc_iibb_tucuman', 'perc_iibb_salta', 'perc_iibb_jujuy','perc_earnings', 'city_tax', 'other_taxes', 'total']

    # Build full query
    query_list = []
    full_query_params = []
    options_per_col_group = report._split_options_per_column_group(options)
    for column_group_key, column_group_options in options_per_col_group.items():
        query, params = self._build_query(report, column_group_options, column_group_key)
        query_list.append(f"({query})")
        full_query_params += params

        # Set defaults here since the results of the query for this column_group_key might be empty
        total_values_dict.setdefault(column_group_key, dict.fromkeys(number_keys, 0.0))

    full_query = " UNION ALL ".join(query_list)
    self._cr.execute(full_query, full_query_params)
    results = self._cr.dictfetchall()
    for result in results:
        # Iterate over these results in order to fill the move_info_dict dictionary
        move_id = result['id']
        column_group_key = result['column_group_key']

        # Convert date to string to be displayed in the xlsx report
        result['date'] = result['date'].strftime("%Y-%m-%d")

        # For number rendering, take the opposite for sales taxes
        sign = -1.0 if result['tax_type'] == 'sale' else 1.0

        current_move_info = move_info_dict.setdefault(move_id, {})

        current_move_info['line_name'] = result['move_name']
        current_move_info[column_group_key] = result

        # Apply sign and add values to totals
        totals = total_values_dict[column_group_key]
        for key in number_keys:
            result[key] = sign * result[key]
            totals[key] += result[key]

    lines = []
    for move_id, move_info in move_info_dict.items():
        # 1 line for each move_id
        line = self._create_report_line(report, options, move_info, move_id, number_keys)
        lines.append((0, line))

    # WHen not printing, avoid displaying too many lines (would crash the browser), by using the load_more_limit.
    if not options['export_mode'] and len(lines) > (report.load_more_limit or 0):
        if warnings is not None:
            warnings['l10n_ar_reports.skipped_lines_warning'] = {}
        lines_to_hide = lines[report.load_more_limit:]
        lines = lines[:report.load_more_limit]
        col_indices_to_sum = [
            i
            for i, col_data in enumerate(options['columns'])
            if col_data['expression_label'] in {'taxed', 'not_taxed', 'vat_25', 'vat_5', 'vat_10', 'vat_21', 'vat_27', 'vat_per', 'other_taxes', 'total'}
        ]

        column_sums = defaultdict(float)
        for _line_sequence, line in lines_to_hide:
            for col_index in col_indices_to_sum:
                column_sums[col_index] += line['columns'][col_index]['no_format']

        lines.append((0, {
            'id': report._get_generic_line_id(None, None, markup='placeholder'),
            'name': _("+%s non-previewed lines", len(lines_to_hide)),
            'columns': [
                {
                    'class': 'number',
                    'no_format': column_sums[col_index],
                    'name': report.format_value(options_per_col_group[col['column_group_key']], column_sums[col_index], figure_type='monetary'),
                }
                if col_index in column_sums
                else {}
                for col_index, col in enumerate(options['columns'])
            ],
            'level': 2,
        }))

    # Single total line if only one type of journal is selected
    if len(self._vat_book_get_selected_tax_types(options)) < 2:
        lines.append((0, self._create_report_total_line(report, options, total_values_dict)))

    return lines