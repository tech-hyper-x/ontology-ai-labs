"""Ch5: 저장된 예시 벡터로 BM25/vector/hybrid 비교. API 호출·DB 변경 없음."""
import argparse
from mfg_bom_agent.graph.client import driver_session
from mfg_bom_agent.graph.cq import run_cq
p=argparse.ArgumentParser();p.add_argument("--example",choices=["CQ-11","G42","G44","G45"],default="CQ-11");p.add_argument("--source",choices=["readme","issue","all"],default=None);p.add_argument("--k",type=int,choices=range(1,21),default=5);a=p.parse_args()
with driver_session() as d:
    meta=d.execute_query("MATCH (m:LabMeta) RETURN m.embedding_provider AS provider,m.embedding_dim AS dimensions").records
    print("색인",[r.data() for r in meta],"예시",a.example,"문서범위",a.source,"k",a.k)
    for mode in ["bm25","vector","hybrid"]:
        print("\nMODE",mode)
        rows=run_cq(d,"CQ-15",example=a.example,q=None,qvec=None,mode=mode,k=a.k,source=a.source)
        for rank,r in enumerate(rows,1):
            print(rank,r["doc_id"],"BM25",r["bm25_rank"],r["bm25_score"],"vector",r["vector_rank"],r["vector_score"],"RRF",r["score"],"parts",[(x["sku"],x["assemblies"]) for x in r["parts"]])
