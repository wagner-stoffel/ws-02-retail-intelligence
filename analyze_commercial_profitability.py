"""WS-02: read-only commercial profitability analysis of synthetic retail sales."""
from pathlib import Path
import argparse
import re
import sys
import pandas as pd

BASE = Path(__file__).resolve().parent
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
COLUMNS = ['Data', 'Mês', 'Unidade', 'Região', 'Canal', 'SKU', 'Categoria', 'Produto',
           'Quantidade', 'Preço tabela unit. (R$)', 'Desconto total (R$)', 'Custo unitário (R$)']
MONEY = ['gross_sales', 'discount', 'net_sales', 'cogs', 'gross_profit', 'loss_on_negative_rows']


def connect():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    # Reuse an existing compatible local token, without overwriting it.
    own_token = BASE / 'profitability_token.json'
    creds = None
    for token in (own_token, BASE / 'token.json', BASE / 'authorized_user.json'):
        if not token.is_file():
            continue
        try:
            candidate = Credentials.from_authorized_user_file(str(token))
            if set(candidate.scopes or []) != set(SCOPES):
                continue
            if not candidate.valid and candidate.expired and candidate.refresh_token:
                candidate.refresh(Request())
            if candidate.valid:
                creds = candidate
                break
        except Exception:
            # An expired, revoked or incompatible token requires fresh consent.
            continue
    if creds is None:
        flow = InstalledAppFlow.from_client_secrets_file(str(BASE / 'credentials.json'), SCOPES)
        creds = flow.run_local_server(port=0)
    own_token.write_text(creds.to_json(), encoding='utf-8')
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def load_sales(service, spreadsheet_id):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="'Vendas'!A:L",
        valueRenderOption='UNFORMATTED_VALUE').execute()
    return result.get('values', [])


def prepare(rows):
    if not rows or rows[0][:12] != COLUMNS:
        raise ValueError('Cabecalho da aba Vendas diferente do esperado. Confira as colunas A:L.')
    data = []
    for line, row in enumerate(rows[1:], 2):
        if not any(v is not None and v != '' for v in row):
            continue
        data.append([line] + (row[:12] + [None] * 12)[:12])
    if not data:
        raise ValueError('Aba Vendas sem registros.')
    df = pd.DataFrame(data, columns=['source_row'] + COLUMNS)
    df.columns = ['source_row', 'date', 'month', 'unit', 'region', 'channel', 'sku', 'category', 'product',
                  'quantity', 'unit_price', 'discount', 'unit_cost']
    for col in ['quantity','unit_price','discount','unit_cost']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    if df.isna().any().any() or df[['date','month','unit','region','channel','sku','category','product']].astype(str).apply(lambda x:x.str.strip().eq('')).any().any():
        raise ValueError('Campos vazios ou numericos invalidos. Execute a validacao de qualidade novamente.')
    if not df['month'].astype(str).str.fullmatch(r'\d{4}-(0[1-9]|1[0-2])').all():
        raise ValueError('Meses invalidos: esperado AAAA-MM.')
    # Daily SKU/store observations may legitimately have zero units sold.
    # Zero-quantity rows must not have a discount and contribute zero to sales and COGS.
    invalid = (df.quantity < 0) | (df.unit_price <= 0) | (df.discount < 0) | (df.unit_cost < 0)
    if invalid.any():
        lines = df.loc[invalid, 'source_row'].tolist()
        raise ValueError(f'Quantidade, preco, desconto ou custo fora dos limites aceitos: '
                         f'{len(lines)} registros. Linhas da aba Vendas: {lines[:20]}')
    fractional = df.quantity % 1 != 0
    if fractional.any():
        raise ValueError(f'Quantidade fracionaria. Linhas da aba Vendas: '
                         f'{df.loc[fractional, "source_row"].tolist()[:20]}')
    zero_with_discount = (df.quantity == 0) & (df.discount != 0)
    if zero_with_discount.any():
        raise ValueError(f'Quantidade zero com desconto diferente de zero. Linhas da aba Vendas: '
                         f'{df.loc[zero_with_discount, "source_row"].tolist()[:20]}')
    df['gross_sales'] = (df.quantity * df.unit_price).round(2)
    df['discount'] = df.discount.round(2)
    df['net_sales'] = (df.gross_sales - df.discount).round(2)
    if (df.net_sales < 0).any():
        raise ValueError('Desconto superior ao faturamento bruto.')
    df['cogs'] = (df.quantity * df.unit_cost).round(2)
    df['gross_profit'] = (df.net_sales - df.cogs).round(2)
    df['loss_on_negative_rows'] = (-df.gross_profit).clip(lower=0)
    df['negative_record'] = (df.gross_profit < 0).astype(int)
    df['sales_record'] = (df.quantity > 0).astype(int)
    return df


def ratio(n, d):
    return n.div(d.where(d != 0)).mul(100).round(4)


def summarise(df, keys):
    agg = df.groupby(keys, dropna=False).agg(
        records=('source_row','size'), sales_records=('sales_record','sum'), quantity=('quantity','sum'),
        gross_sales=('gross_sales','sum'), discount=('discount','sum'),
        net_sales=('net_sales','sum'), cogs=('cogs','sum'), gross_profit=('gross_profit','sum'),
        negative_records=('negative_record','sum'), loss_on_negative_rows=('loss_on_negative_rows','sum')).reset_index()
    agg[MONEY] = agg[MONEY].round(2)
    agg['gross_margin_pct'] = ratio(agg.gross_profit, agg.net_sales)
    agg['weighted_discount_pct'] = ratio(agg.discount, agg.gross_sales)
    return agg


