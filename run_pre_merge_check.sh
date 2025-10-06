#!/bin/bash
# Run pre-merge verification on Railway PostgreSQL database

echo "============================================"
echo "Running Pre-Merge Verification..."
echo "============================================"
echo ""
echo "Connecting to Railway PostgreSQL..."
echo ""

# Use railway connect with service specified
railway connect Postgres <<'EOSQL'
\o pre_merge_output.txt
\i verify_production_pre_merge.sql
\o
\q
EOSQL

if [ -f pre_merge_output.txt ]; then
    echo ""
    echo "✅ Verification complete!"
    echo ""
    echo "Output saved to: pre_merge_output.txt"
    echo ""
    echo "Preview of results:"
    echo "-------------------"
    head -50 pre_merge_output.txt
    echo ""
    echo "Full output is in pre_merge_output.txt"
else
    echo ""
    echo "❌ Failed to create output file"
    echo "Try running manually:"
    echo "  railway connect Postgres"
    echo "  Then in psql: \\i verify_production_pre_merge.sql"
fi
