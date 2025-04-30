# -*- coding: utf-8 -*-
{
    'name': "Percepciones discriminadas en el IVA",

    'summary': """
        Percepciones discriminadas en el IVA""",

    'description': """
        Percepciones discriminadas en el IVA
        Este módulo agrega las percepciones discriminadas en el IVA a los reportes de IVA.
        Se agregan las percepciones de IIBB Tucumán, Salta y Jujuy.
        Se agrega la columna de Percepciones IIBB al libro IVA.
        Se agrega la columna de Percepciones IIBB al libro IVA Ventas.
        Se agrega la columna de Percepciones IIBB al libro IVA Compras.
    """,

    'author': "OutsourceArg",
    'website': "https://www.outsourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['l10n_ar_reports',],
}