#!/usr/bin/env python3
"""
get_kaisou_materials.py - Generate kaisou_materials.json from game master data
Usage: python3 get_kaisou_materials.py <api_start2.json> <main.js> <output.json>
"""
import re
import json
import sys


def parse_shippuupgrade(api_start2_path):
    """Extract remodel consumable costs from api_mst_shipupgrade."""
    costs = {}
    with open(api_start2_path, 'r', encoding='utf8') as f:
        data = json.load(f)
        for item in data.get('api_mst_shipupgrade', []):
            cur_id = item.get('api_current_ship_id', 0)
            if cur_id <= 0:
                continue
            costs[cur_id] = {
                'drawing': item.get('api_drawing_count', 0),
                'catapult': item.get('api_catapult_count', 0),
                'report': item.get('api_report_count', 0),
                'aviation': item.get('api_aviation_mat_count', 0),
                'arms': item.get('api_arms_mat_count', 0),
                'boiler': item.get('api_boiler_count', 0),
                'tech': item.get('api_tech_count', 0),
            }
    return costs


def parse_ship_base(api_start2_path):
    """Extract base remodel info from api_mst_ship."""
    ships = {}
    with open(api_start2_path, 'r', encoding='utf8') as f:
        data = json.load(f)
        for ship in data.get('api_mst_ship', []):
            sid = ship.get('api_id', 0)
            if sid >= 1500:
                continue
            after_id = int(ship.get('api_aftershipid', 0) or 0)
            if after_id <= 0:
                continue
            ships[sid] = {
                'id': sid,
                'name': ship.get('api_name', ''),
                'after_id': after_id,
                'ammo': ship.get('api_afterbull', 0),
                'steel': ship.get('api_afterfuel', 0),
            }
    return ships


def parse_hokoheso(main_js_path):
    """Extract hokoheso (新型火炮兵装資材, id=75) costs from main.js getter.
    
    New obfuscated format:
      Object[obf(0x465)](prototype, obf(0x317c), {
        get: function() { switch(this[obf(0x328e)]) { case 0xNN: return 0xMM; ... } }
      })
    Switch is on mst_id_after (after ship ID), returns hokoheso count.
    """
    result = {}
    rex_case_ret = re.compile(r'((?:case\s+0x[\da-f]+:\s*)+)return\s+(0x[\da-f]+);\s*', re.I)
    rex_case = re.compile(r'case\s+(0x[\da-f]+):', re.I)

    with open(main_js_path, 'r', encoding='utf8') as f:
        ctx = f.read()

    # Find getter with (0x317c) and switch on this[obf(0x328e)]
    rex_func = re.compile(
        r'\w+\(0x317c\).*?switch\s*\(\s*this\[\w+\(0x328e\)\]\s*\)\s*\{((?:(?:case\s+0x[\da-f]+:\s*)+return\s+0x[\da-f]+;\s*)+)',
        re.M | re.I,
    )
    match = rex_func.search(ctx)
    if not match:
        print('WARNING: hokoheso getter pattern not found in main.js')
        return result

    for m in rex_case_ret.finditer(match.group(1)):
        count = int(m.group(2), 16)
        for mc in rex_case.finditer(m.group(1)):
            after_id = int(mc.group(1), 16)
            result[after_id] = count

    # Handle special case: case 0x38f (911): conditional on this[obf(0x2cb3)]
    rex_special = re.compile(
        r'case\s+(0x38f):\s*return\s+(0x[\da-f]+)\s*==\s*this\[\w+\(0x2cb3\)\)\]\s*\?\s*(0x[\da-f]+)\s*:\s*(0x[\da-f]+)',
        re.I,
    )
    special = rex_special.search(ctx)
    if special:
        after_id = int(special.group(1), 16)
        cmp_val = int(special.group(2), 16)
        true_val = int(special.group(3), 16)
        false_val = int(special.group(4), 16)
        result[after_id] = true_val  # default to true_val, could be refined

    return result


