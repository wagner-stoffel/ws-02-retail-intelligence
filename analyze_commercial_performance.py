"""WS-02 / Phase 3: read-only commercial performance and targets analysis.
Requires the corrected Phase 2 module in the same directory.
"""
import argparse
from pathlib import Path
import re
import sys
import numpy as np
import pandas as pd
from analyze_commercial_profitability import connect, prepare

BASE = Path(__file__).resolve().parent
FLOW = ['Data','Mês','Unidade','Região','Canal','Visitas / sessões','Pedidos concluídos']
TARGETS = ['Mês','Unidade','Região','Canal','Meta faturamento (R$)','Meta margem bruta (%)','Meta conversão (%)']
META = ['month','unit','region','channel']
DAY = ['date'] + META
SUMS = ['quantity','gross_sales','discount','net_sales','cogs','gross_profit','negative_record','visits','orders']


def table(rows, headers, names):
    if not rows or rows[0][:len(headers)] != headers:
        raise ValueError(f'Cabecalho inesperado: {headers}')
    body = [(r[:len(headers)] + [None]*len(headers))[:len(headers)] for r in rows[1:]
            if any(v is not None and v != '' for v in r)]
    df = pd.DataFrame(body, columns=names)
    if df.empty or df.isna().any().any() or df.astype(str).apply(lambda c:c.str.strip().eq('')).any().any():
        raise ValueError(f'Tabela vazia ou campos ausentes: {headers}')
    return df


def numeric(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='raise')
        if not np.isfinite(df[c]).all():
            raise ValueError(f'Valor nao finito: {c}')


def dates(df):
    serial = pd.to_numeric(df.date, errors='raise')
    if not np.isfinite(serial).all() or (serial % 1 != 0).any():
        raise ValueError('Data invalida ou com fracao de dia.')
    df['date'] = pd.to_datetime(serial, unit='D', origin='1899-12-30')
    if not df.date.dt.strftime('%Y-%m').eq(df.month).all():
        raise ValueError('Mes divergente da data.')


def unique(df, cols, name):
    if df.duplicated(cols).any():
        raise ValueError(f'Chave duplicada em {name}: {cols}')


def checked_join(left, right, key, name):
    out = left.merge(right, on=key, how='outer', validate='one_to_one', indicator=True)
    missing = out.loc[out['_merge'] != 'both', key+['_merge']]
    if not missing.empty:
        raise ValueError(f'Chaves sem correspondencia em {name}: {missing.head().to_dict("records")}')
    return out.drop(columns='_merge')


def divide(n, d):
    return n.div(d.where(d != 0))


def indicators(df):
    x = df.copy()
    x['conversion_pct'] = divide(x.orders, x.visits)*100
    x['average_ticket'] = divide(x.net_sales, x.orders)
    x['items_per_order'] = divide(x.quantity, x.orders)
    x['revenue_per_visit'] = divide(x.net_sales, x.visits)
    x['gross_margin_pct'] = divide(x.gross_profit, x.net_sales)*100
    x['weighted_discount_pct'] = divide(x.discount, x.gross_sales)*100
    return x


