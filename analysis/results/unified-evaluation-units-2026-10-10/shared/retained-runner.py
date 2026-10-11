"""Retain upstream test/helper bodies, including every assertion in those bodies.

Separate evidence layer from generated protocol continuations in batch.py.
"""
import argparse, ast, copy, hashlib, json, os, sys, textwrap, traceback
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
MODES=['original','observe','reinject','wrong-shape','wrong-value']


def plan():
    out=ROOT/'retained';out.mkdir(exist_ok=False)
    specs=[]
    for c in load(DATA/'candidates.json'):
        cid=c['case_id'];f=c['family'];pt=c['source']['framework']=='pytorch'
        if cid in ['E017','E021','E023']:
            specs.append({'case_id':cid,'status':'unresolved-source-obligation',
                          'reason':'selected PyTorch view tests require storage aliasing and mutation propagation; cross-framework value bridge cannot preserve or certify these obligations'})
            continue
        if int(cid[1:])<=16:
            file='pt_binary.py' if pt else 'tf_binary.py'
            cls='TestBinaryUfuncs' if pt else 'BinaryOpTest'
            methods=['assertEqualHelper','_test_reference_numerics'] if pt else ['_compareCpu']
            kind='complete-upstream-helper-bodies';entry='_test_reference_numerics' if pt else '_compareCpu';paths=[]
            params='frozen expansion input indices 0 and 16; replaces upstream sample generator, not original whole test setup'
        else:
            file,cls,methods,entry,paths={
                'E018':('tf_reshape.py','ReshapeTest',['_testReshape','_testBothReshape','testFloatBasic'],'testFloatBasic',['array_ops.reshape']),
                'E019':('pt_view.py','TestOldViewOps',['test_transposes'],'test_transposes',['METHOD:transpose']),
                'E020':('tf_transpose.py','TransposeTest',['testTranspose2DAuto'],'testTranspose2DAuto',['array_ops.transpose']),
                'E022':('tf_shape.py','ShapeOpsTest',['_compareSqueeze','_compareSqueezeAll','testSqueeze'],'testSqueeze',['array_ops.squeeze']),
                'E024':('tf_shape.py','ShapeOpsTest',['testExpandDimsDimType'],'testExpandDimsDimType',['array_ops.expand_dims']),
                'E025':('pt_tensor.py','TestTensorCreation',['test_cat2'],'test_cat2',['torch.cat']),
                'E026':('tf_concat.py','ConcatOpTest',['testConcatTuple'],'testConcatTuple',['array_ops.concat']),
                'E027':('pt_tensor.py','TestTensorCreation',['test_stack'],'test_stack',['torch.stack']),
                'E028':('tf_stack.py','StackOpTest',['randn','testSimple'],'testSimple',['array_ops_stack.stack']),
                'E029':('pt_torch.py','TestDevicePrecision',['test_clamp'],'test_clamp',['METHOD:clamp']),
                'E030':('tf_clip.py','ClipTest',['testClipByValue'],'testClipByValue',['clip_ops.clip_by_value']),
            }[cid]
            kind='complete-upstream-method-bodies';params='original method inputs; CPU eager; device/dtype parameter fixed where required; decorator variants excluded'
        text=(ROOT/'upstream'/file).read_text();tree=ast.parse(text)
        cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        nodes=[copy.deepcopy(n) for n in cl.body if isinstance(n,ast.FunctionDef) and n.name in methods]
        assert len(nodes)==len(methods)
        locations=[{'method':n.name,'start':n.lineno,'end':n.end_lineno,'decorators':[ast.unparse(d) for d in n.decorator_list]} for n in nodes]
        for n in nodes:n.decorator_list=[]
        base=ast.Module(body=[ast.ClassDef(name='Frozen',bases=[ast.Name(id='Harness',ctx=ast.Load())],keywords=[],body=nodes,decorator_list=[])],type_ignores=[])
        ast.fix_missing_locations(base)
        (out/(cid+'-source.py')).write_text(ast.unparse(base)+'\n',encoding='utf-8')
        class Rewrite(ast.NodeTransformer):
            def visit_Call(self,n):
                self.generic_visit(n)
                if ast.unparse(n.func) in paths:
                    n.func=ast.Name(id='_operation',ctx=ast.Load())
                elif isinstance(n.func,ast.Attribute) and 'METHOD:'+n.func.attr in paths:
                    n.args=[n.func.value]+n.args;n.func=ast.Name(id='_operation',ctx=ast.Load())
                return n
        target=ast.fix_missing_locations(Rewrite().visit(copy.deepcopy(base)))
        def asserts(t):return [ast.dump(n) for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert')]
        # Assertions containing the replaced operation necessarily differ only there.
        (out/(cid+'-target.py')).write_text(ast.unparse(target)+'\n',encoding='utf-8')
        specs.append({'case_id':cid,'status':'registered','file':'upstream/'+file,'class':cls,'methods':locations,
                      'entry':entry,'paths':paths,'kind':kind,'parameters':params,'source_framework':c['source']['framework'],
                      'scope':'new operation-substitution candidates; common source-framework harness; no external migration-quality claim',
                      'assertion_expressions_exact':asserts(base)==asserts(target),'source_hash':sha(out/(cid+'-source.py')),'target_hash':sha(out/(cid+'-target.py'))})
    save(out/'registration.json',specs)
    save(out/'SHA256.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
    print('Registered 27 retained-body pairs; 3 unresolved aliasing obligations')


def execute(out):
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',TF_NUM_INTEROP_THREADS='1',TF_NUM_INTRAOP_THREADS='1',OMP_NUM_THREADS='1')
    sys.path.insert(0,str(ROOT/'dependencies'))
    import numpy as np, tensorflow as tf, torch
    from numbers import Number
    from itertools import product
    from torch.testing import make_tensor
    from tensorflow.python.framework import ops, constant_op, dtypes, test_util
    from tensorflow.python.ops import array_ops,array_ops_stack,clip_ops,variables
    from tensorflow.python.platform.test import TestCase as TFCase
    from torch.testing._internal.common_utils import TestCase as PTCase
    torch.set_num_threads(1)
    regs=load(ROOT/'retained/registration.json');cases={c['case_id']:c for c in load(DATA/'candidates.json')}
    probes=load(DATA/'runs/2026-09-20-dynamic-v3/inputs.freeze.json')
    refs={'add':np.add,'subtract':np.subtract,'multiply':np.multiply,'divide':np.divide,'maximum':np.maximum,'minimum':np.minimum,'power':np.power,'atan2':np.arctan2}
    def asnp(x):
        if isinstance(x,torch.Tensor):return x.detach().cpu().numpy()
        if isinstance(x,tf.Tensor):return x.numpy()
        return np.asarray(x)
    def encode(a):return {'shape':list(a.shape),'dtype':str(a.dtype),'values':a.tolist()}
    results=[]
    for reg in regs:
        if reg['status']!='registered':continue
        cid=reg['case_id'];case=cases[cid];pt=reg['source_framework']=='pytorch'
        sources={}
        for side in ['source','target']:
            env={'torch':torch,'tf':tf,'np':np};exec((ROOT/'registered-tests'/cid/(side+'-function.py')).read_text(),env)
            sources[side]=env[case[side]['entry']]
        scenarios=[0,16] if int(cid[1:])<=16 else [None]
        for scenario in scenarios:
            for side in ['source','target']:
                for mode in MODES:
                    for rep in range(3):
                        np.random.seed(1729);torch.manual_seed(1729);tf.random.set_seed(1729)
                        calls=[];phase=['source-test'];count=[0]
                        def operation(*args,**kw):
                            phase[0]='argument-adapter'
                            names=case['argument_names'];vals=dict(zip(names,args))
                            aliases={'axis':names[-1],'dim':names[-1]}
                            for k,v in kw.items(): vals[aliases.get(k,k)]=v
                            if case['family']=='transpose' and not pt:
                                vals.setdefault('perm',None);vals.setdefault('conjugate',False)
                            if case['family']=='squeeze':vals.setdefault(names[-1],None)
                            if case['family']=='clip' and pt:
                                vals.setdefault('min',None);vals.setdefault('max',None)
                            if case['family'] in ['concat','stack']:vals.setdefault(names[-1],0)
                            converted={};fw=case[side]['framework']
                            def convert_tensor(v):
                                # Canonicalize in source framework first, preserving source defaults.
                                aa=asnp(torch.as_tensor(v) if pt and not isinstance(v,tf.Tensor) else tf.convert_to_tensor(v) if not pt and not isinstance(v,torch.Tensor) else v)
                                return torch.tensor(aa) if fw=='pytorch' else tf.constant(aa)
                            for i,name in enumerate(names):
                                v=vals[name]
                                if case['family'] in ['concat','stack'] and i==0:converted[name]=[convert_tensor(x) for x in v]
                                elif i==0 or case['family'] in refs or (case['family']=='clip' and v is not None):converted[name]=convert_tensor(v)
                                elif v is None:converted[name]=None
                                elif isinstance(v,(torch.Tensor,tf.Tensor,np.ndarray)):converted[name]=asnp(v).tolist()
                                else:converted[name]=v
                            phase[0]='counterpart-execution'
                            native=sources[side](**converted);a=asnp(native)
                            phase[0]='observation-adapter';delivered=a
                            if count[0]==0:
                                if mode=='wrong-shape':delivered=a.reshape((1,)+a.shape)
                                elif mode=='wrong-value':delivered=(a+(np.abs(a)*.2+10)).astype(a.dtype) if a.dtype.kind in 'fiu' else np.logical_not(a)
                                elif mode=='reinject':delivered=a.copy()
                            if count[0]==0:calls.append({'native':encode(a),'delivered':encode(delivered),'input_shapes':{k:list(asnp(v).shape) for k,v in vals.items() if isinstance(v,(np.ndarray,torch.Tensor,tf.Tensor))}})
                            count[0]+=1
                            result=torch.tensor(delivered) if pt else tf.constant(delivered)
                            phase[0]='source-test'
                            return result
                        env={'np':np,'torch':torch,'tf':tf,'ops':ops,'constant_op':constant_op,'dtypes':dtypes,'test_util':test_util,
                             'array_ops':array_ops,'array_ops_stack':array_ops_stack,'clip_ops':clip_ops,'variables':variables,
                             'make_tensor':make_tensor,'product':product,'Number':Number,'Harness':PTCase if pt else TFCase,'_operation':operation,
                             'torch_to_numpy_dtype_dict':{torch.float32:np.float32,torch.float64:np.float64},
                             'numpy_to_torch_dtype_dict':{np.float32:torch.float32,np.float64:torch.float64}}
                        if cid=='E028':
                            original_tree=ast.parse((ROOT/'upstream/tf_stack.py').read_text())
                            helper=next(n for n in original_tree.body if isinstance(n,ast.FunctionDef) and n.name=='np_split_squeeze')
                            exec(compile(ast.Module(body=[helper],type_ignores=[]),str(ROOT/'upstream/tf_stack.py'),'exec'),env)
                        path=ROOT/'retained'/(cid+('-source.py' if side=='source' and mode=='original' else '-target.py'))
                        exec(compile(path.read_text(),str(path),'exec'),env)
                        tester=env['Frozen']();status='passed';err=None;frames=[]
                        try:
                            tester.setUp()
                            if scenario is not None:
                                p=next(p for p in probes if p['case_id']==cid and p['input_index']==scenario)
                                x,y=[np.asarray(v['values'],dtype=v['dtype']) for v in p['arguments'].values()]
                                if pt:
                                    class Sample:
                                        input=torch.tensor(x);args=[torch.tensor(y)]
                                        def numpy(self):return SimpleNamespace(input=x,args=[y])
                                    class Op:
                                        name={'subtract':'sub'}.get(case['family'],case['family'])
                                        ref=staticmethod(refs[case['family']])
                                        def __call__(self,x,y):return operation(x,y)
                                    tester._test_reference_numerics(torch.tensor(x).dtype,Op(),[Sample()])
                                else:tester._compareCpu(x,y,refs[case['family']],operation)
                            elif cid=='E019':getattr(tester,reg['entry'])('cpu',torch.float32)
                            elif cid in ['E025','E029']:getattr(tester,reg['entry'])('cpu',torch.float64)
                            elif cid=='E027':getattr(tester,reg['entry'])('cpu')
                            else:getattr(tester,reg['entry'])()
                        except AssertionError as exc:
                            status='assertion-rejected';err=str(exc)[:1500];frames=[{'file':f.filename,'line':f.lineno,'name':f.name} for f in traceback.extract_tb(exc.__traceback__)]
                        except Exception as exc:
                            status='execution-error';err=type(exc).__name__+': '+str(exc);frames=[{'file':f.filename,'line':f.lineno,'name':f.name} for f in traceback.extract_tb(exc.__traceback__)]
                        finally:
                            try:tester.tearDown()
                            except Exception:pass
                        results.append({'case_id':cid,'scenario':scenario,'side':side,'mode':mode,'repeat':rep,'status':status,'phase':phase[0],
                                        'operation_count':count[0],'first_observation':calls,'error':err,'frames':frames})
        print(cid,flush=True)
    save(out,{'records':results,'versions':{'tensorflow':tf.__version__,'torch':torch.__version__,'numpy':np.__version__,'python':sys.version}})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','execute']);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='plan':plan()
    else:
        assert not a.output.exists();execute(a.output)
