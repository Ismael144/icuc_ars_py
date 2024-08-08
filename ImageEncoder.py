import os
import cv2
import time
import numpy as np
import face_recognition


class ImageEncoder:
    def __init__(self):
        self.encoded_images = []

    def load_image(self, img_path):
        try:
            if not os.path.exists(img_path): 
                return np.zeros((500, 500, 3), dtype=np.uint8)
            
            img = cv2.imread(img_path)

            return img
        except Exception as e:
            print(f"Error loading image: {e}")
            # Return a default image (e.g., a blank image)
            return np.zeros((500, 500, 3), dtype=np.uint8)

    def encode_image(self, img):
        try:
            encode = face_recognition.face_encodings(img)            
            return encode
        except Exception as e:
            print(f"Error encoding image: {e}")


    def encode_images_threaded(self, images: list):
        start_time = time.time()
        
        encoded_images = []
        
        for img_path in images: 
            encoded_image = self.encode_image(self.load_image(img_path))
            encoded_images.append(encoded_image)

        stop_time = time.time()
        print("Finish Time:", round(stop_time - start_time, 2), "Seconds")

        return encoded_images


    def get_encoded_images(self):
        return self.encoded_images
