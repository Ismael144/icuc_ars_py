import redis
import json
import numpy as np
import base64

class DataCacher:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def save_entry(self, staff_id, fullname, images, img_encodings):
        key = f"staff:{staff_id}"
        data = {
            "staff_id": staff_id,
            "fullname": fullname,
            "images": json.dumps(images),
            "img_encodings": json.dumps([self._serialize_ndarray(arr) for arr in img_encodings])
        }
        self.redis_client.hmset(key, data)

    def get_entry(self, staff_id):
        key = f"staff:{staff_id}"
        data = self.redis_client.hgetall(key)
        if not data:
            return None
        
        # Decode byte responses and convert images and img_encodings from JSON strings
        decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}
        decoded_data['images'] = json.loads(decoded_data['images'])
        decoded_data['img_encodings'] = [self._deserialize_ndarray(arr) for arr in json.loads(decoded_data['img_encodings'])]
        return decoded_data

    def update_entry(self, staff_id, fullname=None, images=None, img_encodings=None):
        key = f"staff:{staff_id}"
        data = {}
        if fullname is not None:
            data['fullname'] = fullname
        if images is not None:
            data['images'] = json.dumps(images)
        if img_encodings is not None:
            data['img_encodings'] = json.dumps([self._serialize_ndarray(arr) for arr in img_encodings])
        
        if data:
            self.redis_client.hmset(key, data)

    def delete_entry(self, staff_id):
        key = f"staff:{staff_id}"
        self.redis_client.delete(key)
    
    def list_all_entries(self):
        keys = self.redis_client.keys('staff:*')
        all_entries = []
        for key in keys:
            data = self.get_entry(key.split(b':')[1].decode('utf-8'))
            if data:
                all_entries.append(data)
        return all_entries

    def rewrite_database(self, entries):
        # Clear the existing database
        self.redis_client.flushdb()
        
        # Save new entries
        for entry in entries:
            self.save_entry(entry['id'], entry['fullname'], entry['images'], entry['img_encodings'])

    def _serialize_ndarray(self, array):
        """Serialize a numpy array to a base64 encoded string."""
        if isinstance(array, list):
            array = np.array(array)
        return base64.b64encode(array.tobytes()).decode('utf-8')

    def _deserialize_ndarray(self, array_str):
        """Deserialize a base64 encoded string to a numpy array."""
        if array_str is None:
            return None
        try:
            return np.frombuffer(base64.b64decode(array_str.encode('utf-8')), dtype=np.float64)  # Adjust dtype as needed
        except Exception as e:
            print(f"Error decoding array: {e}")
            return None

# Example usage
if __name__ == "__main__":
    manager = DataCacher()

    # Create a sample ndarray
    sample_array = np.array([1.0, 2.0, 3.0])

    # Add an entry
    manager.save_entry(123, "John Doe", ["image1.png", "image2.png"], [sample_array])

    # Get an entry
    entry = manager.get_entry(123)
    print("Entry:", entry)

    # Update an entry
    new_sample_array = np.array([4.0, 5.0, 6.0])
    manager.update_entry(123, fullname="John D.", images=["image1_updated.png", "image3.png"], img_encodings=[new_sample_array])

    # List all entries
    all_entries = manager.list_all_entries()
    print("All Entries:", all_entries)

    # Rewrite database with new data
    new_data = [
        {"staff_id": 124, "fullname": "Jane Smith", "images": ["image4.png"], "img_encodings": [sample_array.tolist()]},
        {"staff_id": 125, "fullname": "Bob Brown", "images": ["image5.png"], "img_encodings": [new_sample_array.tolist()]}
    ]
    manager.rewrite_database(new_data)

    # List all entries after rewrite
    all_entries = manager.list_all_entries()
    print("All Entries after rewrite:", all_entries)
