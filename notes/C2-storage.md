# C2 Storage: technical note for the paper writer

Scope: `internal/zonelog`, `internal/storage`, `internal/prep` of
`/home/claude/code/core` (branch main, head `da0734b`, 2026-11-16), with
`docs/storage/zonelog.md`, `docs/storage/bulk.md`, `docs/ingest/pipeline.md`
(section 5) and the relevant entries of `docs/protocol/invariants.md` for
context. Everything below was read in the code; where a doc says otherwise,
the code is given and the disagreement is listed in section 20.

Size (non-test `.go`, with comments): zonelog 3 279 lines, storage 5 858,
prep 1 025. zonelog uses only the standard library.

---

## 0. Layering in one picture

```text
client write ──► storage.ApplyRecordContext
                   │ peek: causalWritable (no lock)          [permission.go]
                   ▼
                 diskBatch.submit  (admission, queue, ≤256 per group, 2 ms window)  [write_batch.go]
                   ▼
                 Store.update: writeMu → rowsMu → callbacks on one Tx  [store.go]
                   │ each callback: causalWritable again, receipt, zone seq, record, history, receipts, usage [apply.go]
                   ▼
                 Tx.commit: record rows + control rows → ONE zonelog.Apply  [records.go, tx.go]
                   ▼
zonelog.Apply: prepare all → seq per changed row → memtable → frame → sync (fsync) → visible  [store.go, log.go]
background:    full memtable → flush to segment;  segments → merge          [store.go, segment.go]
reads:         Get / Scan / Children / Total from memtables + segments      [read.go]
bulk:          IXP1 batch → one zonelog Bulk segment → manifest rename      [prep, storage/bulk.go, zonelog/bulk.go]
```

There is one zonelog store per node (one directory `<path>.records`). A vnode
is a set of key ranges inside it. Control state (authority, fences, zone
sequences, receipts, history, staging, counters) is rows of a reserved
collection in the same store, committed in the same frame as the data.

---

## 1. Keys and store order

**Definition.** A key is the byte string under which zonelog stores a row; its
byte order is the store order, and every zone is one contiguous key range.

**Data structure** (`zonelog/key.go`, `makeKey`):

```text
key = collection number (u16, big endian) | location bits (12 B) | depth (1 B) | id (≤ 255 B)
      └──────────────── head: headLen = 15 B ────────────────┘
```

- Location characters are 6-bit indexes in the routing alphabet
  `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_`
  (same as `tree.BASE64`), packed most significant first, left aligned in
  96 bits (`locBits`). Max depth = 96/6 = 16 characters. Bits past `6·depth`
  are zero. Root is `"@"` or `""` (depth 0, all bits 0).
- Collection numbers are assigned in order of first use and named in the
  MANIFEST (`Store.collection`); number 0 is `"\x00receipts"` (legacy).

**Algorithm** (`zoneRange(col, location)` → `[lo, hi)`):

```text
lo = makeKey(col, location, "")            # head of the zone, empty id
hi = lo[:headLen]; hi[depth byte] = 0
add 1 to bit (16 + 6·depth − 1) of hi, carrying toward the collection bytes
return lo, hi
```

**Rule.** Every record at or below a zone lies in `[lo, hi)`, and nothing
else does; a zone and its first child (same bits) are kept apart by the
depth byte, the zone sorting first (ZONE-ID-1 is the identity invariant the
doc cites for this, `docs/storage/zonelog.md`; test
`TestZoneRangeBounds`). `CompareLocations` gives the same order on
location strings (alphabet index, missing char = 0, shallower first); this
is not Go's string order (`TestCompareLocationsIsKeyOrder`).

Consequence used everywhere: the 64 children of a zone of depth d are the
64 consecutive sub-ranges that start at `key(col, zone+c, "")` with depth byte
d+1, and records placed exactly at the zone come before child 0.

---

## 2. Records, rows and the IXR1 value

**Definition.** A zonelog `Record` is what callers write; a `row` is its
stored form with a flag byte, a seq, a weight and metrics.

**Fields** (`zonelog/record.go`): `Record{Collection, Location, ID, Weight,
Metrics []float64, Payload, Deleted, Uncounted, Opaque, Binary}`.
`row{key, flags, seq, req (always 0), weight, metrics, payload | (val file,
voff, vlen), old, below}`.

Flags: `flagDeleted=1, flagRetract=2, flagReceipt=4 (legacy), flagUncounted=8,
flagOpaque=16, flagBinary=32`. `live()` = no flag other than uncounted /
opaque / binary.

**What a row adds to a sum** (`countOf`): `[rows, count]` =
plain live (1, 1); retraction (1, −1); legacy receipt (0, 0); tombstone,
uncounted row or their retraction (1, 0). Weight and metrics are added as
stored (a retraction stores them negated). `Weight 0` is written as 1
(`prepare`).

**IXR1 value** (`appendValue`, in log frames):
`u8 version=1 | u8 flags | u8 metric count | u8 0 | u32 payload length |
f64 weight | m × f64 metrics | payload`. Header 16 B. Max 255 metrics in
zonelog; storage caps at `MaxMetrics = 128` (`storage/records.go`).

**Unchanged writes** (`Store.unchanged`): a write whose flags, weight,
metrics and payload bytes equal the newest stored version, or a delete of a
missing key, takes no seq and writes nothing (`TestUnchangedWritesAndControlRecords`).

---

## 3. The log of frames (zonelog)

**Definition.** The log is a sequence of files of frames; a frame is one
atomic batch of row mutations and is whole or absent after a crash.

**On disk** (`zonelog/log.go`):

```text
file   %020d.log, named by the first seq it holds
frame  u32 body bytes | u32 CRC-32C(body) | body
body   u64 first seq | u32 seqs | u32 count | count × (u64 request hash (0) | u16 key len | key | IXR1 value)
```

`seqs = count`, except the frame of a bulk segment: one seq, zero rows.
Frames follow each other without a hole in the seqs.

**Algorithm** (`Store.Apply` then `Store.sync`):

```text
Apply(batch):
  lock mu
  while mem.bytes ≥ MemoryBytes/16:                  # memtable full
      if imm == nil: imm, mem = mem, new; startWork(); break
      wait flushed                                  # back-pressure ("memtable_full")
  for r in batch: rows[i], prev[i] = prepare(r)     # decide all before placing any; nil = unchanged
  for each non-nil row: seq++; row.seq = seq; place(row, prev)   # memtable, with retraction (§6)
  pending += frame(first, rows)
  unlock; sync(seq)

sync(upto):
  lock syncMu                                       # one log writer
  take all pending frames (if synced < upto)
  if synced ≥ upto: return                          # an earlier holder already wrote my frame
  write frames; fsync log file
  if log file ≥ min(16 MB, LogRetain/4): rotate (new file + dir fsync), drop oldest files covered by segments beyond LogRetain
  synced = visible = last seq written                # only now do readers see the rows
```

