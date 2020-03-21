#!/usr/bin/env python3

import argparse
from collections import defaultdict, namedtuple
import os
import os.path
import pickle
import re
import sqlite3
import sys


def loadDb():
    return sqlite3.connect("index.db")


def createHashesTable(db):
    db.execute("CREATE TABLE hashes(path text, hash text)")


def createDupesTable(db):
    dupes = set()
    for result in db.execute("SELECT p1.hash"
                            " FROM hashes p1 JOIN hashes p2"
                            " WHERE p1.hash == p2.hash"
                            "   AND p1.path != p2.path"):
        dupes.add((result[0],))
    db.execute("CREATE TABLE dupes(hash text)")
    db.executemany("INSERT INTO dupes(hash) VALUES (?)", dupes)


""" Return an entry (hash, path) for every dupe
"""
def getDuplicates(db):
    dupes = set()
    for result in db.execute("SELECT h.hash, h.path"
                            " FROM hashes h JOIN dupes d"
                            " WHERE h.hash == d.hash"):
        dupes.add(result)
    return dupes


""" Return an entry (hash, path1, path2) for every dupe pair within the given path

This will find all pairs where at least one of the pair exist within the path.
"""
def getDuplicatePairs(db, path):
    dupes = set()
    for result in db.execute("SELECT p1.hash, p1.path, p2.path"
                            " FROM hashes p1 JOIN hashes p2"
                            " WHERE p1.hash == p2.hash"
                            "   AND p1.path != p2.path"
                            "   AND p1.path LIKE ?",
                            (path + "%", )):
        hash, p1, p2 = result[0], result[1], result[2]
        dupes.add((hash, min(p1, p2), max(p1, p2)))
    return dupes


""" Given a sequence of (hash, path), return a dict of {hash:set(paths)}
"""
def groupDuplicates(input):
    dupes = defaultdict(set)
    for hash, path in input:
        dupes[hash].add(path)
    return dupes


class Path(object):

    def __init__(self, path):
        self._path = path

    def commonParent(self, otherPath):
        return None

    def __repr__(self):
        return self._path


def readShasumFile(indexFile):
    prefix = "/" + os.path.splitext(os.path.basename(indexFile))[0]
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
    return sums


def _refresh(args):
    # Wipe the database
    if os.path.isfile("index.db"):
        os.remove("index.db")
    db = loadDb()
    try:
        # Create and fill hashes table
        with db:
            db.execute("CREATE TABLE hashes(path text, hash text)")
        folder = "shasums"
        for file in os.listdir("shasums"):
            filePath = os.path.join(folder, file)
            if not os.path.isfile(filePath):
                continue
            if not filePath.endswith(".txt"):
                continue
            with db:
                hashes = readShasumFile(filePath)
                if args.verbose:
                    print("Read {} entries: {}".format(len(hashes), filePath))
                db.executemany("INSERT INTO hashes(path, hash) VALUES (?, ?)", hashes)

        with db:
            createDupesTable(db)

        return True
    finally:
        db.close()


def _dupePairsForPath(args):
    db = loadDb()
    try:
        with db:
            for hash, path1, path2 in getDuplicatePairs(db, args.path):
                print("{} {}".format(path1, path2))
        return True
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process for dupes")
    parser.add_argument("--verbose", action="store_true", help="Print lots of messages")
    tasks = parser.add_subparsers(title="Commands")

    task = tasks.add_parser("refresh", help="Refresh the whole database from shasums folder")
    task.set_defaults(func=_refresh)

    task = tasks.add_parser("dupes")
    task.add_argument("path", type=str)
    task.set_defaults(func=_dupePairsForPath)

    args = parser.parse_args()

    if "func" not in args:
        parser.print_usage()
        sys.exit(1)

    if not args.func(args):
        sys.exit(1)
