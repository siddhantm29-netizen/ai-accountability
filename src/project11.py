from pathlib import Path
import hashlib, json, re, zipfile, uuid, platform, importlib.metadata, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    from IPython.display import display
except ImportError:
    def display(value): print(value.to_string(index=False) if isinstance(value,pd.DataFrame) else value)
from sklearn.metrics import cohen_kappa_score
SEED = 11
BOOTSTRAPS = int(os.environ.get('PROJECT11_BOOTSTRAPS','1000'))
if BOOTSTRAPS < 1000: raise ValueError('Use at least 1000 bootstrap replicates for the final analysis.')
NAME = 'AIID_Excel_Export-20261019.xlsx'
EXPECTED_SHA256 = '41758b56b948f62f75385108977f58af8e1faefad03bb0203cda03b889660ae2'
REVIEW_DIR = Path(os.environ.get('PROJECT11_REVIEW_DIR', '/kaggle/input/project11-human-review' if Path('/kaggle/input').exists() else 'data/review')).resolve()
base = Path(os.environ.get('PROJECT11_OUTPUT_DIR','/kaggle/working' if Path('/kaggle/working').exists() else 'results')).resolve()
base.mkdir(parents=True,exist_ok=True)
input_roots = [Path('/kaggle/input'), Path.cwd(), Path.cwd()/'upload']
configured = os.environ.get('PROJECT11_DATA_PATH')
found = [Path(configured).expanduser().resolve()] if configured else sorted({p.resolve() for root in input_roots if root.exists() for p in root.rglob(NAME)})
if not found or not found[0].is_file(): raise FileNotFoundError(f'Attach the official public workbook {NAME}.')
source = found[0]
sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
if sha256 != EXPECTED_SHA256: raise ValueError('Source differs from the audited snapshot. Audit and explicitly repin before proceeding.')
run_id = uuid.uuid4().hex[:10]
out = base / f'project11_final_{run_id}'
out.mkdir(parents=True, exist_ok=False)
manifest, status = [], {}
def save_table(df, stem):
    path = out/f'{stem}.csv'; df.to_csv(path,index=False); manifest.append(path)
    display(df)
def save_figure(fig, stem):
    for ext in ['pdf','png']:
        path=out/f'{stem}.{ext}';fig.savefig(path,dpi=300,bbox_inches='tight');manifest.append(path)
    plt.show();plt.close(fig)
def block(exhibits, reason):
    for name in exhibits: status[name] = 'PENDING: '+reason
    print(reason)
def success(name): status[name]='GENERATED'
def text_ok(series): return series.notna() & series.astype(str).str.strip().ne('')
def require(condition, message):
    if not bool(condition): raise ValueError(message)
def require_urls(series):
    require(series.fillna('').astype(str).str.match(r'^https?://[^\s]+$').all(),'Every evidence URL must be a nonblank HTTP(S) URL. URLs still require human verification.')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
print('Source:',source,'SHA256:',sha256,'Output:',out)

inc=pd.read_excel(source,sheet_name='Incidents',header=2)
rep=pd.read_excel(source,sheet_name='Reports',header=1)
ent=pd.read_excel(source,sheet_name='Entities',header=1).dropna(how='all')
needed={'Incident ID','date','year','developer','deployer','harmed','Risk Domain','Sector of Deployment','report_count','title','description'}
require(needed.issubset(inc.columns),'Unexpected incident schema.')
require({'Report Number','URL'}.issubset(rep.columns),'Unexpected report schema.')
for frame,key in [(inc,'Incident ID'),(rep,'Report Number')]:
    require(frame[key].notna().all() and frame[key].is_unique,f'Invalid {key} identifiers.')
