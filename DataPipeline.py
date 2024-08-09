# Process #1

import os 
import time
import json
import requests
from typing import List
from ImageEncoder import ImageEncoder
from ImageDownloader import ImageDownloader
from DataCacher import DataCacher
from init import config_parser, concat_to_base_uri, logger
from SSCProtocolController import SSCProtocolController
from AttendanceRegistryController import AttendanceRegistryController

class DataPipeline:
    def __init__(self): 
        self.image_encoder = ImageEncoder()
        self.downloaded_images_dir = config_parser.get_option('storage', 'donwloaded_images_dir')
        self.data_cacher = DataCacher()
        self.ssc_protocol_controller = SSCProtocolController()
        self.image_downloader = ImageDownloader(self.downloaded_images_dir)
        self.attendance_registry_controller = AttendanceRegistryController()
        
        
    def start_scout(self): 
        """Monitors changes of data and then immediately updates
         Compare the hashes, if not the same 
         Refetch the data 

        Returns:
            None
        """
        
        while True: 
            print("Checking For Server Connectivity...")
            if not self.ssc_protocol_controller.check_server_connectivity(): 
                print("Could not connect To Server")
                time.sleep(5)
                continue

            # Migrate attendance data 
            self.attendance_registry_controller.migrate_data_from_sqlite_to_server_db()
            
            # Compare hashes
            if self.compare_hashes():
                time.sleep(5)
                continue
            else: 
                # Updating cached data 
                self.update_images_dir()
                results = self.get_encodings_and_associate_to_api_records()
                print(f"\n{self.image_downloader.get_downloaded_images_count()} Images Were Successfully Downloaded\n")
                
                # Cache the results
                print("Caching Results...")
                self.data_cacher.rewrite_database(results)
                
                print(f"\n{len(results)} Results Were Cached To Redis...\n")
                
    
    @staticmethod 
    def request_get(url: str) -> str: 
        """
        Makes requests to given API 
        
        Returns
            str 
        """
        try: 
            request = requests.get(url)
            response_content = request.text
        except Exception as e: 
            print(e)
            
        return response_content
    
    
    def fetch_api_staff_data(self) -> dict:
        staff_api_data = requests.get(concat_to_base_uri('/staff_data/index'))
        api_response = staff_api_data.json()
        
        return api_response
    
    def compare_hashes(self):
        api_hash = self.request_get(concat_to_base_uri('/staff_data/hash'))
        api_hash_dict = json.loads(api_hash)
        local_hash = config_parser.get_option('api', 'hash')
        
        if local_hash != api_hash_dict['hash']: 
            print("Changed Hash From", api_hash_dict['hash'], "To", local_hash)
            # update the hash to latest
            config_parser.set_option('api', 'hash', api_hash_dict['hash'])
            return False 
        
        # If hash from server did not change
        return True


    def get_images_from_api(self): 
        staff_api_images = self.fetch_api_staff_data()
        all_enlisted_images = list(map(lambda x: x.get('images'), staff_api_images))
        merged_images_list = sum(all_enlisted_images, [])
                            
        return merged_images_list


    def get_and_download_images(self):
        try:
            merged_images_list = self.get_images_from_api()
            self.image_downloader.download_images_concurrently(merged_images_list)
        except Exception as e:
            logger.error("An Error Occured while downloading the images:", e)


    @staticmethod
    def _get_image_name(img_url: str):
        # Since the images downloaded are in png format, we change the image extension to png
        img_path = img_url.split("/")[::-1]
        png_img_path = os.path.splitext(img_path[0])[0] + ".png"
        return png_img_path

    
    def get_downloaded_images(self):
        """
            Reads directory with staff images 
            
            returns: 
                list
        """
        images = os.listdir(self.downloaded_images_dir)
        return images
    
    
    def remove_downloaded_image(self, img_name: str) -> bool: 
        if not os.path.exists(os.path.join(self.downloaded_images_dir, img_name)): 
            return False
            
        os.remove(os.path.join(self.downloaded_images_dir, img_name))
        return True 
    

    def update_images_dir(self) -> None:
        """
        Deletes and adds images into the directory depending on the ones on the API
        
        returns: 
            None 
        """
        images_from_api = self.get_images_from_api()
        downloaded_images = self.get_downloaded_images()
        list_of_images_to_download = []

        for api_image in images_from_api:
            if os.path.exists(os.path.join(self.downloaded_images_dir, api_image)):
                continue
            list_of_images_to_download.append(api_image)

        # If image is not in the new images that came from the api, gets removed.
        for downloaded_image in downloaded_images:
            if downloaded_image in images_from_api:
                continue
            self.remove_downloaded_image(downloaded_image)
            
        # Donwload the images concurrently
        self.image_downloader.download_images_concurrently(list_of_images_to_download)
     
            
    def get_encodings_and_associate_to_api_records(self): 
        api_data = self.fetch_api_staff_data()
        api_data = list(filter(lambda item: len(item['images']), api_data))
        print(api_data)
        for api_record in api_data:
            if len(api_record.get('images')) < 1:
                logger.info(f"{api_record['fullname']} has no images")
                continue

            # Get the images and encode them, after that then return them
            image_path_names = list(map(lambda image: os.path.join("images", self._get_image_name(image)), api_record['images']))
            api_record['img_encodings'] = self.image_encoder.encode_images_threaded(image_path_names)
            image_path_names = list(filter(lambda img: os.path.exists(img), image_path_names))
            api_record['images'] = image_path_names
        
        return api_data


    def check_cached_data_validity(self, cached_data: List[dict]): 
        if len(cached_data):
            return False
    
        corrupt_data_counter = 0
        for item in cached_data: 
            corrupt_data_counter += 1 if len(item['img_encodings']) else 0
            
        if len(cached_data) == corrupt_data_counter: 
            return True 
        elif int(len(cached_data) - corrupt_data_counter) < 2: 
            return True 
        else: 
            return False


images_manager = DataPipeline()
images_manager.start_scout()




