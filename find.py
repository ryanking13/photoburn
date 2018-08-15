import argparse
from collections import Counter
import pathlib
import sys
import uuid
from PIL import Image
import imagehash as ih

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
THRESHOLD = 5


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='target directory')
    parser.add_argument('-p', '--preserve', default=False, action='store_const', const=True,
                        help='do not delete images, only do grouping')

    args = parser.parse_args()
    return args


def calculate_hashes(files):
    hashes = {}

    for file in files:
        if not (file.is_file() and file.suffix.lower() in IMAGE_EXTS):
            continue

        try:
            hash = ih.phash(Image.open(str(file)))
            hashes[file] = hash
        except:
            print('[-] hash calculation fail on', str(file))

    return hashes


def group_hashes(hashes):
    groups = {}

    # TODO: if grouping is two slow, change it to union find algorithm
    for k1, v1 in hashes.items():
        img_id = groups.get(k1, None)
        if img_id is None:
            img_id = uuid.uuid4().hex[:10]
            groups[k1] = img_id

        for k2, v2 in hashes.items():
            if k1 == k2:
                continue
            if v1 - v2 <= THRESHOLD:
                original_id = groups.get(k2, None)
                if original_id is None:
                    groups[k2] = img_id
                else:
                    for g in groups:
                        if groups[g] == original_id:
                            groups[g] = img_id

    # groups with only one element are filtered
    cnt = Counter(groups.values())
    filtered = [g for g in groups.items()]
    filtered = filter(lambda g: True if cnt[g[1]] > 1 else False, filtered)

    # don't need to sort
    # filtered_groups = sorted(sorted_groups, key=lambda g: (g[1], g[0]))

    return filtered


def main():
    args = parse_args()
    target_directory = args.dir
    target_path = pathlib.Path(target_directory)
    target_files = target_path.glob('**')

    hashes = calculate_hashes(target_files)
    groups = group_hashes(hashes)

    for group in groups:
        group_path = target_path / group[1]
        group_path.mkdir(exist_ok=True)
        group[0].rename(group_path / group[0].name)


if __name__ == '__main__':
    main()