require(not inc.duplicated().any(),'Exact incident duplicates found; investigate before analysis.')
inc['date']=pd.to_datetime(inc['date'],errors='coerce')
inc['year']=pd.to_numeric(inc['year'],errors='coerce')
require(inc['date'].notna().all() and inc['year'].notna().all(),'Invalid incident dates/years.')
require(inc['date'].dt.year.eq(inc['year']).all(),'Date and recorded year disagree.')
inc['report_count']=pd.to_numeric(inc['report_count'],errors='coerce')
require(inc['report_count'].notna().all() and inc['report_count'].ge(0).all() and inc['report_count'].mod(1).eq(0).all(),'Invalid incident report counts.')
url=rep['URL'].fillna('').astype(str).str.strip()
audit=pd.DataFrame({'check':['incidents','reports','populated entities','duplicate incident IDs','exact duplicate incident rows','missing risk domain','missing deployment sector','blank report URLs','extra repeated nonblank URLs'],
 'count':[len(inc),len(rep),len(ent),inc['Incident ID'].duplicated().sum(),inc.duplicated().sum(),(~text_ok(inc['Risk Domain'])).sum(),(~text_ok(inc['Sector of Deployment'])).sum(),url.eq('').sum(),url[url.ne('')].duplicated().sum()]})
save_table(audit,'data_audit')
missing=pd.DataFrame({'field':inc.columns,'missing_n':[int((~text_ok(inc[c])).sum()) for c in inc.columns]})
missing['missing_fraction']=missing.missing_n/len(inc);save_table(missing,'field_missingness')

def norm(value):
    if pd.isna(value): return ''
    value=re.sub(r'\s+',' ',str(value).casefold().strip())
    return '' if value in {'','unknown','not known','unspecified','n/a','none','nan'} else value
dev,dep=inc.developer.map(norm),inc.deployer.map(norm)
observed=dev.ne('') & dep.ne('')
inc['actor_string_group']=np.select([observed & dev.eq(dep),observed & dev.ne(dep)],['same string','different strings'],default='unknown')
inc['risk_domain']=inc['Risk Domain'].where(text_ok(inc['Risk Domain']),'Unclassified')
inc['harmed_present']=text_ok(inc.harmed)
inc['cohort']=np.where(inc.year.isin([2024,2025]),'construction',np.where(inc.year.eq(2026),'later','outside'))
construction=inc[inc.cohort.eq('construction')].copy()
later=inc[inc.cohort.eq('later')].copy()
require(len(construction)>0 and len(later)>0,'Required cohorts are empty.')
parts=[]
for (cohort,year,group),g in inc[inc.cohort.ne('outside')].groupby(['cohort','year','actor_string_group'],sort=True):
    target=30 if cohort=='construction' else 20
    s=g.sample(n=min(target,len(g)),random_state=SEED).copy()
    s['stratum']=f'{cohort}|{int(year)}|{group}';s['population_n']=len(g);s['sample_n']=len(s)
    s['inclusion_probability']=len(s)/len(g);s['design_weight']=len(g)/len(s);parts.append(s)
sample=pd.concat(parts).sort_values('Incident ID').reset_index(drop=True)
sample_cols=['Incident ID','cohort','year','stratum','population_n','sample_n','inclusion_probability','design_weight','title','description','developer','deployer','harmed','risk_domain','report_count','actor_string_group']
save_table(sample[sample_cols],'sampling_frame_selected')
print('Construction / later population:',len(construction),len(later),'Selected:',sample.groupby('cohort').size().to_dict())

FIELDS=['actor_group','accountability_clarity','response','redress']
ALLOWED={'actor_group':{'one organization','multiple organizations','unknown'},'accountability_clarity':{'clear','unclear'},'response':{'documented','explicitly absent','unclear'},'redress':{'documented','explicitly absent','unclear'}}
codebook=pd.DataFrame([
 ('actor_group','Verify legal/organizational identities and developer/deployer roles; names alone are insufficient.'),
 ('accountability_clarity','Clear requires a documented identifiable responsible party and role; otherwise unclear.'),
 ('response','Document an institutional action following the incident; mere allegations or harm descriptions are insufficient.'),
 ('redress','Document an accessible remedy/appeal/compensation route; distinguish a route from successful remedy.'),
 ('evidence_url','Public evidence supporting the row; add field-specific sources and quotations in evidence_note.'),
 ('coding_procedure','Preserve AI-assistance provenance, both saved label sets and adjudication rationale; disclose whether suggestions were shared.'),
 ('sampling','Complete every selected row. Missing review is not evidence of no response.')],columns=['field','rule'])
