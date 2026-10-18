"""Read-only-source trial on copied real merger files; scratch output only."""
import hashlib
import json
from pathlib import Path
import tempfile
import bindings


def hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


def main():
    original = Path('line-1/tools/threeway')
    original_hashes = hashes(original)
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as directory:
        roots = [Path(directory) / side for side in bindings.tree.SIDES]
        for root in roots:
            root.mkdir()
            for relative in original_hashes:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((original / relative).read_bytes())
        ours = roots[1] / 'merge.py'
        theirs = roots[2] / 'merge.py'
        text = ours.read_text()
        assert text.count('from pathlib import Path\n') == 1
        ours.write_text(text.replace('from pathlib import Path\n',
                                     'from pathlib import Path as shared_value\n'))
        text = theirs.read_text()
        assert text.count('MAX_LINES = 4000\n') == 1
        theirs.write_text(text.replace('MAX_LINES = 4000\n', 'shared_value = 4000\n'))
        before = [hashes(root) for root in roots]
        report = bindings.from_directories(roots)
        item = next(file for file in report['files'] if file['path'] == 'merge.py')
        finding = next(c for c in item['collisions'] if c['name'] == 'shared_value')
        assert report['text_merge_clean'] and report['review_required']
        assert finding['classification'] == 'new-combination'
        assert len(finding['versions']['ours']) == len(finding['versions']['theirs']) == 1
        assert len(finding['versions']['candidate']) == 2
        assert before == [hashes(root) for root in roots]
        assert original_hashes == hashes(original)
        print(json.dumps({'source': str(original), 'source_hashes': original_hashes,
                          'copied_files_per_tree': len(original_hashes),
                          'text_merge_clean': report['text_merge_clean'],
                          'review_required': report['review_required'],
                          'candidate_sha256': item['candidate_sha256'],
                          'finding': finding, 'inventory_complete': item['complete'],
                          'inventory_problems': item['problems'],
                          'source_and_trial_inputs_unchanged': True,
                          'candidate_executed': False}, indent=2))


if __name__ == '__main__':
    main()
