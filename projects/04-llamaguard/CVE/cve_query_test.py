from cve_vectordb import CVEVectorDB
from cve_vectordb import CVEEntry

db = CVEVectorDB()
db.load('cve_index.faiss', 'cve_data.pkl')
results = db.search('Improper memory management in C++ can lead to buffer overflow vulnerabilities')

print(results)