def parse_devkit_buildkit(main_js_path):
    """Extract devkit and buildkit costs from main.js (obfuscated format).
    
    New main.js uses computed property access instead of named functions:
      prototype[obf(0xcc7)] = function(id, drawing, steel) { switch(id) {...} }
      prototype[obf(0xad9)] = function(id) { switch(id) {...} }
    """
    devkit = {}
    buildkit = {}
    use_devkit_group = []

    rex_case_ret = re.compile(r'((?:case\s+0x[\da-f]+:\s*)+)return\s+(0x[\da-f]+);\s*', re.I)
    rex_case = re.compile(r'case\s+(0x[\da-f]+):', re.I)

    with open(main_js_path, 'r', encoding='utf8') as f:
        ctx = f.read()

    # buildkit: (0xad9)]=function(shipId){switch(shipId){...}}
    rex_buildkit = re.compile(
        r'\(0xad9\)\]\s*=\s*function\s*\(\s*(\w+)\s*\)\s*\{\s*switch\s*\(\s*\1\s*\)\s*\{((?:(?:case\s+0x[\da-f]+:\s*)+return\s+0x[\da-f]+;\s*)+)',
        re.M | re.I,
    )
    match = rex_buildkit.search(ctx)
    if match:
        for m in rex_case_ret.finditer(match.group(2)):
            value = int(m.group(2), 16)
            for mc in rex_case.finditer(m.group(1)):
                buildkit[int(mc.group(1), 16)] = value

    # devkit: (0xcc7)]=function(id,drawing,steel){...switch(id){...}}
    rex_devkit = re.compile(
        r'\(0xcc7\)\]\s*=\s*function\s*\([^)]+\)\s*\{.+?switch\s*\(\s*(\w+)\s*\)\s*\{((?:(?:case\s+0x[\da-f]+:\s*)+return\s+0x[\da-f]+;\s*)+)',
        re.M | re.I,
    )
    match = rex_devkit.search(ctx)
    if match:
        for m in rex_case_ret.finditer(match.group(2)):
            value = int(m.group(2), 16)
            for mc in rex_case.finditer(m.group(1)):
                devkit[int(mc.group(1), 16)] = value

    # USE_DEVKIT_GROUP: constructor pattern this[obf(0x494)]=[0xNN,0xNN]
    rex_group = re.compile(
        r'this\[\w+\(0x494\)\]\s*=\s*\[((?:0x[\da-f]+\s*,\s*)*0x[\da-f]+)\]',
        re.I,
    )
    match = rex_group.search(ctx)
    if match:
        use_devkit_group = [int(n.group(), 16) for n in re.finditer(r'0x([\da-f]+)', match.group(1), re.I)]

    print(f'  Buildkit switch entries: {len(buildkit)}')
    print(f'  Devkit switch entries: {len(devkit)}')
    print(f'  USE_DEVKIT_GROUP: {use_devkit_group}')

    return devkit, buildkit, use_devkit_group


def main():
    if len(sys.argv) < 4:
        print(f'Usage: {sys.argv[0]} <api_start2.json> <main.js> <output.json>')
        sys.exit(1)

    api_start2_path = sys.argv[1]
    main_js_path = sys.argv[2]
    output_path = sys.argv[3]

    print(f'Step 1: parse api_start2.json for ship base info')
    ship_base = parse_ship_base(api_start2_path)
    print(f'  Found {len(ship_base)} remodel-able ships')

    print(f'Step 2: parse api_start2.json for shipupgrade data')
    upgrade_costs = parse_shippuupgrade(api_start2_path)
    print(f'  Found {len(upgrade_costs)} ship upgrade entries')

    print(f'Step 3: parse main.js for hokoheso')
    hokoheso = parse_hokoheso(main_js_path)
    print(f'  Found {len(hokoheso)} hokoheso entries')

    print(f'Step 4: parse main.js for devkit/buildkit')
    devkit_map, buildkit_map, use_devkit_group = parse_devkit_buildkit(main_js_path)
    print(f'  Found {len(devkit_map)} devkit entries, {len(buildkit_map)} buildkit entries')
    print(f'  USE_DEVKIT_GROUP: {use_devkit_group}')

    # Material ID mapping
    MATERIAL_ID_MAP = {
        'drawing': 58,
        'catapult': 65,
        'report': 78,
        'devkit': 3,
        'buildkit': 2,
        'aviation': 77,
        'hokoheso': 75,
        'arms': 94,
        'boiler': 899,
        'tech': 100,
    }

    kaisou_materials = {}

    for sid, base in ship_base.items():
        cost = upgrade_costs.get(sid, {})

        drawing = cost.get('drawing', 0)
        steel = base['steel']

        # devkit calculation logic
        if sid in devkit_map:
            devkit = devkit_map[sid]
        elif drawing != 0 and sid not in use_devkit_group:
            devkit = 0
        else:
            devkit = 0 if steel < 4500 else 10 if steel < 5500 else 15 if steel < 6500 else 20

        buildkit = buildkit_map.get(sid, 0)

        # hokoheso: matched by after_id
        after_id = base['after_id']
        hokoheso_count = hokoheso.get(after_id, 0)

        values = {
            'drawing': drawing,
            'catapult': cost.get('catapult', 0),
            'report': cost.get('report', 0),
            'devkit': devkit,
            'buildkit': buildkit,
            'aviation': cost.get('aviation', 0),
            'hokoheso': hokoheso_count,
            'arms': cost.get('arms', 0),
            'boiler': cost.get('boiler', 0),
            'tech': cost.get('tech', 0),
        }

        consumable = []
        for mat_name, mat_id in MATERIAL_ID_MAP.items():
            count = values.get(mat_name, 0)
            if count > 0:
                consumable.append([mat_id, count])

        kaisou_materials[str(sid)] = {
            'ammo': base['ammo'],
            'steel': base['steel'],
            'consumable': consumable,
            'equipment': [],
        }

    with open(output_path, 'w', encoding='utf8') as f:
        json.dump(kaisou_materials, f, ensure_ascii=False, separators=(',', ':'))

    print(f'Done: {len(kaisou_materials)} ships exported to {output_path}')


if __name__ == '__main__':
    main()
