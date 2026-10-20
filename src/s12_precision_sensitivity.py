#!/usr/bin/env python3
"""Precision sensitivity and D3 gate. Never supplies or modifies human labels.

Uniform independent thinning within artefact/event class, fixed exposure, paired
repository bootstrap. This propagates precision, not recall or correlated errors.

Rename sensitivity: break counts are additionally thinned by (1 - share of true breaks that are moves or renames), taken from Sheet B column
break_cause (results/human_validation.json, key B_cause). "rename only" keeps raw break counts, "precision and rename" thins break counts by
precision x (1 - rename share) and in-sync counts by their precision point estimate.
Writes results/precision_sensitivity.json and ../manuscript/sensitivity_numbers.tex (one macro per number; PENDING while inputs are incomplete).
"""
from pathlib import Path
import csv, itertools, json, os
import numpy as np

ART = Path(__file__).resolve().parents[1]
RES = ART / 'results'
B, SEED = 2000, 20261013
OUT_TEX = Path(os.environ.get('S12_TEX') or ART.parent / 'manuscript' / 'sensitivity_numbers.tex')
POS = ['estimate', 'lower', 'upper']
NAMES = ['break_ratio_pooled', 'break_ratio_entry_observed', 'insync_gap_readme_minus_context']

def values(st):
    return [st['weighted_share'], *st['ci']]

def decision(h):
    if not h.get('complete'):
        return {'status': 'unevaluated', 'reason': 'Human labels, adjudications and author verification are incomplete.'}
    checks = {}
    for sheet in ('B_breaks', 'S_insync'):
        checks[sheet + '_kappa_at_least_0.6'] = h[sheet]['cohen_kappa'] >= .6
        for art in ('context', 'readme'):
            x = h[sheet][art]
            checks[sheet + '_' + art + '_precision_at_least_0.75'] = x['weighted_share'] >= .75
            checks[sheet + '_' + art + '_lower_bound_at_least_0.50'] = x['ci'][0] >= .5
        lo, hi = h[sheet]['difference_context_minus_readme']['ci']
        checks[sheet + '_difference_interval_contains_zero'] = lo <= 0 <= hi
    return {'status': 'criteria_met' if all(checks.values()) else 'criteria_failed', 'checks': checks,
            'interpretation': 'D3 difference criterion interpreted as an interval containing zero, consistent with PLAN section 5. This is not an equivalence test or an author submission decision.'}

def expected(counts, exposure, precision):
    # cols: context breaks, readme breaks, context sync, readme sync
    v = counts.sum(axis=0) * np.array(precision)
    ex = exposure.sum(axis=0)
    ratio = (v[0]/ex[0]) / (v[1]/ex[1]) if ex.min()>0 and v[1]>0 else None
    gap = v[3]/(v[1]+v[3]) - v[2]/(v[0]+v[2]) if min(v[1]+v[3], v[0]+v[2])>0 else None
    return ratio, gap

