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
    print(index["tree"])
    index["tree"].printTree(2)


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
    prefix = os.path.splitext(os.path.basename(indexFile))[0]
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
            fullPath = prefix + path[1:]
            sums.append((fullPath, hash))
    if VERBOSE:
        print("Read {} entries: {}".format(len(sums), indexFile))
    return sums


def createIndex(shasums):
    filesByHash = defaultdict(list)
    for path, shasum in shasums:
        filesByHash[shasum].append(path)

    # Create a nested TreeNode structure
    fileNodesByHash = defaultdict(list)
    tree = TreeNode(fileNodesByHash, "")
    for hash, files in filesByHash.items():
        for file in files:
            node = tree
            dirParts = file.split("/")
            for dirPart in dirParts[:-1]:
                node = node.subfolder(dirPart)
            node.file(dirParts[-1], hash)

    if VERBOSE:
        print("Of {} entries, {} are unique".format(len(shasums), len(filesByHash.keys())))
        print("Of {} entries, {} are unique".format(len(shasums), len(fileNodesByHash.keys())))

    return dict(filesByHash=filesByHash, tree=tree, fileNodesByHash=fileNodesByHash)


class TreeNode(object):

    def __init__(self, fileNodesByHash, name):
        self._parent = None
        self._name = name
        self._dirs = {}
        self._fileNodesByHash = fileNodesByHash
        self._files = {}
        self._stats = None

    def subfolder(self, name):
        node = self._dirs.get(name)
        if node is None:
            node = TreeNode(self._fileNodesByHash, name)
            node._parent = self

            self._dirs[name] = node

            self._stats = None
        return node

    def file(self, name, hash):
        node = self._files.get(name)
        if node is None:
            node = FileNode(self._fileNodesByHash, name, hash)
            node._parent = self

            self._files[name] = node
            self._fileNodesByHash[hash].append(node)

            self._stats = None
        return node

    def fullPath(self):
        if self._parent is None:
            return self._name
        return "{}/{}".format(self._parent.fullPath(), self._name)

    def stats(self):
        if self._stats is None:
            totalFiles = len(self._files)
            totalDupes = 0
            for node in self._dirs.values():
                nodeStats = node.stats()
                totalFiles += nodeStats["files"]
                totalDupes += nodeStats["dupes"]
            for node in self._files.values():
                if node.isDupe():
                    totalDupes += 1
            self._stats = dict(files=totalFiles, dupes=totalDupes)
        return self._stats

    def printTree(self, depth):
        # Some stats and printing we don't care about
        if self._name in [".git", "@eaDir"]:
            return

        # Print self
        print(self)

        if depth == 0:
            return

        # Stop traversal if no dupes exist
        if self.stats()["dupes"] == 0:
            return

        for node in self._dirs.values():
            node.printTree(depth - 1)

    def __repr__(self):
        stats = self.stats()
        return "{}: {} files, {} dupe ({:.2f}%)".format(
               self.fullPath(),
               stats["files"],
               stats["dupes"],
               stats["dupes"] * 100 / stats["files"])


class FileNode(object):

    def __init__(self, fileNodesByHash, name, hash):
        self._fileNodesByHash = fileNodesByHash
        self._name = name
        self._hash = hash

    def fullPath(self):
        return "{}/{}".format(self._parent.fullPath(), self._name)

    def isDupe(self):
        return len(self._fileNodesByHash[self._hash]) > 1

if __name__ == "__main__":
    main()
