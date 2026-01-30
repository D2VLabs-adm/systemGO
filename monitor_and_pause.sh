#!/bin/bash
echo "🎯 Monitoring for test 1/5 completion..."
echo "Will automatically pause before test 2/5 starts"
echo ""

while true; do
  # Check if test 2/5 is about to start or test 1/5 passed
  if tail -200 /tmp/throttled_full_run.log | grep -q "Benchmark Test 2/5"; then
    echo "🛑 Test 2/5 detected - stopping script now!"
    pkill -f "run_throttled.sh"
    pkill -f "pytest.*test_mode_performance"
    sleep 2
    echo ""
    echo "✅ Paused successfully!"
    echo "📊 Benchmark data saved to: reports/benchmarks/"
    echo ""
    tail -30 /tmp/throttled_full_run.log | grep -E "(PASS|Test 1/5|Test 2/5)"
    break
  fi
  
  if tail -200 /tmp/throttled_full_run.log | grep -q "test_mode_response_time_distribution PASSED"; then
    echo "✅ Test 1/5 PASSED - waiting for cooldown before stopping..."
    sleep 35  # Wait for cooldown
    pkill -f "run_throttled.sh"
    pkill -f "pytest.*test_mode_performance"
    echo "🛑 Stopped before test 2/5"
    break
  fi
  
  echo "⏳ Still running test 1/5... ($(date +%H:%M:%S)) - Queries: $(grep 'POST /rag/query' /tmp/backend_fresh.log 2>/dev/null | wc -l | xargs)"
  sleep 15
done
