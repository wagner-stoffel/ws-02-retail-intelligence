"""WS-02 / Task 01. Read-only commercial data quality audit.
Usage: python validate_commercial_data.py --credentials credentials.json
Requires: pandas, gspread. Uses OAuth with read-only Sheets scope.
"""
import argparse
from pathlib import Path
import pandas as pd

SHEET_ID = '11bWvdIncRzSw08eDGhYBs9zC8eCFKe8ZiipIIwK46_4'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
RANGES = {'Vendas': 'A1:L4400', 'Fluxo': 'A1:G400', 'Metas': 'A1:G30'}
KEYS = {'Vendas': ['Data','Unidade','SKU'], 'Fluxo': ['Data','Unidade'], 'Metas': ['Mês','Unidade']}
EXPECTED_DATES = pd.date_range('2026-09-01','2026-10-31')
EXPECTED_MONTHS = ['2026-09','2026-10']
NUMERIC = {'Vendas':['Quantidade','Preço tabela unit. (R$)','Desconto total (R$)','Custo unitário (R$)'], 'Fluxo':['Visitas / sessões','Pedidos concluídos'], 'Metas':['Meta faturamento (R$)','Meta margem bruta (%)','Meta conversão (%)']}
HEADERS = {'Vendas':['Data','Mês','Unidade','Região','Canal','SKU','Categoria','Produto',*NUMERIC['Vendas']], 'Fluxo':['Data','Mês','Unidade','Região','Canal',*NUMERIC['Fluxo']], 'Metas':['Mês','Unidade','Região','Canal',*NUMERIC['Metas']]}

def load_data(credentials, token):
    import gspread
    client = gspread.oauth(credentials_filename=credentials, authorized_user_filename=token, scopes=SCOPES)
    book = client.open_by_key(SHEET_ID)
    tables = {}
    for name, area in RANGES.items():
        rows = book.worksheet(name).get(area, value_render_option='UNFORMATTED_VALUE', pad_values=True)
        if not rows or rows[0] != HEADERS[name]:
            raise ValueError(f'{name}: cabeçalhos inesperados ou ausentes')
        tables[name] = pd.DataFrame(rows[1:], columns=rows[0])
    return tables

