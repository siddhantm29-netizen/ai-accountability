"""Boundary checks for documentation coverage and unsupported complete cases."""
import ast,json,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'src/project11.py').read_text()
module=ast.parse(source)
functions=[x for x in module.body if isinstance(x,ast.FunctionDef) and x.name in {'risk_difference','bootstrap_rd'}]
ns={'np':np,'pd':pd,'SEED':11,'BOOTSTRAPS':1000}
exec(compile(ast.Module(body=functions,type_ignores=[]),'estimators','exec'),ns)
def fixture():
    return pd.DataFrame({'actor_group':['one organization']*20+['multiple organizations']*20,'redress':['documented']*10+['unclear']*10+['documented']*5+['unclear']*15,'design_weight':[1.]*40,'stratum':['one']*20+['multi']*20})
class AnalysisTests(unittest.TestCase):
    def test_documentation_coverage(self):
        self.assertAlmostEqual(ns['risk_difference'](fixture()),-.25)
    def test_no_absence_complete_cases_suppressed(self):
        self.assertTrue(np.isnan(ns['risk_difference'](fixture(),'exclude unclear')))
    def test_missing_comparison_group(self):
        self.assertTrue(np.isnan(ns['risk_difference'](fixture().iloc[:20])))
    def test_sparse_intervals_suppressed(self):
        f=fixture();f.loc[20,'redress']='unclear'
        point,lo,hi,_=ns['bootstrap_rd'](f)
        self.assertTrue(np.isfinite(point));self.assertTrue(np.isnan(lo) and np.isnan(hi))
    def test_bootstrap_supported_groups(self):
        point,lo,hi,count=ns['bootstrap_rd'](fixture())
        self.assertEqual(count,1000);self.assertTrue(lo<=point<=hi)
    def test_notebook_sync_and_unexecuted(self):
        n=json.loads((ROOT/'notebooks/Project_11_Final_Code.ipynb').read_text())
        c=[c for c in n['cells'] if c['cell_type']=='code']
        self.assertEqual(source.strip(),'\n\n'.join(c1['source'] for c1 in c).strip())
        for cell in c:
            self.assertIsNone(cell['execution_count']);self.assertEqual(cell['outputs'],[])
            compile(cell['source'],'cell','exec')
if __name__=='__main__':unittest.main()
