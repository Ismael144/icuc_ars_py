# Process #2
import os
import cv2
import time
import cvzone
import datetime
import numpy as np
import face_recognition
from init import config_parser 
from DataCacher import DataCacher
from AttendanceRegistryController import AttendanceRegistryController
import psutil
import os
import time
import json

class FaceRecognitionSystem: 
    def __init__(self): 
        self.attendance_registry_controller = AttendanceRegistryController()        
        self.redis_cacher_class = DataCacher()
        
        self.modeType = 0
        self.counter = 0
        self.id = -1        

    def get_cache_data(self): 
        encodeListKnown = []
        cache_data = self.redis_cacher_class.list_all_entries()

        # Filtering out data without images
        cache_data = list(filter(lambda entry: len(entry['images']), cache_data))
        
        if len(cache_data):
            if not len(cache_data[0]['img_encodings']):
                return False

        staffIds = []
        fullNames = []

        for item in cache_data:
            if not len(item["img_encodings"]):
                continue
            
            for encoding in item["img_encodings"]:
                encodeListKnown.append(encoding)
                
                staffIds.append(item['staff_id'])
                fullNames.append(item['fullname'])

        
        # Function to check if all keys are present and extract values
        retrieved_cache_data = {
            "ids": staffIds,
            "fullNames": fullNames, 
            "data": cache_data,
            "encodeListKnown": list(filter(lambda enc: len(enc), encodeListKnown))
        }
        
        return retrieved_cache_data 


    @staticmethod
    def _get_image_name(img_url: str):
        img_path = img_url.split("/")[::-1]
        return img_path[0]
    
    
    def get_attendance_settings(self): 
        attendance_settings = {
            "arrival_time": config_parser.get_option("attendance_settings", "check_in_time"),
            "departure_time": config_parser.get_option("attendance_settings", "check_out_time")
        }
        
        return attendance_settings


    def main(self):
        cap = cv2.VideoCapture(0)
        cap.set(3, 640)
        cap.set(4, 480)

        imgBackground = cv2.imread('Resources/background.png')

        # Importing the mode images into a list
        folderModePath = 'Resources/Modes'
        modePathList = os.listdir(folderModePath)
        imgModeList = []
        for path in modePathList:
            imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))
        while True:
            is_registration = False 
            _, img = cap.read()

            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            faceCurFrame = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)
            
            # This code means, if it tries the system tries to access blank data
            if self.get_cache_data() == False: 
                print("The cached data for running the system might be corrupt or empty")
                continue

            imgBackground[162:162 + 480, 55:55 + 640] = img
            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]

            # Show Check In Or Out Text
            cvzone.putTextRect(imgBackground, self.attendance_registry_controller.is_check_in_or_out_time().upper(), (590, 85), scale=2)
            cv2.imshow("ICUC Face Recognition Attendance System", imgBackground)
            cv2.waitKey(1)
            
            if faceCurFrame:
                for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                    print(self.get_cache_data()['encodeListKnown'], "\n\n\n")
                    matches = face_recognition.compare_faces(self.get_cache_data()['encodeListKnown'], encodeFace)
                    faceDis = face_recognition.face_distance(self.get_cache_data()['encodeListKnown'], encodeFace)

                    matchIndex = np.argmin(faceDis)

                    recognized_staff_id = None 
                    
                    if matches[matchIndex]:
                        # print("Known Face Detected")
                        y1, x2, y2, x1 = faceLoc
                        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                        bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                        imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                        
                        recognized_staff_id = self.get_cache_data()['ids'][matchIndex]
                        
                        if self.counter == 0:
                            cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                            cv2.imshow("ICUC Face Recognition Attendance System", imgBackground)
                            cv2.waitKey(1)
                            self.counter = 1
                            self.modeType = 1
                    
                    else: 
                        cvzone.putTextRect(imgBackground, "Unknown", (275, 400))
                        cv2.imshow("ICUC Face Recognition Attendance System", imgBackground)
                        cv2.waitKey(1)
                        self.counter = 1
                        self.modeType = 1
                
                if recognized_staff_id is None:
                    print("Face Not Recognized...")
                    self.counter = 0
                    self.modeType = 0
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
        
                if self.counter != 0 and recognized_staff_id is not None:
                    if self.counter == 1:
                        # Get the Data
                        staffMemberInfo = []
                        for staffId in self.get_cache_data()['ids']:
                            if staffId == recognized_staff_id:
                                print(staffId)
                                for item in self.get_cache_data()['data']:
                                    if item['staff_id'] == recognized_staff_id: 
                                        staffMemberInfo = item

                        print(staffMemberInfo)

                        staffImage = cv2.imread(staffMemberInfo['images'][0])

                        staffImage = cv2.resize(staffImage, (216, 216))

                        if self.attendance_registry_controller.is_check_out_time() and self.attendance_registry_controller.is_staff_attendance_finalized(recognized_staff_id):
                            self.counter = 0
                            self.modeType = 1
                            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
                            cv2.putText(imgBackground, str(staffMemberInfo['fullname']), (900, 310), cv2.FONT_HERSHEY_DUPLEX, 1, (100, 100, 100), 2)

                        if self.attendance_registry_controller.is_check_out_time() and not self.attendance_registry_controller.is_staff_attendance_finalized(recognized_staff_id):  
                            print(f"Finalized Attendance... {recognized_staff_id}")
                            self.attendance_registry_controller.finalize_attendance(recognized_staff_id)
                            self.counter = 0
                            self.modeType = 1
                            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
                            cvzone.putTextRect(imgBackground, "REGISTERED", (910, 119), scale=2)
                            cv2.imshow("ICUC Face Recognition Attendance System", imgBackground)
                            cv2.waitKey(1)
                            
                        if self.modeType == 2:
                            imgBackground[175:175 + 216, 909:909 + 216] = staffImage
                            
                        if self.attendance_registry_controller.staff_is_registered(recognized_staff_id) and self.attendance_registry_controller.is_check_in_time():
                            print("Staff Is Already Registered")
                            self.counter = 0
                            self.modeType = 3
                            
                        # Check if its arrival_time or departure_time
                        if self.attendance_registry_controller.is_check_in_time(): 
                            if not self.attendance_registry_controller.staff_is_registered(recognized_staff_id): 
                                self.attendance_registry_controller.register_attendance(recognized_staff_id)
                                print("Is Registering...")
                                self.counter = 0
                                self.modeType = 1
                                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
                                is_registration = True 
                                
                        elif self.attendance_registry_controller.is_check_out_time():
                            if self.attendance_registry_controller.is_staff_attendance_finalized(recognized_staff_id):
                                print("Check Out Time")
                                print("Staff Is Already Registered")
                                self.counter = 0
                                self.modeType = 1
                                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType] 
                                cv2.putText(imgBackground, str(staffMemberInfo['fullname']), (900, 300), cv2.FONT_HERSHEY_DUPLEX, 1, (100, 100, 100), 2)

                        if self.attendance_registry_controller.is_check_in_time(): 
                            if not self.attendance_registry_controller.staff_is_registered(recognized_staff_id):
                                self.modeType = 1
                                self.counter = 0
                                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
                                

                    if self.modeType != 3:
                        if 10 < self.counter < 20:
                            if recognized_staff_id is not None: 
                                self.modeType = 1
                            else: 
                                self.modeType = 0

                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
                        
                        if self.counter <= 10:
                            attendance_record = self.attendance_registry_controller.get_attendance_record(recognized_staff_id)
                            print(attendance_record)
                            if isinstance(attendance_record, dict):
                                settings_arrival_time = self.get_attendance_settings().get('arrival_time')
                                departure_time = attendance_record.get('departure_time')
                                time_late = self.attendance_registry_controller.get_time_difference(settings_arrival_time, attendance_record['arrival_time'])
                                print("Time Comparison: ", settings_arrival_time, attendance_record['arrival_time'])
                                cv2.putText(imgBackground, str(time_late['time_difference']), (910, 119), cv2.FONT_HERSHEY_DUPLEX, 0.6, (50, 50, 50), 1)
                                arrival_time_for_record = attendance_record['arrival_time']
                                cv2.putText(imgBackground, str(f'Arrived: {self.attendance_registry_controller.convert_to_12_hour(arrival_time_for_record)}'), (930, 500), cv2.FONT_HERSHEY_DUPLEX, 0.6, (50, 50, 50), 1)

                                if departure_time is not None: 
                                    cv2.putText(imgBackground, str(f"Departed: {self.attendance_registry_controller.convert_to_12_hour(attendance_record['departure_time'])}"), (930, 555), cv2.FONT_HERSHEY_DUPLEX, 0.6, (50, 50, 50), 1)
                                
                            cv2.putText(imgBackground, str("YES"), (900, 630), cv2.FONT_HERSHEY_DUPLEX, 0.6, (100, 100, 100), 1)
                            cv2.putText(imgBackground, str("Staff"), (995, 630), cv2.FONT_HERSHEY_DUPLEX, 0.6, (100, 100, 100), 1)
                            cv2.putText(imgBackground, str(datetime.datetime.now().strftime("%d/%m/%Y")), (1095, 630), cv2.FONT_HERSHEY_DUPLEX, 0.6, (100, 100, 100), 1)

                            cvzone.putTextRect(imgBackground, self.attendance_registry_controller.is_check_in_or_out_time().upper(), (590, 85), scale=2)

                            (w, h), _ = cv2.getTextSize(staffMemberInfo['fullname'], cv2.FONT_HERSHEY_DUPLEX, .75, 1)
                            offset = (414 - w) // 2
                            cv2.putText(imgBackground, str(staffMemberInfo['fullname']), (780 + offset, 450),
                                        cv2.FONT_HERSHEY_DUPLEX, 1, (50, 50, 50), 1)

                            imgBackground[175:175 + 216, 909:909 + 216] = staffImage


                    if is_registration: 
                        time.sleep(5) 
                        print("Is Registration")
                    
                        self.counter += 1

                        if self.counter >= 20:
                            self.counter = 0
                            self.modeType = 0
                            staffMemberInfo = []
                            staffImage = []
                            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[self.modeType]
            else:
                self.modeType = 0
                self.counter = 0

            # cv2.imshow("Webcam", img)
            cv2.imshow("ICUC Face Recognition Attendance System", imgBackground)
            cv2.waitKey(1)

face_recognition_app = FaceRecognitionSystem()

# Function to get the memory usage of the current process
def get_memory_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # Convert bytes to MB

# Function to log memory usage to a file
def log_memory_usage(filename="memory_usage.json", interval=5):
    memory_data = []  # Initialize an empty list to store memory data
    try:
        with open(filename, "a") as log_file:
            while True:
                mem_usage = get_memory_usage()
                entry = {"fr_system": {
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "memory_usage_mb": round(mem_usage, 2)
                    }
                }
                memory_data.append(entry)  # Add the entry to the list
                log_file.seek(0)  # Go to the start of the file for overwriting
                json.dump(memory_data, log_file, indent=4)  # Write JSON data
                log_file.flush()  # Ensure data is written to disk
                time.sleep(interval)
    except KeyboardInterrupt:
        print("Memory logging stopped.")

if __name__ == "__main__":
    # Start the memory logging in a separate thread
    from threading import Thread
    monitoring_thread = Thread(target=log_memory_usage)
    monitoring_thread.daemon = True
    monitoring_thread.start()

    # Run your main script
    face_recognition_app.main()  # Assuming your_script has a main() function
