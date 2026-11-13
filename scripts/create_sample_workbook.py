"""Synthetic, anonymous example. This is NOT the user's real ProjectPlan.xlsx."""
from pathlib import Path
import pandas as pd
rows = [
 ['SilverBank Non-Banking Extension','Task','Debt Management','Implement repayment schedule','In progress','Developer A',5,0.5,True,'Financial','2026-10-01','2026-10-08','2026-10-02',None,'Debt schedule and installment processing'],
 ['SilverBank Non-Banking Extension','Task','Debt Management','Validate overdue calculation','Pending',None,3,None,True,'Financial','2026-10-03','2026-10-10',None,None,'Calculate arrears from outstanding debt'],
 ['SilverBank Non-Banking Extension','Task','API Service Program','Create account API','Completed','Developer B',4,1,False,'Financial','2026-10-01','2026-10-07','2026-10-01','2026-10-06','REST account registration'],
 ['SilverBank Non-Banking Extension','Task','General Administration','Build audit viewer','In progress','Developer A',2,0.25,False,'Non-Financial','2026-10-05','2026-10-15','2026-10-06',None,'Operational audit UI'],
 ['SilverBank Non-Banking Extension','Task','API Service Program','Document endpoints','Pending','Developer C',1,0,False,'Non-Financial','2026-10-09','2026-10-16',None,None,'OpenAPI documentation'],
 ['Other Project','Task','Debt Management','Unrelated task','Completed','Developer D',99,1,False,'Financial','2026-10-01','2026-10-02','2026-10-01','2026-10-02','Must be excluded from SilverBank totals'],
]
cols=['Project','Type','Module','Task','Status','Assigned To','Target Manday','Completion %','Overdue','Financial / Non-Financial Mapping','Planned Start','Planned End','Actual Start','Actual End','Remarks']
p=Path(__file__).resolve().parents[1]/'data/ProjectPlan_SAMPLE.xlsx'
with pd.ExcelWriter(p,engine='openpyxl') as writer:
    pd.DataFrame({'Instructions':['Synthetic teaching data. Not the real project plan.','Select DevPlan, header row 3.','Scope: Project = SilverBank Non-Banking Extension.','Completion is a fraction; blanks are unknown.']}).to_excel(writer,sheet_name='START HERE',index=False)
    pd.DataFrame(rows,columns=cols).to_excel(writer,sheet_name='DevPlan',startrow=2,index=False)
    ws=writer.sheets['DevPlan'];ws['A1']='SYNTHETIC DEVELOPMENT PLAN';ws.freeze_panes='A4'
    for cell in ws[3]: cell.font=__import__('openpyxl').styles.Font(bold=True,color='FFFFFF');cell.fill=__import__('openpyxl').styles.PatternFill('solid',fgColor='176E5B')
    for row in range(4,10): ws.cell(row,8).number_format='0%'
    for c in ws.columns: ws.column_dimensions[c[0].column_letter].width=24
print(p)
