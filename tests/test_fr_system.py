import unittest 
from ..FaceRecognitionSystem import FaceRecognitionSystem

class TestFRecognitionSysMethodTest(unittest.TestCase): 
    def setUp(self): 
        super().setUp()
        self.fr_system = FaceRecognitionSystem()
        
    
    def test_encodelistknown_from_cache(self):
        encode_list_known = self.fr_system.get_cache_data()['encodeListKnown']

        contains_empty_encodings = False 

        for encoding in encode_list_known: 
            if len(encoding) == 0: 
                contains_empty_encodings = True
        
        self.assertFalse(contains_empty_encodings)
        
        
if __name__ == '__main__': 
    unittest.main()