**Rule.** A batch is acknowledged only after its frame is fsynced, and no
reader sees a row before that ("no dirty read", `TestWriteIsInvisibleUntilSynced`;
reads filter rows with `seq > visible`). Whoever holds `syncMu` writes every
pending frame, so concurrent `Apply` callers share one fsync (zonelog-level
group commit). A torn or CRC-failing frame ends a file: it was never
acknowledged (`readFrames`).

**Recovery** (`Store.recover`): replay files in name order; frames with seq ≤
`durable` (the last seq held by a segment, from the MANIFEST) are skipped;
the rest rebuild the memtable via `lookup` + `place`. A hole above
`durable` (`first > seq+1 && first−1 > durable`) refuses the open. A file with
no whole frame is removed. Then a fresh log file `seq+1` is opened.

Constants: `LogRetain` 64 MB (flushed log kept besides segments), rotation at
`min(16 MB, LogRetain/4)` = 16 MB. CRC table: Castagnoli.

---

## 4. Group commit in storage: the `diskBatch` committer

**Definition.** `diskBatch` (`storage/write_batch.go`) turns concurrent client
writes into one storage transaction and therefore one zonelog frame and one
fsync, while keeping ACK-after-commit.

**Fields:** `pending []diskWrite{apply, done, bytes, submitted}`, `size`
(group bound), `delay` (collection window), `admitted`, `admittedBytes`,
`maxPending`, `maxBytes`, `running`, `stats`.

**Defaults:** `storage.Open` → `BatchWrites: true, BatchSize: 256,
BatchDelay: 2 ms`. `OpenWithOptions` with `BatchWrites` and `BatchSize 0`
→ 1 000; without `BatchWrites` → size 1, delay 0. Admission:
`DefaultMaxPendingWrites = 4096`, `DefaultMaxPendingBytes = 64 MB`
(weight = encoded record + keys + ids + 8·metrics + 256, `writeRequest.weight`).

**Algorithm:**

```text
submit(ctx, bytes, fn):                     # stage "admission_lock"
  if closed → ErrClosed; if ctx done → ctx.Err
  if admitted ≥ maxPending or bytes > maxBytes − admittedBytes → WriteAdmissionError (ErrWriteOverload), never queued
  admitted++, pending += call; if !running: start run()
  wait call.done                            # caller learns the real outcome, even if ctx is cancelled later

run():                                      # one group in flight per store
  loop: if pending empty → stop
        if len(pending) < size: sleep(delay)          # one short collection window
        calls = first min(len, size) of pending       # stage "queue" = submit → here
        commit(calls)

commit(calls):
  loop: err = update(tx ⇒ for c in calls: c.apply(tx))   # one Tx, one zonelog.Apply, one fsync
        if callback i failed: remove it, retry the others as a group
        else: complete all with err; break
  each removed callback: run alone in its own update
```

**Stages reported in `CommitStats.Stages`** (`/metrics`): `admission_lock`,
`queue`, `write_lock` (`writeMu`), `rows_lock` (`rowsMu`), `validation`
(running the callbacks), then zonelog's `zonelog_lock`, `memtable_full`,
`sync_lock`, and background `flush`, `merge`, `publish` (`zonelog/timing.go`);
histograms `CommitLog2` (one transaction + fsync) and `WaitLog2` (submit →
done), power-of-two microsecond buckets.

**Rules.** (a) A write is acknowledged only after the commit that contains it
is durable. (b) A refused write does not fail its group: authority refusals
and receipt conflicts are returned as `writeOutcome.refuse` with a nil
callback error ("soft refuse", `apply.go`), so siblings commit
(`TestDiskBatchCallbackFailureKeepsSiblingCommits`). (c) Callbacks are
re-executed on a sibling's failure and reset their output first. (d) Admission
bounds queued plus in-flight work (`TestWriteAdmissionBoundsQueuedAndInFlight`).

Note for the paper: `Store.update` holds `writeMu` and then `rowsMu` across
the callbacks **and** the zonelog `Apply` including its fsync
(`updateLocked` → `tx.commit`). So at storage level there is one commit in
flight; reads in `view` (which take `rowsMu.RLock`) wait for it, and any long
read under `rowsMu` delays every commit (the planning-totals fix, §16).

---

## 5. The storage transaction and control rows

**Definition.** A `Tx` (`storage/tx.go`) is a read or an update of control
state plus record rows; an update buffers its writes and commits them as one
zonelog batch.

**Data structure.** Control rows are zonelog records of collection
`kvCollection = "\x00kv"`, location `@`, id = *path*: the bbolt bucket names
and key it used to have, each element escaped (`0x00` → `00 01`) and ended by
`00 00` (`key`, `element`), so ids sort as bbolt sorted them and rows below a
path follow it. Payload = `'v'` + value (an empty payload is a reservation,
e.g. `staging/<operation>`). Paths in use: `meta/{identity, storage-id,
storage-format = "indexus-flat-1", causal…, data-usage, zonelog-row-bytes,
bulk-v1/<batch>, cold…}`, `live/<zone>/{sequence, 0x02+requestID}`,
`history/<zone>/<u64 seq>`, `operations/<requestID>`, `staging/<op>/<zone>/…`,
`transfer-snapshots/<op>/<zone>`, `causal-migration-zones/<op>/<zone>`.
Record rows are zonelog records of their own collection and location.

`Tx{version = db.Seq(), pending map[path]payload, below map[path]count,
records map[zone]*pendingZone, delta}`; `Tx.ID()` = zonelog visible seq.

**Algorithm** (`Tx.commit`, `storage/records.go`):

```text
if fn failed: drop everything (nothing was written)
if delta ≠ 0: put meta/zonelog-row-bytes += delta
batch = record rows sorted by (zone key, id)   # nil → zonelog delete; record → toLog(record)
      + control rows sorted by path            # nil payload → zonelog delete
zonelog.Apply(batch)                           # one frame, one fsync
```

**Rule.** Control state and data of one update are one atomic cut: all or
nothing after a crash, one fsync (`zonelog.md`: "one atomic cut"). Reads
inside an update see the update's own writes over committed rows
(`Tx.get`, `Tx.rows`).

Row-level amplification of one client write (`applyWrite`): 1 record row +
`live/<zone>/sequence` + `live/<zone>/<receipt>` + `operations/<req>` +
`history/<zone>/<seq>` (unless `OmitHistory`) + `meta/data-usage` +
`meta/zonelog-row-bytes` (+ `causal-migration-zones` on a zone's first write
during a warm transfer, + cold activity counter during a cold drain). Because
`pending` is a map, a group of B writes in the same commit shares the two
`meta` rows and the per-zone sequence row when zones repeat.

---

## 6. Memtables and flush

