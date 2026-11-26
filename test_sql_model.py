"""Offline integration test. Run from the project root after extracting the package."""
import calendar
import datetime
from pathlib import Path
import sqlite3
import tempfile
import unittest
from analyze_commercial_profitability import COLUMNS
from build_retail_database import build, FLOW, TARGETS


def fixture():
    sales, flow, targets = [COLUMNS], [FLOW], [TARGETS]
    for month in (9, 10):
        period = f'2026-{month:02}'
        for unit, region, channel in [('L01','Sul','Físico'),('L02','Nacional','Digital')]:
            targets.append([period,unit,region,channel,10000,.17,.15 if channel=='Físico' else .025])
            for day in range(1,calendar.monthrange(2026,month)[1]+1):
                serial = (datetime.date(2026,month,day)-datetime.date(1899,12,30)).days
                flow.append([serial,period,unit,region,channel,20,2])
                sales.append([serial,period,unit,region,channel,'A','Phone','A',2,100,50 if day==1 else 0,80])
                sales.append([serial,period,unit,region,channel,'B','Case','B',0 if day%2 else 1,30,0,10])
    return [sales,flow,targets]


class ModelTest(unittest.TestCase):
    def test_load_and_constraints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); db=root/'db.sqlite3'; reports=root/'reports'
            arrays=fixture(); build(arrays,db,reports)
            self.assertEqual(len(list(reports.glob('*.csv'))),8)
            conn=sqlite3.connect(db)
            try:
                conn.execute('PRAGMA foreign_keys=ON')
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM fact_sales').fetchone()[0],244)
                self.assertEqual(conn.execute('SELECT SUM(visits) FROM v_daily_performance').fetchone()[0],2440)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM fact_sales WHERE quantity=0').fetchone()[0],62)
                self.assertEqual(conn.execute('SELECT -SUM(gross_profit_cents) FROM v_sales WHERE gross_profit_cents<0').fetchone()[0],4000)
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute("INSERT INTO fact_sales VALUES ('2026-09-01','L01','BAD',9999,1,100,0,50)")
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute("INSERT INTO fact_traffic VALUES ('2026-09-01','L01',20,2)")
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute('UPDATE fact_sales SET discount_cents=1 WHERE quantity=0')
            finally:
                conn.close()
            old=db.read_bytes(); arrays[0].append(arrays[0][1].copy())
            with self.assertRaises(ValueError): build(arrays,db,reports)
            self.assertEqual(db.read_bytes(),old)


if __name__=='__main__': unittest.main()