def build_reports(sales_rows, flow_rows, target_rows):
    sales = prepare(sales_rows)
    numeric(sales, ['quantity','unit_price','unit_cost','discount'])
    dates(sales)
    unique(sales, ['date','unit','sku'], 'Vendas')
    flow = table(flow_rows, FLOW, DAY+['visits','orders'])
    dates(flow)
    numeric(flow, ['visits','orders'])
    if ((flow[['visits','orders']] < 0) | (flow[['visits','orders']] % 1 != 0)).any().any() or (flow.orders > flow.visits).any():
        raise ValueError('Fluxo: visitas ou pedidos invalidos.')
    unique(flow, ['date','unit'], 'Fluxo')
    target = table(target_rows, TARGETS, META+['target_net_sales','target_margin_rate','target_conversion_rate'])
    numeric(target, ['target_net_sales','target_margin_rate','target_conversion_rate'])
    if (target.target_net_sales <= 0).any() or not target.target_margin_rate.between(0,1).all() or not target.target_conversion_rate.between(0,1).all():
        raise ValueError('Metas invalidas: margem e conversao devem ser fracoes entre 0 e 1.')
    unique(target, ['month','unit'], 'Metas')
    # Aggregate the SKU-level table first. Never multiply traffic by joining to individual SKUs.
    daily_sales = sales.groupby(DAY, as_index=False)[SUMS[:-2]].sum()
    unique(daily_sales, ['date','unit'], 'Vendas agregadas')
    daily = checked_join(daily_sales, flow, DAY, 'Vendas x Fluxo')
    if (daily.orders > daily.quantity).any() or ((daily.orders == 0) & (daily.quantity > 0)).any():
        raise ValueError('Pedidos e itens inconsistentes na agregacao diaria.')
    daily = indicators(daily).sort_values(['date','unit'])
    monthly = daily.groupby(META, as_index=False).agg(**{c:(c,'sum') for c in SUMS}, days=('date','nunique'))
    unique(monthly, ['month','unit'], 'Vendas e Fluxo mensais')
    monthly = checked_join(monthly, target, META, 'Indicadores x Metas')
    # Monthly targets are for complete calendar months in this exercise.
    expected = pd.to_datetime(monthly.month+'-01', format='%Y-%m-%d').dt.days_in_month
    if not monthly.days.eq(expected).all():
        raise ValueError('Periodo incompleto: metas mensais nao devem ser comparadas a meses parciais.')
    monthly = indicators(monthly)
    monthly['net_sales_per_day'] = divide(monthly.net_sales,monthly.days)
    monthly['gross_profit_per_day'] = divide(monthly.gross_profit,monthly.days)
    monthly['visits_per_day'] = divide(monthly.visits,monthly.days)
    monthly['orders_per_day'] = divide(monthly.orders,monthly.days)
    monthly['target_margin_pct'] = monthly.target_margin_rate*100
    monthly['target_conversion_pct'] = monthly.target_conversion_rate*100
    monthly['sales_attainment_pct'] = divide(monthly.net_sales,monthly.target_net_sales)*100
    monthly['sales_gap_brl'] = monthly.net_sales-monthly.target_net_sales
    monthly['margin_gap_pp'] = monthly.gross_margin_pct-monthly.target_margin_pct
    monthly['conversion_gap_pp'] = monthly.conversion_pct-monthly.target_conversion_pct
    # Profit gap at actual sales; conversion gap at actual traffic. Not forecasts.
    monthly['profit_gap_at_actual_sales'] = monthly.gross_profit-monthly.net_sales*monthly.target_margin_rate
    monthly['order_gap_at_actual_visits'] = monthly.orders-monthly.visits*monthly.target_conversion_rate
    for name, col in [('sales','sales_gap_brl'),('margin','margin_gap_pp'),('conversion','conversion_gap_pp')]:
        monthly[name+'_status'] = np.where(monthly[col].isna(),'UNDEFINED',np.where(monthly[col]>=-1e-8,'MET','BELOW'))
    monthly['targets_met'] = monthly[['sales_status','margin_status','conversion_status']].eq('MET').sum(axis=1)
    monthly['targets_below'] = monthly[['sales_status','margin_status','conversion_status']].eq('BELOW').sum(axis=1)
    monthly['targets_undefined'] = 3-monthly.targets_met-monthly.targets_below
    monthly = monthly.sort_values(['month','unit'])

    # Channel comparisons keep physical visits and digital sessions separate.
    channel_source = monthly.assign(required_profit=monthly.net_sales*monthly.target_margin_rate,
                                    required_orders=monthly.visits*monthly.target_conversion_rate)
    channel = channel_source.groupby(['month','channel'],as_index=False)[SUMS+['target_net_sales','required_profit','required_orders']].sum()
    channel = indicators(channel)
    channel['target_margin_pct_at_actual_mix'] = divide(channel.required_profit,channel.net_sales)*100
    channel['target_conversion_pct_at_actual_traffic'] = divide(channel.required_orders,channel.visits)*100
    channel['sales_attainment_pct'] = divide(channel.net_sales,channel.target_net_sales)*100
    channel['sales_gap_brl'] = channel.net_sales-channel.target_net_sales
    channel['margin_gap_pp'] = channel.gross_margin_pct-channel.target_margin_pct_at_actual_mix
    channel['conversion_gap_pp'] = channel.conversion_pct-channel.target_conversion_pct_at_actual_traffic

    # Compare each unit across consecutive observed months; daily metrics correct for month length.
    comparisons=[]
    for unit,g in monthly.groupby('unit'):
        g=g.sort_values('month')
        for (_,a),(_,b) in zip(g.iloc[:-1].iterrows(),g.iloc[1:].iterrows()):
            if pd.Period(b.month,freq='M')-pd.Period(a.month,freq='M') != pd.offsets.MonthEnd(1):
                raise ValueError(f'Meses nao consecutivos: {unit}')
            row={'unit':unit,'channel':b.channel,'from_month':a.month,'to_month':b.month}
            for c in ['net_sales','gross_profit','net_sales_per_day','gross_profit_per_day','visits_per_day','orders_per_day','average_ticket','items_per_order','revenue_per_visit']:
                row[c+'_change_pct']=(b[c]/a[c]-1)*100 if pd.notna(a[c]) and a[c]!=0 else np.nan
            for c in ['gross_margin_pct','conversion_pct','weighted_discount_pct']:
                row[c+'_change_pp']=b[c]-a[c]
            row['net_sales_change_brl']=b.net_sales-a.net_sales
            # Exact sequential bridge R = days * visits/day * orders/visits * revenue/order.
            # Order of attribution is explicit; interactions allocated to later factors.
            old=np.array([a.days,a.visits_per_day,a.conversion_pct/100,a.average_ticket],dtype=float)
            new=np.array([b.days,b.visits_per_day,b.conversion_pct/100,b.average_ticket],dtype=float)
            effects=[]
            current=old.copy()
            for i in range(4):
                before=np.prod(current);current[i]=new[i];effects.append(np.prod(current)-before)
            for c,v in zip(['days_effect_brl','traffic_effect_brl','conversion_effect_brl','ticket_effect_brl'],effects):row[c]=v
            row['bridge_residual_brl']=row['net_sales_change_brl']-sum(effects)
            comparisons.append(row)
    comparison=pd.DataFrame(comparisons)
    if comparison.empty:
        raise ValueError('Sao necessarios pelo menos dois meses consecutivos para comparacao.')
    # Network financial totals only: do not pool physical visits and online sessions.
    network=monthly.groupby('month',as_index=False)[SUMS[:-2]+['target_net_sales']].sum()
    network['gross_margin_pct']=divide(network.gross_profit,network.net_sales)*100
    network['weighted_discount_pct']=divide(network.discount,network.gross_sales)*100
    network['sales_attainment_pct']=divide(network.net_sales,network.target_net_sales)*100
    network['sales_gap_brl']=network.net_sales-network.target_net_sales
    # Reconcile before writing. Each source observation contributes exactly once.
    for c in SUMS[:-2]:
        if not np.isclose(monthly[c].sum(),sales[c].sum(),atol=.01,rtol=0):
            raise ValueError(f'Falha de reconciliacao Vendas: {c}')
    for c in ['visits','orders']:
        if monthly[c].sum()!=flow[c].sum():raise ValueError(f'Falha de reconciliacao Fluxo: {c}')
    if not np.isclose(monthly.target_net_sales.sum(),target.target_net_sales.sum(),atol=.01,rtol=0):
        raise ValueError('Falha de reconciliacao Metas.')
    if not comparison.bridge_residual_brl.dropna().abs().le(.01).all():
        raise ValueError('Falha na decomposicao da variacao de faturamento.')
    return {
        'daily_performance.csv':daily,
        'monthly_performance_targets.csv':monthly,
        'channel_performance.csv':channel,
        'monthly_performance_comparison.csv':comparison,
        'network_financial_performance.csv':network,
        'target_exceptions.csv':monthly.loc[(monthly.targets_below+monthly.targets_undefined)>0].copy(),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spreadsheet',help='Google Sheets URL ou ID')
    args=parser.parse_args()
    value=(args.spreadsheet or input('Cole a URL ou ID da planilha: ')).strip()
    match=re.search(r'/spreadsheets/d/([\w-]+)',value)
    sid=match.group(1) if match else value
    if not re.fullmatch(r'[\w-]+',sid):raise ValueError('URL ou ID invalido.')
    print('Conectando ao Google Sheets (somente leitura)...')
    service=connect()
    result=service.spreadsheets().values().batchGet(spreadsheetId=sid,ranges=['Vendas!A:L','Fluxo!A:G','Metas!A:G'],valueRenderOption='UNFORMATTED_VALUE').execute()
    arrays=[r.get('values',[]) for r in result.get('valueRanges',[])]
    if len(arrays)!=3:raise ValueError('Tres abas sao necessarias.')
    reports=build_reports(*arrays)
    folder=BASE/'reports'/'performance';folder.mkdir(parents=True,exist_ok=True)
    for name,df in reports.items():
        df.to_csv(folder/name,index=False,encoding='utf-8-sig',sep=';',decimal=',',float_format='%.6f',date_format='%Y-%m-%d')
        print(f'  {name}: {len(df)} linhas')
    print('Reconciliacao: vendas, visitas, pedidos e metas conferem com as fontes.')
    print('Concluido. Nenhum dado foi alterado no Google Sheets.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f'Falha: {exc}',file=sys.stderr);sys.exit(1)
