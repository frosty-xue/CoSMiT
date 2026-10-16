"""Optional single-operation replay; prints observations, never annotation labels."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    ids = [r['candidate_id'] for r in json.loads((root / 'candidate-index.json').read_text(encoding='utf8'))]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=ids)
    parser.add_argument('--side', required=True, choices=['source', 'target'])
    parser.add_argument('--input-index', required=True, type=int, choices=range(64))
    args = parser.parse_args()
    folder = root / 'candidates' / args.case
    meta = json.loads((folder / 'metadata.json').read_text(encoding='utf8'))
    code = (folder / f'{args.side}-operation.py').read_bytes()
    if hashlib.sha256(code).hexdigest() != meta['operation_sha256'][args.side]:
        raise ValueError('Operation code changed; review the change before replaying.')
    import numpy as np
    framework = meta[args.side]['framework']
    module = importlib.import_module('torch' if framework == 'pytorch' else 'tensorflow')
    namespace = {'np': np, 'torch' if framework == 'pytorch' else 'tf': module}

    def convert(arg):
        if arg['kind'] == 'literal':
            return arg['value']
        if arg['kind'] == 'tensor-list':
            return [convert(item) for item in arg['items']]
        if arg['kind'] == 'tensor':
            value = np.asarray(arg['values'], dtype=arg['dtype'])
            return module.tensor(value) if framework == 'pytorch' else module.constant(value)
        raise ValueError('Unsupported input encoding: ' + arg['kind'])

    probe = json.loads((folder / 'inputs.json').read_text(encoding='utf8'))[args.input_index]
    record = {'candidate_id': args.case, 'side': args.side, 'input_index': args.input_index,
              'versions': {framework: module.__version__, 'numpy': np.__version__},
              'scope': 'single-operation uninstrumented replay; no automatic annotation'}
    try:
        exec(compile(code, str(folder / f'{args.side}-operation.py'), 'exec'), namespace)
        value = namespace[meta[args.side]['entry']](**{k: convert(v) for k, v in probe['arguments'].items()})
        if framework == 'pytorch' and isinstance(value, module.Tensor):
            value = value.detach().cpu().numpy()
        array = np.asarray(value)
        record.update(status='ok', value=array.tolist(), shape=list(array.shape), dtype=str(array.dtype))
    except Exception as error:
        record.update(status='error', error=type(error).__name__, message=str(error))
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
