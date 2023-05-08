import shutil
import sys
import datetime
import os

SAVED_BACKUPS_COUNT = 7

src = sys.argv[1]
dest = sys.argv[2]
files = os.listdir(dest)
files_sorted = sorted(files)
for file in files_sorted[:-(SAVED_BACKUPS_COUNT-1)]:
    path = os.path.join(dest, file)
    if os.path.isdir(path):
        shutil.rmtree(path)


shutil.copytree(src, dest + "/" + str(datetime.datetime.now()))