**Definition.** The memtable is an in-memory skiplist of rows not yet in a
segment; at most one more, immutable memtable (`imm`) is being flushed.

**Data structure** (`zonelog/memtable.go`): skiplist `maxLevel = 16`,
xorshift level choice (p = 1/4). Accounting `bytes += len(key) +
len(payload) + 8·len(metrics) + 320` per put. Each node holds the newest row
of its key; `row.below` is the version it replaced (kept for readers until
the new row is synced); `row.old` is the retraction of the version on disk.

**place** (`Store.place`):

```text
if the key already has a memtable row cur: r.old = cur.old         # keep cancelling the same disk version
elif prev (newest version outside the memtable) is live: r.old = prev.retraction()
mem.put(r, visible)                                               # r.below = cur; drop cur.below once cur is visible
```

A memtable iterator yields, per key, the newest version with `seq ≤ visible`
and then its `old` retraction (`memIter`).

**Flush** (`workOnce(flush=true)`, own goroutine since commit `6a353d5`):

```text
take imm; id = nextFile++
sync(imm.maxSeq)                         # readers must not see a segment before its rows are synced
build segment id from imm (rows + retractions), expected rows 2·imm.rows
fsync .seg and .val, fsync directory
lock mu: segs += g; durable = imm.maxSeq; imm = nil; write MANIFEST (tmp, fsync, rename, dir fsync)
remove nothing else; dropPayloadFiles(); startWork() (a flush may make a merge eligible); broadcast
```

**Rules.** Memory per memtable is bounded at `MemoryBytes/16` (16 MB of the
default 256 MB); a writer waits only when both memtables are full
(`TestCommitsProgressDuringMerge`: commits progress while a merge is paused).
Workers stop when idle: no timer and no permanent goroutine.

Constants (`zonelog.Options`): `MemoryBytes` 256 MB (`storage.memory_bytes`),
memtables `MemoryBytes/16` each, page cache `MemoryBytes/8` minus resident
segment memory, floor `MemoryBytes/64`.

---

## 7. Immutable sorted segments and their index

**Definition.** A segment `NNNNNNNN.seg` is an immutable file of rows sorted
by key, laid out in column pages, followed by a tail (page index with sums,
key filter, payload-file usage, counts) and a footer.

**On disk** (`zonelog/segment.go`, top comment, little endian):

```text
page    u16 n | u8 m metric columns | u8 has-payloads | u32 id bytes | 8 × 0          (16 B header)
        [n][15]u8 key heads | [n]u8 flags | [n]u8 metric count | [n]u16 id end
        [n]u64 seq | [n]u64 request (0) | [n]f64 weight
        if payloads: [n]u32 payload file | [n]u64 offset | [n]u32 bytes
        [m][n]f64 metrics (one column per metric) | id bytes | u32 CRC-32C
tail    u32 pages | per page: u32+first key | u32+last key | u64 offset | u32 bytes | u32 k, k × f64 sums
        u32 filter bytes, filter | u32 files, per file (u64 file, u64 bytes pointed) | u64 rows | u64 max seq
footer  u64 tail offset | u32 CRC-32C of the tail | "ZLS3"                           (16 B)
```

Page sums are the Neumaier pairs of `[rows, count, weight, metrics…]`, i.e.
`2·(3+m)` floats.

**Page cut rule** (`segWriter.add`), applied only between two different keys
(a record and its retraction stay in one page):

```text
cut if n ≥ pageRows (256)
    or payload bytes held ≥ 1 MB
    or n ≥ pageRows/4 (64) and the two keys share fewer location characters than any pair inside the page
```

So the children of a large zone start on page boundaries, and their sums can
be taken from the index without reading a page.

**What an open segment keeps in RAM** (`readTail`, `memory()`): per run of
`superPages = 64` pages (a *block*) its first key, its summed sums, and the
offset/size/CRC of its index entries; per `bloomChunk = 4096` B of filter a
CRC; the last key; the payload-file map. Index entries (by block), filter
chunks and pages are read through the LRU page cache and CRC-checked.

**Filter:** Bloom, `bloomBits = 10` bits per expected row, `bloomK = 6`
probes (double hashing from FNV-64a), sized `expectRows·10/8 + 8` bytes.

**Writer memory:** index entries spill to `NNNNNNNN.idx.tmp` past
`indexSpill = 1 MB`; the filter (1.25 B per row) is held until `finish`.

**Point read** (`segment.get`): outside `[first key, last key]` → absent;
filter says no → absent; `seek` = binary search over blocks (RAM), one index
block (cache), binary search on ≤ 64 entries, one page, binary search on the
page. `Store.lookup` checks mem, imm, then segments newest first.

**Rule.** Segments are never modified; the MANIFEST names the live set, and a
`.seg` not named there, or any `.tmp`, is removed at Open (`Open`). A footer
other than `ZLS3` refuses the open (`TestSegmentOfAnotherFormatIsRefused`).

---

## 8. How a zone's sum is read (Children, Total over spans) and why it is exact

**Definition.** `Children(collection, zone)` returns 65 `Sum{Count, Weight,
Metrics, Only}`: `[0]` the records placed exactly at the zone, `[1+c]`
everything at or below child c. `Total(collection, zone)` is the zone's slot
in its parent's `Children` (for the root: the 65 parts added, `totalOf`).
`storage.ZoneChildren` / `ZoneTotal` (`storage/zone_sums.go`) pass straight
through; they count every row on the disk whatever its authority (residual
zones not yet collected included).

**Algorithm** (`zonelog/read.go`, under `mu.RLock`):

```text
Children(col, zone):
  lo, hi = zoneRange(col, zone); d = depth(zone)          # d < 16
  bounds = [lo, child_0, …, child_63, hi]                  # child_c: bits of zone + char c, depth byte d+1
  spans(bounds):
    for each memtable (mem, imm): walk rows in [lo, hi) with seq ≤ visible;
        add row and its .old retraction to the span the key falls in
    for each segment g:
        from = g.seek(lo); end = g.seek(hi)
        for each span i: to = g.seek(bounds[i+1]); g.sumRange(from, to) into span i; record first/last key heads
  for each span with count ≠ 0: Count = round(sum.count), Weight, Metrics, Only = only(span)

sumRange(a, b):                       # rows [a, b) of one segment
  while a ≠ b:
    if a is at a block start and a whole block fits before b: add block sum (RAM); skip 64 pages
    elif a starts a whole page before b's page: add that page's index-entry sum
    else: read the page, add its rows column by column (first or last partial page)
```

**Why the sum is exact in which rows it counts.** No version lookup is done:
every row adds, and the store keeps the sum of all rows equal to the sum of
the newest live versions:

1. A write over a live version that is outside the memtable stores its
   *retraction* (old weight and metrics negated, `[rows, count] = (1, −1)`,
   same seq as the version it cancels) next to the new row (§6). A version
   replaced inside the memtable is never summed (only the newest visible
   memtable row and its `old` are).
