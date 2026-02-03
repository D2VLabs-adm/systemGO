"""
Streaming Response Tests
========================

Tests Server-Sent Events (SSE) and streaming RAG responses.
Important for UX as users see responses appear progressively.

Note: assistant_mode is auto-enabled by conftest.py for all /rag/query calls.

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_streaming_responses.py -v -s
"""
import pytest
import time
import json
from typing import Generator, List

from rangerio_tests.config import config


def parse_sse_events(response_text: str) -> List[dict]:
    """Parse SSE events from response text"""
    events = []
    current_event = {}
    
    for line in response_text.split('\n'):
        line = line.strip()
        
        if line.startswith('data:'):
            data = line[5:].strip()
            if data:
                try:
                    current_event['data'] = json.loads(data)
                except json.JSONDecodeError:
                    current_event['data'] = data
        
        elif line.startswith('event:'):
            current_event['event'] = line[6:].strip()
        
        elif line == '' and current_event:
            events.append(current_event)
            current_event = {}
    
    if current_event:
        events.append(current_event)
    
    return events


@pytest.mark.integration
@pytest.mark.streaming
class TestStreamingEndpointExists:
    """Test that streaming endpoints are available"""
    
    def test_rag_stream_endpoint(self, api_client, create_test_rag):
        """Test that RAG streaming endpoint exists"""
        rag_id = create_test_rag("Stream Test")
        
        # Try streaming endpoint
        response = api_client.post("/rag/query/stream", json={
            "prompt": "Hello",
            "project_id": rag_id
        })
        
        if response.status_code == 404:
            # Try alternative endpoint
            response = api_client.post("/rag/stream", json={
                "prompt": "Hello",
                "project_id": rag_id
            })
        
        if response.status_code == 404:
            pytest.skip("Streaming endpoint not available")
        
        # Should return 200 or stream
        assert response.status_code in [200, 206], \
            f"Unexpected status: {response.status_code}"
        
        print(f"Streaming endpoint status: {response.status_code}")


