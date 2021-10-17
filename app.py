import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument('tax_worksheet_csv',
                    help='Tax worksheet (w/ wash sales) from tax center')
parser.add_argument('eur_usd_csv',
                    help='EUR/USD reference rate from Deutsche Bundesbank')
args = parser.parse_args()

tax_worksheet = pd.read_csv(filepath_or_buffer=args.tax_worksheet_csv)

for col in ['PROCEEDS', 'COST', 'GAIN_LOSS']:
    tax_worksheet[col] = tax_worksheet[col].str.replace(pat='$', repl='',
                                                        regex=False)
    tax_worksheet[col] = pd.to_numeric(arg=tax_worksheet[col])

for col in ['FILE_CLOSING_DATE', 'CLOSE_DATE', 'OPEN_DATE']:
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
tax_worksheet['EUR_USD_OPEN'] = open_rates.values
tax_worksheet['EUR_USD_CLOSE'] = close_rates.values


def compute_eur_from_usd(row: pd.Series, balance_type: str) -> pd.Series:
    if row['OPENING_TRANSACTION'] == 'BTO':
        if balance_type == 'PROCEEDS':
            return row[balance_type] / row['EUR_USD_CLOSE']
        elif balance_type == 'COST':
            return row[balance_type] / row['EUR_USD_OPEN']
    elif row['OPENING_TRANSACTION'] == 'STO':
        if balance_type == 'PROCEEDS':
            return row[balance_type] / row['EUR_USD_OPEN']
        elif balance_type == 'COST':
            return row[balance_type] / row['EUR_USD_CLOSE']


tax_worksheet['PROCEEDS_EUR'] = tax_worksheet.apply(
    func=lambda x: compute_eur_from_usd(row=x, balance_type='PROCEEDS'), axis=1)
tax_worksheet['COST_EUR'] = tax_worksheet.apply(
    func=lambda x: compute_eur_from_usd(row=x, balance_type='COST'), axis=1)

tax_worksheet['GAIN_LOSS_EUR'] = (tax_worksheet['PROCEEDS_EUR']
                                  - tax_worksheet['COST_EUR'])

print(tax_worksheet['GAIN_LOSS_EUR'].sum())
