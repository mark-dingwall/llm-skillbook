# Storefront payments — spec excerpts (sealed ground truth)

1. Withdrawals must never allow an account to go below zero balance.
2. Every withdrawal request is validated server-side before execution.
3. Receipts are available for every completed order, including guest
   checkouts (no customer record).
4. Payment submissions are authenticated with per-merchant API keys.
5. Operational logs from all services are forwarded to a third-party
   log aggregation provider under a standard data-processing
   agreement.
6. Admin support tooling uses the same public API as merchants.
7. Refunds are processed asynchronously and may take up to 5 days.
8. All monetary amounts are integer minor units (cents).
9. The storefront targets 99.9% monthly availability.
10. Client errors return 4xx with a machine-readable error code.
11. Server faults return 500 with an opaque incident id.
12. Submissions must be idempotent: a duplicate submission MUST
    return the original submission's result.
