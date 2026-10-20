#!/usr/bin/env python3
"""Additional analyses from shipped timelines and CSVs. Preserves earlier robustness keys."""
from pathlib import Path
import collections, csv, gzip, json
import numpy as np

ART = Path(__file__).resolve().parents[1]
RES = ART / 'results'
SEED, B = 20261011, 2000

def rows(name):
    with (RES / name).open() as f:
        return list(csv.DictReader(f))

def form(c):
    return 'command' if c['kind'] != 'path' else 'link' if c['sub'] == 'link' else 'code_span'

def repo_form(cons, breaks, removals, repos):
    lookup = {(c['repo'], c['file'], c['key']): c for c in cons}
    out = {}
    for kind in ('insync', 'open'):
        counts = collections.defaultdict(lambda: np.zeros((2, 2)))
        for e in breaks + (removals if kind == 'insync' else []):
            if e['born_valid'] != '1' or ('type' in e and e['type'] != 'sync_removal'):
                continue
            c = lookup[e['repo'], e['file'], e['key']]
            j = 0 if e['is_ctx'] == '1' else 1
            key = (e['repo'], form(c))
            counts[key][j, 1] += 1
            counts[key][j, 0] += int(e.get('type') == 'sync_removal' if kind == 'insync' else e['end'] == 'open')
        terms = {r: np.zeros(2) for r in repos}
        matched = []
        for (repo, f), a in sorted(counts.items()):
            (yc, nc), (yr, nr) = a
            if nc and nr:
                w = nc * nr / (nc + nr)
                diff = yr / nr - yc / nc
                if kind == 'open':
                    diff = -diff
                terms[repo] += [w * diff, w]
                matched.append({'repo': repo, 'form': f, 'context_yes': int(yc), 'context_n': int(nc),
                                'readme_yes': int(yr), 'readme_n': int(nr), 'weight': w, 'difference': diff})
        arr = np.array([terms[r] for r in repos])
        total = arr.sum(axis=0)
        rng = np.random.default_rng(SEED + (kind == 'open'))
        sums = np.array([arr[rng.integers(0, len(arr), len(arr))].sum(axis=0) for _ in range(B)])
        vals = sums[sums[:, 1] > 0, 0] / sums[sums[:, 1] > 0, 1]
        out[kind] = {'est': total[0] / total[1], 'ci': np.percentile(vals, [2.5, 97.5]).tolist(),
                     'matched_strata': len(matched), 'matched_repositories': int(sum(a[1] > 0 for a in terms.values())),
                     'strata': matched, 'bootstrap_resamples': B, 'seed': SEED + (kind == 'open'),
                     'scope': 'Only repository-by-form strata containing both artefacts contribute.'}
    return out

def presence_spells():
    agg = {k: {'all_spells': 0, 'anchored_spells': 0, 'breaks': 0, 'in_sync': 0, 'exposure_days': 0., 'readded_spells': 0} for k in ('context', 'readme')}
    for path in sorted((ART / 'data/mined').glob('*.json.gz')):
        with gzip.open(path, 'rt') as f:
            d = json.load(f)
        snaps = d['snaps']
        rank = {s[0]: i for i, s in enumerate(snaps)}
        ts = {s[0]: s[1] for s in snaps}
        events = collections.defaultdict(list)
        for e in d['events']:
            events[e['file'], e['key']].append(e)
        for name, fd in d['files'].items():
            a = agg['readme' if name == 'README.md' else 'context']
            for key, c in fd['constraints'].items():
                groups = []
                for obs in c['obs']:
                    if not groups or rank[obs[0]] != rank[groups[-1][-1][0]] + 1:
                        groups.append([])
                    groups[-1].append(obs)
                a['all_spells'] += len(groups)
                a['readded_spells'] += max(0, len(groups) - 1)
                for group in groups:
                    if group[0][1] <= 0:
                        continue
                    a['anchored_spells'] += 1
                    for (s0, v0), (s1, v1) in zip(group, group[1:]):
                        if v0 > 0:
                            a['exposure_days'] += max(0, ts[s1] - ts[s0]) / 86400
                            a['breaks'] += int(v1 == 0)
                    endrank = rank[group[-1][0]] + 1
                    if endrank < len(snaps):
                        end = snaps[endrank][0]
                        a['in_sync'] += sum(e['type'] == 'sync_removal' and group[-1][0] < e['idx'] <= end
                                            for e in events[name, key])
    for a in agg.values():
        a['exposure_years'] = a['exposure_days'] / 365.25
        a['break_rate_per_100_years'] = 100 * a['breaks'] / a['exposure_years']
        a['invalidation_rate_per_100_years'] = 100 * (a['breaks'] + a['in_sync']) / a['exposure_years']
    return {'definition': 'A new spell starts after an evaluated snapshot in which the key is absent. Each spell is anchored only if valid at re-entry. As in the original estimator, exposure uses valid-start intervals between consecutive observations of the key, now restricted to one spell; no absent gap is bridged. Events hidden between sampled snapshots remain unobserved.',
            **agg}

