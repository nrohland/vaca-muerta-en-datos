import csv
from datetime import date
from pathlib import Path
import sys,tempfile,unittest
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from parquet_candidate import arrow_schema,append_csv
class ParquetContractTests(unittest.TestCase):
    def write(self,rows):
        contract={'anio':'numeric','mes':'numeric','idpozo':'numeric','idusuario':'numeric','id':'numeric','formacion':'text','prod_pet':'numeric','fecha_data':'timestamp'}
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        path=root/'source.csv';fields=[k for k in contract if k!='id']
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        dest=root/'candidate.parquet'
        with pq.ParquetWriter(dest,arrow_schema(contract),compression='zstd') as writer:
            result=append_csv(writer,path,contract,2023,'a'*64,'2026-10-13T00:00:00+00:00','2026-10-13T01:00:00+00:00')
        return pq.read_table(dest),result
    def row(self,**changes):return dict(anio=2023,mes=1,idpozo=1,idusuario='',formacion='',prod_pet='-0.00000001',fecha_data='2023-01-10',**changes)
    def test_nulls_empty_strings_negative_outside_product_and_types_preserved(self):
        table,result=self.write([self.row()]);r=table.to_pylist()[0]
        self.assertIsNone(r['id']);self.assertIsNone(r['idusuario']);self.assertEqual(r['formacion'],'');self.assertEqual(r['prod_pet'],-1e-8)
        self.assertEqual(r['periodo'],date(2023,1,1));self.assertEqual(r['fecha_data'].isoformat(),'2023-01-10T00:00:00+00:00');self.assertEqual(result['period_rows'],{'2023-01-01':1})
    def test_duplicate_grain_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.write([self.row(),self.row()])
    def test_numeric_nan_and_fractional_ids_are_rejected(self):
        for field,value in [('prod_pet','NaN'),('idpozo','1.2')]:
            row=self.row();row[field]=value
            with self.assertRaises(ValueError):self.write([row])
    def test_large_int64_id_survives_without_float_rounding(self):
        row=self.row();row['idpozo']='9007199254740993';table,_=self.write([row]);self.assertEqual(table.to_pylist()[0]['idpozo'],9007199254740993)
