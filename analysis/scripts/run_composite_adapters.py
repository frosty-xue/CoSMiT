"""Execute unchanged full counterparts on fixed public samples; no human labels."""
import argparse,ast,hashlib,inspect,json,os,sys,traceback
from pathlib import Path
os.environ.setdefault('CUDA_VISIBLE_DEVICES','')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--case');parser.add_argument('--output',required=True)
 args=parser.parse_args();root=Path(__file__).resolve().parent
 manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
 selected=[m for m in manifest['cases'] if not args.case or m['candidate_id']==args.case]
 if not selected:raise ValueError('Unknown candidate')
 import numpy as np
 import torch
 import tensorflow as tf
 from public_oracle import value_test
 result={'versions':{'python':sys.version,'numpy':np.__version__,'torch':torch.__version__,'tensorflow':tf.__version__},'scope':'fixed public samples; controlled adaptation; not human labels','records':[],'coverage':{}}
 def encode(x):
  if isinstance(x,torch.Tensor):x=np.asarray(x.detach().cpu().numpy())
  elif isinstance(x,tf.Tensor):x=np.asarray(x.numpy())
  if isinstance(x,np.ndarray):
   # Preserve complex values without lossy casts.
   return {'kind':'array','dtype':str(x.dtype),'shape':list(x.shape),'values':x.real.tolist() if np.iscomplexobj(x) else x.tolist(),**({'imag':x.imag.tolist()} if np.iscomplexobj(x) else {})}
  if isinstance(x,(list,tuple)):return [encode(y) for y in x]
  if isinstance(x,dict):return {k:encode(v) for k,v in x.items()}
  if isinstance(x,np.generic):return x.item()
  if isinstance(x,(torch.dtype,tf.dtypes.DType)):return {'kind':'framework_dtype','value':str(x)}
  return x
 def convert(x,target):
  if isinstance(x,torch.Tensor):x=np.asarray(x.detach().cpu().numpy())
  elif isinstance(x,tf.Tensor):x=np.asarray(x.numpy())
  if isinstance(x,np.ndarray):return tf.constant(x.copy()) if target=='tensorflow' else torch.tensor(x.copy())
  if isinstance(x,list):return [convert(y,target) for y in x]
  if isinstance(x,tuple):return tuple(convert(y,target) for y in x)
  if isinstance(x,dict):return {k:convert(v,target) for k,v in x.items()}
  return x
 def leaves(x):
  if isinstance(x,(tuple,list)):return [a for y in x for a in leaves(y)]
  if isinstance(x,torch.Tensor):x=x.detach().cpu().numpy()
  elif isinstance(x,tf.Tensor):x=x.numpy()
  return [np.asarray(x)]
 def call(fn,bound,filename):
  seen=set()
  def trace(frame,event,arg):
   if frame.f_code.co_filename==filename and event=='line':seen.add(frame.f_lineno)
   return trace
  previous=sys.gettrace();sys.settrace(trace)
  try:return fn(*bound.args,**bound.kwargs),None,sorted(seen)
  except Exception as e:return None,{'type':type(e).__name__,'message':str(e)},sorted(seen)
  finally:sys.settrace(previous)
 # Adapter checks: scalar tensor conversion must not turn tensors into NumPy scalars.
 assert tuple(convert(tf.constant(2.,dtype=tf.float32),'pytorch').shape)==()
 assert convert(tf.constant(2.,dtype=tf.float32),'pytorch').dtype==torch.float32
 assert tuple(convert(torch.tensor(2.,dtype=torch.float64),'tensorflow').shape)==()
 assert convert(torch.tensor(2.,dtype=torch.float64),'tensorflow').dtype==tf.float64
 for candidate in [np.array([1.],dtype=np.float32),np.array(1.,dtype=np.float64)]:
  try:value_test(ret_np_flat=[candidate],ret_np_from_gt_flat=[np.array(1.,dtype=np.float32)],backend='check',ground_truth_backend='check')
  except AssertionError:pass
  else:raise AssertionError('Oracle failed to detect shape/dtype difference')
 result['adapter_checks']={'scalar_shape_dtype_checks':4,'oracle_negative_controls':2,'status':'passed'}
 allowed_calls={'np.random.randn','np.random.randint','torch.tensor','tf.constant'}
 for m in selected:
  cid=m['candidate_id'];folder=root/'cases'/cid;raw=(folder/'counterpart.json').read_bytes()
  if hashlib.sha256(raw).hexdigest()!=m['original_json_sha256']:raise ValueError('Changed public record: '+cid)
  c=json.loads(raw);functions={};filenames={};all_lines={};covered={'source':set(),'target':set()}
  for role,fw in [('source',m['source_framework']),('target',m['target_framework'])]:
   code=(folder/f'{role}-operation.py').read_text(encoding='utf-8')
   if code!=c['counterparts'][fw]:raise ValueError('Changed operation')
   filename=str(folder/f'{role}-operation.py');ns={'torch':torch,'tf':tf,'np':np};exec(compile(code,filename,'exec'),ns)
   functions[role]=ns[fw+'_call'];filenames[role]=filename
   all_lines[role]=sorted({n.lineno for n in ast.walk(ast.parse(code)) if isinstance(n,ast.stmt) and not isinstance(n,ast.FunctionDef)})
  for sample_index,sample in enumerate(c['sample_inputs']):
   rec={'candidate_id':cid,'sample_index':sample_index,'seed':1234,'source_lines':[],'target_lines':[]}
   result['records'].append(rec)
   try:
    tree=ast.parse(sample)
    if any(isinstance(n,(ast.Import,ast.ImportFrom,ast.With,ast.FunctionDef,ast.ClassDef)) for n in ast.walk(tree)):raise ValueError('Unsupported sample statement')
    for n in ast.walk(tree):
     if isinstance(n,ast.Call) and ast.unparse(n.func) not in allowed_calls:raise ValueError('Unreviewed sample call: '+ast.unparse(n.func))
    np.random.seed(1234);torch.manual_seed(1234);tf.random.set_seed(1234)
    ns={'np':np,'torch':torch,'tf':tf};exec(compile(sample,'public-sample','exec'),ns)
    kwargs={k:ns[k] for k in c['inputs'] if k in ns}
    bound=inspect.signature(functions['source']).bind(**kwargs);bound.apply_defaults()
    rec['arguments']=encode(dict(bound.arguments))
   except Exception as e:rec.update(status='input_or_binding_error',error={'type':type(e).__name__,'message':str(e)});continue
   src,err,lines=call(functions['source'],bound,filenames['source']);rec['source_lines']=lines;covered['source'].update(lines)
   if err:rec.update(status='source_error',source_error=err);continue
   rec['source_output']=encode(src)
   try:
    converted_args=convert(bound.args,m['target_framework']);converted_kwargs=convert(bound.kwargs,m['target_framework'])
    target_bound=inspect.signature(functions['target']).bind(*converted_args,**converted_kwargs)
   except Exception as e:rec.update(status='target_conversion_or_binding_error',error={'type':type(e).__name__,'message':str(e)});continue
   target,err,lines=call(functions['target'],target_bound,filenames['target']);rec['target_lines']=lines;covered['target'].update(lines)
   if err:rec.update(status='target_error',target_error=err);continue
   rec['target_output']=encode(target)
   try:
    value_test(ret_np_flat=leaves(target),ret_np_from_gt_flat=leaves(src),backend=m['target_framework'],ground_truth_backend=m['source_framework'],**m['oracle_settings'])
    rec['status']='oracle_pass'
   except Exception as e:rec.update(status='oracle_fail',oracle_error={'type':type(e).__name__,'message':str(e)})
  result['coverage'][cid]={role:{'executed_lines':sorted(covered[role]),'unexecuted_statement_lines':sorted(set(all_lines[role])-covered[role])} for role in ['source','target']}
  counts={s:sum(r['candidate_id']==cid and r['status']==s for r in result['records']) for s in sorted({r['status'] for r in result['records'] if r['candidate_id']==cid})}
  print(cid,json.dumps(counts),flush=True)
 dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
 # NaN/Infinity retained as explicit strings in a strict JSON record.
 def strict(x):
  if isinstance(x,float) and not np.isfinite(x):return 'NaN' if np.isnan(x) else 'Infinity' if x>0 else '-Infinity'
  if isinstance(x,list):return [strict(y) for y in x]
  if isinstance(x,dict):return {k:strict(y) for k,y in x.items()}
  return x
 dest.write_text(json.dumps(strict(result),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
