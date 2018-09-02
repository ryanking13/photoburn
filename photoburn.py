import argparse
from collections import Counter
import hashlib
import multiprocessing as mp
import pathlib
import sys
import uuid
import warnings
from PIL import Image
import imagehash as ih
import groups
from iterview import iterview


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
    parser.add_argument('-b', '--best', default='ALL',
                        help='best selection mechanism (filesize, resolution, all)')
    args = parser.parse_args()
    return args


def calculate_hash(file):
    _hash = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _hash = ih.phash(Image.open(str(file)))
    except:
        print('[-] hash calculation fail on', str(file))

    return file, _hash


def calculate_hashes(files):
    debug('Start calculating hashes...')
    hashes = {}

    filtered_files = filter(lambda x: x.is_file() and x.suffix.lower() in IMAGE_EXTS, files)
    pool = mp.Pool(processes=mp.cpu_count())
    _hashes = pool.map(calculate_hash, filtered_files)

    for h in _hashes:
        if h[1] is None:
            continue
        hashes[h[0]] = h[1]

    return hashes


def group_hashes(hashes):
    debug('Start grouping hashes...')

    g = groups.Groups(hashes.keys())
    for k1, v1 in iterview(hashes.items()):
        img_id = g.find(str(k1))
        for k2, v2 in hashes.items():
            if k1 == k2:
                continue
            if v1 - v2 <= HASH_THRESHOLD:
                g.unite(img_id, str(k2))

    # groups with only one element are filtered
    group_result = g.get()
    cnt = Counter(group_result.values())
    filtered = [item for item in group_result.items()]
    filtered = filter(lambda g: True if cnt[g[1]] > 1 else False, filtered)

    return filtered

    # groups = {}
    #
    # # TODO: if grouping is two slow, change it to union find algorithm
    # for k1, v1 in hashes.items():
    #     img_id = groups.get(k1, None)
    #     if img_id is None:
    #         # generate new group name
    #         img_id = uuid.uuid4().hex[:16]
    #         groups[k1] = img_id
    #
    #     for k2, v2 in hashes.items():
    #         if k1 == k2:
    #             continue
    #         if v1 - v2 <= HASH_THRESHOLD:
    #             original_id = groups.get(k2, None)
    #             if original_id is None:
    #                 groups[k2] = img_id
    #             else:
    #                 for g in groups:
    #                     if groups[g] == original_id:
    #                         groups[g] = img_id
    #
    # # groups with only one element are filtered
    # cnt = Counter(groups.values())
    # filtered = [g for g in groups.items()]
    # filtered = filter(lambda g: True if cnt[g[1]] > 1 else False, filtered)
    #
    # # don't need to sort
    # # filtered_groups = sorted(sorted_groups, key=lambda g: (g[1], g[0]))
    #
    # return filtered


def gather_images(base_path, groups):
    debug('Start gathering images with same group...')

    paths = set()
    for group in groups:
        # make directory by group name
        group_path = base_path / hashlib.md5(group[1].encode()).hexdigest()
        group_path.mkdir(exist_ok=True)
        paths.add(group_path)

        # move original image to group directory
        path = pathlib.Path(group[0])
        path.rename(group_path / path.name)

    return paths


def update_best(best, img, file_size, width, height, best_algorithm='ALL'):
    best_algorithm = best_algorithm.upper()

    if best_algorithm not in ('ALL', 'FILESIZE', 'RESOLUTION'):
        print('[-] Undefined best selection algorihtm: {}, using default'.format(best_algorithm))
        best_algorithm = 'ALL'

    if best_algorithm == 'ALL':
        # if this image is better than previous best
        if file_size >= best['file_size']and\
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
            return True
        # not better and not worse, cannot determine
        else:
            return False

    elif best_algorithm == 'FILESIZE':
        # if this image is better than previous best
        if file_size >= best['file_size']:
            best.update({
                'file': img,
                'file_size': file_size,
                'width': width,
                'height': height,
            })
        # if this image is worse than previous best
        elif file_size < best['file_size']:
            return True
        # not better and not worse, cannot determine
        else:
            return False

    elif best_algorithm == 'RESOLUTION':
        # if this image is better than previous best
        if width >= best['width'] and height >= best['height']:
            best.update({
                'file': img,
                'file_size': file_size,
                'width': width,
                'height': height,
            })
        # if this image is worse than previous best
        elif width <= best['width'] and height <= best['height']:
            return True
        # not better and not worse, cannot determine
        else:
            return False

    return True


def clear_similars(original_path, target_path, best_algorithm):
    print('Removing similar images on "{}"'.format(target_path))

    best = dict(file=None, file_size=0, width=0, height=0)

    # find best image
    for img in pathlib.Path(target_path).glob('*'):
        file_size = img.stat().st_size
        # TODO: calculateing width and height without opening?
        width, height = Image.open(str(img)).size

        success = update_best(best, img, file_size, width, height, best_algorithm)
        if not success:
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
            clear_similars(target_path, group_directory, args.best)


if __name__ == '__main__':
    main()
