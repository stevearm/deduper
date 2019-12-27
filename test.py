#!/usr/bin/env python3
import unittest

import process

class TestProcess(unittest.TestCase):

    def setUp(self):
        self.db = process.loadDb()

    def tearDown(self):
        self.db.close()
        self.db = None

    def testGetDuplicates(self):
        with self.db:
            dupes = process.getDuplicates(self.db)
            expectedDupe = ("043ad92262a2b0593176aa94b7ff02d5",
                            "/misc/to-be-deleted/dropbox-photos/2012.07 Alberta Reunion/07.06 Train tunnels/DSCN1116.JPG")
            self.assertTrue(expectedDupe in dupes)

    def testGroupDuplicates(self):
        dupes = [("hash1", "/path1"),
                 ("hash1", "/path2"),
                 ("hash1", "/path3"),
                 ("hash4", "/path4"),
                 ("hash4", "/path5")]
        groupedDuplicates = process.groupDuplicates(dupes)
        self.assertEqual(groupedDuplicates.keys(), set(["hash1", "hash4"]))
        self.assertEqual(groupedDuplicates["hash1"], set(["/path1", "/path2", "/path3"]))
        self.assertEqual(groupedDuplicates["hash4"], set(["/path4", "/path5"]))

        with self.assertRaises(TypeError):
            process.groupDuplicates(None)


if __name__ == '__main__':
    unittest.main()
