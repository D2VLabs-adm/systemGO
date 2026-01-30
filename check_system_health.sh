#!/bin/bash
# System Health Check for Safe Testing
# Checks memory, CPU, and backend status before running heavy tests

echo ""
echo "🏥 SYSTEM HEALTH CHECK"
echo "=================================="
echo ""

# 1. Memory Check
echo "💾 Memory Status:"
vm_stat | grep -E "Pages free|Pages active|Pages inactive|Pages wired" | awk '{print "  " $0}'
free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
free_mb=$((free_pages * 4096 / 1024 / 1024))
echo "  Available RAM: ~${free_mb} MB"

if [ $free_mb -lt 2000 ]; then
    echo "  ⚠️  WARNING: Low memory (<2GB free). Consider closing apps."
else
    echo "  ✅ Memory OK"
fi
echo ""

# 2. CPU Check
echo "🔥 CPU Load:"
top -l 1 | grep "CPU usage" | awk '{print "  " $0}'
echo ""

# 3. Backend Check
echo "🔌 Backend Status:"
if curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "  ✅ Backend responding on port 9000"
    
    # Check backend memory usage
    backend_pid=$(ps aux | grep "python -m api.server" | grep -v grep | awk '{print $2}' | head -1)
    if [ ! -z "$backend_pid" ]; then
        backend_mem=$(ps -o rss= -p $backend_pid | awk '{print int($1/1024)}')
        echo "  Backend PID: $backend_pid (using ~${backend_mem}MB)"
    fi
else
    echo "  ❌ Backend NOT responding!"
    echo "  Please start with: cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp && source venv/bin/activate && python -m api.server"
    exit 1
fi
echo ""

# 4. Recommendation
echo "📋 Recommendation:"
if [ $free_mb -gt 4000 ]; then
    echo "  ✅ System is healthy - safe to run full test suite"
elif [ $free_mb -gt 2000 ]; then
    echo "  ⚠️  Run tests in staggered mode (use run_mode_tests_safely.sh)"
else
    echo "  ❌ Close some applications first, or run small test subsets only"
fi
echo ""






