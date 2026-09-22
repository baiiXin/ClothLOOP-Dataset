"""Load a selected snapshot without assuming geometry-passed means dynamics-ready."""
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(case_id, variant=None, allow_failed=False):
    dataset = json.loads((ROOT / 'dataset.json').read_text())
    case = next((c for c in dataset['cases'] if c['id'] == case_id), None)
    if case is None:
        raise KeyError(f'Unknown case: {case_id}')
    variant = variant or case['default_variant']
    record = next((s for s in dataset['snapshots'] if s['case_id'] == case_id and s['variant'] == variant), None)
    if record is None:
        raise KeyError(f'Unknown variant {variant!r} for {case_id}')
    if not record['geometry_passed'] and not allow_failed:
        raise ValueError('This is an intersecting failure candidate. Explicitly use --allow-failed for inspection.')
    folder = ROOT / record['directory']
    with np.load(folder / 'firstframe.npz', allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    parameters = json.loads((folder / 'body_parameters.json').read_text())
    return arrays, parameters, record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case')
    parser.add_argument('--variant')
    parser.add_argument('--allow-failed', action='store_true')
    args = parser.parse_args()
    arrays, parameters, record = load(args.case, args.variant, args.allow_failed)
    print(json.dumps({'case': record['case_id'], 'variant': record['variant'],
                      'geometry_passed': record['geometry_passed'],
                      'body_model': parameters['model']['family'],
                      'arrays': {key: {'shape': list(value.shape), 'dtype': str(value.dtype)}
                                 for key, value in arrays.items()},
                      'note': 'Single-frame geometry only; read quality limitations before simulation.'}, indent=2))
