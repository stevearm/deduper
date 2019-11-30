#!/usr/bin/env python3

import argparse
from collections import defaultdict, namedtuple
import os
import os.path
import pickle
import re

VERBOSE=False

def main():
    parser = argparse.ArgumentParser(description="Process for dupes")
    parser.add_argument("--verbose", action="store_true", help="Print lots of messages")
    parser.add_argument("--shasums", action="store_true", help="Refresh shasums.pickle")
    parser.add_argument("--index", action="store_true", help="Refresh index.pickle")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE=args.verbose

    shasums = createOrUseCache(args.shasums, "shasums.pickle", readShasums)

    index = createOrUseCache(args.index, "index.pickle", createIndex, shasums)

    return False
    createMasterList()
    index = getMasterList()
    statTree = createDuplicatePercentageTree(index)
    print(statTree[4].keys())
    printStatTree(statTree)


def createOrUseCache(override, filename, function, *posArgs):
    if override or not os.path.isfile(filename):
        value = function(*posArgs)
        with open(filename, "wb") as pickleFile:
            pickle.dump(value, pickleFile)
        return value
    with open(filename, "rb") as pickleFile:
        return pickle.load(pickleFile)


def readShasums():
    folder = "shasums"
    sums = list()
    for file in os.listdir(folder):
        filePath = os.path.join(folder, file)
        if not os.path.isfile(filePath):
            continue
        if not filePath.endswith(".txt"):
            continue
        sums = sums + readShasumFile(filePath)
    if VERBOSE:
        print("Total of {} entries".format(len(sums)))
    return sums


def readShasumFile(indexFile):
    baseFolder = os.path.dirname(indexFile)
    sums = list()
    with open(indexFile, "r") as indexFileStream:
        pattern = re.compile(r"^([a-f0-9]{32}) +(\./.*)$")
        for line in indexFileStream:
            if line.startswith("Started indexing") or \
               line.startswith("Finished indexing") or \
               line.endswith("folder-index.txt") or \
               line.endswith("nohup.out") or \
               line.endswith(".DS_Store") or \
               line.strip() == "":
                continue
            parsed = re.match(pattern, line)
            if parsed is None:
                raise Exception("In {} could not parse: {}".format(indexFile, line))
            hash = parsed.group(1)
            path = parsed.group(2)
            fullPath = baseFolder + path[1:]
            sums.append((fullPath, hash))
    if VERBOSE:
        print("Read {} entries: {}".format(len(sums), indexFile))
    return sums


def createIndex(shasums):
    hashes = set()
    filesByHash = defaultdict(list)
    for path, shasum in shasums:
        filesByHash[shasum].append(path)
        hashes.add(shasum)

    # Create a nested TreeNode structure where the .files dict maps the filename
    # to a list of full paths for the same hash
    TreeNode = namedtuple("TreeNode", ["dirs", "files"])
    def newNode():
        return TreeNode(dict(), dict())

    tree = TreeNode(dict(), dict())
    for hash, files in filesByHash.items():
        for file in files:
            node = tree
            dirParts = path.split("/")
            for dirPart in dirParts[:-1]:
                nextNode = node.dirs.get(dirPart)
                if nextNode is None:
                    nextNode = newNode()
                    node.dirs[dirPart] = nextNode
                node = nextNode
            node.files[dirParts[-1]] = files

    if VERBOSE:
        print("Of {} entries, {} are unique".format(len(shasums), len(hashes)))
    return dict(filesByHash=filesByHash)


if __name__ == "__main__":
    main()