def run(h):
    out = {'status': 'pending', 'source': 'results/human_validation.json', 'd3': decision(h),
           'definition': __doc__, 'seed': SEED, 'resamples': B}
    if not h.get('complete'):
        return out
    with (RES/'constraints.csv').open() as f: cons=list(csv.DictReader(f))
    with (RES/'removals.csv').open() as f: rem=list(csv.DictReader(f))
    with (RES/'repos.csv').open() as f: repos=sorted(r['repo'] for r in csv.DictReader(f))
    ix={r:i for i,r in enumerate(repos)}
    counts=np.zeros((len(repos),4),dtype=int)
    entry=np.zeros_like(counts)
    exposure=np.zeros((len(repos),2));entry_ex=np.zeros_like(exposure)
    lookup={(c['repo'],c['file'],c['key']):c for c in cons}
    for c in cons:
        if c['born_valid']!='1':continue
        i=ix[c['repo']];j=0 if c['is_ctx']=='1' else 1
        counts[i,j]+=int(c['n_breaks']);exposure[i,j]+=float(c['exposure_days'])/365.25
        if c['left_truncated']=='0':
            entry[i,j]+=int(c['n_breaks']);entry_ex[i,j]+=float(c['exposure_days'])/365.25
    for e in rem:
        if e['born_valid']!='1' or e['type']!='sync_removal':continue
        i=ix[e['repo']];j=2 if e['is_ctx']=='1' else 3
        counts[i,j]+=1
        if lookup[e['repo'],e['file'],e['key']]['left_truncated']=='0':entry[i,j]+=1
    options=[values(h[s][a]) for s,a in [('B_breaks','context'),('B_breaks','readme'),('S_insync','context'),('S_insync','readme')]]
    raw_ratio,raw_gap=expected(counts,exposure,[1]*4)
    raw_entry,_=expected(entry,entry_ex,[1]*4)
    out['unthinned']={'break_ratio_pooled':raw_ratio,'break_ratio_entry_observed':raw_entry,'insync_gap_readme_minus_context':raw_gap}
    def evaluate(precision, positions):
        rng=np.random.default_rng(SEED) # common random seed across scenarios
        ratio,gap=expected(counts,exposure,precision)
        eratio,_=expected(entry,entry_ex,precision)
        samples=[[],[],[]]
        for _ in range(B):
            idx=rng.integers(0,len(repos),len(repos))
            kept=rng.binomial(counts,precision)
            ekeep=rng.binomial(entry,precision)
            rr,gg=expected(kept[idx],exposure[idx],[1]*4)
            ee,_=expected(ekeep[idx],entry_ex[idx],[1]*4)
            for vals,v in zip(samples,[rr,ee,gg]):
                if v is not None and np.isfinite(v):vals.append(v)
        scenario={'positions':positions,'retention_probabilities':list(precision)}
        for name,v,bs,null,base in zip(NAMES,[ratio,eratio,gap],samples,[1,1,0],[raw_ratio,raw_entry,raw_gap]):
            scenario[name]={'est':v,'ci':np.percentile(bs,[2.5,97.5]).tolist() if bs else None,
                            'sign_flips':v is not None and (v-null)*(base-null)<0,'valid_resamples':len(bs)}
        return scenario
    scenarios=[]
    # Endpoints are a rectangular sensitivity region, not a joint confidence region.
    for pos in itertools.product(range(3),repeat=4):
        precision=[options[j][k] for j,k in enumerate(pos)]
        scenarios.append(evaluate(precision,dict(zip(['break_context','break_readme','sync_context','sync_readme'],[POS[x] for x in pos]))))
    out.update(status='complete',scenarios=scenarios,
               withdraw_contrasts={k:any(s[k]['sign_flips'] for s in scenarios) for k in out['unthinned']})
    # ---- rename sensitivity (needs Sheet B break_cause)
    bc=h.get('B_cause',{})
    if bc.get('status')!='complete':
        out['rename']={'status':'pending','reason':'Sheet B break_cause is missing or unadjudicated.'}
        return out
    rshare=[[bc[a]['moved_renamed']['share'],*bc[a]['moved_renamed']['ci']] for a in ('context','readme')]
    rename_only,combined=[],[]
    for pos in itertools.product(range(3),repeat=2):
        r=[rshare[0][pos[0]],rshare[1][pos[1]]]
        where={'rename_share_context':POS[pos[0]],'rename_share_readme':POS[pos[1]]}
        rename_only.append(evaluate([1-r[0],1-r[1],1,1],where))
        combined.append(evaluate([options[0][0]*(1-r[0]),options[1][0]*(1-r[1]),options[2][0],options[3][0]],where))
    out['rename']={'status':'complete','rename_share':{'context':bc['context']['moved_renamed'],'readme':bc['readme']['moved_renamed']},
                   'rename_only_scenarios':rename_only,'precision_and_rename_scenarios':combined,
                   'withdraw_contrasts_rename_only':{k:any(s[k]['sign_flips'] for s in rename_only) for k in NAMES},
                   'withdraw_contrasts_precision_and_rename':{k:any(s[k]['sign_flips'] for s in combined) for k in NAMES}}
    return out

def summarize(scs, name):
    """Point scenario (all positions at the estimate) plus the envelope over the whole rectangular region."""
    pt=next(x for x in scs if all(v=='estimate' for v in x['positions'].values()))[name]
    los=[x[name]['ci'][0] for x in scs if x[name]['ci']]; his=[x[name]['ci'][1] for x in scs if x[name]['ci']]
    return {'est':pt['est'],'ci':pt['ci'],'lo':min(los) if los else None,'hi':max(his) if his else None,'flip':any(x[name]['sign_flips'] for x in scs)}

def write_tex(out):
    macros={}
    def put(prefix,scs):
        for name,suf,scale,d in (('break_ratio_pooled','Ratio',1,2),('break_ratio_entry_observed','RatioEntry',1,2),('insync_gap_readme_minus_context','Gap',100,1)):
            sm=summarize(scs,name); f=lambda v: 'n/a' if v is None else f'{scale*v:.{d}f}'
            macros[prefix+suf]=f(sm['est']); macros[prefix+suf+'CI']='n/a' if not sm['ci'] else f"{f(sm['ci'][0])} to {f(sm['ci'][1])}"
            macros[prefix+suf+'Env']='n/a' if sm['lo'] is None else f"{f(sm['lo'])} to {f(sm['hi'])}"
            macros[prefix+suf+'Flip']='yes' if sm['flip'] else 'no'
    names=[]
    for prefix in ('sPrec','sRen','sComb'):
        for suf in ('Ratio','RatioEntry','Gap'):
            names += [prefix+suf+x for x in ('','CI','Env','Flip')]
    names += ['sRawRatio','sRawRatioEntry','sRawGap']
    if out.get('status')=='complete':
        put('sPrec',out['scenarios'])
        u=out['unthinned']; macros.update(sRawRatio=f"{u['break_ratio_pooled']:.2f}",sRawRatioEntry=f"{u['break_ratio_entry_observed']:.2f}",sRawGap=f"{100*u['insync_gap_readme_minus_context']:.1f}")
        if out['rename']['status']=='complete':
            put('sRen',out['rename']['rename_only_scenarios']); put('sComb',out['rename']['precision_and_rename_scenarios'])
    with OUT_TEX.open('w') as f:
        f.write('% Generated by the precision sensitivity script. Do not edit by hand. Input after human_numbers.tex.\n')
        f.write('\\providecommand{\\PENDING}{\\textcolor{red}{\\textbf{[PENDING]}}}\n')
        for n in names: f.write(f"\\newcommand{{\\{n}}}{{{macros.get(n,'\\PENDING')}}}\n")

if __name__ == '__main__':
    h=json.loads((RES/'human_validation.json').read_text())
    out=run(h)
    (RES/'precision_sensitivity.json').write_text(json.dumps(out, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else x) + '\n')
    write_tex(out)
    print(out['status'],out['d3']['status'],out.get('rename',{}).get('status'))