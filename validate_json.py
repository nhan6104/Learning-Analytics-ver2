"""
Validate learning_plan.json node IDs against Moodle DB.
Also performs deep analysis to determine if IDs are cm_id or instance_id.

Usage:
  python validate_json.py --host HOST --port 3306 --db moodle --user USER --password PASS --prefix mdl_
"""

import json
import re
import argparse
import sys
from collections import Counter, defaultdict

try:
    import pymysql as mysql_driver
    DRIVER = 'pymysql'
except ImportError:
    try:
        import mysql.connector as mysql_driver
        DRIVER = 'mysql.connector'
    except ImportError:
        print("ERROR: pip install pymysql")
        sys.exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--host',     default='192.168.1.220')
parser.add_argument('--port',     type=int, default=3306)
parser.add_argument('--db',       default='moodle_ubuntu')
parser.add_argument('--user',     default='remoteuser')
parser.add_argument('--password', default='123')
parser.add_argument('--prefix',   default='mdl_')
parser.add_argument('--json',     default='microlearning/learning_plan.json')
args = parser.parse_args()

P = args.prefix

# Load JSON
with open(args.json) as f:
    data = json.load(f)
nodes = data['nodes']
edges = data['edges']

print(f"Loaded {len(nodes)} nodes, {len(edges)} edges")
print()

# Parse IDs
prefixes = Counter()
by_prefix = defaultdict(list)
for n in nodes:
    m = re.match(r'^([a-z]+)_(\d+)$', n['id'])
    if m:
        p, num = m.group(1), int(m.group(2))
        prefixes[p] += 1
        by_prefix[p].append({'id': n['id'], 'num': num, 'title': n['title']})
    else:
        print(f"  UNUSUAL ID: {n['id']}")

print("ID prefix breakdown:")
for p, c in sorted(prefixes.items()):
    print(f"  {p:12s} → {c:3d} nodes")
print()

