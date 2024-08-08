import requests 
import init

# SSCProtocolController stands for Simultaneous Server Connectivity Protocol 
class SSCProtocolController: 
    def check_server_connectivity(self): 
        # Make a request to the server
        try: 
            test_request = requests.get(init.concat_to_base_uri('/staff_data/index'))
            return True
        except requests.ConnectionError as e: 
            print("Unable to connect to server...")
            return False

