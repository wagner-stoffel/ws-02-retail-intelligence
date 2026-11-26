"""WS-02 phase 4: load a validated Google Sheets snapshot into SQLite, reconcile and export SQL reports."""
import argparse
import calendar
import csv
from decimal import Decimal
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import pandas as pd
import numpy as np
from analyze_commercial_profitability import connect, prepare
from analyze_commercial_performance import (build_reports, table, numeric, dates, FLOW, TARGETS, DAY, META)

BASE = Path(__file__).resolve().parent


def cents(v):
    d = Decimal(str(v)) * 100
    if not d.is_finite() or d != d.to_integral_value():
        raise ValueError(f'Valor monetario com mais de dois decimais: {v}')
    return int(d)


def tuples(df, columns):
    return list(df[columns].itertuples(index=False, name=None))


def ensure(condition, msg):
    if not condition:
        raise ValueError(msg)


def load_snapshot(conn, arrays):
    # Reuse Phase 3 validation and its independent Pandas KPI results as reference.
    reference = build_reports(*arrays)
    sales = prepare(arrays[0]); dates(sales)
    flow = table(arrays[1], FLOW, DAY+['visits','orders']); dates(flow)
    numeric(flow, ['visits','orders'])
    targets = table(arrays[2], TARGETS, META+['target_net_sales','target_margin_rate','target_conversion_rate'])
    numeric(targets, ['target_net_sales','target_margin_rate','target_conversion_rate'])
    units = pd.concat([sales[META[1:]],flow[META[1:]],targets[META[1:]]]).drop_duplicates()
    products = sales[['sku','category','product']].drop_duplicates()
    ensure(not units.duplicated('unit').any(), 'Cadastro de unidade divergente.')
    ensure(not products.duplicated('sku').any(), 'Cadastro de SKU divergente.')
    # This fixed exercise has a complete daily unit/SKU grid; zero sales are observations.
    expected = len(flow)*len(products)
    ensure(len(sales)==expected, f'Grade dia/unidade/SKU incompleta: {len(sales)} de {expected}.')
    date_keys = sales[['date','month']].drop_duplicates().sort_values('date')
    months = sorted(date_keys.month.unique())
    conn.executescript((BASE/'sql'/'schema.sql').read_text(encoding='utf-8'))
    with conn:
        conn.executemany('INSERT INTO dim_month VALUES (?,?)', [(m,calendar.monthrange(*map(int,m.split('-')))[1]) for m in months])
        conn.executemany('INSERT INTO dim_date VALUES (?,?)', [(d.strftime('%Y-%m-%d'),m) for d,m in tuples(date_keys,['date','month'])])
        conn.executemany('INSERT INTO dim_unit VALUES (?,?,?)', tuples(units,['unit','region','channel']))
        conn.executemany('INSERT INTO dim_product VALUES (?,?,?)', tuples(products,['sku','category','product']))
        conn.executemany('INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?)', [(d.strftime('%Y-%m-%d'),u,s,int(n),int(q),cents(p),cents(dis),cents(c)) for d,u,s,n,q,p,dis,c in tuples(sales,['date','unit','sku','source_row','quantity','unit_price','discount','unit_cost'])])
        conn.executemany('INSERT INTO fact_traffic VALUES (?,?,?,?)',[(d.strftime('%Y-%m-%d'),u,int(v),int(o)) for d,u,v,o in tuples(flow,['date','unit','visits','orders'])])
        conn.executemany('INSERT INTO fact_targets VALUES (?,?,?,?,?)',[(m,u,cents(s),float(g),float(c)) for m,u,s,g,c in tuples(targets,['month','unit','target_net_sales','target_margin_rate','target_conversion_rate'])])
    ensure(conn.execute('PRAGMA integrity_check').fetchall()==[('ok',)],'SQLite integrity_check falhou.')
    ensure(not conn.execute('PRAGMA foreign_key_check').fetchall(),'Chaves estrangeiras invalidas.')
    counts = {name:conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in ['dim_month','dim_date','dim_unit','dim_product','fact_sales','fact_traffic','fact_targets','v_daily_performance','v_monthly_performance']}
    for name,n in [('fact_sales',len(sales)),('fact_traffic',len(flow)),('fact_targets',len(targets)),('v_daily_performance',len(flow)),('v_monthly_performance',len(targets))]:
        ensure(counts[name]==n,f'Contagem divergente: {name}')
    sql = pd.read_sql_query('SELECT * FROM v_monthly_performance ORDER BY month,unit',conn)
    py = reference['monthly_performance_targets.csv'].sort_values(['month','unit']).reset_index(drop=True)
    ensure(sql[['month','unit']].equals(py[['month','unit']]),'Chaves mensais divergentes.')
    checks=[]
    def check(field,actual,expected,tolerance=0):
        ensure(np.allclose(actual,expected,atol=tolerance,rtol=0,equal_nan=True),f'Reconciliacao SQL x Pandas: {field}')
        checks.append((field,'OK'))
    for k in ['quantity','visits','orders','days']:
        check(k,sql[k],py[k])
    for k in ['gross_sales','discount','net_sales','cogs','gross_profit']:
        check(k,sql[k+'_cents'],np.rint(py[k]*100))
    check('target_sales',sql.target_sales_cents,np.rint(py.target_net_sales*100))
    check('negative_records',sql.negative_records,py.negative_record)
    for k in ['gross_margin_pct','conversion_pct','sales_attainment_pct','weighted_discount_pct','items_per_order','margin_gap_pp','conversion_gap_pp']:
        check(k,sql[k],py[k],1e-7)
    for k in ['average_ticket','revenue_per_visit']:
        check(k,sql[k+'_brl'],py[k],1e-7)
    for k in ['sales_status','margin_status','conversion_status']:
        ensure(sql[k].equals(py[k]),f'Status divergente: {k}');checks.append((k,'OK'))
    # Compare negative subset independently at cent precision.
    loss=conn.execute('SELECT COALESCE(-SUM(gross_profit_cents),0) FROM v_sales WHERE gross_profit_cents<0').fetchone()[0]
    check('loss_on_negative_rows',[loss],[int(round(sales.loss_on_negative_rows.sum()*100))])
    return counts, checks, loss


