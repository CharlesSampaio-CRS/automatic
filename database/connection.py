from pymongo import MongoClient

client = MongoClient('mongodb+srv://SpaceWalletRootUser:VvhEnifxJUkA4918@clusterspacewallet.kwbw5gv.mongodb.net/')
db = client['AutomaticInvest']

def connection_mongo(collection):
    return db[collection]