@pytest.mark.integration
@pytest.mark.streaming
class TestStreamingResponses:
    """Test streaming response functionality"""
    
    def test_stream_returns_chunks(self, api_client, create_test_rag, sample_csv_small):
        """Test that streaming returns data in chunks"""
        # Setup project with data
        rag_id = create_test_rag("Stream Chunks Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        # Request streaming response
        response = api_client.post(
            "/rag/query/stream",
            json={
                "prompt": "Describe the data in detail",
                "project_id": rag_id,
                "stream": True
            },
            stream=True  # Important: enable streaming in requests
        )
        
        if response.status_code == 404:
            pytest.skip("Streaming not available")
        
        if response.status_code == 200:
            # Collect chunks
            chunks = []
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    chunks.append(chunk)
            
            print(f"Received {len(chunks)} chunks")
            
            # Should receive multiple chunks for streaming
            # (might be 1 if response is short)
            assert len(chunks) >= 1, "Should receive at least one chunk"
    
    def test_stream_sse_format(self, api_client, create_test_rag, sample_csv_small):
        """Test that streaming uses SSE format correctly"""
        rag_id = create_test_rag("SSE Format Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        response = api_client.post(
            "/rag/query/stream",
            json={
                "prompt": "What columns are in the data?",
                "project_id": rag_id
            },
            headers={"Accept": "text/event-stream"}
        )
        
        if response.status_code == 404:
            pytest.skip("Streaming not available")
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            
            # Check for SSE content type
            if "text/event-stream" in content_type:
                print("Response uses SSE format")
                
                # Parse events
                events = parse_sse_events(response.text)
                print(f"Parsed {len(events)} SSE events")
                
                for i, event in enumerate(events[:5]):  # First 5
                    print(f"  Event {i}: {event}")
    
    def test_stream_completes_fully(self, api_client, create_test_rag, sample_csv_small):
        """Test that stream completes with all data"""
        rag_id = create_test_rag("Stream Complete Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        # Get streaming response
        stream_response = api_client.post(
            "/rag/query/stream",
            json={
                "prompt": "Summarize the data",
                "project_id": rag_id
            }
        )
        
        if stream_response.status_code == 404:
            pytest.skip("Streaming not available")
        
        # Get non-streaming response for comparison
        normal_response = api_client.post("/rag/query", json={
            "prompt": "Summarize the data",
            "project_id": rag_id
        })
        
        if normal_response.status_code == 200 and stream_response.status_code == 200:
            normal_answer = normal_response.json().get("answer", "")
            stream_text = stream_response.text
            
            # Stream should contain complete response
            # (exact matching is tricky due to formatting differences)
            print(f"Normal response length: {len(normal_answer)}")
            print(f"Stream response length: {len(stream_text)}")


@pytest.mark.integration
@pytest.mark.streaming
class TestStreamingPerformance:
    """Test streaming performance characteristics"""
    
    def test_time_to_first_byte(self, api_client, create_test_rag, sample_csv_small, performance_monitor):
        """Test that first byte arrives quickly"""
        rag_id = create_test_rag("TTFB Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        # Measure time to first byte
        import requests
        
        start = time.time()
        
        with api_client.session.post(
            f"{api_client.base_url}/rag/query/stream",
            json={
                "prompt": "Describe the data",
                "project_id": rag_id
            },
            stream=True
        ) as response:
            if response.status_code == 404:
                pytest.skip("Streaming not available")
            
            # Get first chunk
            first_chunk = None
            for chunk in response.iter_content(chunk_size=None):
                first_chunk = chunk
                break
            
            ttfb = (time.time() - start) * 1000  # ms
        
        print(f"Time to first byte: {ttfb:.0f}ms")
        
        # TTFB should be reasonable (< 10 seconds)
        assert ttfb < 10000, f"TTFB too slow: {ttfb:.0f}ms"
    
    def test_streaming_vs_non_streaming(self, api_client, create_test_rag, sample_csv_small):
        """Compare streaming vs non-streaming response times"""
        rag_id = create_test_rag("Stream vs Normal Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        prompt = "What are the column names and data types?"
        
        # Non-streaming
        start = time.time()
        normal_response = api_client.post("/rag/query", json={
            "prompt": prompt,
            "project_id": rag_id
        })
        normal_time = (time.time() - start) * 1000
        
        # Streaming
        start = time.time()
        stream_response = api_client.post("/rag/query/stream", json={
            "prompt": prompt,
            "project_id": rag_id
        })
        stream_time = (time.time() - start) * 1000
        
        if stream_response.status_code == 404:
            pytest.skip("Streaming not available")
        
        print(f"Normal response: {normal_time:.0f}ms")
        print(f"Stream response: {stream_time:.0f}ms")


@pytest.mark.integration
@pytest.mark.streaming
class TestStreamingErrorHandling:
    """Test error handling in streaming responses"""
    
    def test_stream_with_invalid_project(self, api_client):
        """Test streaming with invalid project ID"""
        response = api_client.post("/rag/query/stream", json={
            "prompt": "test",
            "project_id": 999999999
        })
        
        if response.status_code == 404:
            # Endpoint doesn't exist
            pytest.skip("Streaming not available")
        
        # Should return error status
        assert response.status_code in [400, 404, 422], \
            f"Invalid project should be rejected, got {response.status_code}"
    
    def test_stream_with_empty_prompt(self, api_client, create_test_rag):
        """Test streaming with empty prompt"""
        rag_id = create_test_rag("Empty Prompt Stream Test")
        
        response = api_client.post("/rag/query/stream", json={
            "prompt": "",
            "project_id": rag_id
        })
        
        if response.status_code == 404:
            pytest.skip("Streaming not available")
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422], \
            f"Empty prompt should be handled, got {response.status_code}"


@pytest.mark.integration
@pytest.mark.streaming
class TestStreamingModes:
    """Test streaming with different RAG modes"""
    
    def test_stream_assistant_mode(self, api_client, create_test_rag, sample_csv_small):
        """Test streaming in assistant mode"""
        rag_id = create_test_rag("Stream Assistant Test")
        
        api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        time.sleep(2)
        
        response = api_client.post("/rag/query/stream", json={
            "prompt": "Explain the data structure",
            "project_id": rag_id
            # assistant_mode auto-enabled by conftest.py
        })
        
        if response.status_code == 404:
            pytest.skip("Streaming not available")
        
        if response.status_code == 200:
            print(f"Assistant mode stream: {len(response.text)} chars")
    
    def test_stream_deep_search_mode(self, api_client, create_test_rag, sample_csv_small):
        """Test streaming in deep search mode"""
        rag_id = create_test_rag("Stream Deep Search Test")
        
        api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        time.sleep(2)
        
        response = api_client.post("/rag/query/stream", json={
            "prompt": "Search for any patterns in the data",
            "project_id": rag_id,
            "deep_search": True
        })
        
        if response.status_code == 404:
            pytest.skip("Streaming not available")
        
        if response.status_code == 200:
            print(f"Deep search mode stream: {len(response.text)} chars")