def run_queries(conn):
    source=(BASE/'sql'/'queries.sql').read_text(encoding='utf-8')
    result={}
    for block in re.split(r'^-- name: ',source,flags=re.M)[1:]:
        name,query=block.split('\n',1)
        ensure(bool(re.fullmatch(r'[a-z_]+',name)), 'Nome de consulta invalido.')
        result[name+'.csv']=pd.read_sql_query(query,conn)
    ensure(len(result)==7,'Esperadas sete consultas SQL.')
    return result


def build(arrays, db, report_dir):
    db.parent.mkdir(parents=True,exist_ok=True)
    # Create a temporary database; do not replace the previous snapshot on failed validation.
    with tempfile.TemporaryDirectory(dir=db.parent) as staging:
        temp=Path(staging)/db.name
        conn=sqlite3.connect(temp)
        try:
            conn.execute('PRAGMA foreign_keys=ON')
            counts,checks,loss=load_snapshot(conn,arrays)
            reports=run_queries(conn)
        finally:
            conn.close()
        temp.replace(db)
    report_dir.mkdir(parents=True,exist_ok=True)
    for name,df in reports.items():
        df.to_csv(report_dir/name,index=False,encoding='utf-8-sig',sep=';',decimal=',',float_format='%.6f')
    pd.DataFrame(checks,columns=['check','status']).to_csv(report_dir/'reconciliation.csv',index=False,encoding='utf-8-sig',sep=';')
    print('Tabelas e visoes:')
    for name,n in counts.items(): print(f'  {name}: {n} linhas')
    print(f'Reconciliacao SQL x Pandas: {len(checks)}/{len(checks)} OK')
    print(f'Perda bruta em registros negativos: R$ {loss/100:.2f}')
    print(f'Banco local: {db}')
    print(f'Relatorios SQL: {len(reports)+1} arquivos em {report_dir}')
    print('Concluido. Nenhum dado foi alterado no Google Sheets.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spreadsheet',help='Google Sheets URL ou ID')
    args=parser.parse_args()
    value=(args.spreadsheet or input('Cole a URL ou ID da planilha: ')).strip()
    match=re.search(r'/spreadsheets/d/([\w-]+)',value)
    sid=match.group(1) if match else value
    ensure(bool(re.fullmatch(r'[\w-]+',sid)),'URL ou ID invalido.')
    print('Conectando ao Google Sheets (somente leitura)...')
    response=connect().spreadsheets().values().batchGet(spreadsheetId=sid,ranges=['Vendas!A:L','Fluxo!A:G','Metas!A:G'],valueRenderOption='UNFORMATTED_VALUE').execute()
    arrays=[x.get('values',[]) for x in response.get('valueRanges',[])]
    ensure(len(arrays)==3,'Tres abas sao necessarias.')
    build(arrays,BASE/'data'/'retail_intelligence.sqlite3',BASE/'reports'/'sql')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'Falha: {exc}',file=sys.stderr);sys.exit(1)
