import os

# Mirrors the dummy properties used by the Java AgentApplicationTests
# (@SpringBootTest(properties = {...})) so Settings() never needs real
# credentials during the test suite.
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("OPENAI_CHAT_MODEL", "gpt-5.6-luna")
os.environ.setdefault("OPENAI_REASONING_EFFORT", "low")
os.environ.setdefault("TAVILY_API_KEY", "dummy")
os.environ.setdefault("DYNAMODB_ENDPOINT", "http://localhost:8000")
os.environ.setdefault("AWS_REGION", "ap-northeast-2")
os.environ.setdefault("SPRING_PROFILES_ACTIVE", "local")
