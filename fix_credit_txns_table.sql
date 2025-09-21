-- Fix credit_txns table missing ref_txn_id and idempotency_key columns
-- These columns are used for transaction referencing and deduplication in the credit system

BEGIN;

-- Add ref_txn_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'credit_txns' AND column_name = 'ref_txn_id') THEN
        ALTER TABLE credit_txns ADD COLUMN ref_txn_id INTEGER NULL;
        RAISE NOTICE 'Added ref_txn_id column to credit_txns table';
    ELSE
        RAISE NOTICE 'ref_txn_id column already exists in credit_txns table';
    END IF;
END $$;

-- Add idempotency_key column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'credit_txns' AND column_name = 'idempotency_key') THEN
        ALTER TABLE credit_txns ADD COLUMN idempotency_key TEXT NULL;
        RAISE NOTICE 'Added idempotency_key column to credit_txns table';
    ELSE
        RAISE NOTICE 'idempotency_key column already exists in credit_txns table';
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN credit_txns.ref_txn_id IS 'Reference to another transaction ID for linking related transactions';
COMMENT ON COLUMN credit_txns.idempotency_key IS 'Unique key to prevent duplicate transactions';

COMMIT;

-- Verify the columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'credit_txns'
AND column_name IN ('ref_txn_id', 'idempotency_key')
ORDER BY column_name;