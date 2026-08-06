import os
from pymongo import MongoClient


class MongoDB:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo_db = os.getenv("MONGO_DB", "shitstorm_db")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]

    def collection(self, name: str):
        return self.db[name]

    def close(self):
        self.client.close()