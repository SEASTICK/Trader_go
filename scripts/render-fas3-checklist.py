#!/usr/bin/env python3
"""Validate canonical Phase 3 status and render its Markdown and optional chat view."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/fas3-status.json'
TARGET = ROOT / 'docs/fas3-checklista.md'


def render():
    data = json.loads(SOURCE.read_text())
    assert data['schema_version'] == 1
    ids = set()
    tasks = [t for g in data['groups'] for t in g['tasks']]
    for task in tasks:
        assert task['id'] not in ids, 'Duplicate task ID'
        ids.add(task['id'])
        assert task['status'] in ('todo', 'in_progress', 'done')
        if task['status'] == 'done':
            assert task['evidence'], task['id'] + ': evidence required'
        for item in task['evidence']:
            path = (ROOT / item['file']).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), 'Invalid evidence path'
            assert item['detail'].strip(), 'Evidence description required'
    done = sum(t['status'] == 'done' for t in tasks)
    lines = ['# Fas 3 – Utvecklingsplan', '',
             f"**{done} av {len(tasks)} uppgifter verifierade · {len(data['groups'])} arbetsområden.**", '',
             f"Planering · Kontrollerad {data['updated']} · Granskad kodversion `{data['reviewed_revision']}`.", '',
             data.get('reviewed_scope', ''), '',
             '## Uppdateringsregler', '',
             '- `docs/fas3-status.json` är gemensam källa för status. Ändra status där; denna Markdown genereras.',
             '- Efter varje relevant kodändring: kontrollera berörda uppgifter, kör relevanta tester och uppdatera status/underlag i samma leverans.',
             '- Bocka bara av verifierat och granskat arbete. Att en fil finns eller att en commit är pushad räcker inte.',
             '- Spara kod-/testunderlag i `evidence`. Sätt `in_progress` när arbetet pågår och `todo` om en tidigare verifiering inte längre gäller.',
             '- Skilj på lokal kod, mergad kod, driftsättning, publicering och installerat app-test. De har egna kontrollpunkter.',
             '- Framåttest kräver READY_FOR_PAPER, fryst strategi och startbeslut. H-0013 förblir REJECT; inga frysta resultat ändras.',
             '- Kör `python3 scripts/render-fas3-checklist.py` efter uppdatering och `python3 scripts/render-fas3-checklist.py --check` före commit.',
             '- Chatvyn är en ögonblicksbild. En filändring i en annan session startar inte en verifiering här. Begär en ny kontroll eller uppdatera vyn i nästa leverans.', '']
    for group in data['groups']:
        count = sum(t['status'] == 'done' for t in group['tasks'])
        lines += [f"## {group['title']}", '', f"{count}/{len(group['tasks'])} verifierade.", '']
        for task in group['tasks']:
            extra = ' **Pågår.**' if task['status'] == 'in_progress' else ''
            lines.append(f"- [{'x' if task['status'] == 'done' else ' '}] **{task['id']}** {task['title']}{extra}")
            for item in task['evidence']:
                lines.append(f"  - Underlag: [{item['file']}]({Path(item['file']).relative_to('docs') if item['file'].startswith('docs/') else '../' + item['file']}) — {item['detail']}")
            if task.get('note'):
                lines.append('  - ' + task['note'])
        lines.append('')
    return data, '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true', help='Fail if generated Markdown is stale')
    p.add_argument('--visual', type=Path, help='Also render the in-chat HTML fragment at this path')
    args = p.parse_args()
    data, content = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != content:
            raise SystemExit('Checklist stale; run python3 scripts/render-fas3-checklist.py')
    else:
        TARGET.write_text(content)
    if args.visual:
        template = (ROOT / 'docs/templates/fas3-checklista.html').read_text()
        payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
        args.visual.parent.mkdir(parents=True, exist_ok=True)
        args.visual.write_text(template.replace('__FAS3_DATA__', payload))
    print('PASS: Phase 3 checklist schema, evidence paths and generated status')


if __name__ == '__main__':
    main()
