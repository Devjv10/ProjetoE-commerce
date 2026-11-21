from scripts.seed_mongodb import seed as mongo
from scripts.seed_redis import seed as redis
from scripts.seed_neo4j import seed as neo4j

if __name__ == '__main__':
    mongo()
    redis()
    neo4j()
