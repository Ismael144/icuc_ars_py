import DataCacher
redis_cacher_class = DataCacher.DataCacher()
cache_data = redis_cacher_class.list_all_entries()
print(cache_data)