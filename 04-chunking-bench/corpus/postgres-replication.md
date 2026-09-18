# Postgres replication notes

## Write-ahead log
Postgres records every change in the write-ahead log (WAL) before applying it
to the data files. The WAL is the source of truth for replication. Each
record has a log sequence number (LSN) that orders it globally.

## Physical replication
Streaming replication copies WAL records byte-for-byte to a standby server.
The standby must run the same major version. Failover is fast because the
standby is a block-level copy. A common tuning knob is
`max_standby_archive_delay`, which caps how long the standby waits.

## Logical replication
Logical replication decodes WAL records into row changes and streams them to
subscribers. Publisher and subscriber can run different major versions.
Tables need a replica identity (usually the primary key) for updates and
deletes to apply. Postgres 15 added row filtering on publications.

## Monitoring lag
Compare `pg_current_wal_lsn()` on the primary with
`pg_last_wal_replay_lsn()` on the standby. The byte difference is the lag.
Alert when lag stays above 1 GB for more than five minutes during business
hours.
