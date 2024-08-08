from YAMLConfigParser import YAMLConfigParser
from Logger import Logger

config_parser = YAMLConfigParser('data_storage/config.yaml')
logger = Logger()

def concat_to_base_uri(extended_uri: str) -> str: 
    base_uri = config_parser.get_option('api', 'endpoint')
    full_uri = base_uri + extended_uri
    
    return full_uri 