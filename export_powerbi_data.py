"""WS-02 Phase 5: export validated SQLite tables for Power BI (read-only)."""
import argparse
import csv
from pathlib import Path
import sqlite3
import tempfile

BASE = Path(__file__).resolve().parent
QUERIES = {
    'dim_month': 'SELECT month, days_in_month FROM dim_month ORDER BY month',
    'dim_date': 'SELECT date, month FROM dim_date ORDER BY date',
    'dim_unit': 'SELECT unit, region, channel FROM dim_unit ORDER BY unit',
    'dim_product': 'SELECT sku, category, product FROM dim_product ORDER BY sku',
    'fact_sales': '''SELECT date, unit, sku, source_row, quantity, unit_price_cents,
        discount_cents, unit_cost_cents, gross_sales_cents, net_sales_cents,
        cogs_cents, gross_profit_cents FROM v_sales ORDER BY date, unit, sku''',
    'fact_traffic': 'SELECT date, unit, visits, orders FROM fact_traffic ORDER BY date, unit',
    'fact_targets': '''SELECT month, unit, target_sales_cents, target_margin_rate,
        target_conversion_rate FROM fact_targets ORDER BY month, unit''',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def export(db, output):
    require(db.is_file(), f'Banco nao encontrado: {db}')
    output.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        conn.execute('BEGIN')  # consistent read snapshot
        require(conn.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'Banco inconsistente')
        require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'Chaves estrangeiras invalidas')
        with tempfile.TemporaryDirectory(dir=output) as tmp:
            stage = Path(tmp)
            for name, query in QUERIES.items():
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                require(bool(rows), f'Tabela vazia: {name}')
                require(len(rows) == conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0], f'Contagem divergente: {name}')
                with (stage / (name + '.csv')).open('w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow([c[0] for c in cursor.description])
                    writer.writerows(rows)
                print(f'  {name}.csv: {len(rows)} linhas')
            # Check the actual serialized export against the database views.
            def records(name):
                with (stage / (name + '.csv')).open(encoding='utf-8-sig', newline='') as f:
                    return list(csv.DictReader(f, delimiter=';'))
            sales, traffic, targets = map(records, ('fact_sales', 'fact_traffic', 'fact_targets'))
            def sums(rows, cols):
                return tuple(sum(int(r[c]) for r in rows) for c in cols)
            cols = ('quantity','gross_sales_cents','discount_cents','net_sales_cents','cogs_cents','gross_profit_cents')
            expected = conn.execute('SELECT '+','.join('SUM('+c+')' for c in cols)+' FROM v_sales').fetchone()
            require(sums(sales, cols) == expected, 'Exportacao financeira divergente')
            require(sums(traffic, ('visits','orders')) == conn.execute('SELECT SUM(visits),SUM(orders) FROM fact_traffic').fetchone(), 'Fluxo divergente')
            require(sums(targets, ('target_sales_cents',)) == conn.execute('SELECT SUM(target_sales_cents) FROM fact_targets').fetchone(), 'Metas divergentes')
            for name in QUERIES:
                (stage / (name + '.csv')).replace(output / (name + '.csv'))
            print(f'Receita apos descontos: R$ {expected[3]/100:.2f}')
            print(f'Lucro bruto: R$ {expected[5]/100:.2f}')
            print('Reconciliacao da exportacao: OK')
    finally:
        conn.close()
    print(f'Arquivos disponiveis em {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=BASE/'data'/'retail_intelligence.sqlite3')
    parser.add_argument('--output', type=Path, default=BASE/'data'/'powerbi')
    args = parser.parse_args()
    try:
        export(args.db, args.output)
    except Exception as exc:
        parser.exit(1, f'Falha: {exc}\n')