save_table(codebook,'coding_codebook')
independent=pd.DataFrame([{'Incident ID':i,'coder_slot':slot,'coder_id':'',**{f:'' for f in FIELDS},'evidence_url':'','evidence_note':''} for i in sample['Incident ID'] for slot in [1,2]])
save_table(independent,'independent_codes_TEMPLATE')
adjudicated=pd.DataFrame({'Incident ID':sample['Incident ID']})
for col in FIELDS+['evidence_url','evidence_note','adjudicator','adjudication_note']: adjudicated[col]=''
save_table(adjudicated,'adjudicated_codes_TEMPLATE')
print('Complete independent_codes.csv and adjudicated_codes.csv in REVIEW_DIR. Public source verification remains the team’s responsibility.')

t1=(construction.groupby(['risk_domain','actor_string_group'],dropna=False).agg(incidents=('Incident ID','size'),harmed_field_present=('harmed_present','sum'),median_reports=('report_count','median')).reset_index())
t1['share_within_actor_group']=t1.incidents/t1.groupby('actor_string_group').incidents.transform('sum')
save_table(t1,'table_1A_role_risk_screen');success('1A')
cov=construction.groupby('actor_string_group').agg(n=('Incident ID','size'),harmed_field_present=('harmed_present','sum')).reset_index()
cov['fraction']=cov.harmed_field_present/cov.n;save_table(cov,'figure_1B_values')
fig,ax=plt.subplots(figsize=(7,4));ax.bar(cov.actor_string_group,100*cov.fraction,color='#24517a')
ax.set(ylabel='Incidents with affected-party field (%)',ylim=(0,105),title='1B. Recorded affected-party coverage, 2024–2025')
for i,r in enumerate(cov.itertuples()): ax.text(i,100*r.fraction+1,f'{r.harmed_field_present}/{r.n}',ha='center')
save_figure(fig,'figure_1B_affected_party_coverage');success('1B')

coded=None
paths=[REVIEW_DIR/'independent_codes.csv',REVIEW_DIR/'adjudicated_codes.csv']
if not all(p.exists() for p in paths):
    block(['1C','1D','2A','2B','2C','2D','3C','3D'],'Human review pending: both completed coding files are required.')
else:
    raw=pd.read_csv(paths[0]);adj=pd.read_csv(paths[1])
    require({'Incident ID','coder_slot','coder_id','evidence_url','evidence_note',*FIELDS}.issubset(raw.columns),'Independent coding schema is incomplete.')
    require({'Incident ID','evidence_url','evidence_note','adjudicator','adjudication_note',*FIELDS}.issubset(adj.columns),'Adjudication schema is incomplete.')
    ids=set(sample['Incident ID'])
    require(set(raw['Incident ID'])==ids and set(adj['Incident ID'])==ids,'Review IDs must exactly match the current selected sample.')
    require(adj['Incident ID'].is_unique,'Duplicate adjudicated IDs.')
    require(len(raw)==2*len(sample) and not raw.duplicated(['Incident ID','coder_slot']).any(),'Exactly two reviewer rows per incident are required.')
    require(raw.groupby('Incident ID').coder_slot.apply(lambda s:set(s)=={1,2}).all(),'Each incident needs coder slots 1 and 2.')
    for frame in [raw,adj]:
        for f in FIELDS: require(frame[f].isin(ALLOWED[f]).all(),f'Invalid or missing {f} code.')
        for f in ['evidence_note','evidence_url']: require(text_ok(frame[f]).all(),f'Blank {f}.')
        require_urls(frame.evidence_url)
    require(text_ok(raw.coder_id).all(),'Coder names/IDs are required.')
    raw['coder_id']=raw.coder_id.astype(str).str.strip()
    require(raw.groupby('Incident ID').coder_id.nunique().eq(2).all(),'Two distinct coders are required per incident.')
    for f in ['adjudicator','adjudication_note']: require(text_ok(adj[f]).all(),f'Blank {f}.')
    agreement=[]
    for field in FIELDS:
        p=raw.pivot(index='Incident ID',columns='coder_slot',values=field)
        agreement.append({'field':field,'double_coded_n':len(p),'agreement':p[1].eq(p[2]).mean(),'cohen_kappa':cohen_kappa_score(p[1],p[2]) if len(set(p[1])|set(p[2]))>1 else np.nan})
    save_table(pd.DataFrame(agreement),'coder_agreement')
    coded=sample.merge(adj,on='Incident ID',how='inner',validate='one_to_one')
    save_table(coded[['Incident ID','cohort','stratum','design_weight',*FIELDS,'evidence_url','evidence_note']],'adjudicated_analysis_data')
    print('Coding structure validated. This check does not authenticate source claims or prove independent work.')