def main():
    cons, brk, rem, rp = [rows(n + '.csv') for n in ('constraints', 'breaks', 'removals', 'repos')]
    repos = sorted(r['repo'] for r in rp)
    p = RES / 'robustness.json'
    out = json.loads(p.read_text())
    out['repository_by_form'] = repo_form(cons, brk, rem, repos)
    out['presence_spells'] = presence_spells()
    c = collections.Counter(b['repo'] for b in brk if b['is_ctx'] == b['born_valid'] == '1')
    values = [c[r] for r in repos]
    out['alarm_burden'] = {'definition': 'One alert per anchored context break episode across each observed repository window, including zeros. No deduplication by commit and no inferred false-alarm rate.',
                           'repositories': len(repos), 'alerts': sum(values), 'mean': float(np.mean(values)),
                           'median': float(np.median(values)), 'iqr': np.percentile(values, [25,75]).tolist(), 'max': max(values)}
    bytype = {}
    for ft in ('AGENTS.md', 'CLAUDE.md'):
        cs = [c for c in cons if c['ftype'] == ft and c['born_valid'] == '1']
        keys = {(c['repo'], c['file'], c['key']) for c in cs}
        b = sum(int(c['n_breaks']) for c in cs)
        s = sum(r['type'] == 'sync_removal' and (r['repo'], r['file'], r['key']) in keys for r in rem)
        ex = sum(float(c['exposure_days']) for c in cs) / 365.25
        bytype[ft] = {'anchored_lifetimes': len(cs), 'breaks': b, 'in_sync': s, 'exposure_years': ex,
                      'break_rate': 100*b/ex, 'invalidation_rate': 100*(b+s)/ex, 'in_sync_share': s/(s+b)}
    out['dynamics_by_file_type'] = bytype
    design = {}
    for sheet in ('B_breaks', 'S_insync'):
        with (ART/'labelling/key'/(sheet+'.csv')).open() as f:
            keyrows = list(csv.DictReader(f))
        vs, ns = [], {}
        for art in ('context', 'readme'):
            ss = [r for r in keyrows if r['artefact'] == art]
            n = collections.Counter(r['stratum'] for r in ss)
            pop = {r['stratum']: int(r['stratum_population']) for r in ss}
            total = sum(pop.values())
            v = sum((pop[s]/total)**2/n[s] for s in n)
            vs.append(v)
            ns[art] = 1/v
        design[sheet] = {'effective_n': ns, 'detectable_gap_80pct_two_sided_5pct_conservative':
                         (1.959963984540054+0.8416212335729143)*(.25*sum(vs))**.5}
    design['definition'] = 'Normal planning approximation at maximum Bernoulli variance 0.25, known stratum weights, independent items, complete ratings and no unsure exclusions. Clustering would reduce effective sample sizes. Not an equivalence test.'
    (RES/'precision_design.json').write_text(json.dumps(design, indent=1)+'\n')

    # Remove a stale private review pointer without treating AI spot-check counts as evidence.
    out['internal_ai_spot_check']['source'] = 'Aggregate counts from an internal AI-assisted development review. Raters were AI systems, not humans. Item-level labels are unavailable. Not used as evidence in the paper.'
    p.write_text(json.dumps(out, indent=1)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k in ('presence_spells','alarm_burden','dynamics_by_file_type')},indent=1))

if __name__ == '__main__':
    main()
