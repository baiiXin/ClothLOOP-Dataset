"""Build the standalone local review page using only files in this test set."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).with_name('review_assets')


def main():
    dataset = json.loads((ROOT / 'dataset.json').read_text())
    cases = []
    for number, item in enumerate(dataset['snapshots'], 1):
        folder = ROOT / item['directory']
        quality = json.loads((folder / 'reports/quality.json').read_text())
        record = dict(item['display'], id=item['id'], number=number,
                      passed=item['geometry_passed'], kind=item['display_kind'],
                      counts=item['intersection_counts'], sha256=item['firstframe_sha256'],
                      image=f"{item['directory']}/media/preview_front_back.png",
                      stretch=quality.get('principal_stretch_vs_preserved_rest'), closeup=None)
        record['links'] = {label: f"{item['directory']}/{filename}" for label, filename in [
            ('衣物 + 人体 NPZ', 'firstframe.npz'), ('人体参数 / 体型', 'body_parameters.json'),
            ('当前归档状态', 'state.json'), ('衣物 OBJ', 'cloth.obj'), ('人体 OBJ', 'body.obj'),
            ('严格相交检查', 'reports/geometry.json'), ('内部点检查', 'reports/containment.json'),
            ('网格质量', 'reports/quality.json'), ('来源 / 修改记录', 'reports/provenance.json'),
            ('部件映射', 'components.json')]}
        if (folder / 'media/maximum_stitch_gap_closeup.png').exists():
            record['closeup'] = f"{item['directory']}/media/maximum_stitch_gap_closeup.png"
        cases.append(record)
    html = (ASSETS / 'index.html').read_text()
    for key, value in [('__STYLE__', (ASSETS / 'review.css').read_text()),
                       ('__SCRIPT__', (ASSETS / 'review.js').read_text()),
                       ('__DATA__', json.dumps({'created_at': dataset['created_at'], 'cases': cases}, ensure_ascii=False).replace('<', '\\u003c'))]:
        assert html.count(key) == 1
        html = html.replace(key, value)
    (ROOT / 'index.html').write_text(html)
    print('Built local review: 14 motion cases / 15 snapshots (both 85_12 variants).')


if __name__ == '__main__':
    main()