def weighted_rates(frame, field, group='actor_group'):
    rows=[]
    for name,g in frame.groupby(group,dropna=False):
        total=g.design_weight.sum()
        for label in sorted(ALLOWED[field]):
            rows.append({group:name,'category':label,'sample_n':len(g),'sample_category_n':int(g[field].eq(label).sum()),'weighted_total':total,'weighted_fraction':float(g.loc[g[field].eq(label),'design_weight'].sum()/total)})
    return pd.DataFrame(rows)
def risk_difference(frame, policy='documentation coverage'):
    g=frame[frame.actor_group.isin(['one organization','multiple organizations'])].copy()
    if policy=='exclude unclear':
        g=g[g.redress.ne('unclear')]
        if g.redress.nunique()<2:return np.nan
    values={}
    for name in ['one organization','multiple organizations']:
        t=g[g.actor_group.eq(name)]
        if t.empty:return np.nan
        y=t.redress.eq('documented').astype(float)
        if policy=='unclear documented':y=t.redress.ne('explicitly absent').astype(float)
        values[name]=np.average(y,weights=t.design_weight)
    return values['multiple organizations']-values['one organization']
def bootstrap_rd(frame, policy='documentation coverage'):
    estimate=risk_difference(frame,policy)
    if not np.isfinite(estimate):return estimate,np.nan,np.nan,0
    rng=np.random.default_rng(SEED)
    numer=np.zeros((2,BOOTSTRAPS));denom=np.zeros((2,BOOTSTRAPS))
    for _,g in frame.groupby('stratum',sort=True):
        ix=rng.integers(0,len(g),size=(BOOTSTRAPS,len(g)))
        w=g.design_weight.to_numpy()[ix]
        labs=g.redress.to_numpy()[ix];actors=g.actor_group.to_numpy()[ix]
        for k,name in enumerate(['one organization','multiple organizations']):
            mask=actors==name
            if policy=='exclude unclear':mask=mask & (labs!='unclear')
            y=(labs!='explicitly absent') if policy=='unclear documented' else (labs=='documented')
            denom[k]+=(w*mask).sum(axis=1);numer[k]+=(w*mask*y).sum(axis=1)
    good=(denom>0).all(axis=0)
    draws=numer[1,good]/denom[1,good]-numer[0,good]/denom[0,good]
    valid=frame[frame.actor_group.isin(['one organization','multiple organizations'])]
    if policy=='exclude unclear':valid=valid[valid.redress.ne('unclear')]
    enough=True
    for name in ['one organization','multiple organizations']:
        t=valid[valid.actor_group.eq(name)]
        positives=int(t.redress.ne('explicitly absent').sum()) if policy=='unclear documented' else int(t.redress.eq('documented').sum())
        enough &= len(t)>=10 and positives>=5 and len(t)-positives>=5
    if not enough or len(draws)<.95*BOOTSTRAPS:return estimate,np.nan,np.nan,len(draws)
    lo,hi=np.quantile(draws,[.025,.975]);return estimate,float(lo),float(hi),len(draws)


