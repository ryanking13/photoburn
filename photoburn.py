import argparse
from collections import Counter
import pathlib
import sys
import uuid
from PIL import Image
import imagehash as ih

VERBOSE = False

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
HASH_THRESHOLD = 5

def debug(msg):
    if VERBOSE:
        print(msg)


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='target directory')
    parser.add_argument('-p', '--preserve', action='store_true',
                        help='do not delete images, only do grouping')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print all debug messages')

    args = parser.parse_args()
    return args


def calculate_hashes(files):
    debug('Start calculating hashes...')
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
    debug('Start grouping hashes...')
    groups = {}

    # TODO: if grouping is two slow, change it to union find algorithm
    for k1, v1 in hashes.items():
        img_id = groups.get(k1, None)
        if img_id is None:
            # generate new group name
            img_id = uuid.uuid4().hex[:16]
            groups[k1] = img_id

        for k2, v2 in hashes.items():
            if k1 == k2:
                continue
            if v1 - v2 <= HASH_THRESHOLD:
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


def gather_images(base_path, groups):
    debug('Start gathering images with same group...')

    paths = set()
    for group in groups:
        # make directory by group name
        group_path = base_path / group[1]
        group_path.mkdir(exist_ok=True)
        paths.add(group_path)

        # move original image to group directory
        group[0].rename(group_path / group[0].name)

    return paths


def clear_similars(original_path, target_path):
    print('Removing similar images on "{}"'.format(target_path))

    best = dict(file=None, file_size=0, width=0, height=0)

    # find best image
    for img in pathlib.Path(target_path).glob('*'):
        file_size = img.stat().st_size
        # TODO: calculateing width and height without opening?
        width, height = Image.open(str(img)).size

        # if this image is better than previous best
        if file_size  >= best['file_size']and\
                width >= best['width'] and height >= best['height']:
            best.update({
                'file': img,
                'file_size': file_size,
                'width': width,
                'height': height,
            })
        # if this image is worse than previous best
        elif file_size < best['file_size'] and \
                width <= best['width'] and height <= best['height']:
            continue
        # not better and not worse, cannot determine
        else:
            print('[-] Cannot determine best on "{}", skipped'.format(target_path))
            return

    # move best image to original directory
    debug('Best image on {}: {}'.format(target_path, best['file'].name))
    best['file'].rename(original_path / best['file'].name)

    # clear other images
    for img in pathlib.Path(target_path).glob('*'):
        img.unlink()
        debug('Removed: {}'.format(str(img)))

    target_path.rmdir()


def main():
    global VERBOSE

    args = parse_args()
    VERBOSE = args.verbose

    target_directory = args.dir
    target_path = pathlib.Path(target_directory)

    # no recursive search (TODO: better recursive?)
    target_files = target_path.glob('*')

    hashes = calculate_hashes(target_files)
    groups = group_hashes(hashes)
    group_directories = gather_images(target_path, groups)

    # if preserve option is not set, remove duplicate images
    if not args.preserve:
        for group_directory in group_directories:
            clear_similars(target_path, group_directory)


if __name__ == '__main__':
    main()
