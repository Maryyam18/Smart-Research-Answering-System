import requests
res = requests.post("http://127.0.0.1:8000/answer", json={"query": "What are recent advancements in NLP models?"})
print(res.status_code)
print(res.json())