if coded is not None:
    c=coded[coded.cohort.eq('construction')].copy()
    matrix=weighted_rates(c,'accountability_clarity');save_table(matrix,'table_1C_verified_actor_matrix');success('1C')
    evidence=c[['Incident ID','actor_group','accountability_clarity','response','redress','evidence_url','evidence_note']].copy()
    save_table(evidence,'figure_1D_evidence_map_values')
    shown=c.head(15)
    fig,ax=plt.subplots(figsize=(8,max(3,.3*len(shown))))
    a=np.column_stack([shown.accountability_clarity.eq('clear'),shown.response.eq('documented'),shown.redress.eq('documented')]).astype(int)
    ax.imshow(a,aspect='auto',vmin=0,vmax=1,cmap='Blues');ax.set_xticks(range(3),['Clear accountability','Response documented','Redress route documented'])
    ax.set_yticks(range(len(shown)),shown['Incident ID'].astype(str));ax.set_title('1D. First 15 sampled construction cases by ID; full evidence map in CSV')
    ax.set_ylabel('Incident ID');fig.text(.1,.01,'Dark = documented/clear. Light combines other codes; consult the evidence CSV.',fontsize=8)
    save_figure(fig,'figure_1D_case_evidence_map');success('1D')

if coded is not None:
    c=coded[coded.cohort.eq('construction')].copy()
    response=weighted_rates(c,'response');save_table(response,'table_2A_response_by_verified_group');success('2A')
    c['report_depth']=np.where(c.report_count.ge(3),'3+ reports','0–2 reports')
    depth=weighted_rates(c,'redress',group='report_depth');save_table(depth,'figure_2B_values')
    p=depth.pivot(index='report_depth',columns='category',values='weighted_fraction').fillna(0)
    ax=(100*p).plot.bar(stacked=True,figsize=(8,4),rot=0);ax.set(ylabel='Weighted incidents (%)',title='2B. Redress evidence by report depth');ax.legend(bbox_to_anchor=(1.02,1),loc='upper left')
    save_figure(ax.figure,'figure_2B_redress_by_depth');success('2B')
    est,lo,hi,b=bootstrap_rd(c)
    effect=pd.DataFrame([{'comparison':'multiple minus one organization','estimand':'weighted difference in documented-redress coverage; all coded cases retained','risk_difference':est,'bootstrap_lower':lo,'bootstrap_upper':hi,'finite_bootstraps':b,'sample_n':len(c),'interval_note':'Suppressed if either group has <10 cases, <5 documented or <5 other outcomes, or <95% finite draws. Unclear remains distinct from explicit absence.'}])
    save_table(effect,'table_2C_weighted_descriptive_difference');success('2C')
    pathway=pd.concat([weighted_rates(c,f).assign(measure=f) for f in ['response','redress']],ignore_index=True)
    save_table(pathway,'figure_2D_values')
    present=pathway[pathway.category.eq('documented')].pivot(index='actor_group',columns='measure',values='weighted_fraction')
    ax=(100*present).plot.bar(figsize=(8,4),rot=15);ax.set(ylabel='Weighted documented evidence (%)',title='2D. Response and redress are distinct outcomes');ax.legend()
    save_figure(ax.figure,'figure_2D_response_redress');success('2D')

