import yaml

class YAMLConfigParser:
    def __init__(self, config_file):
        self.config_file = config_file

    def parse_config(self):
        try:
            with open(self.config_file, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Config file not found: {self.config_file}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            return {}

    def get_option(self, section, option):
        self.config = self.parse_config()  # Reparse the config file every time
        return self.config.get(section, {}).get(option)

    def set_option(self, section, option, value):
        self.config = self.parse_config()  # Reparse the config file before setting the option
        if section not in self.config:
            self.config[section] = {}
        self.config[section][option] = value
        self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)