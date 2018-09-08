# Photoburn

Find duplicate & similar photos and group/remove it.

[phash](http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html) is used for comparing images.

## Requirements

- Python >= 3.5

## How to Run

```
# install dependencies
# pip install -r requirements.txt

python photoburn.py <images_directory>
```

```
usage: photoburn.py [-h] [-p] [-v] dir

positional arguments:
  dir             target directory

optional arguments:
  -h, --help      show this help message and exit
  -p, --preserve  do not delete images, only do grouping
  -v, --verbose   print all debug messages
```
