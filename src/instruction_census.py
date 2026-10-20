from pathlib import Path, PurePosixPath
import concurrent.futures, gzip, json, os, re, subprocess
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--clones', type=Path, required=True, help='Local clones at the pinned mined commits; no network fetches')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
clones=args.clones
allowed={'AGENTS.md','CLAUDE.md','.cursorrules','copilot-instructions.md'}
roots={'AGENTS.md','CLAUDE.md','.claude/CLAUDE.md','.cursorrules','.github/copilot-instructions.md'}
rule_dirs=('.cursor/rules/','.claude/rules/','.github/instructions/','.windsurf/rules/')
def census(path):
 with gzip.open(path,'rt') as f:d=json.load(f)
 repo=d['repo']; p=subprocess.run(['git','-C',str(clones/repo.replace('/','__')),'ls-tree','-rz','--name-only',d['head']],capture_output=True,timeout=30,env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0'})
 if p.returncode: return {'repo':repo,'status':'unavailable','error':p.stderr.decode(errors='replace')[:120]}
 paths=set(p.stdout.decode().strip('\0').split('\0'))
 nested=sorted(x for x in paths if PurePosixPath(x).name in allowed and x not in roots)
 rules=sorted(x for x in paths if x.startswith(rule_dirs))
 imports=[]
 for name,fd in d['files'].items():
  if name=='README.md':continue
  text=fd.get('head_text') or ''
  for token in re.findall(r'(?<![\w.])@([^\s`<>"\']+)',text):
   candidate=(PurePosixPath(name).parent / token.rstrip('.,;:)')).as_posix()
   candidate=os.path.normpath(candidate)
   if candidate in paths and candidate.lower().endswith(('.md','.mdx','.txt','.rst','.adoc')):
    imports.append({'from':name,'target':candidate})
 return {'repo':repo,'head':d['head'],'status':'complete','nested':nested,'rule_files':rules,'import_candidates':imports}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 data=list(ex.map(census,sorted((root/'data/mined').glob('*.json.gz'))))
out={'definition':'Pinned-head local git trees. Nested: studied basename outside the predefined root locations. Rules: tracked files under .cursor/rules, .claude/rules, .github/instructions or .windsurf/rules. Imports: @path tokens in shipped root context text resolving to tracked .md/.mdx/.txt/.rst/.adoc files relative to that root file. Import candidates are syntactic, not human-confirmed directives; other import syntaxes are unmeasured.',
     'repositories':len(data),'complete':sum(r['status']=='complete' for r in data),'counts':{k:sum(bool(r.get(k)) for r in data) for k in ('nested','rule_files','import_candidates')},'rows':data}
out['counts']['any']=sum(any(r.get(k) for k in ('nested','rule_files','import_candidates')) for r in data)
(root/'results/instruction_coverage.json').write_text(json.dumps(out,indent=1)+'\n')
print({k:v for k,v in out.items() if k!='rows'})