period=inc[inc.cohort.ne('outside')].copy()
miss=period.groupby('year').agg(n=('Incident ID','size'),unclassified=('risk_domain',lambda s:s.eq('Unclassified').sum()),median_reports=('report_count','median')).reset_index()
miss['unclassified_fraction']=miss.unclassified/miss.n;save_table(miss,'table_3A_missingness_by_period');success('3A')
n=len(construction);m=int(construction.risk_domain.eq('Unclassified').sum());known=n-m
require(known>0,'No classified construction incidents.')
counts=construction.loc[construction.risk_domain.ne('Unclassified'),'risk_domain'].value_counts().sort_values()
bounds=counts.rename_axis('risk_domain').reset_index(name='classified_n')
bounds['complete_case_share']=bounds.classified_n/known;bounds['lower']=bounds.classified_n/n;bounds['upper']=(bounds.classified_n+m)/n
save_table(bounds,'figure_3B_values')
fig,ax=plt.subplots(figsize=(10,5));y=np.arange(len(bounds));ax.hlines(y,bounds.lower,bounds.upper,lw=6,color='#8da8c3',label='Per-domain extreme bounds');ax.scatter(bounds.complete_case_share,y,color='#173e63',label='Classified cases')
ax.set_yticks(y,bounds.risk_domain);ax.set(xlabel='Share of construction incidents',title=f'3B. Classification sensitivity; missing {m}/{n}');ax.legend();save_figure(fig,'figure_3B_risk_bounds');success('3B')

if coded is not None:
    c=coded[coded.cohort.eq('construction')].copy()
    rows=[]
    for policy in ['documentation coverage','exclude unclear','unclear absent','unclear documented']:
        est,lo,hi,b=bootstrap_rd(c,policy);rows.append({'policy':policy,'difference':est,'lower':lo,'upper':hi,'finite_bootstraps':b})
    group_bounds={}
    for name,g in c[c.actor_group.ne('unknown')].groupby('actor_group'):
        w=g.design_weight;total=w.sum();group_bounds[name]=(w[g.redress.eq('documented')].sum()/total,w[g.redress.ne('explicitly absent')].sum()/total)
    if {'one organization','multiple organizations'}.issubset(group_bounds):
        one,multi=group_bounds['one organization'],group_bounds['multiple organizations']
        rows.append({'policy':'worst-case identification interval','difference':np.nan,'lower':multi[0]-one[1],'upper':multi[1]-one[0],'finite_bootstraps':0})
    save_table(pd.DataFrame(rows),'table_3C_unclear_code_sensitivity');success('3C')
    rows=[]
    for threshold in [1,3,5]:
        g=c[c.report_count.ge(threshold)];est,lo,hi,b=bootstrap_rd(g)
        rows.append({'minimum_reports':threshold,'reviewed_n':len(g),'difference':est,'lower':lo,'upper':hi,'finite_bootstraps':b})
    depth=pd.DataFrame(rows);save_table(depth,'figure_3D_values')
    fig,ax=plt.subplots(figsize=(7,4));ax.scatter(depth.minimum_reports,depth.difference,color='#24517a')
    for r in depth.itertuples():
        if np.isfinite(r.lower) and np.isfinite(r.upper):ax.vlines(r.minimum_reports,r.lower,r.upper,color='#24517a')
    ax.axhline(0,color='gray',lw=1);ax.set(xticks=[1,3,5],xlabel='Minimum linked-report count',ylabel='Weighted documented-redress coverage difference',title='3D. Report-depth sensitivity; intervals suppressed for sparse groups')
    save_figure(fig,'figure_3D_reporting_depth');success('3D')

scenario_cols=['scenario_id','name','axis1_name','axis2_name','axis1_state','axis2_state','assumption','revision_rule']
claim_cols=['scenario_id','claim_id','claim','Incident ID','evidence_url','interpretation_note']
signpost_cols=['scenario_id','signpost_id','metric','direction','threshold','revision_rule']
challenge_cols=['scenario_id','Incident ID','judgment','reason','evidence_url']
for stem,cols in [('scenarios_TEMPLATE',scenario_cols),('scenario_claims_TEMPLATE',claim_cols),('scenario_signposts_TEMPLATE',signpost_cols),('later_challenges_TEMPLATE',challenge_cols)]:save_table(pd.DataFrame(columns=cols),stem)
print('Supported observed metrics: response_documented, redress_documented, accountability_clear. Thresholds are fractions in [0,1]; directions are above/below. They are revision triggers, not predictions.')