def audit(tables):
    checks, details = [], []
    def add(table, rule, count, severity='ERRO'):
        checks.append({'aba':table,'regra':rule,'ocorrencias':int(count),'status':severity if count else 'OK'})
    def mark(table, rule, df, mask, severity='ERRO'):
        mask = mask.fillna(False)
        add(table,rule,mask.sum(),severity)
        for idx in df.index[mask]:
            details.append({'aba':table,'linha_planilha':int(idx)+2,'regra':rule,'gravidade':severity})
    data = {}
    for name, raw in tables.items():
        df = raw.copy().replace(r'^\s*$',pd.NA,regex=True)
        add(name,'Campos obrigatórios vazios',df.isna().sum().sum())
        mark(name,'Chave duplicada (ocorrências adicionais)',df,df.duplicated(KEYS[name]))
        for col in NUMERIC[name]:
            converted = pd.to_numeric(df[col],errors='coerce')
            mark(name,f'Número inválido: {col}',df,converted.isna() | converted.isin([float('inf'),float('-inf')]))
            df[col] = converted
        if 'Data' in df:
            serial = pd.to_numeric(df['Data'],errors='coerce')
            df['Data'] = pd.to_datetime(serial,unit='D',origin='1899-12-30',errors='coerce')
            mark(name,'Data inválida ou fora do período',df,~df['Data'].isin(EXPECTED_DATES))
            mark(name,'Mês divergente da data',df,df['Data'].dt.strftime('%Y-%m').ne(df['Mês']))
            add(name,'Dias ausentes',len(set(EXPECTED_DATES)-set(df['Data'].dropna())))
        else:
            mark(name,'Mês fora do período',df,~df['Mês'].isin(EXPECTED_MONTHS))
        data[name] = df
    v,f,m = (data[n] for n in ('Vendas','Fluxo','Metas'))
    q,p,d,c = (v[k] for k in NUMERIC['Vendas'])
    mark('Vendas','Quantidade negativa ou fracionária',v,(q<0)|(q%1!=0))
    mark('Vendas','Preço/custo inválido',v,(p<=0)|(c<=0)|(c>p))
    mark('Vendas','Desconto inválido',v,(d<0)|(d>q*p+1e-6))
    gross = q*(p-c)-d
    mark('Vendas','Lucro bruto negativo',v,gross < -1e-6,'ALERTA')
    visits,orders = (f[k] for k in NUMERIC['Fluxo'])
    mark('Fluxo','Visitas/pedidos inválidos',f,(visits<0)|(orders<0)|(visits%1!=0)|(orders%1!=0)|(orders>visits))
    target,margin,conversion = (m[k] for k in NUMERIC['Metas'])
    mark('Metas','Metas inválidas',m,(target<=0)|(~margin.between(0,1))|(~conversion.between(0,1)))
    def tuples(df, cols):
        return set(df[cols].dropna().itertuples(index=False,name=None))
    def compare(label, left, right):
        add('Integração',label,len(left-right)+len(right-left))
    unit_cols = ['Unidade','Região','Canal']
    units = tuples(v,unit_cols)
    compare('Unidades Vendas × Fluxo',units,tuples(f,unit_cols))
    compare('Unidades Vendas × Metas',units,tuples(m,unit_cols))
    compare('Data/unidade Vendas × Fluxo',tuples(v,['Data','Unidade']),tuples(f,['Data','Unidade']))
    compare('Mês/unidade Vendas × Metas',tuples(v,['Mês','Unidade']),tuples(m,['Mês','Unidade']))
    add('Vendas','SKUs com cadastro divergente',int((v.groupby('SKU')[['Categoria','Produto']].nunique()>1).any(axis=1).sum()))
    unit_ids = set(v['Unidade'].dropna()); sku_ids = set(v['SKU'].dropna())
    add('Vendas','Quantidade de unidades diferente de 6',abs(len(unit_ids)-6))
    add('Vendas','Quantidade de SKUs diferente de 12',abs(len(sku_ids)-12))
    expected_v = {(day,u,s) for day in EXPECTED_DATES for u in unit_ids for s in sku_ids}
    expected_f = {(day,u) for day in EXPECTED_DATES for u in unit_ids}
    expected_m = {(month,u) for month in EXPECTED_MONTHS for u in unit_ids}
    for name,df,expected in [('Vendas',v,expected_v),('Fluxo',f,expected_f),('Metas',m,expected_m)]:
        add(name,'Combinações obrigatórias ausentes',len(expected-tuples(df,KEYS[name])))
    qty = v.groupby(['Data','Unidade'])['Quantidade'].sum()
    aligned = pd.MultiIndex.from_frame(f[['Data','Unidade']]).map(qty)
    mark('Fluxo','Pedidos superiores a itens vendidos',f,orders>pd.Series(aligned,index=f.index))
    return pd.DataFrame(checks), pd.DataFrame(details,columns=['aba','linha_planilha','regra','gravidade'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials',default='credentials.json')
    parser.add_argument('--token',default='authorized_user.json')
    parser.add_argument('--output',default='reports')
    args = parser.parse_args()
    tables = load_data(args.credentials,args.token)
    report, occurrences = audit(tables)
    out = Path(args.output); out.mkdir(parents=True,exist_ok=True)
    report.to_csv(out/'quality_report.csv',index=False,encoding='utf-8-sig',sep=';')
    occurrences.to_csv(out/'quality_occurrences.csv',index=False,encoding='utf-8-sig',sep=';')
    print({name:len(df) for name,df in tables.items()})
    print(report.to_string(index=False))
    blocked = report['status'].eq('ERRO').any()
    print('\nBLOQUEADO' if blocked else '\nAPTO COM RESSALVAS' if report['status'].eq('ALERTA').any() else '\nAPTO')
    raise SystemExit(1 if blocked else 0)

if __name__ == '__main__':
    main()