2. A delete is therefore a subtraction: the tombstone (or, in storage, an
   uncounted row) adds `(1, 0)` and nothing else, the retraction removes the
   old version's count, weight and metrics.
3. A merge drops a retraction only together with the version it cancels
   (same key and seq among the sources), and drops a tombstone only when the
   oldest segment is among the sources (§9). A bulk replace writes the
   retractions in its own segment (§17).

Each column is a Neumaier compensated pair (`sums.put`, format
`zonelog-2`): pages, index entries and block sums store value and
compensation, and `sums.add` adds both. So a retraction cancels its row to
the bit, and `1e16 + 1 − 1e16 = 1` wherever the three rows are (memtable,
one segment, two segments, after reopen; `TestSumsAreCompensatedAcrossSegments`).
The docs' own limit: adding the same float64 values in another order can
still differ in the last bit (`zonelog.md`, Risks). Count is `round(Σ count)`.

**One-location rule** (`only`): if the span's first and last key heads are
equal, that location holds all its records; if they differ and every row is
live (`rows == count`), there are several; otherwise scan to the first
counted live row and check that the range `[head, head with depth+1)` counts
as many as the span. Used by `/sets` (query.md key rule).

**Rule** (no code invariant name; comment in `record.go`: "the sum of a key
range is the sum of its rows in every segment and in the memtable, with no
lookup of which version wins"). Checked against a brute-force model in
`TestRandomMutationsMatchModel` and the power-loss tests.

---

## 9. Merges (compaction)

**Definition.** A merge rewrites a contiguous run of segments into one,
keeping the newest version of each key.

**Selection** (`Store.mergeable`, in order):

```text
1. a segment pointing into a dead payload file (pointed bytes < 2/3 of the file): that segment alone
2. all segments, if Σ rows − Σ count > Σ count over all blocks and there is more than one segment
   (non-live rows — retractions, replaced versions, tombstones, uncounted rows — exceed live ones)
3. scanning from the newest end: ≥ 4 neighbouring segments of the same size class,
   class(g) = bitlen(bytes / (MemoryBytes/32 + 1)) / 2   (a factor of 4 per class)
```

Code comment: "Each row is then rewritten about log4(data / memtable) times;
large payloads are not." No merge starts while a bulk segment is written.

**Build** (`Store.build` + `eachKey`, sources newest first, merge sources read
without the cache so hot pages stay):

```text
for each key (k-way, smallest key first):
  real = versions (records, tombstones) newest first; retract = its retractions
  r = real[0]
  if r has only a pointer and (vlen < BlobBytes or its file is to be rewritten): load payload (copied into new .val)
  write r unless (bottom and r is a tombstone) or r is a legacy receipt row
  for t in retract: write t unless some version in real has t.seq    # its target is in an older segment
finish: fsync .seg, .val, directory → open segment
publish (under mu): replace segs[lo:hi] by g; write MANIFEST; only then remove inputs; dropPayloadFiles
```

`bottom` = the oldest segment is among the sources (`lo == 0`, not a flush).

**Rule.** A merge never changes any sum or any read: it drops only pairs that
cancel and tombstones with nothing older below. Inputs become garbage only
after the MANIFEST that no longer names them is durable. A single segment is
never merged for waste (uncounted live rows would restart it forever).

---

## 10. Payloads

**Definition.** Payload bytes live in payload files `NNNNNNNN.val`, written
with segment NNNNNNNN; a row stores (file, offset, length) in payload bytes
before compression.

**On disk** (`zonelog/val.go`):

```text
frames  each flate(BestSpeed) of up to 64 KB of payload bytes, or the bytes as they are if not smaller
index   per frame: u64 offset in file | u32 stored bytes | u32 raw bytes
footer  u64 index offset | u32 frames | u32 CRC-32C of the index | "ZLV1"      (20 B)
```

Compression runs off the writer goroutine (`valWorkers = 2`, `valAhead = 4`
frames in flight); after a frame that shrinks by less than 1/16, the next
`valSkip = 16` frames are stored raw. A read decompresses the frames it needs
and keeps them in the page cache (key `file | 1<<63`).

**Rule.** Payloads of at least `BlobBytes = 4096` B are written twice in their
life (log, then the payload file at flush) and merges keep pointing at them;
smaller ones are copied into the merge's own file. A payload file is
rewritten (its live payloads copied out) when segments point at less than
two thirds of it; a file no segment points at is closed and removed
(`dropPayloadFiles`; `TestMergesPointAtLargePayloads`,
`TestPayloadsAreCompressedOnDisk`).

---

## 11. Storage records on zonelog

**Mapping** (`storage/records.go`, `toLog` / `fromLog`):

- live record → zonelog record with weight and metrics; JSON payload stored
  as `json.Marshal(json.RawMessage)` (compact, HTML escaped); `Binary` →
  zonelog `Binary` with the decoded bytes;
- deleted record (storage tombstone) → `Opaque | Uncounted` row whose payload
  is the record's JSON: kept for snapshots and seals, out of every count;
- a cleared zone row (`setRecord(..., nil)`, used by `clearZone`, install,
  drop) → zonelog `Deleted` (a real delete with a retraction).

`Record.Weight`: 0 means 1 and is how 1 is stored (`WeightOf`); writes refuse
negative, NaN, infinite weights and more than `MaxMetrics = 128` metrics
(`newWriteRequest`).

**Capacity unit** (`logSize`): a row counts `16 + 8·metrics + payload`
bytes, a new row also `1 + len(id)` (`rowDelta`); kept in
`meta/zonelog-row-bytes`. Physical load `Owned + Residual + Staging +
ReservedIncoming ≤ capacity` is checked on every commit that adds owned bytes
(`putWriteTotals`, `persistCapacity`; CAP-1). It counts encoded data, not
filesystem bytes.

---

## 12. Replay receipts (idempotent retries) and their retention

**Definition.** A request receipt remembers that a request id produced a
mutation, without a second copy of the value.

**Data structure** (`storage/receipts.go`): `RequestReceipt{Digest [32]byte
= SHA-256 of the canonical record JSON, RequestID, Seq (zone seq), Collection,
Location}`, stored twice as JSON: `live/<zone>/0x02+requestID` (travels with
the zone in a handoff) and `operations/<requestID>` (node-wide ledger that
answers retries).

**Algorithm** (`replayReceipt`, inside the commit, after the permission check):

```text
raw = operations/<requestID>; if none → new write
if digest, request id, collection or location differ → soft-refuse ErrConflict
else → return Mutation{requestID, old.Seq, record}; write nothing, no seq, no history
```

**Rule.** A retry of an acknowledged request returns the original result and
changes nothing, even after the record was overwritten or deleted, after a
handoff and after a restart; the same id with other content is a conflict
(MUT-2 / compact receipts; `TestCompactReceiptsPreserveOldResultsAcrossHandoffAndRestart`).

**Retention: indefinite.** `receipts.go`: "These receipts are retained
indefinitely; no session expiry is implied." No TTL, no count bound
(`docs/protocol/compact-receipts.md` agrees). On install, staged receipts are
copied into `operations/` and refused if a different receipt holds the id
(`installStagedZone`); receiver capacity reserves them before readiness
(`dataUsage`, `ReservedIncoming`). zonelog itself keeps no request ids: the
`req` column/frame field is always 0, and legacy receipt rows (`flagReceipt`,
collection 0) are in no read and dropped by merges.

Bulk batches have their own receipt (§17), also kept for ever.

---

## 13. The write path in storage

**Algorithm** (`ApplyRecordContext` → `applyWrite`, `storage/apply.go`):

```text
w = newWriteRequest(id, r)                       # validate, canonical JSON, digest, zone key
peek(causalWritable(w.zone))                     # cheap, lock-free: frozen/non-owned never queues
submit to diskBatch:
  in the group Tx:
    causalWritable(w.zone) else soft-refuse      # the authoritative check
    replayReceipt → done if known
    seq = live/<zone>/sequence; out = Mutation{id, seq+1, record}
    putRecord (returns the previous record for exact summary deltas); put sequence
    appendHistory: history/<zone>/<seq+1> = mutation JSON   (unless OmitHistory)
    putRequestReceipts (zone + node-wide)
    usage += deltas; refuse ErrDataCapacity if over; put meta/data-usage
    on a zone's first write: noteMigrationZone (joins a warm transfer covering it)
```

Per-zone sequence (`Mutation.Seq`) is storage's, contiguous per zone; the
zonelog seq is global and local to the disk (it changes when a zone moves).

---

## 14. The single write predicate (permission)

**Definition.** `causalWritable(tx, zone)` (`storage/permission.go`) is "the
sole causal write-permission predicate. Routes, summaries and planner
decisions cannot bypass it."

**Algorithm** (`writableIn` on the `causalSnapshot` decoded for the exact
control bytes of this Tx; `causal_cache.go` keeps two such snapshots):

```text
placed(): this vnode active (else ErrNotReady); placement valid; placement disk == this storage-id (else ErrNotOwner)
holder, token = replica.HolderOfZone(zone)
holder.Storage == storage-id and holder.VNode == node        else ErrNotOwner
not outgoingFrozen(state, zone, storage-id)                  else ErrFrozen
grant = replica.Grant(token)
if grant.Holder == holder: token ∈ state.Installed            else ErrNotReady
else (a per-zone handoff overrides an unconsumed leaf grant):
     some ZoneTransfer{zone, From = grant.Holder, To = holder} whose operation has Zones[zone].Installed   else ErrNotReady
```

`outgoingFrozen`: some transfer out of this disk has the zone `Frozen` and not
`Transferred`, or the region is `Frozen`, its certificate not `Emitted`,
covers the zone, and the zone is not `Transferred` (`handoff.go`).

**Rule.** Only the installed, unconsumed, unfenced holder on its own disk
acknowledges a write, checked inside the commit transaction; a preflight
check never authorizes an ACK (AUTH-3; ROUTE-1; storage-id ties authority to
the physical disk, so a restored copy elsewhere cannot write, MOVE-2). Every
outgoing fence is checked before any historical installation. The same
predicate gates bulk ingest (per zone of the batch) and inventory pages.

---

## 15. Handoff transactions on the storage side

Two levels share state in `CausalState.Transfers[operation]` (`ZoneState
{Frozen, Sealed, Transferred, Installed}` per zone; `CausalTransfer{Certificate,
Frozen, Emitted, Installed, Zones}`) and frozen snapshot rows under
`transfer-snapshots/<op>/<zone>`. Every step is one `updateCausal`
transaction, i.e. one zonelog frame and fsync: what it writes is durable
together, or not at all. Seals: `Snapshot.Seal()` = SHA-256 of the JSON of the
zone's records (sorted by id, tombstones included) and receipts (sorted by
request id), with `Seq`, `Items` (non-deleted), `Bytes`.