def monthly_comparison(unit_month):
    cols = ['net_sales','gross_profit','gross_margin_pct','weighted_discount_pct']
    sep = unit_month.loc[unit_month.month == '2026-09', ['unit'] + cols].set_index('unit').add_suffix('_sep')
    octo = unit_month.loc[unit_month.month == '2026-10', ['unit'] + cols].set_index('unit').add_suffix('_oct')
    comp = sep.join(octo, how='outer').reset_index()
    for metric in ['net_sales','gross_profit']:
        comp[metric + '_change_brl'] = (comp[metric+'_oct'] - comp[metric+'_sep']).round(2)
    comp['net_sales_change_pct'] = ratio(comp.net_sales_change_brl, comp.net_sales_sep)
    for metric in ['gross_margin_pct','weighted_discount_pct']:
        comp[metric.replace('_pct','')+'_change_pp'] = (comp[metric+'_oct'] - comp[metric+'_sep']).round(4)
    return comp


def limits(df):
    # Costs/prices can vary, so report each observed combination rather than invent a single SKU ceiling.
    out = df[['sku','product','unit_price','unit_cost']].drop_duplicates().copy()
    for target in (0, 5):
        raw = (1 - out.unit_cost / (out.unit_price * (1-target/100))) * 100
        out[f'feasible_margin_{target}pct_at_list_price'] = raw >= -1e-9
        out[f'max_discount_pct_for_margin_{target}pct'] = raw.where(raw >= -1e-9).clip(lower=0).round(4)
    return out.sort_values(['sku','unit_price','unit_cost'])


def scenario(df, target):
    # Static simulation: quantities and costs unchanged, no demand/elasticity forecast.
    x = df.copy()
    cap = x.gross_sales - x.cogs / (1-target/100)
    # Round the allowable total discount down to cents to preserve the target.
    import numpy as np
    cap = np.floor((cap.clip(lower=0) + 1e-8) * 100) / 100
    x['scenario_discount'] = x.discount.where(x.discount <= cap, cap)
    x['uplift'] = (x.discount - x.scenario_discount).round(2)
    x['scenario_net_sales'] = (x.net_sales + x.uplift).round(2)
    x['scenario_gross_profit'] = (x.gross_profit + x.uplift).round(2)
    x['infeasible_at_list_price'] = ((x.gross_sales * (1-target/100) + 1e-8) < x.cogs).astype(int)
    x['adjusted_record'] = (x.uplift > 0).astype(int)
    result = x.groupby(['month','unit']).agg(
        actual_net_sales=('net_sales','sum'), actual_gross_profit=('gross_profit','sum'),
        simulated_net_sales=('scenario_net_sales','sum'), simulated_gross_profit=('scenario_gross_profit','sum'),
        gross_profit_uplift=('uplift','sum'), adjusted_records=('adjusted_record','sum'),
        infeasible_records=('infeasible_at_list_price','sum')).reset_index()
    result['target_margin_pct'] = target
    result['simulated_margin_pct'] = ratio(result.simulated_gross_profit, result.simulated_net_sales)
    for c in ['actual_net_sales','actual_gross_profit','simulated_net_sales','simulated_gross_profit','gross_profit_uplift']:
        result[c] = result[c].round(2)
    return result


def make_reports(df, folder):
    folder.mkdir(parents=True, exist_ok=True)
    unit_month = summarise(df, ['month','unit'])
    reports = {
        'profitability_by_unit.csv': summarise(df, ['unit']),
        'profitability_by_product.csv': summarise(df, ['sku','product']),
        'profitability_by_unit_month.csv': unit_month,
        'monthly_comparison_sep_oct.csv': monthly_comparison(unit_month),
        'discount_limits_by_sku.csv': limits(df),
        'discount_scenarios.csv': pd.concat([scenario(df,0),scenario(df,5)], ignore_index=True),
        'negative_profit_details.csv': df.loc[df.negative_record == 1].copy(),
    }
    for name, data in reports.items():
        data.to_csv(folder / name, index=False, encoding='utf-8-sig', sep=';', decimal=',')
        print(f'  {name}: {len(data)} linhas')
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spreadsheet', help='Google Sheets URL ou ID')
    args = parser.parse_args()
    value = args.spreadsheet or input('Cole a URL ou ID da planilha: ').strip()
    match = re.search(r'/spreadsheets/d/([\w-]+)', value)
    spreadsheet_id = match.group(1) if match else value
    if not re.fullmatch(r'[\w-]+', spreadsheet_id):
        raise ValueError('URL ou ID da planilha invalido.')
    print('Conectando ao Google Sheets (somente leitura)...')
    df = prepare(load_sales(connect(), spreadsheet_id))
    print(f'Registros processados: {len(df)} | Meses: {", ".join(sorted(df.month.unique()))}')
    print(f'Registros com quantidade zero: {(df.quantity == 0).sum()}')
    print(f'Registros com lucro bruto negativo: {df.negative_record.sum()}')
    print(f'Perda bruta nos registros negativos: R$ {df.loss_on_negative_rows.sum():.2f}')
    print('Relatorios gerados:')
    make_reports(df, BASE / 'reports' / 'profitability')
    print('Concluido. Nenhum dado foi alterado no Google Sheets.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Falha: {exc}', file=sys.stderr)
        sys.exit(1)
