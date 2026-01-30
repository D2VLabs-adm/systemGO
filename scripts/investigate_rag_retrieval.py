#!/usr/bin/env python3
"""
Investigation script to analyze RAG retrieval patterns.

This script helps diagnose why RAG might be returning metadata/profiles
instead of actual data chunks.

Usage:
    python investigate_rag_retrieval.py --project-id 1 --query "What regions are in the sales data?"
"""
import sys
import requests
from pathlib import Path
from typing import Dict, List, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rangerio_tests.config import RANGERIO_BACKEND_URL, VECTORDB_DIR


def analyze_rag_retrieval(project_id: int, query: str, backend_url: str = RANGERIO_BACKEND_URL):
    """
    Analyze what ChromaDB retrieves for a query and what gets sent to the LLM.
    
    Args:
        project_id: RangerIO project ID
        query: Query to test
        backend_url: Backend API URL
    """
    print(f"\n{'='*80}")
    print(f"RAG RETRIEVAL INVESTIGATION")
    print(f"{'='*80}")
    print(f"Project ID: {project_id}")
    print(f"Query: {query}")
    print(f"Backend: {backend_url}")
    print(f"{'='*80}\n")
    
    # 1. Query RAG API
    print("📊 Step 1: Querying RAG API...")
    try:
        response = requests.post(
            f"{backend_url}/rag/query",
            json={
                "project_id": project_id,
                "prompt": query,
                "assistant_mode": False,  # Basic mode for baseline
                "deep_search_mode": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        result = response.json()
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        
        print(f"✓ Answer length: {len(answer)} characters")
        print(f"✓ Number of sources: {len(sources)}")
        print(f"\nAnswer preview (first 200 chars):")
        print(f"{answer[:200]}...")
        
    except Exception as e:
        print(f"❌ Failed to query RAG API: {e}")
        return
    
    # 2. Analyze sources composition
    print(f"\n{'='*80}")
    print("📊 Step 2: Analyzing Source Composition...")
    print(f"{'='*80}\n")
    
    profile_sources = [s for s in sources if s.get('type') == 'data_source_profile']
    data_sources = [s for s in sources if s.get('type') == 'data_source_data']
    other_sources = [s for s in sources if s.get('type') not in ('data_source_profile', 'data_source_data')]
    
    print(f"Profile chunks: {len(profile_sources)}")
    print(f"Data row chunks: {len(data_sources)}")
    print(f"Other chunks: {len(other_sources)}")
    
    # 3. Query ChromaDB directly for comparison
    print(f"\n{'='*80}")
    print("📊 Step 3: Querying ChromaDB Directly...")
    print(f"{'='*80}\n")
    
    try:
        from chromadb import PersistentClient
        
        # Get data sources for this project
        ds_response = requests.get(f"{backend_url}/datasources", params={"project_id": project_id})
        if ds_response.status_code == 200:
            data_source_ids = [ds['id'] for ds in ds_response.json()]
            print(f"✓ Project has {len(data_source_ids)} data sources: {data_source_ids}")
        else:
            print(f"❌ Failed to get data sources: {ds_response.status_code}")
            data_source_ids = []
        
        if not data_source_ids:
            print("⚠️  No data sources found for this project")
            return
        
        # Connect to ChromaDB
        client = PersistentClient(path=str(VECTORDB_DIR))
        collection = client.get_collection("rangerio_docs")
        
        # Get all documents for these data sources
        print(f"\nFetching all documents for data sources...")
        all_profile_docs = []
        all_data_docs = []
        
        for ds_id in data_source_ids:
            # Get profiles
            profile_results = collection.get(
                where={"$and": [
                    {"data_source_id": ds_id},
                    {"type": "data_source_profile"}
                ]},
                include=["documents", "metadatas"]
            )
            
            # Get data rows
            data_results = collection.get(
                where={"$and": [
                    {"data_source_id": ds_id},
                    {"type": "data_source_data"}
                ]},
                include=["documents", "metadatas"]
            )
            
            if profile_results.get("documents"):
                all_profile_docs.extend(profile_results["documents"])
            if data_results.get("documents"):
                all_data_docs.extend(data_results["documents"])
        
        # Calculate composition
        profile_chars = sum(len(doc) for doc in all_profile_docs)
        data_chars = sum(len(doc) for doc in all_data_docs)
        total_chars = profile_chars + data_chars
        
        print(f"\n{'='*80}")
        print("📊 ChromaDB Composition Analysis")
        print(f"{'='*80}")
        print(f"Profile documents: {len(all_profile_docs)} ({profile_chars:,} chars)")
        print(f"Data documents: {len(all_data_docs)} ({data_chars:,} chars)")
        print(f"Total: {total_chars:,} chars")
        
        if total_chars > 0:
            profile_pct = (profile_chars / total_chars) * 100
            data_pct = (data_chars / total_chars) * 100
            print(f"\nRatio:")
            print(f"  Profile: {profile_pct:.1f}%")
            print(f"  Data: {data_pct:.1f}%")
            
            if profile_pct > 30:
                print(f"\n⚠️  WARNING: Profile makes up {profile_pct:.1f}% of content!")
                print(f"    This may cause LLM to focus on metadata instead of actual data.")
        
        # Sample a few documents
        print(f"\n{'='*80}")
        print("📄 Sample Documents")
        print(f"{'='*80}")
        
        if all_profile_docs:
            print(f"\nProfile Document Sample (first 300 chars):")
            print(f"{all_profile_docs[0][:300]}...")
        
        if all_data_docs:
            print(f"\nData Row Document Sample (first 300 chars):")
            print(f"{all_data_docs[0][:300]}...")
        
    except ImportError:
        print("⚠️  ChromaDB not available in test environment")
    except Exception as e:
        print(f"❌ Failed to query ChromaDB directly: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Summary and recommendations
    print(f"\n{'='*80}")
    print("📊 DIAGNOSIS & RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    # Check if answer seems to be metadata-focused
    metadata_keywords = ['file', 'structure', 'schema', 'columns', 'format', 'metadata', 'profile']
    answer_lower = answer.lower()
    metadata_mentions = sum(1 for kw in metadata_keywords if kw in answer_lower)
    
    if metadata_mentions >= 3:
        print("🔴 ISSUE DETECTED: Answer appears to be metadata-focused")
        print(f"   Found {metadata_mentions} metadata-related keywords")
        print("\n   Likely causes:")
        print("   1. Profile chunks are ranking higher in semantic search")
        print("   2. Context building prioritizes profile over data")
        print("   3. LLM prompt doesn't emphasize data rows")
        print("\n   Recommended fixes:")
        print("   - Enhance LLM prompt to prioritize data rows")
        print("   - Reorder context to put data rows first")
        print("   - Add visual separators between data and metadata")
    else:
        print("✅ Answer seems to use actual data (low metadata keyword count)")
    
    # Check answer length
    if len(answer) > 500:
        print(f"\n⚠️  Answer is lengthy ({len(answer)} chars)")
        print("   Consider dynamic max_tokens based on data size")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Investigate RAG retrieval patterns")
    parser.add_argument("--project-id", type=int, required=True, help="Project ID to investigate")
    parser.add_argument("--query", type=str, required=True, help="Query to test")
    parser.add_argument("--backend-url", type=str, default=RANGERIO_BACKEND_URL, help="Backend API URL")
    
    args = parser.parse_args()
    
    analyze_rag_retrieval(
        project_id=args.project_id,
        query=args.query,
        backend_url=args.backend_url
    )






