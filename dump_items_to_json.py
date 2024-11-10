import json
import os
import re

input_dir = './osrs-flatcache/dump/item_defs/'
output_dir = './data_files/'

def natural_key(string_):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

all_files = sorted(os.listdir(input_dir), key=natural_key)

good_params = {
    'id': 'id',
    'name': 'name',
    'wearPos1': 'wearpos1',
    'wearPos2': 'wearpos2',
    'wearPos3': 'wearpos3',
}

# remove all Nones from list
def parseActions(actions, save_nones=True):
    return list(filter(lambda x: x != None, actions))

bad_slots = set([0, 12, 13])
item_dict = {}
for filename in all_files:
    with open(input_dir + filename, encoding='utf8') as f:
        data = json.load(f)
    resdata = {}
    for old_param_name, new_param_name in good_params.items():
        if old_param_name in data:
            resdata[new_param_name] = data[old_param_name]

    # We only care about items where wearPos1/2/3 are rendered
    # Unforutnately wearpos is 0 if it is a head slot or blank, so I have to use headModel as a work around
    if resdata['wearpos1'] not in bad_slots or resdata['wearpos2'] not in bad_slots or resdata['wearpos3'] not in bad_slots or data['maleHeadModel'] != -1 or data['femaleHeadModel'] != -1:
        # Attempt to fix the incorrect 0s to -1s
        # Assume any 0 is NOT a head and should be -1 if there are no chatheads
        # If there is a chathead, then the first 0 is legit and the others should be -1
        if data['maleHeadModel'] == -1 and data['femaleHeadModel'] == -1:
            resdata['wearpos1'] = -1 if resdata['wearpos1'] == 0 else resdata['wearpos1']
            resdata['wearpos2'] = -1 if resdata['wearpos2'] == 0 else resdata['wearpos2']
            resdata['wearpos3'] = -1 if resdata['wearpos3'] == 0 else resdata['wearpos3']
        else:
            resdata['wearpos2'] = -1 if resdata['wearpos2'] == 0 else resdata['wearpos2']
            resdata['wearpos3'] = -1 if resdata['wearpos3'] == 0 else resdata['wearpos3']


        item_dict[resdata['id']] = resdata

with open(output_dir + 'items.json', 'w') as outfile:
    json.dump(item_dict, outfile, indent=1)

with open(output_dir + 'itemsmin.js', 'w') as outfile:
    minified_json = json.dumps(item_dict, separators=(',',':'))
    outfile.write('items=' + minified_json)
