import argparse

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('tax_worksheet_csv',
                    help='Tax worksheet (w/o wash sales) from tax center')
parser.add_argument('eur_usd_csv',
                    help='EUR/USD reference rate from Deutsche Bundesbank')
args = parser.parse_args()

tax_worksheet = pd.read_csv(filepath_or_buffer=args.tax_worksheet_csv)
tax_worksheet = tax_worksheet.drop(labels=['TAX YEAR', 'FILE_CLOSING_DATE',
                                           'GAIN_ADJ', 'SHORT_TERM_GAIN_LOSS',
                                           'LONG_TERM_GAIN_LOSS',
                                           'ORDINARY_GAIN_LOSS_AMT'], axis=1)

for col in ['PROCEEDS', 'COST']:
    tax_worksheet[col] = tax_worksheet[col].str.replace(pat='$', repl='',
                                                        regex=False)
    tax_worksheet[col] = pd.to_numeric(arg=tax_worksheet[col])

for col in ['CLOSE_DATE', 'OPEN_DATE']:
    tax_worksheet[col] = pd.to_datetime(arg=tax_worksheet[col],
                                        format='%m/%d/%y')

eur_usd = pd.read_csv(filepath_or_buffer=args.eur_usd_csv,
                      delimiter=';')
eur_usd = eur_usd.iloc[8:, :]
eur_usd = eur_usd.rename(
    columns={eur_usd.columns[0]: 'DATE', eur_usd.columns[1]: 'EUR_USD_RATE'})
eur_usd = eur_usd.drop(labels=eur_usd.columns[2], axis=1)
eur_usd = eur_usd[eur_usd['EUR_USD_RATE'] != '.']
eur_usd['DATE'] = pd.to_datetime(arg=eur_usd['DATE'], format='%Y-%m-%d')
eur_usd = eur_usd.set_index(keys='DATE')
eur_usd['EUR_USD_RATE'] = eur_usd['EUR_USD_RATE'].str.replace(pat=',', repl='.',
                                                              regex=False)
eur_usd['EUR_USD_RATE'] = pd.to_numeric(arg=eur_usd['EUR_USD_RATE'])

open_rates = eur_usd['EUR_USD_RATE'].loc[tax_worksheet['OPEN_DATE']]
close_rates = eur_usd['EUR_USD_RATE'].loc[tax_worksheet['CLOSE_DATE']]
tax_worksheet['EUR_USD_OPEN_TX'] = open_rates.values
tax_worksheet['EUR_USD_CLOSE_TX'] = close_rates.values

tax_worksheet.loc[
    np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BTO',
                  tax_worksheet['OPENING_TRANSACTION'] == 'BUY'), 'COST'] = (
        tax_worksheet['COST'] / tax_worksheet['EUR_USD_OPEN_TX'])

tax_worksheet.loc[
    np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BTO',
                  tax_worksheet['OPENING_TRANSACTION'] == 'BUY'),
    'PROCEEDS'] = (tax_worksheet['PROCEEDS'] /
                   tax_worksheet['EUR_USD_CLOSE_TX'])

tax_worksheet.loc[
    np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'STO',
                  tax_worksheet['OPENING_TRANSACTION'] == 'SEL'),
    'PROCEEDS'] = (tax_worksheet['PROCEEDS'] / tax_worksheet['EUR_USD_OPEN_TX'])

tax_worksheet.loc[
    np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'STO',
                  tax_worksheet['OPENING_TRANSACTION'] == 'SEL'), 'COST'] = (
        tax_worksheet['COST'] / tax_worksheet['EUR_USD_CLOSE_TX'])

tax_worksheet['GAIN_LOSS'] = tax_worksheet['PROCEEDS'] - tax_worksheet['COST']

print('Ausländische Kapitalerträge:', tax_worksheet['GAIN_LOSS'].sum())
print('Gewinne aus Aktienverkäufen:',
      tax_worksheet.loc[
          np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BUY',
                        tax_worksheet['OPENING_TRANSACTION'] == 'SEL')]
      ['GAIN_LOSS'].sum())

print('Einkünfte aus Stillhalterprämien und Gewinne aus Termingeschäften:',
      tax_worksheet.loc[
          np.logical_and(
              np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BTO',
                            tax_worksheet['OPENING_TRANSACTION'] == 'STO'),
              tax_worksheet['GAIN_LOSS'] > 0)]
      ['GAIN_LOSS'].sum())

print('Verluste - ohne Verluste aus Aktienverkäufen:',
      tax_worksheet.loc[
          np.logical_and(
              np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BTO',
                            tax_worksheet['OPENING_TRANSACTION'] == 'STO'),
              tax_worksheet['GAIN_LOSS'] < 0)]
      ['GAIN_LOSS'].sum())

print('Verluste aus Aktienverkäufen:',
      tax_worksheet.loc[
          np.logical_and(
              np.logical_or(tax_worksheet['OPENING_TRANSACTION'] == 'BUY',
                            tax_worksheet['OPENING_TRANSACTION'] == 'SEL'),
              tax_worksheet['GAIN_LOSS'] < 0)]
      ['GAIN_LOSS'].sum())

print('Verluste aus Termingeschäften (Verfall):',
      tax_worksheet.loc[
          np.logical_and(tax_worksheet['CLOSING_TRANSACTION'] == 'EXP',
                         tax_worksheet['GAIN_LOSS'] < 0)]['GAIN_LOSS'].sum())
