import os
import json
import sqlite3
import datetime
import requests
from typing import Union, List, Dict
from init import config_parser, concat_to_base_uri
from SSCProtocolController import SSCProtocolController

class AttendanceRegistryController:
    def __init__(self):
        # Initialize the IIEC Protocol
        self.ssc_protocol_controller = SSCProtocolController()
        # Initialize SQLite
        self.sqliteManager = sqlite3.connect('data_storage/attendances.db')
        self.cursor = self.sqliteManager.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS attendance (staff_id INTEGER, date_attended TEXT, arrival_time TEXT, departure_time TEXT)')
        self.sqliteManager.commit()


    def fetch_all_attendances(self) -> Dict[str, any]: 
        self.cursor.execute("SELECT * FROM attendance")
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        return results
    
    
    def get_attendance_record(self, staff_id: int, date_attended: str = 'today') -> List:
        if date_attended == 'today':
            date_attended = datetime.datetime.now().strftime('%Y-%m-%d')
        elif date_attended == 'yesterday':
            date_attended = (datetime.now() - datetime.datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self.cursor.execute("SELECT * FROM attendance WHERE staff_id = ? AND date_attended = ?", [staff_id, date_attended])
        row = self.cursor.fetchone()
        
        if row:
            columns = [column[0] for column in self.cursor.description]
            attendance_record = dict(zip(columns, row))
            return attendance_record
        else:
            return []
    
    
    def staff_is_registered(self, staff_id: int, date_attended: str = "today") -> bool:
        attendance_record = self.get_attendance_record(staff_id=staff_id, date_attended=date_attended)
        print(attendance_record)
        
        return True if len(attendance_record) else False


    def migrate_data_from_sqlite_to_server_db(self) -> bool:
        from datetime import datetime
        all_attendances = self.fetch_all_attendances()

        all_attendances = [{"date_attended" if k == "date" else k: v for k, v in elem.items()} for elem in all_attendances]
        all_attendances = [{"staff_data_id" if k == "staff_id" else k: v for k, v in elem.items()} for elem in all_attendances]

        # Do a bulk register of attendance 
        api_response = requests.put(concat_to_base_uri('/attendance/register?mode=bulk'), json=all_attendances)

        json_res = api_response.json()
        
        now = datetime.now()
        is_midnight = now.hour == 0 and now.minute == 0

        print("The attendance data was migrated successfuly")
        
        if json_res.get('is_successful') and is_midnight:
            # Truncate all the data
            self.cursor.execute("DELETE FROM attendance")
            self.sqliteManager.commit()


    def register_attendance(self, staff_id: int) -> bool:
        if not self.staff_is_registered(staff_id):
            current_time = datetime.datetime.now().strftime("%H:%M")
            self.cursor.execute('INSERT INTO attendance (staff_id, date_attended, arrival_time) VALUES (?, DATE(\'now\'), ?)', (staff_id, current_time))
            self.sqliteManager.commit()
            print('Attendance created offline successfully')
    

    def is_staff_attendance_finalized(self, id: int) -> bool:
        attendance_result = self.get_attendance_record(id)

        if not len(attendance_result) or attendance_result['departure_time'] is None:
            return False
        
        return True


    def finalize_attendance(self, staff_id: int) -> bool:
        if not self.is_staff_attendance_finalized(staff_id):
            # Finalize attendance offline
            current_departure_time = datetime.datetime.now().strftime("%H:%M")

            self.cursor.execute('UPDATE attendance SET departure_time = ? WHERE staff_id = ? AND date_attended = DATE(\'now\')', (current_departure_time, staff_id))
            self.sqliteManager.commit()
            print('Attendance finalized offline successfully')


    def time_comparison(self, time_to_compare1: str, time_to_compare2: str = 'now'):
        # Parse the input times
        try:
            time1 = datetime.datetime.strptime(time_to_compare1, "%H:%M").time()
            if time_to_compare2 == 'now':
                time2 = datetime.datetime.now().time()
            else:
                time2 = datetime.datetime.strptime(time_to_compare2, "%H:%M").time()
        except ValueError:
            return False  # Return False if the input times are not in the correct format

        # Check if time1 is later than time2
        if time1 > time2:
            return True
        return False
    
    
    def is_check_in_or_out_time(self) -> str: 
        if self.is_check_in_time(): 
            return 'Check In'
        
        return 'Check Out'
    
    
    def is_check_in_time(self): 
        attendance_settings = self.get_attendance_settings()
        arrival_time = attendance_settings.get('arrival_time')
        departure_time = attendance_settings.get('departure_time')

        return self.time_comparison(arrival_time) == False and self.time_comparison(departure_time) == True


    def is_check_out_time(self): 
        attendance_settings = self.get_attendance_settings()
        departure_time = attendance_settings.get('departure_time')

        return self.time_comparison(departure_time) == False
 

    def get_attendance_settings(self) -> Dict[str, str]: 
        return {
            "arrival_time": config_parser.get_option('attendance_settings', 'check_in_time'), 
            "departure_time": config_parser.get_option('attendance_settings', 'check_out_time'),  
        }
        

    def get_time_difference(self, time_str1: str, time_str2: str) -> Dict[str, Union[str, int]]:
        from datetime import datetime
        """
        This function calculates the time difference between two times in the format 'HH:MM'.

        Args:
            time_str1: The first time string in 'HH:MM' format.
            time_str2: The second time string in 'HH:MM' format.

        Returns:
            A dictionary containing:
                - 'time_difference': A string representing the time difference in a human-readable format.
                - 'hours_passed': The number of hours passed.
                - 'minutes_passed': The number of minutes passed.
        """

        try:
            time1 = datetime.strptime(time_str1, "%H:%M").time()
            time2 = datetime.strptime(time_str2, "%H:%M").time()
        except ValueError:
            print("Invalid format")
            return "--:--"

        time_delta = abs(datetime.combine(datetime.today(), time2) - datetime.combine(datetime.today(), time1))
        total_seconds = time_delta.total_seconds()

        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)

        time_diff_str = ""
        if hours > 0:
            time_diff_str += f"{hours} hour{'s' if hours > 1 else ''}"
        if minutes > 0:
            if time_diff_str:
                time_diff_str += " and "
                time_diff_str += f"{minutes} minute{'s' if minutes > 1 else ''}"

        time_difference_dict = {
            'hours': hours,
            'minutes': minutes,
            'time_difference': time_diff_str,
        }

        return time_difference_dict


    def convert_to_12_hour(self, time24: str) -> str:
        # Splitting the input into hours and minutes
        hours, minutes = map(int, time24.split(':'))
        
        # Determining AM/PM and converting hours
        period = 'am'
        if hours >= 12:
            period = 'pm'
            if hours > 12:
                hours -= 12
        
        # Special case: midnight (00:00) and noon (12:00)
        if hours == 0:
            hours = 12  # 12 AM
        elif hours == 12:
            hours = 12  # 12 PM
        
        # Formatting the output as "h:mm AM/PM"
        return f"{hours}:{minutes:02} {period}"

# attendance_registry_controller = AttendanceRegistryController()
# print(attendance_registry_controller.get_attendance_settings())

# I want you to fix my code, use the right conditioning, and also use common practices of coding, handle every error, so that it doesn't cause errors, write a processRunner.py that will run the system and the 