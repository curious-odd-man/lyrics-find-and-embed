import logging
import unittest

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

library_path = r'D:\My Music\Music'


class StorageTests(unittest.TestCase):

    def test_overall_stats(self):
        pass


if __name__ == '__main__':
    unittest.main()

"""
Total artists: xxx
Total albums: xxx
Total songs: xxx
Total artists full with lyrics: xxx (yyy%)
Total albums full with lyrics: xxx (yyy%)
Total songs with lyrics: xxx (yyy%)
Missing lyrics stats:
   <<<artist>>> (yyy%)
        <<<album>>> (yyy%)
            <<<song1>>>
            <<<song2>>>
"""