scenario_data=None
names=['scenarios.csv','scenario_claims.csv','scenario_signposts.csv','later_challenges.csv']
if coded is None or not all((REVIEW_DIR/n).exists() for n in names):
    block(['4A','4B','4C','4D'],'RQ4 pending: completed coding and all four scenario evidence files are required.')
else:
    sc,cl,sp,ch=[pd.read_csv(REVIEW_DIR/n) for n in names]
    for frame,cols in [(sc,scenario_cols),(cl,claim_cols),(sp,signpost_cols),(ch,challenge_cols)]:
        require(set(cols).issubset(frame.columns),'Scenario file schema incomplete.')
        require(not frame.empty and frame[cols].apply(text_ok).all().all(),'Blank scenario evidence fields.')
    require(len(sc)==4 and sc.scenario_id.is_unique,'Exactly four unique scenarios are required.')
    require(sc.axis1_name.nunique()==1 and sc.axis2_name.nunique()==1 and sc.axis1_name.iloc[0]!=sc.axis2_name.iloc[0],'Define two distinct uncertainty axes consistently.')
    require(set(zip(sc.axis1_state,sc.axis2_state))=={('low','low'),('low','high'),('high','low'),('high','high')},'Four low/high combinations required.')
    sids=set(sc.scenario_id)
    for frame in [cl,sp,ch]:require(set(frame.scenario_id)==sids,'Every scenario needs claims, signposts and later challenges.')
    require(cl.claim_id.is_unique and sp.signpost_id.is_unique,'Claim and signpost IDs must be globally unique.')
    require(not ch.duplicated(['scenario_id','Incident ID']).any(),'Duplicate later-case judgments.')
    require(set(cl['Incident ID']).issubset(set(coded.loc[coded.cohort.eq('construction'),'Incident ID'])),'Scenario evidence must reference reviewed construction incidents.')
    require(set(ch['Incident ID']).issubset(set(coded.loc[coded.cohort.eq('later'),'Incident ID'])),'Challenges must reference reviewed later incidents.')
    require(ch.judgment.isin(['supports','challenges','unclear']).all(),'Invalid later-case judgment.')
    require_urls(cl.evidence_url);require_urls(ch.evidence_url)
    require(sp.metric.isin(['response_documented','redress_documented','accountability_clear']).all(),'Unsupported signpost metric.')
    require(sp.direction.isin(['above','below']).all(),'Invalid signpost direction.')
    sp['threshold']=pd.to_numeric(sp.threshold,errors='coerce')
    require(sp.threshold.between(0,1).all(),'Signpost thresholds must be fractions from 0 to 1.')
    require(sp.groupby('scenario_id').size().between(2,4).all(),'Each scenario needs 2–4 signposts.')
    scenario_data=(sc,cl,sp,ch)