**Per zone** (`storage/causal_zone.go`):

| Step | Function | Checks | Durable after the step |
| --- | --- | --- | --- |
| freeze/fence | `FreezeZones(op, zones)` (donor) | transfer is ours, not emitted; region covers zone; every descendant in the set already `Transferred` (ZONE-2, `descendantsTransferred`) | zone `Frozen` (writes now `ErrFrozen`) and its frozen snapshot row (records + receipts + seq = barrier F), in the same Tx as the fence (HND-4) |
| stage | `StageZones(op, source, snaps)` (receiver) | not installed; receiver not closed (moving / cold drain); restage refuses a lower seq than mirrored, and never replaces a certified copy | staged copy under `staging/<op>/<zone>/` (records, receipts, seq, header) and `Certified` = seal; zone `Sealed` |
| emit transfer | `EmitZoneTransfers(op, zones)` (donor) | zone frozen; descendants transferred | `ZoneTransfer{op, zone, From, To, Seq = barrier, DataDigest = seal}` added to the authority delta; zone `Transferred` (from here only the receiver may ACK the zone, ZONE-1) |
| install | `InstallZones(op, zts)` (receiver) | region not installed; ZoneTransfer for this vnode and disk; staged header certified and equal to (zone, seq, digest) | in one Tx: zone cleared, staged records put live, receipts copied to `operations/` and the zone (conflict refused), zone seq = barrier, ZoneTransfer merged, zone `Installed` → `writableIn` admits writes |

