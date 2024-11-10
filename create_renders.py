import json
import uuid
import os
import subprocess
import base64
from typing import List
from pathlib import Path
from PIL import Image
from flask import Flask, make_response, abort, request, jsonify
from dotenv import load_dotenv
load_dotenv()

ITEMS_JSON_PATH = Path(os.getenv('DATAFILES_DIR'), 'items.json')
RENDERER_PATH = Path(os.getenv('RENDERER_PATH'))
TMP_DIR = '/tmp'

ROTATIONS = {
    0: 128,
    1: 384,
    2: 1152,
    3: 1664,
}
COMMA = ','
XAN2D = 96
ZAN2D = 0
EQUIPPED_ITEM_OFFSET = 2048

# Read json file
with open(ITEMS_JSON_PATH, 'r') as f:
    ITEM_CONFIG = json.load(f)

app = Flask(__name__)

@app.route('/render', methods=['POST'])
def render():
    data = request.get_json(silent=True)
    if data is None:
        return abort(400)

    # Validate and parse item ID
    try:
        item_id = int(data['id'])
        rotation = ROTATIONS[int(data['rotation'])]
        pose_anim = data['poseAnim']
    except (TypeError, ValueError, KeyError):
        abort(400)

    item_ids = [item_id]
    payload = handle_request(item_ids, rotation, pose_anim)
    return make_response(payload)


def equip_item(playerkit, item_id, wearpos1, wearpos2, wearpos3):
    # "Equip" the item in wearpos1 and zero out the other slots if they are set
    new_playerkit = playerkit[:]
    new_playerkit[wearpos1] = item_id + EQUIPPED_ITEM_OFFSET
    if wearpos2 != -1:
        new_playerkit[wearpos2] = 0
    if wearpos3 != -1:
        new_playerkit[wearpos3] = 0
    return new_playerkit

def handle_request(ids: List[str], rotation: int, pose_anim: int):
    # Set up some hardcoded values for the render
    male_playerkit = [0, 0, 0, 0, 274, 0, 282, 292, 259, 289, 298, 270]
    male_colorkit = [0, 6, 9, 0, 1]

    female_playerkit = [0, 0, 0, 0, 312, 0, 320, 326, 382, 324, 336, 552]
    female_colorkit = [5, 19, 9, 1, 2]

    request_id = str(uuid.uuid4())
    outdir = Path(TMP_DIR, request_id)
    # TODO: Make this take in an arbitrary cache
    cache = './caches/cache'

    # We need to make sure we "equip" the items and zero out any other playerkit slots that are overridden
    for item_id in ids:
        item_def = ITEM_CONFIG[item_id]
        male_playerkit = equip_item(male_playerkit, item_def['id'], item_def['wearpos1'], item_def['wearpos2'], item_def['wearpos3'])
        female_playerkit = equip_item(female_playerkit, item_def['id'], item_def['wearpos1'], item_def['wearpos2'], item_def['wearpos3'])

    should_render_chatheads = True if item_def['wearpos1'] == 0 else False

    # Generate the equipped and chathead renders as necessary
    generate_render(request_id, outdir, cache, male_playerkit, male_colorkit, pose_anim, XAN2D, rotation, ZAN2D, False)
    generate_render(request_id, outdir, cache, female_playerkit, female_colorkit, pose_anim, XAN2D, rotation, ZAN2D, True)
    if should_render_chatheads:
        generate_chathead(request_id, outdir, cache, male_playerkit, male_colorkit, False)
        generate_chathead(request_id, outdir, cache, female_playerkit, female_colorkit, True)
        flip_chatheads(outdir)

    # Create the payload to send back to the client
    def b64encode_file(filename):
        with open(filename, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    male_filename = f'{str(male_playerkit)}_{str(male_colorkit)}.png'
    female_filename = f'{str(female_playerkit)}_{str(female_colorkit)}.png'
    payload = {
        'request_id': request_id,
        'maleRenderBlob': b64encode_file(outdir.joinpath('player', male_filename)),
        'femaleRenderBlob': b64encode_file(outdir.joinpath('player', female_filename)),
    }
    if should_render_chatheads:
        payload['maleChatheadRenderBlob'] = b64encode_file(outdir.joinpath('playerchathead', male_filename))
        payload['femaleChatheadRenderBlob'] = b64encode_file(outdir.joinpath('playerchathead', female_filename))

    return payload

# Respond with blobs
def generate_render(request_id: str, outdir: str, cache: str, playerkit: List, colorkit: List, pose_anim: int, xan2d: int, yan2d: int, zan2d: int, is_female: bool):
    subprocess.run(
        [
            'java', '-jar', str(RENDERER_PATH), '--cache', cache, '--out', outdir,
            '--playerkit', COMMA.join([str(k) for k in playerkit]), '--playercolors', COMMA.join([str(k) for k in colorkit]),
            '--poseanim', str(pose_anim), '--xan2d', str(xan2d), '--yan2d', str(yan2d), '--zan2d', str(zan2d),
            f'{"--playerfemale" if is_female else ""}'
        ],
        check=True
    )
def generate_chathead(request_id: str, outdir: str, cache: str, playerkit: List, colorkit: List, is_female: bool):
    subprocess.run(
        [
            'java', '-jar', str(RENDERER_PATH), '--cache', cache, '--out', outdir,
            '--playerkit', COMMA.join([str(k) for k in playerkit]), '--playercolors', COMMA.join([str(k) for k in colorkit]),
            '--playerchathead', '--anim', '589', '--lowres', '--crophead', '--yan2d', '128',
            f'{"--playerfemale" if is_female else ""}'
        ],
        check=True
    )

def flip_chatheads(outdir: str):
    chathead_dir = Path(outdir, 'playerchathead')
    for name in os.listdir(chathead_dir):
        # Pillow is extremely stupid and won't let me overwrite without a tempfile
        filename = str(chathead_dir.joinpath(name))
        tmp_filename = str(chathead_dir.joinpath('flipped_' + name))
        with Image.open(filename) as im:
            # Flip the image from left to right
            im.transpose(method=Image.Transpose.FLIP_LEFT_RIGHT).save(tmp_filename)
        os.replace(tmp_filename, filename)

if __name__ == '__main__':
    print('Did you mean to call this on main? If so, delete this line.')
    exit(-1)
    ids = ['30321'] 
    rotation_enum_value = int(0)
    pose_anim = int(808)
    rotation = ROTATIONS[rotation_enum_value]

    handle_request(ids, rotation, pose_anim)