if scenario_data is not None:
    sc,cl,sp,ch=scenario_data
    ledger=sc.merge(cl.groupby('scenario_id').agg(evidence_claims=('claim_id','size'),distinct_construction_cases=('Incident ID','nunique')),on='scenario_id')
    save_table(ledger,'table_4A_scenario_evidence_ledger');save_table(cl,'scenario_claims');success('4A')
    metrics=[]
    definitions={'response_documented':('response','documented'),'redress_documented':('redress','documented'),'accountability_clear':('accountability_clarity','clear')}
    for cohort,g in coded.groupby('cohort'):
        for metric,(field,label) in definitions.items():
            metrics.append({'cohort':cohort,'metric':metric,'weighted_fraction':np.average(g[field].eq(label),weights=g.design_weight),'sample_n':len(g)})
    metrics=pd.DataFrame(metrics);sign_values=sp.merge(metrics,on='metric',how='left')
    sign_values['review_triggered']=np.where(sign_values.direction.eq('above'),sign_values.weighted_fraction.gt(sign_values.threshold),sign_values.weighted_fraction.lt(sign_values.threshold))
    save_table(sign_values,'figure_4B_values')
    threshold_rows=[]
    for metric in ['accountability_clear','redress_documented']:
        grid=[.60,.70,.80] if metric=='accountability_clear' else [.15,.25,.35]
        for threshold in grid:
            for row in metrics[metrics.metric.eq(metric)].itertuples():
                threshold_rows.append({'metric':metric,'cohort':row.cohort,'threshold':threshold,'weighted_fraction':row.weighted_fraction,'above':row.weighted_fraction>threshold,'below':row.weighted_fraction<threshold,'interpretation':'illustrative threshold sensitivity; not estimated or validated'})
    save_table(pd.DataFrame(threshold_rows),'signpost_threshold_sensitivity')
    p=metrics.pivot(index='metric',columns='cohort',values='weighted_fraction')
    ax=(100*p).plot.bar(figsize=(9,4),rot=15);ax.set(ylabel='Weighted documented/clear evidence (%)',title='4B. Observed signposts; 2026 partial and subject to reporting lag')
    save_figure(ax.figure,'figure_4B_observed_signposts');success('4B')
    save_table(ch,'table_4C_later_case_challenge_log');success('4C')
    trace=pd.DataFrame([{'scenario_id':sid,'claims':len(cl[cl.scenario_id.eq(sid)]),'evidence_cases':cl.loc[cl.scenario_id.eq(sid),'Incident ID'].nunique(),'signposts':len(sp[sp.scenario_id.eq(sid)]),'later_cases':len(ch[ch.scenario_id.eq(sid)]),'challenging_cases':int(ch.loc[ch.scenario_id.eq(sid),'judgment'].eq('challenges').sum())} for sid in sc.scenario_id])
    save_table(trace,'figure_4D_values')
    ax=trace.set_index('scenario_id')[['claims','evidence_cases','signposts','later_cases','challenging_cases']].plot.bar(figsize=(10,4),rot=0)
    ax.set(ylabel='Count',title='4D. Traceability and challenge coverage; not a validity score');ax.legend(bbox_to_anchor=(1.02,1),loc='upper left')
    save_figure(ax.figure,'figure_4D_traceability');success('4D')

expected=['1A','1B','1C','1D','2A','2B','2C','2D','3A','3B','3C','3D','4A','4B','4C','4D']
report=pd.DataFrame([{'exhibit':k,'status':status.get(k,'PENDING')} for k in expected]);save_table(report,'exhibit_status')
packages={p:importlib.metadata.version(p) for p in ['pandas','numpy','matplotlib','scikit-learn','openpyxl']}
provenance={'source_filename':source.name,'source_sha256':sha256,'seed':SEED,'bootstrap_replicates':BOOTSTRAPS,'python':platform.python_version(),'packages':packages,'counts':{'incidents':len(inc),'reports':len(rep),'entities':len(ent),'construction':len(construction),'later':len(later)},'review_file_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in REVIEW_DIR.glob('*.csv')} if REVIEW_DIR.exists() else {},'coding_provenance':'Shared AI-assisted draft label sets, reported team verification and adjudication; agreement is not independent-human reliability.','limitations':['Media-selected archive; not population incidence.','Weights address the designed review sample only.','Intervals omit media selection and coding uncertainty.','2026 is incomplete and classification lag is substantial.','Scenario traceability does not validate a forecast.']}
p=out/'provenance.json';p.write_text(json.dumps(provenance,indent=2));manifest.append(p)
manifest=list(dict.fromkeys(p for p in manifest if p.name != 'output_manifest.csv'))
files=pd.DataFrame([{'filename':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in manifest]);save_table(files,'output_manifest')
archive=base/f'project11_final_results_{run_id}.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in manifest:z.write(path,arcname=path.name)
print('Results ZIP:',archive)
print('Generated exhibits:',sum(v=='GENERATED' for v in status.values()),'/16. Pending exhibits require genuine human evidence.')