Mirror before the freeze (`Prepare`, `MirrorBatch`/`mirrorZone`): a warm copy
is staged (`stageOnce`), then history tails are applied only if contiguous
(`m.Seq == staged seq + 1`), each with its receipt, record, seq and a replay
hash `staging/<op>/<zone>/replays/<seq>`; overlapping replays must match
(hash, or the snapshot's receipt), else `ErrSequence`; nothing is mirrored
onto a certified copy. Backlog is read by `MutationsBatch` from
`history/<zone>/<seq>` (gaps → `ErrSequence`).

**Per region** (`storage/causal_data.go`):

| Step | Function | Durable after the step |
| --- | --- | --- |
| capture (warm) | `CaptureCausal` | intent: certificate draft (previous token, outputs = region to target + remainders to self), zone list; warm snapshots are scanned in a read Tx and not stored |
| freeze | `PrepareCausal` / `FreezeRegion` | region `Frozen` + final inventory (all zone snapshots, barrier = max seq, `DataDigest`) in the same write Tx |
| stage | `StageCausal` (receiver) | certificate added; every snapshot staged and certified (`inventoryDigest == DataDigest` required) |
| emit (irreversible) | `EmitCausal` (donor) | requires every zone `Transferred`; certificate in the delta, per-zone ZoneTransfers of the op folded away, donor's remainder tokens installed, `Emitted`; the parent token is consumed (AUTH-2/AUTH-4) |
| install | `InstallCausal` (receiver) | zones not yet installed per zone: live zone dropped, staged bytes and receipts installed; staging dropped; token `{cert, 0}` installed; `Installed`; per-zone states and snapshot rows dropped |
| complete | `CompleteCausal` (donor, after the receiver's durable install answer) | `Installed`; migration journal dropped; the certificate stays as a forwarding fence |
| collect | `CollectTransferred` → `collectBatch` | per Tx at most `collectBatchZones = 1000` zones: drop the zone's live rows, sequence, receipts, history unless this disk holds the zone again; when the work list is empty, drop it and compact per-zone states (GC-1, MIG-1) |

**Rules.** HND-2 (an acknowledged write survives the handoff with its
receipt), HND-4 (freeze partitions the log at F), ZONE-1, ZONE-2, MIG-1,
GC-1, REC-1 (each phase is a durable intent; restart resumes it), AUTH-4
(restart does not restore a consumed token). Tests:
`TestCausalCrashCutsPreserveSingleWriterAndAcknowledgedRows`,
`sealed_stage_replay_test.go`, `zone_transaction_test.go`,
`TestHandoffCarriesBulkZones`. Zones created during a warm transfer are
journalled in `causal-migration-zones/<op>/` and folded into the transfer by
`readCausal` (MIG-1: they must flip before the certificate).

---

## 16. Inventory and planning totals (with the paging fix)

**Inventory pages** (`storage/inventory_page.go`, `CausalInventoryPage`):
one read Tx per page; `Watermark = tx.ID()` (zonelog visible seq);
`completeInventorySnapshot` refuses a partial read while local transfers are
unresolved; zones failing `writableIn` with `ErrNotOwner`/`ErrNotReady` are
skipped; byte budget `DefaultInventoryPageBytes = 1 MB` (soft; one row may
exceed it), hard `MaxInventoryRPCBytes = 32 MB` per row; cursor
`{Collection, Location, RecordID, Watermark, EndOfZone}` in store key order;
a commit between pages (`Watermark` changed) or a vanished cursor row →
`ErrReadChanged`, the whole read restarts. `MetricsOnly` drops payloads
before counting. Rule (READ-1): an authoritative inventory comes from one
committed version and only from installed, current grants.

**Planning totals** (`storage/planning_stats.go`, `PlanningTotals`):

```text
first = last = −1
loop:
  view(tx):                                   # rowsMu read lock for one page only
    last = tx.ID(); if first < 0: first = last; if cache.txID == first → return cached
    visit zones after `from` (eachInventoryZoneFrom), skipping `from` itself;
    stop after planningPage = 1024 zones: count live items (non-deleted), zones, collections; from = last zone
  if all zones visited: break
if first == last: cache {txID, totals}        # kept only if no commit landed during the count
```

The fix (commit `b6bc03d`, 2026-11-16, REM-83): before it, the whole count
ran in one read and held `rowsMu`, which every commit needs (§4); on AWS
(16 × i4i) writes queued for up to a second. After: commits land between
pages; "wait before commit p99 524 → 8 ms at 16 200 writes/s, 1 048 → 16 ms
at 24 300", up to 47 069 acknowledged writes/s (commit message). Totals under
writes are advisory (monitoring, autoscale), never used to authorize
(`TestPlanningTotalsPagesLetCommitsIn`). `PlanningStats` (per-zone items and
seal-sized bytes, `zoneBytesOf`) still reads in one Tx.

---

## 17. Bulk ingest (IXP1 batches, one segment, one receipt)

**IXP1 batch** (`internal/prep`, pipeline.md §5): a directory
`manifest.json` (`format = "indexus-prep-v1"`, collection, metrics, records,
payloadEncoding `json`|`binary`, splitDepth, parts with `first`/`last`
`location/id`, sha256, bytes, optional `zones`, inputs, `id` = SHA-256 of
canonical inputs), `part-NNNNN.ixp`, optional `zones.ixp`. Part format
(`prep/part.go`):

```text
header 16 B  "IXP1" | u16 version 1 | u16 m | u8 flags (bit 0: payloads) …
block        u32 n | u32 id bytes | u64 payload bytes | [n][13]u8 heads | pad8 | [n]u32 id end | pad8
             | [n]u64 payload end (if payloads) | [n]f64 weight | [m][n]f64 metrics | ids pad8 | payloads pad8
             | u32 CRC-32 (IEEE) | u32 0
index        per block 32 B: first head (13 B) | 3 × 0 | u64 offset | u32 bytes | u32 rows
footer 32 B  u64 index offset | u64 rows | u32 blocks | u32 CRC-32 of index | "IXP1" | u32 0
```

A head is the zonelog key without its collection number (13 B); rows are
strictly increasing by (head, id) within and across parts. `maxRows = 65 536`
rows or `maxBlock = 64 MB` of payload per block. `zones.ixp`: same format, one
row per zone, id empty, weight = Σ weights, metrics = `m+1` columns (count,
then Σ metrics).

**Node algorithm** (`storage/bulk.go` `ingest`, `bulk_stream.go`
`IngestBulkStream` for the tar stream; `zonelog/bulk.go`):

```text
batch key = hex(SHA-256(format, collection, m, ["binary"], parts' sha256))[:16 B]
zone = common prefix of first and last location ("@" if none)
lock writeMu (all writes, fences, handoff steps wait; reads go on)
view: receipt meta/bulk-v1/<key> exists → answer Already
      handoff, move or cold fold in progress → ErrNotReady (503)
      causal snapshot, usage
BeginBulk(col, zone, replace, records): Flush(); no other bulk; without replace the zone must have no live row (ErrNotEmpty→409);
      reserve ONE seq, pending += frame(seq, 1 seq, no rows); s.bulk = true (no merge starts)
Also(control row "\x00control"/bulk/<key> = receipt JSON)            # receipt is a row of the same segment
for each part (prep.ReadPart: streams once, checks block CRCs, order, index, footer, size, SHA-256):
  for each row: on a new location, writableIn(zone of row) else refuse (421)
                weight finite ≥ 0, metrics finite, payload canonical JSON unless binary
                accumulate shallowest zones.ixp depth sums; bytes += 1+id+logSize
                AddHead(head, id, weight, metrics, payload): key in zone, strictly after the last
                  with replace: before it, every old live key not rewritten → tombstone + retraction;
                                the old version of a rewritten key → retraction after the new row
check record count = manifest; zones.ixp rows at its shallowest depth = record sums to relative 1e-9
check capacity (507)
lock rowsMu; Commit: remaining retractions; finish (.seg/.val fsync); open; sync(bulk seq);
      segs += g; MANIFEST rename (+dir fsync) = THE CUT; startWork if mergeable
Tx: meta/bulk-v1/<key> = receipt, meta/data-usage, meta/zonelog-row-bytes      # second commit
```

**Rules.** A batch is all or nothing: nothing is visible before the MANIFEST
rename, everything after (AUTH-4 tests `TestPowerLossDuringBulkIsAllOrNothing`,
`TestKillDuringBulkIsAllOrNothing`; `TestBulkCorruptBatchLeavesNothing`:
`ReadPart` may show rows before finding a bad SHA-256, but the segment is
aborted). Retrying the same batch is recognised by content for ever. A batch
writes no history, no per-record receipt, no zone sequence (its zones have
sequence 0 until a write); all its rows carry the single bulk seq; a handoff
carries bulk zones in its frozen snapshot (HND-2 for bulk,
`TestHandoffCarriesBulkZones`). A crash between the cut and the second commit
is finished at Open by `reconcileBulk`: it finds `bulk/<key>` rows in
`zonelog.Control` without a storage receipt, records them and recounts row
bytes (`TestBulkCutWithoutControlReceiptIsReconciledAtOpen`).

---

## 18. Crash safety

**zonelog syncs** (removing any of the first four makes
`TestPowerLossKeepsAcknowledgedBatches` fail, per `zonelog.md`):

1. log write: `log.Sync()` before visibility and ACK (`sync`);
2. new log file: directory `Sync()` after `Create` (`openLog`);
3. segment: `.seg` and `.val` `Sync()` then directory `Sync()` (`build`,
   `segWriter.finish`);
4. MANIFEST: `MANIFEST.tmp` write + `Sync()`, `Rename`, directory `Sync()`
   ("the rename is the commit, and it is not durable before this").

**Open** (`zonelog.Open`): refuse a MANIFEST whose format is not
`zonelog-2`; open the named segments (footer `ZLS3`, tail CRC); remove
unnamed `.seg` and every `.tmp` (unfinished flush/merge/bulk/spill); remove
payload files no segment points at; replay the log above `durable`. Storage
`OpenWithOptions` refuses a file at the store's path (a bbolt store), checks
`storage-format = indexus-flat-1` and the cluster/node identity, creates a
random `storage-id` once, and runs `reconcileBulk`.

**Tests** (`zonelog/memfs_test.go`, `crash_test.go`): a power-loss file
system that keeps only synced bytes plus random torn garbage and undoes
unsynced creates/renames/removes: 60 random cut points (append, flush, merge,
manifest rename, log rotation, open) and two more after each recovery; each
reopen equals a brute-force model and holds a whole number of batches
including every acknowledged one. Also a killed writer process with real
fsync (12 kills) and a log cut at 40 random bytes. Storage:
`TestCausalCrashCutsPreserveSingleWriterAndAcknowledgedRows` (cuts between
handoff steps), bulk kill/power tests.

**Not covered** (`zonelog.md`): an fsync that lies, bit rot in synced data (a
bad CRC is an error, no repair), a full disk. An error in a background flush
or merge sets `s.err` and stops further writes.

---

## 19. Implemented vs documented only

Implemented (code + tests): everything in sections 1 to 18.

Documented only, or removed from the code:

- The RETRY-1 receipt window (last 262 144 writes or 24 h; seq-guarded writes
  outside it) in `invariants.md`: not in the code; receipts are kept for ever.
- The HND-2 paragraph on zonelog *tails* `(After, Through]` over the global
  zonelog seq: not implemented; the mirror uses per-zone storage sequences
  and history rows.
- pipeline.md §5.5: forwarding of runs owned by another node, a contiguous
  seq range per batch, a request hash per row, replace through zonelog
  `Drop`, comparing `Children` with `zones.ixp` after install. Code: refuse
  zones not held (no forwarding, the `localdata` tool splits by owner), one
  seq per batch, request hash 0, replace by retractions inside the segment,
  `zones.ixp` checked before the cut against the records (bulk.md lists these
  differences itself).
- zonelog `Since`, `Mirror`, `Seal`, `Ingest`, `Drop`, request receipts and
  `IfSeq`: removed in November 2026 (`zonelog.md`); the `req` field remains in
  frames and pages, always 0.
- Opening payload files on demand (one open file per payload file today) and
  a whole-filesystem quota: listed as limits, not implemented.

---

## 20. Docs / code disagreements (the code wins)

1. `zonelog.md` Risks, "One background worker. A long merge delays the next
   flush": since `6a353d5` (2026-11-16) flushes have their own worker
   (`startWork`, `workOnce(true)`); only one merge and one immutable memtable
   at a time. Writers still wait when both memtables are full.
2. `zonelog.md` "Code size 2 442 lines without tests": today 3 279 (with
   comments).
3. `zonelog.md` "pages of 64 to 256 rows": a page can be shorter (the last
   page of a segment; 1 MB of payloads held cuts at any row count).
4. `zonelog.md` / `store.go` "all merge when replaced versions and tombstones
   outnumber half the live records": the test is `rows − count > count`,
   i.e. non-live rows are more than half of all rows (more than the live
   rows), and only with more than one segment.
5. `segment.go` comment on `sumRange`, "The cost does not grow with the size
   of the range": it grows by one block sum per 64 pages (plus ≤ 126 index
   entries and ≤ 2 pages); the doc's measurements say so ("hundreds of index
   entries per child").
6. `bulk.md` step 1 "Spool. The tar is read into `<storage>.causal.db.bulk-*`
   … Open removes spools": the node streams (`IngestBulkStream`: "nothing is
   spooled"); bulk.md's own Measured section says "no spool". A temporary
   `.bulk-` directory exists only in the client tool (`tools/localdata/bulk.go`).
7. `bulk.md` batch key omits the `"\x00binary"` term added for binary payload
   batches (`BatchKey`).
8. `invariants.md` RETRY-1 and HND-2 (see 19); HND-2 also calls zonelog "not
   wired", while it is the only engine.
9. Stale "Bolt" wording in code comments and docs: `storage/store.go`
   ("atomic Bolt transactions", "one Bolt transaction"), `write_batch.go`
   ("waiting for Bolt/fsync"), `causal_cache.go`, `causal_data.go`,
   `compact-receipts.md` ("transaction Bolt"), `invariants.md` CAP-1 ("Bolt
   page allocation", `storage.engine`). The transaction is now a zonelog
   frame.
10. `records.go`: "a record with more metrics than zonelog keeps in columns,
    is an opaque row": writes and batches above `MaxMetrics = 128` are
    refused, and `toLog` makes only tombstones opaque.
11. `storage.OpenWithOptions` with `BatchWrites` and no `BatchSize` uses 1 000,
    not 256 (`storage.Open` and `consistency.md` say 256, 2 ms).

---

## 21. Constants

| Constant | Value | Where |
| --- | --- | --- |
| key head | 15 B (2 col + 12 bits + 1 depth); id ≤ 255 B; depth ≤ 16 | `zonelog/key.go` |
| format | `zonelog-2` (Neumaier pairs) | `zonelog/store.go` |
| `MemoryBytes` | 256 MB; memtables /16 each; cache /8 (floor /64) | `zonelog/store.go` |
| `LogRetain` | 64 MB; log rotation at min(16 MB, LogRetain/4) | `store.go`, `log.go` |
| `BlobBytes` | 4 096 B | `store.go` |
| `pageRows`, `superPages` | 256 rows, 64 pages per block | `segment.go` |
| page cut on zone boundary | from 64 rows (pageRows/4); on 1 MB payload held | `segWriter.add` |
| Bloom | 10 bits/row, k = 6, CRC per 4 096 B chunk | `segment.go` |
| `indexSpill` | 1 MB | `segment.go` |
| skiplist | 16 levels, p = 1/4, +320 B per row accounted | `memtable.go` |
| payload frames | 64 KB, flate BestSpeed, 2 workers, 4 ahead, skip 16 | `val.go` |
| merge class | factor 4, unit MemoryBytes/32; ≥ 4 neighbours | `mergeable` |
| dead payload file | pointed < 2/3 of its bytes | `deadFiles` |
| magic / footers | `ZLS3` (16 B), `ZLV1` (20 B), `IXP1` (32 B) | |
| group commit | 256 writes, 2 ms window (Open); 1 000 default in OpenWithOptions | `storage/store.go` |
| admission | 4 096 writes, 64 MB | `write_batch.go` |
| `MaxMetrics` | 128 | `storage/records.go` |
| `scanPage` | 512 records per zonelog read lock | `records.go` |
| `planningPage` | 1 024 zones per read Tx | `planning_stats.go` |
| inventory page | 1 MB soft, 32 MB hard per row | `inventory_page.go` |
| `collectBatchZones` | 1 000 zones per collection Tx | `causal_data.go` |
| IXP1 block | ≤ 65 536 rows or 64 MB payload; parts ~64 MB | `prep/part.go`, `batch.go` |
| bulk sums tolerance | relative 1e-9 | `storage/bulk.go` `near` |

---

## 22. Things a newcomer must understand, in order

1. The key: `collection | 96 location bits | depth | id`. A zone is a key
   range; its 64 children are 64 consecutive sub-ranges; the depth byte keeps
   a zone's own records before its first child.
2. One store per node, one global seq; a write group is one frame and one
   fsync, and nothing is visible or acknowledged before that fsync.
3. Control state is rows of the same store (paths in `\x00kv`), so authority,
   receipts, history, sequences and data commit in the same cut.
4. Memtable → immutable segments → merges: an LSM tree whose segments are
   column pages with an index of page sums.
5. Sums are read, not maintained: every row adds; retractions make a
   replace or delete a subtraction; merges drop only cancelling pairs; sums are
   Neumaier pairs. Hence `Children` and `Total` are exact in which rows they
   count and cost index entries, not records.
6. The storage write: permission predicate in the commit, then receipt, zone
   sequence, record, history, receipts, usage; group commit with soft refusal.
7. The single permission predicate, and why only it authorizes an ACK.
8. Handoff as a chain of durable one-transaction steps: freeze (fence +
   snapshot), stage (+ certify), emit, install, complete, collect.
9. Bulk: a prepared sorted batch becomes one segment, one seq, one receipt;
   the MANIFEST rename is the cut.
10. Crash safety: four syncs (log, log directory entry, segment, manifest
    rename) and an Open that deletes what no MANIFEST names.

---

## 23. Candidate "Calculations"

### 23.1 Cost of a zone sum read

`Total(z)` = one `Children(parent(z))`. For S segments, a memtable range of
R_mem rows, and for child range i of P_i pages in segment g:

```text
seeks        = S × 66 × (log2(blocks) in RAM + 1 index block (cache) + log2 64 + ≤ 1 page)
range sums   ≤ Σ_g Σ_i ( ⌊P_i / 64⌋ block sums + ≤ 2·63 index entries + ≤ 2 partial pages )
memtable     = R_mem row additions
each addition = (3 + m) Neumaier puts on (value, compensation) pairs
```

Because pages are cut at zone boundaries, the partial pages are often absent
for large zones. Illustration (assumptions stated, not measured): a 14 M-row
bulk segment has at least 14·10⁶ / 256 ≈ 55 000 pages; a child holding one
eighth of it spans ≈ 6 800 pages → ≈ 106 block sums plus up to 126 index
entries, each 2·(3+13) = 32 floats for 13 metrics: ~7 500 float additions,
independent of the 1.75 M records below that child. Measured on 15 M records
(`zonelog.md`): warm children of the vegetation root 1.37 ms p50, of a depth-3
zone 0.09 ms; cold root 11.5 ms (index blocks of ~20 KB and filter chunks of
4 KB from disk). Contrast: bbolt scan of the root 10 467 ms.

### 23.2 Write amplification

Per row of small payload (< `BlobBytes`): 1 write in the log, 1 in the flush,
then ≈ log4(data / memtable) merge rewrites (code comment on `mergeable`).
With the default memtable of 16 MB (accounting, `MemoryBytes/16`) and 10 GB of
segments: log4(640) ≈ 4.7, so ≈ 6.7 writes of each row. A payload of ≥ 4 KB is
written twice (log, payload file) and not rewritten by merges unless its file
is more than a third dead. Row-level amplification in storage: one client
write commits ≈ 5 rows of its own (record, zone sequence, 2 receipts, history)
plus 2 meta rows shared by the whole group (§5). Measured disk/raw:
1.01 to 1.23 for insert-only data, 1.5 to 2.1 for records replaced 20 times
between merges (`zonelog.md`).

### 23.3 Group commit amortisation

With group bound B (256), window δ (2 ms, only when fewer than B are queued),
fsync latency f, and per-write validation and apply time c:

```text
throughput ≈ B / (f + B·c + [δ if the queue is short])
fsync per acknowledged write = f / B
```

At B = 256 one fsync is shared by 256 acknowledgements; under saturation the
window is skipped ("A full backlog can go straight to disk"). Measured
(`zonelog.md`, 2 vCPU, virtual disk): zonelog one write per fsync
6 038 inserts/s; 256 concurrent callers 73 764/s (≈ 288 groups/s if each
group were full, ≈ 3.5 ms per group); one call of 256 rows 151 527/s. bbolt
before: 284/s and 5 551/s. AWS ladder after the paging fix: up to 47 069
acknowledged writes/s per cluster of 16 nodes (commit `b6bc03d`).
