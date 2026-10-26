import redis

client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)

client.set("codeguard_test", "Redis is working!")

print(client.get("codeguard_test"))