# Connect
try:
    conn = mysql_driver.connect(
        host=args.host, port=args.port,
        database=args.db, user=args.user, password=args.password,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    print(f"Connected to {args.db}@{args.host}:{args.port}")
    print()
except Exception as e:
    print(f"DB connection failed: {e}")
    sys.exit(1)

print("=" * 60)
print("VALIDATION RESULTS")
print("=" * 60)
print()

# 1. Sections
section_ids = [n['num'] for n in by_prefix.get('section', [])]
if section_ids:
    ph = ','.join(['%s'] * len(section_ids))
    cursor.execute(f"SELECT id, name FROM {P}course_sections WHERE id IN ({ph})", section_ids)
    found = {r[0]: r[1] for r in cursor.fetchall()}
    missing = [i for i in section_ids if i not in found]
    print(f"[SECTIONS] {len(section_ids)} IDs in {P}course_sections.id")
    print(f"  Found: {len(found)}, Missing: {len(missing)}")
    if missing:
        print(f"  Missing IDs: {missing}")
    print()

# 2. Deep analysis: cm_id vs instance_id for each prefix
print("[DEEP ANALYSIS] cm_id vs instance_id per prefix:")
print()
mapping = {}  # prefix -> 'cm_id' or 'instance_id'

for prefix in ['page', 'forum', 'url', 'assign', 'resource', 'quiz', 'module']:
    nodes_of_type = by_prefix.get(prefix, [])
    if not nodes_of_type:
        continue
    ids = [n['num'] for n in nodes_of_type]
    ph = ','.join(['%s'] * len(ids))

    # Try as cm_id
    cursor.execute(
        f"SELECT cm.id, m.name FROM {P}course_modules cm "
        f"JOIN {P}modules m ON m.id = cm.module "
        f"WHERE cm.id IN ({ph})",
        ids
    )
    as_cmid = {r[0]: r[1] for r in cursor.fetchall()}

    # Try as instance_id (with matching modname)
    mod_name = 'assign' if prefix == 'assign' else prefix
    cursor.execute(
        f"SELECT cm.instance, cm.id, m.name FROM {P}course_modules cm "
        f"JOIN {P}modules m ON m.id = cm.module "
        f"WHERE m.name = %s AND cm.instance IN ({ph})",
        [mod_name] + ids
    )
    as_instance = {r[0]: {'cm_id': r[1], 'modname': r[2]} for r in cursor.fetchall()}

    verdict = '?'
    if len(as_instance) > len(as_cmid):
        verdict = 'INSTANCE_ID'
    elif len(as_cmid) > 0:
        verdict = 'CM_ID'
    mapping[prefix] = verdict

    print(f"  {prefix:10s} ({len(ids):3d} nodes): "
          f"as cm_id={len(as_cmid)}/{len(ids)}, "
          f"as instance_id={len(as_instance)}/{len(ids)} "
          f"→ {verdict}")

    # Show sample mismatches for cm_id case
    if verdict == 'CM_ID' and prefix != 'module':
        wrong = [(n['id'], as_cmid.get(n['num'], '?')) for n in nodes_of_type
                 if n['num'] in as_cmid and as_cmid[n['num']] != prefix]
        if wrong:
            print(f"    ⚠ modname mismatches (first 3):")
            for nid, actual_mod in wrong[:3]:
                print(f"      {nid} → actual modname='{actual_mod}'")

print()

# 3. Edge integrity
print("[EDGES] Checking references:")
node_ids = {n['id'] for n in nodes}
bad = []
for e in edges:
    if e['from'] not in node_ids:
        bad.append(f"  from='{e['from']}' missing")
    if e['to'] not in node_ids:
        bad.append(f"  to='{e['to']}' missing")

if bad:
    print(f"  ✗ {len(bad)} broken references:")
    for b in bad:
        print(b)
    print()

    # Look up missing refs in DB
    missing_refs = set()
    for e in edges:
        if e['from'] not in node_ids:
            missing_refs.add(e['from'])
        if e['to'] not in node_ids:
            missing_refs.add(e['to'])

    print("  DB lookup for missing nodes:")
    for ref in sorted(missing_refs):
        m = re.match(r'^([a-z]+)_(\d+)$', ref)
        if not m:
            continue
        p, num = m.group(1), int(m.group(2))

        # Try cm_id
        cursor.execute(
            f"SELECT cm.id, m.name, cm.instance, cs.name as section_name "
            f"FROM {P}course_modules cm "
            f"JOIN {P}modules m ON m.id = cm.module "
            f"LEFT JOIN {P}course_sections cs ON cs.id = cm.section "
            f"WHERE cm.id = %s", [num]
        )
        row = cursor.fetchone()
        if row:
            # Get actual name from module table
            mod_table = row[1]
            cursor.execute(
                f"SELECT name FROM {P}{mod_table} WHERE id = %s", [row[2]]
            )
            name_row = cursor.fetchone()
            actual_name = name_row[0] if name_row else '?'
            print(f"    {ref} → cm_id={row[0]}, modname={row[1]}, "
                  f"name='{actual_name[:40]}', section='{row[3]}'")
        else:
            # Try instance_id
            cursor.execute(
                f"SELECT cm.id, m.name, cm.instance FROM {P}course_modules cm "
                f"JOIN {P}modules m ON m.id = cm.module "
                f"WHERE m.name = %s AND cm.instance = %s", [p, num]
            )
            row = cursor.fetchone()
            if row:
                print(f"    {ref} → instance_id match: cm_id={row[0]}, modname={row[1]}")
            else:
                print(f"    {ref} → NOT FOUND in DB")
else:
    print(f"  ✓ All {len(edges)} edges reference valid nodes")
print()

# 4. Summary
print("=" * 60)
print("CONCLUSION")
print("=" * 60)
print()
print("ID mapping rules:")
for prefix, verdict in mapping.items():
    if verdict == 'CM_ID':
        print(f"  {prefix}_{{N}} → mdl_course_modules.id = N")
    elif verdict == 'INSTANCE_ID':
        print(f"  {prefix}_{{N}} → mdl_{prefix}.id = N (instance_id)")
    else:
        print(f"  {prefix}_{{N}} → unclear")

conn.close()
