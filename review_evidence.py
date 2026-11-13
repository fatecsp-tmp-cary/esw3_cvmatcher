import os,json,sys,hashlib,time
from pathlib import Path
from datetime import date,datetime,UTC
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'scripts/evaluation')]
OUT=Path(os.environ['CVMATCHER_REVIEW_OUTPUT']);OUT.mkdir(exist_ok=True)
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
from evaluate import evaluate,validate_fixture
from src.matching.ranking import SimilarityCalibration
from src.matching.semantic import ExperienceScore,semantic_score
protocol={'calibration_grid_zero':[i/100 for i in range(91)],'full_anchor':1.0,'classification_cutoff':50,'selection':'maximize mean PT/EN accuracy, then minimum language accuracy, then closeness to previous zero=0.5','extraction':'unchanged pinned model, threshold and contextual classification','heldout_tuning':False,'created_at':datetime.now(UTC).isoformat()}
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
import torch
torch.set_num_threads(1)
from src.embeddings.encoder import LocalEmbeddingEncoder
from src.embeddings.config import EmbeddingConfig
from src.extraction.gliner import GlinerExtractor,EXTRACTION_VERSION
from src.extraction.classification import annotate_spans
fixture_path=Path(os.environ['CVMATCHER_REVIEW_GOLD']);fixture=json.loads(fixture_path.read_text());cases=validate_fixture(fixture)
partition=fixture['provenance']['partition']
print('Loading pinned offline models',flush=True)
extractor=GlinerExtractor(os.environ['CVMATCHER_REVIEW_MODEL'])
encoder=LocalEmbeddingEncoder(EmbeddingConfig())
def score(raw,cal):
 vals=[cal.score(c) for c in raw['cosines']];n=raw['experience_count']
 return semantic_score(tuple(ExperienceScore(v,date(2020,1,1),None) for v in vals[:n]),tuple(vals[n:])) if vals else 0.0
def run_phase(phase,cal):
 predictions=[];raws=[];ids=set(partition[phase+'_ids'])
 for case in cases:
  if case['id'] not in ids:continue
  job=case['job'];full=job['title']+'\n'+job['description'];offset=len(job['title'])+1
  spans=annotate_spans(full,[s.serialize(full) for s in extractor.extract(full)])
  req=[]
  for span in spans:
   if span['start']<offset:continue
   a,b=span['start']-offset,span['end']-offset
   req.append({'start':a,'end':b,'text':job['description'][a:b],'requirement_class':span['requirement_class']})
  req=list({(r['start'],r['end']):r for r in req}.values())
  ex=[x['title']+'\n'+x['description'] for x in case['candidate']['experiences']];ed=[x['title'] for x in case['candidate']['education']]
  cos=[]
  if ex+ed:
   j=encoder.encode_jobs([full])[0]
   cos=[sum(a*b for a,b in zip(v,j,strict=True)) for v in encoder.encode_queries(ex+ed)]
  raw={'id':case['id'],'cosines':cos,'experience_count':len(ex)};raws.append(raw)
  predictions.append({'id':case['id'],'requirements':req,'role_score':score(raw,cal)})
  print(phase,case['id'],'completed',flush=True)
 return predictions,raws
preds,raws=run_phase('calibration',SimilarityCalibration())
(OUT/'calibration-raw.json').write_text(json.dumps(raws,indent=2)+'\n')
cal_cases={c['id']:c for c in cases if c['id'] in set(partition['calibration_ids'])}
trials=[]
for zero in protocol['calibration_grid_zero']:
 cal=SimilarityCalibration(zero=zero,full=1.0)
 accuracy={}
 for lang in ['pt','en']:
  group=[r for r in raws if cal_cases[r['id']]['language']==lang]
  accuracy[lang]=sum((score(r,cal)>=50)==(cal_cases[r['id']]['expected']['role_relation']=='relevant') for r in group)/len(group)
 trials.append({'zero':zero,'accuracy':accuracy,'objective':[(accuracy['pt']+accuracy['en'])/2,min(accuracy.values()),-abs(zero-.5)]})
best=max(trials,key=lambda x:x['objective']);params={'zero':best['zero'],'full':1.0,'cutoff':50}
version='human-calibration-v1-'+hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()[:12]
cal=SimilarityCalibration(version=version,zero=best['zero'],full=1.0)
freeze={'version':version,**params,'frozen_at':datetime.now(UTC).isoformat(),'gold_sha256':hashlib.sha256(fixture_path.read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'embedding_model':encoder.model_version,'extraction_version':EXTRACTION_VERSION,'calibration_ids':partition['calibration_ids'],'heldout_ids':partition['heldout_ids'],'release_quality_approved':False,'hard_exclusions_enabled':False}
(OUT/'frozen-calibration.json').write_text(json.dumps(freeze,indent=2)+'\n')
(OUT/'calibration-search.json').write_text(json.dumps(trials,indent=2)+'\n')
for pred,raw in zip(preds,raws,strict=True):pred['role_score']=score(raw,cal)
def save_phase(phase,predictions):
 doc={'schema_version':'1.0','predictions':predictions}
 report=evaluate(fixture,doc,case_ids=partition[phase+'_ids']);report['measurement']=freeze
 for suffix,value in [('predictions',doc),('report',report)]:
  (OUT/f'{phase}-{suffix}.json').write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
 print(phase,'report saved',flush=True)
save_phase('calibration',preds)
print('Configuration frozen; beginning held-out inference without further tuning',flush=True)
heldout,_=run_phase('heldout',cal);save_phase('heldout',heldout)
print('DONE',flush=True)
