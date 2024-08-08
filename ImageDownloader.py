import os
import requests
from PIL import Image 
from io import BytesIO
from rembg import remove
from init import config_parser, logger
from concurrent.futures import ThreadPoolExecutor, as_completed

class ImageDownloader:
    def __init__(self, downloaded_images_dir: str):
        self.downloaded_images_dir = downloaded_images_dir

    def _get_image_name(self, img_url: str):
        # Since the images downloaded are in png format, we change the image extension to png
        img_path = img_url.split("/")[::-1]
        png_img_path = os.path.splitext(img_path[0])[0] + ".png"
        return png_img_path
    

    def download_and_rem_bg(self, img_url: str) -> bool:
        try:
            response = requests.get(img_url)
            if response.status_code == 200:
                image_data = response.content
                input_image = Image.open(BytesIO(image_data))
                
                # Resize the image while preserving its quality
                resized_image = input_image.resize((640, 480), resample=Image.BICUBIC)
                output = remove(resized_image)
                image_name = os.path.join(self.downloaded_images_dir, self._get_image_name(img_url))
                output.save(image_name)
                print("Image saved successfully!")
                return True
            else:
                logger.error(f"Failed to download image from {img_url}.")
                print(f"Failed to download image from {img_url}.")
                return False
        except Exception as e:
            logger.error(f"Error downloading image from {img_url}: {e}")
            print(f"Error downloading image from {img_url}: {e}")
            return False


    def download_images_concurrently(self, img_urls: list):
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.download_and_rem_bg, url) for url in img_urls]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing image: {e}")
                    logger.error(f"Error processing image: {e}")

