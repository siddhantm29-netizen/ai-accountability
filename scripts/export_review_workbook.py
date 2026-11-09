"""Export the six supplied review sheets without modifying their judgments."""
import argparse
from pathlib import Path
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('workbook',type=Path);p.add_argument('--output',type=Path,default=Path('data/review'));args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
sheets={'Final coding':'adjudicated_codes','Reviewer labels':'independent_codes','Scenarios':'scenarios','Claims':'scenario_claims','Signposts':'scenario_signposts','Later challenges':'later_challenges'}
for sheet,name in sheets.items():
    dest=args.output/f'{name}.csv'
    if dest.exists():raise FileExistsError(f'{dest} exists; choose a fresh export directory.')
for sheet,name in sheets.items():
    pd.read_excel(args.workbook,sheet_name=sheet).to_csv(args.output/f'{name}.csv',index=False)
print('Exported six CSVs. Structural acceptance does not authenticate the evidence.')
