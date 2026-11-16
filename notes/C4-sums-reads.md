# C4 — Sums and reads: technical note for the paper writer

Code read on 2026-11-16: `/home/claude/code/core` (Go) and `/home/claude/code/sdk/src` (JS).
Rule of this note: the code wins. Every disagreement with the docs is listed in §12.
Paths are relative to `core/` or `sdk/src/` as marked.

Vocabulary used below (fixed, one meaning each):

- **zone**: a (collection, location) pair; location is a string over the routing alphabet
  `0-9A-Za-z-_` (64 characters, 6 bits each); the root is `@`.
- **Sum**: the (count, metric sums) pair of a set of records (Go `wire.Abelian`).
- **row** (of a zone answer): one key of a zone with its Sum.
- **Block**: one IXB2 rows section, i.e. the rows of one zone at one key length.
- **owner** of a zone: the vnode whose id is XOR-closest to the zone id (C1/C3).
- **holder**: the (vnode, host, storage) the durable routing snapshot routes a zone to (C3).
- **boundary** (edge): a zone this vnode owns whose parent another vnode owns.
- **contribution**: the absolute, versioned Sum of a boundary, sent to the parent's owner.

---

## 1. The Sum of a zone

**Definition.** The Sum of a zone is the count of items at or below it and, per metric
position, the sum of their metrics. It is an element of an abelian group: it adds, it
subtracts, and the empty Sum is its identity.

**Data structure** (`core/internal/wire/aggregate.go`, `type Abelian`):
```
Abelian { count int; metrics []float64; compensation []float64 }   // compensation: local only
JSON: {"count": n, "metrics": [...]}                                  // corrected sums
```

**Pseudocode** (`accumulate`, used by `Sum` sign=+1 and `Substract` sign=-1):
```
accumulate(a, delta, sign):
  if delta == nil: return
  a.count += sign * delta.count
  widen(a, len(delta.metrics))          // narrower deltas touch only their positions,
                                        // wider ones grow a; missing positions read 0
  for i, v in delta.metrics:
    addMetric(a, i, sign*v)             // Neumaier step: keep the lost low-order part
    addMetric(a, i, sign*delta.compensation[i])
Metric(i) = metrics[i] + compensation[i]   (0 if i out of range)
```

**Rule.** Sums are order-free and invertible: `S(A ∪ B) = S(A) + S(B)`, `S(A \ B) = S(A) − S(B)`
for disjoint A, B; metric widths may differ across records. Float sums are IEEE-754 with
Neumaier compensation, not exact reals (stated in `aggregate.go` and
`docs/protocol/aggregation-verification.md`). No named invariant in code; the docs call the
parent rule AGG-1 (§3).

**Count is items, not records.** Every server path builds the Abelian count as
`round(Weight)` (`internal/summary/fold.go itemCount`, `store.go valueLocked`:
`NewAbelian(int(math.Round(total.Weight)), ...)`): a pre-aggregated record with weight w
counts for w items (`wire.Item.Weight`, 0 meaning one).

**Deletes.** A delete is a tombstone row in the store; the store's range sums skip it
(`zonelog` `flagUncounted`), so the zone's Sum decreases. Upward, nothing subtracts a delta:
the boundary's new absolute value replaces the old (§3.4). `recordDelta` in `fold.go`
computes (add, remove) from (record, previous) only to decide whether a write changed
anything.

**Files.** `core/internal/wire/aggregate.go`; JS mirror `sdk/src/tree/abelian.js`
(functions over `{count, metrics}`, equality with tolerance 1e-9).

---

## 2. Sums in the store (interface used by C4; construction is C2)

**Definition.** The store answers the Sum of any zone from precomputed range sums in its
segments, without reading records.

**Data structure** (`core/internal/zonelog/read.go`):
```
Sum { Count int64 /*live records*/; Weight float64 /*items*/; Metrics []float64; Only string }
Children(collection, zone) -> [65]Sum   // [0] records placed exactly at zone, [1+c] at/below child c
Total(collection, zone)    -> Sum       // = Children(parent)[1+c], or Σ children for the root
```
`Only` is the one location holding every live record of the range, or `""`.

**Rule.** `ZoneChildren` "reads every row the disk holds, whatever its authority: zones
handed away and not yet collected count until they are" (`internal/storage/zone_sums.go`).
The summary layer corrects for that (§3.2). Exposed as `storage.Store.ZoneChildren /
ZoneTotal / Collections`.

---

## 3. The summary tree of a node (`core/internal/summary`)

**Definition.** For each vnode, the summary is the read accelerator that answers a zone
it owns: the store's sums of local rows, corrected by the contributions of children held by
other vnodes. "A summary is a read accelerator: it never grants permission to write"
(`tree.go` package comment).

### 3.1 State (`tree.go type Tree`)
```
incoming      map[Key]summaryContribution   // one per remote child: absolute versioned Sum
Edges         map[Key]*Edge                  // boundaries this vnode pushes
pendingEdges  set[Key]                       // edges with a value to send; one timer for all
flushTimer, flushAt                          // the single flush timer
Summaries     *foldMark{digest}              // view the summaries were made ready for
lastDigest, LastReconcile, LastFold, PollEvery, fullTicks, revision, epoch
```
```
summaryContribution { epoch, generation, revision uint64; holder causal.Holder;
                      value *Abelian; exact string }
Edge { Pending *mesh.Contribution; Stale bool; lastAttempt, retryAt time.Time; failures int }
mesh.Contribution { Collection, Location, Epoch, Revision, Generation, Holder,
                    Count, Metrics, Exact }
```
No Sum per zone is held in memory: "only those contributions (mesh.incoming, one per remote
child) and the boundaries waiting to be pushed" (`store.go`).

### 3.2 Owned Sums: store minus remote rows plus remote contributions
```
valueLocked(col, loc):                       // store.go
  part = storePart(value = Total(col,loc) as Abelian, local = Total.Count, exact = Total.Only)
  for key in incomingBelowLocked(col, loc):  // remote children strictly below loc,
                                             // outermost only (not below another one)
    local = Total(col, key.loc)
    part.value -= local                      // local copy of rows that are now remote
    part.local -= local.Count
    if incoming[key].count > 0: part.value += incoming[key].value; part.remote++
    exact = (remote==1 && local==0) ? incoming[key].exact : ""
  return part.value, part.exact
```
**Rule.** Owned value = Σ local rows at/below z − Σ local rows at/below each outermost
remote child + Σ contributions of those children. Each record counts once if each
remote child's contribution is that child's absolute total (§3.4).

### 3.3 Answering a zone: `Tree.Set(collection, location)` (`store.go`)
```
Set(col, loc):
  if Summaries == nil or view == nil or Summaries.digest != view.digest or LastFold.zero:
      return (nil, false)                       // not ready: caller scans instead
  if view.Len() > 1 and authorityDigest() != lastDigest:
      return (nil, false)                       // authority changed since last full poll
  parts[0..64] = ZoneChildren(col, loc)         // [0] self, [1+c] child c
  for key in incomingBelowLocked(col, loc):
      parts[1 + index(key.loc[len(loc)])].correct(...)   // as in valueLocked
  set = {}
  if parts[0].count > 0: set[loc] = parts[0]
  for c in 0..63: if parts[1+c].count > 0:
      set[groupKey(loc, loc+c, parts[1+c].exact)] = parts[1+c]
  return (set, true)
```
**Keys of a zone** (`groups.go`, `zoneKeyDepth = 4`):
```
groupKey(path, child, exact):
  if exact is not strictly below child: return child          // one character under path
  return exact[:min(len(exact), len(path)+4)]                  // the lone location, cut 4 chars
```
A key longer than one character means "every record of this child sits in that cell".
The relay/scan path builds the same keys with `summary.Groups` (`Add`, `Set`), so owner
summary and scan answer the same rows (tests named in wire-block.md:
`TestRelayedBlockReadEqualsTheOwners`, `TestZoneKeysAreTheSameFromOwnerAndRelay`).
`Owned(col, loc)` returns `valueLocked` for an owned zone (used by `/aggregates`).

### 3.4 Boundaries and push
**Boundaries** (`store.go boundaries`): DFS from the root over zones with records on this
disk; emit z when this vnode owns z, does not own its parent, z ≠ root. Prune where
`ownerBelow(view, id, depth)` says one vnode owns every descendant and it is not this one
(or this one already owns z), or at depth ≥ 16 characters.

**Which boundary a write queues** (`boundaryOf`): walk up from the written location while
this vnode owns the zone; the highest such zone (≠ root) is the edge.

```
OnLocalWrite(record, previous):                // fold.go
  if recordDelta(record, previous) is empty: return
  queueEdgeLocked(boundaryOf(record.loc))

queueEdgeLocked(key):                          // store.go
  edge.Stale = true; pendingEdges += key
  wait = remaining of the 1 s window since edge.lastAttempt, else 1 s
  armFlushLocked(now + wait)                   // one timer; only moves earlier

FlushPendingEdges():                           // fold.go, run by sendEdge (one pass in flight + one follow-up)
  for key in pendingEdges (each under Mu on its own):
    if edge.Stale and retryAt passed: edge.Pending = wireLocked(key); Stale = false
    if Pending == nil: drop key;  if retryAt in future: skip
    collect (key, Pending); lastAttempt = now
  group by holder of parent (CausalRouting.Route); self-holder → AcceptWire locally
  per host, in parallel: batches of 512 → Exchange(KindSummaryContribute), timeout 2 s
  on failure: failures++; retryAt = now + min(3 s << min(failures-1, 8), 30 s); arm
  on success: if Pending is the sent (epoch, revision, generation, holder): Pending = nil, drop key
```
`wireLocked(key)` reads the value **at send time** from the store (`valueLocked`), and
increments `revision`. So all writes inside one window travel as one absolute value.

**Accepting** (`accept.go acceptChild`):
```
acceptChild(in):
  parent = Parent(in.loc); if not OwnsHere(parent): droppedNotOwner++; return ErrNotOwner
  if in.holder == self: Fold(force)            // boundary moved here: local data wins
  if not ChildHolderCurrent(in.loc, in.holder): droppedStaleHolder++; return
  if incoming[key] exists and not newerContribution(old, in): return  // idempotent
  incoming[key] = in;  accepted++
  then refreshZone(parent) → queueAboveLocked(parent)   // cascade to the next boundary up
newerContribution(old, in) = in.holder != old.holder
  or (epoch, generation, revision) of in > old, compared lexicographically
```
**Rule (versioned replacement; docs AGG-1, code comment "SUM-1, SUM-2").**
A parent keeps one absolute contribution per remote child and only replaces it with a
newer one; "Replacing it is the only allowed update; a bare delta is not" (`fold.go
summaryContribution`). Re-applying a contribution changes nothing; a stale holder's value is
dropped; a missing message is not zero.

`epoch`: one per incarnation of the vnode's store (`New(service, epoch, hooks)`);
`generation`: the view's generation; `revision`: per-tree counter bumped by every `wireLocked`.

### 3.5 Repair: reconcile, polls, folds
```
Reconcile(force):                               // every ReconcileEvery tick (indexus maintenance)
  RefreshView()
  if authorityDigest changed: fullTicks = 5
  if fullTicks > 0 or active since last poll: PollEvery = 5 s
  all  = force or Summaries nil or fullTicks > 0 or never reconciled
  full = all or since(LastReconcile) >= max(PollEvery, 5 s)
  Fold(force=false); flushPending()
  if full:
    PollRemoteHosts(all)    // all: every remote host; else rotating window
    on success: lastDigest = digest; LastReconcile = now
                PollEvery = pollChanged ? 5 s : min(2·every, 2 min)
```
- `summaryPollWindow(N) = min(N, max(4, bits.Len(N)))`; `rotateHosts` covers all hosts in
  ⌈N/window⌉ polls (**SUM-2**, `docs/protocol/invariants.md`).
- `PollHost`: `KindSummaryGet` pages of 8192 contributions, timeout 10 s per page; the
  peer answers with `ExportPage` = `wireLocked` of each of its boundaries whose parent this
  node owns (Count > 0 only), cursor = last key.
- `Fold(force)`: due when forced, authority digest changed, never folded, or (store
  revision changed and ≥ 5 min since last fold and `Quiet()`); `FoldLocal` re-marks the
  view and `refreshLocked` (drops incoming of children no longer remote/current, recomputes
  all boundaries, queues every one). No record is read ("The store keeps the sums").
- `SetView(view, local, repush)`: a changed view digest re-queues every owned boundary.
- `Ensure(ctx)`: first read may force a Fold.

**Rule.** The push path is primary; polls only repair. Eventual convergence after writes
stop and messages are delivered; no bounded delay under partition (consistency.md,
aggregation-verification.md).

**Constants** (`fold.go`): `summaryRemoteWindow = 1 s`, `summaryRetryAfter = 3 s`,
`summaryRetryCap = 30 s`, `summaryRPCTimeout = 2 s`, `summaryPollPage = 8192`,
`summaryPollTimeout = 10 s`, `ReconcileEvery = 5 s`, `ReconcileIdleMax = 2 min`,
`InventoryEvery = 5 min`, `summaryContributionBatch = 512`, `FullTicksAfterChange = 5`;
`groups.go zoneKeyDepth = 4`; `boundaries` depth cap 16 characters.

**Observed in code, not covered by a test (verify before stating in the paper).** If a
write queues an edge while that edge's push is in flight, `queueEdgeLocked` sets
`Stale = true`. On success `FlushPendingEdges` finds `Pending` equal to the sent value,
clears it and removes the key from `pendingEdges` without checking `Stale`. The later flush
does not see the key. The new value then reaches the parent only by a poll, or by the next
write to that edge.

---

## 4. Read paths in `indexus` (server)

### 4.1 One zone: `meshGet` (`indexus/mesh_runtime.go`)
```
GetSetContext(ctx, col, loc, deep, via, refresh):   // read.go; via is accepted, unused
  take one of 8 readSlots (batchParallelism)
  (contact, set) = meshGet(col, loc, deep || refresh, refresh)
  if set: reads.put(key, set, now)                 // every success fills the read cache

meshGet(col, loc, deep, refresh):
  (contact, local) = meshReadRoute(zone)           // CausalRouting.Route(zone.ID)
  if not deep and not local: return (contact, nil) // redirect
  if local and not refresh:
      if summary.Set(col, loc) ok: return it       // derived, from memory + store sums
      if summary.Ensure(ctx) and summary.Set ok: return it
  inventory = QueryPrefixMetrics(col, loc)         // authoritative scan, metrics only, 30 s
  groups = Groups(loc); for each live record at its snapshot's zone: groups.Add
  return (meshReadRoute(zone).contact, groups.Set())
```
| request | holder is this node | holder is another node |
|---|---|---|
| `deep=false` | summary (or scan if not ready) | redirect (contact, no set) |
| `deep=true` (HTTP default) | summary (or scan if not ready) | relay scan of holders' records |
| `refresh=true` | scan | scan |

### 4.2 Many zones: `GetSetsBlockContext` → `resolveSets` → `wire.EncodeSetsBlockColumns`
Dedupe locations (≤ `MaxReadLocations = 1024`), 8 workers, one `GetSetContext` or
`ReadContext` per location; first error cancels the batch; nil set + remote contact →
redirect `{Location, Name, IP, Port}`. With an explicit policy: `deep, via, refresh = true,
nil, true`.

### 4.3 Read policies (`indexus/read_policy.go`)
```
ReadContext(col, loc, {Mode, MaxAge}):
  cached: if reads.get(key, MaxAge) hit: return {Source:"cache", ObservedAt}
  loop with 30 s budget:
    GetSetContext(deep=true, refresh=true)        // fresh never uses summaries
    ok → {Source:"inventory", ObservedAt: now}
    stale-if-error: on error return cache hit with FallbackError, else fail
    retry only on ErrFrozen/ErrNotReady/ErrNotOwner/ErrDependency,
      backoff min(5 ms << min(attempt,5), 100 ms)
```
Cache: ≤ 32 entries, ≤ 16 MiB estimated (`Set.Clone(limit)`), oldest evicted, a hit does
not refresh `ObservedAt`; `forget(collection)` drops a collection. `MaxAge` bounds time since
this node observed the result, not the age of remote contributions inside a summary.

**Two families of freshness, not to be confused.**
- *summary vs deep/refresh*: summary = derived (store sums + contributions), served only by
  the holder with `refresh=false`; `refresh=true` (or any explicit policy) = authoritative
  scan of the durable inventories.
- *fresh / cached / stale-if-error*: per-node result cache policy on top of the scan.

### 4.4 Records: `GetRecordsContext` (`indexus/content_records.go`)
`QueryPrefixLimited(col, prefix, limit ≤ 10000, bytes ≤ 64 MiB)`, live records under the
prefix, sorted by (location, id), over budget → `ErrQueryBudget` (HTTP 413).

### 4.5 `GetAggregates` (`indexus/read.go`)
Only for locations this vnode owns in the current view and whose placement is on this
storage: `summary.Owned`.

---

## 5. HTTP read endpoints (`core/internal/adapter/http/p2p`, high level)

| endpoint | params | answer |
|---|---|---|
| `GET /sets` | `collection`, `location=a,b,…` (≤1024), `deep` (default true), `refresh`, `via`, `read_mode`, `max_age`, `metrics=f64`, `columns=i,j,…` | IXB2 (`application/vnd.indexus.block`), gzip if ≥ 1400 bytes and accepted (gzip cache 16 MiB by SHA-256); `X-Indexus-Read-Mode`; ingress hint `X-Indexus-Ingress-{Name,IP,Port}` from `X-Indexus-Routing-Key` |
| `GET /set` | one location, same flags | JSON `{contact, set}`; with policy `X-Indexus-Read-Source`, `X-Indexus-Observed-At`, `X-Indexus-Read-Fallback` |
| `GET /records` | `collection`, `location`, `limit` 1..10000, `format=binary` | JSON `{"records":[…]}` or IXRB v2, streamed, gzip |
| `GET /aggregates` | `collection`, `location=a,b` | JSON `{"aggregates": {loc: Abelian}}` |
| `GET /content` | content stream (out of scope) | |

`format=block` and `envelope` are accepted and ignored. Scope `read` is required on each.

---

## 6. The Block (IXB2) and IXRB (`core/internal/wire/sets_block.go`, `records_wire.go`)

**Definition.** A Block is the Sums of the keys of one zone at one key length, as aligned
little-endian columns. A `/sets` answer for one zone is the sums of its children: one row
for the records exactly at the zone, one row per non-empty child character (or its lone
location, ≤ 4 characters below), so at most 65 rows over at most 5 sections
(suffix length 0..4).

**Layout** (all LE, sections 4-aligned):
```
Header 16 B : "IXB2" | u16 headerBytes=16 | u16 flags (b0 redirects, b1 f64, b2 columns) | u32 sectionCount | u32 0
Section 8 B : u32 sectionBytes | u16 kind (1 rows, 2 redirects, 3 columns) | u16 0
Rows body   : u32 n | u8 parentLen | u8 suffixChars s | u8 keyWords k=ceil(6s/32) | u8 metricCount m
              | u32 revision (written 0) | parent ASCII (root = ""), pad 4
              | [n·k] u32 keys (6-bit routing indices, MSB-first) | [n] u32 count
              | [m][n] f32 metrics, column-major   (f64: pad to 8 from body start, [m][n] f64)
Columns     : u32 c | [c] u16 positions | pad 4                    (first, when columns=)
Redirects   : u32 count | per item u16 locLen, nameLen, ipLen, port | strings | pad 4
```
**Encoder pseudocode** (`EncodeSetsBlockColumns`):
```
for index, loc in locations:  for (key, sum) in sets[loc]:
    key = strip ":ref", cut to SetsPrecision (32)
    suffix = key minus parent (else fallback: parent "", full key)
    row.order = index<<39 | fallback<<38 | chars<<32 | words[0]
radix-sort rows by order (8 byte passes, skipped when constant), ties on words[1:]
section = run of equal order>>32 (location, fallback, chars)
in each section: equal keys fold (count and metrics summed in float64, rounded once to f32)
```
**Rule.** Keys unique and ascending in a section; sections in request order, then by
ascending `suffixChars`; owner, relay and refresh answers equal byte for byte for the same
data (wire-block.md, tests cited there). `columns=` selects what is sent, not what is summed.
float32 keeps 24 bits; `metrics=f64` for exact sums beyond that.

**IXRB v2** (`/records?format=binary`): `"IXRB" | u8 2 | 3×0 | u32 count | records`; record =
`u16 len, location | u16 len, id | u8 flags (b0 binary) | f64 weight | u8 n, n×f64 metrics
| u32 len | 0–3 zero bytes | payload` (payload 4-aligned in the body).

**Constants** (`wire.go`, mirrored in `sdk/src/api/wire.js`): `MaxReadLocations = 1024`,
`MaxContentRecords = 10000`, `MaxContentParts = 1024`, `MaxContentBytes = 64 MiB`,
`SetsPrecision = 32`, `SetsPropertyCount = 4` (scratch sizing only), `SetsMetricScale =
1 000 000` (v1 relic, unused by IXB2); scratch pool cap 32 MiB.

**Decoder** (`sdk/src/wire/block.js decodeBlocks`): zero-copy typed-array views on the
response buffer; rejects bad magic, header ≠ 16, overrun, non-4 section, `k ≠ ceil(6s/32)`,
trailing bytes, f64 body not 8-aligned, columns flag/section mismatch.

---

## 7. Client network layer (`sdk/src/network`, `sdk/src/api`)

**Definition.** `Network` is one client session: a peer table, a read path for `/sets`
and `/records`, a cache, and coalescing of concurrent reads.

**Two navigations** (`network/setsFetch.js`, default `ingress`, `helpers.normalizeNavigation`):
- **ingress**: one sticky peer, XOR-nearest to a random 16-byte session routing key
  (`randomRoutingKey(16)`), `deep=true`, so the server relays (§4.1); 3 attempts, a failed
  peer is removed; the ingress hint header can move the session.
- **direct**: `deep=false`; per location pick the remembered owner (`_owners`, ≤ 4096) or
  the XOR-nearest peer excluding `via`; group by peer; follow redirects; rounds ≤
  max(8, 3·locations). Soft miss (no peer) is never cached as empty.

**Raw read** (`setsRaw.js _getSetsRaw`), used by the heat worker:
```
for zone: join the in-flight wave of that zone if it is not aborted and (it refreshes or we don't)
others → one SharedRead wave (timeout 15 s) through the coalesce pool
result: responses (IXB2 buffers), empty (answered without rows), unresolved (ask later)
```
Coalesce pool (`setsCoalescePool.js`): merges callers within a microtask per collection,
chunks of `setsMaxChunkSize = 128` locations, `setsMaxParallelChunks = concurrency` (50).

**Element read** (`sets.js getSets`, used by nearby search): LRU `_cache` (default 1000
zones) of Items/Sets built by `blocksToElements` (one object per row; count 1 → Item, else
Set; metrics kept in the v1 shape: positions 2, 3, 4, position 2 truncated; `_terminal =
false`). `refresh` reuses an entry younger than `refreshTtlMs = 5000`. A non-empty entry
is never replaced by an empty answer.

**Implemented vs not.** The SDK never sends `read_mode`/`max_age`; it uses `deep`,
`refresh`, `via`, `metrics`, `columns`. `api/getZone.js` calls `/set?deep=true&refresh=true`.

---

## 8. The walk: which zones a view reads (`sdk/src/walk`)

### 8.1 Zone index (`walk/zones.js`)
```
ZoneSummary { location, depth, count, metricCount, metricSums,
              own {count, metricSums},                 // the suffixChars-0 row
              children {count[64], rows[64], items[64], metricSums[64·m]},  // by first routing digit
              blocks [{handle, n, suffixChars, metricCount, ranges[2·64]}] }  // rows of digit r: ranges[2r]..[2r+1]
zoneLevels(space, summary): levels j = 0..step; level j bins the 64 digits by their first
  j·size geometric bits; geometric digit = (r − offset(depth)) mod 64
```
With `space.size` coordinates and `space.step = 6 / size` binary levels per character
(2-D GPS: size 2, step 3). A node of the descent is (zone, j, p) or the child row (zone,
step, r); its resolution is `zone.depth·step + j`.

### 8.2 Descent (`walk/index.js descend`, the Cube.retrieve of v1)
```
descend(index, R, bounds, policy, items, missing):
  stack = [root node]
  while stack: n = pop
    skip if no rows, or cell does not overlap bounds (contained → bypass later tests)
    if res(n) == R or (not items and res(n) > R): out += n; continue
    if n.j < step: childCount = levels[j].children[p]
    else: child = index.get(location + r)
          if child loaded: continue in child at j = 0; complete = (child.count == count)
          else: childCount = 0; if not items and not (covered and count ≤ limit): missing += child loc
    if covered and (count ≤ limit or childCount < need): out += n; continue
    if childCount == 0 or not complete: out += n; continue
    push children (next binary level, or the child characters)
```
### 8.3 Viewport (`walkViewport`)
```
center = floor(zoom + resolution)          // default resolution 5 (WALK_DEFAULTS.algorithmResolution)
for slot in center-1 .. center+1:          // three slots
  for depth = slot down to max(0, center - 6):     // parentFallbackDepth 6
    cells = descend(depth); if cells non-empty: picked += (slot, depth, cells); break
emit each slot (plain cells, or virtual split ≤ 4 binary levels, ≤ 20000 cells per slot)
stats = descend(statsDepth, strictBounds, items=true), weighted by visible fraction
```
**Output: `Plan`** — `entries` (8 u32 each: handle, firstRow, rowCount, slot, targetResolution,
flags ENTER 1 / LEAVE 2 / NUDGE 4 / VIRTUAL 8, outBase, binCapacity), `capacity` (instances),
`parents` (anchor per output), `anchors` (count, m, metric sums of parent cells), `pinned`,
`missing`, `stats`, `signature` (FNV-1a of entries). Instance = 14 floats.

**Rule.** The zones a view reads are exactly `plan.missing`: the not-yet-loaded child zones
of every cell that overlaps the render window and is coarser than the target resolution of
a slot. A partially delivered child (`child.count != parent row count`) never replaces its
parent's mass. Every drawn mass is a Sum read from a Block, never a count of records on the
client.

**Window.** `viewWindow`: the strict view expanded by `WINDOW_MARGIN = 0.25` of its height and
width on each side, kept while the depth is unchanged and it still contains the view.
`nextDisplayZoom`: a jump of exactly two depths shows one intermediate bracket.

**Virtual split.** A cell coarser than its slot by 1..4 binary levels (`MAX_VIRTUAL_CHILD_
DEPTH_DELTA = 4`) is split without loading the child zone when its rows sit in one block
whose `suffixChars·6` covers the needed bits: this uses the multi-character keys of §3.3.
This is why the server cuts lone locations at 4 characters.

### 8.4 The heat worker loop (`walk/heat/worker.js`)
```
refresh(): (plan, missing) = walk(); abortStale(missing); request(missing); publish(plan)
request(missing): wanted = missing − inflight − empty − waiting-retry
                  read(wanted)  → network.getSets(raw: true, metrics "f32[;columns]")
read(): per answered zone: index.ingest(zone, handles, blocks); post BLOCKS (buffer transferred)
        answer.empty → zone marked empty; unresolved → retry after RETRY_MS = 2000
reconcile(force): queue = [root]; read with refresh: true and unchanged: true, batches of 16,
        ≤ 48 zones unless forced; descend into a loaded child in view whose child count changed,
        down to depth ceil((depthOf(zoom)+1)/step); skip zones fetched < refreshTtlMs ago
        (debounce 1000 ms after reads settle, 10 s idle)
```
`completePlans`: a plan waits up to 2500 ms for its detail. Handles are dense and reused
only after `STORE_EVICTED`.

---

## 9. Store, GPU and the heat pipeline (`sdk/src/store`, `gpu`, `map/heat`)

### 9.1 Block store (`store/index.js`) — CPU copy, main thread
```
put(handle, zone, rowsBlock)   // keeps the response buffer by its views, no copy
get(handle)                    // bumps the buffer in LRU order
pin(handles)                   // the handles of the last plan (and their zones' ancestors: pinsOf)
evict()                        // while bytes > budget: drop least recent unpinned buffer, whole
```
**Rule.** A buffer is counted once and leaves only as a whole; pinned buffers are never
evicted, so pins may hold the store above budget. Default budget `256 << 20` (256 MiB).

### 9.2 GPU arena (`gpu/arena.js`)
Three STORAGE buffers (`keys`, `count`, `metrics`) sub-allocated per block by a bump
pointer, plus a block table of 48 bytes per handle (origin = the parent zone's cell
coordinates, depth, offsets). Holes from `drop`; on overflow reallocate and copy live blocks
GPU→GPU: same size when holes ≥ 25 % (`COMPACT_RATIO`), else ×2; cap = budget (256 MiB) and
device limits. f64 metrics are rounded to f32 once at upload. After device loss `rebuild`
rewrites everything from the CPU store, without the network.

### 9.3 Pack (`gpu/pack.js`)
One 64-lane workgroup per output sums count and the metrics the heat rules need over the
entry's runs of rows (tree reduction, no float atomics) and writes 14 floats. A virtual entry
owns 2^(bits−6) outputs; its rows per bin are at most two runs, found by binary search,
because geometric digit = routing digit − offset mod 64. Heat rules: ≤ 3 `{num, den, minDen,
transform (0 | 1 = log1p), shift}`, column −1 = count. Transitions: previous plan copied, then
shifted, ENTER/LEAVE from `planMotion`.

### 9.4 Field, Cell, combine, compose (`gpu/field.js`, `gpu/combine.js`, `map/heat/compose.js`)
- **Cell**: (c0, c1, c2, resolution) — integer coordinates with the collection's offset
  removed. It is the key shared by collections that cut space the same way.
- **Field**: one GPU buffer per collection per view: header (tableSize, capacity, coarsest),
  open-addressing hash table on `cellHash`, rows `c0, c1, c2, resolution+1, num, den`
  (6 u32/f32). `FIELD_MAX_RESOLUTION = 32`.
- **Combine**: for each output of the first field, find in every other field the row of the
  same Cell or of the nearest enclosing one, take num/den; missing field → its `missing`
  value or the cell is dropped. Expression compiled once to postfix (≤ 24 ops, stack 8;
  `+ - * /`, unary −, min, max, abs, log1p, clamp, ramp; total: x/0 = 0).
- **compose({fields ≤ 4, expression})**: one heat pipeline per field; all fields must have
  identical dimensions (`spaceOf` check); the first field's cells are drawn.

### 9.5 Pipeline (`map/heat/pipeline.js`)
Worker messages: `BLOCKS` → `adoptBlocks` (store.put; arena.put), `PLAN` → `store.pin`,
`store.evict` → `STORE_EVICTED`, packer packs; `DROP` → store.drop → `STORE_EVICTED`.
Cross-fade 400 ms (`TRANSITION_DURATION_MS`).

---

## 10. Incremental nearby search: 2024 paper vs SDK today

**Is it in the SDK?** Yes, as `Local` (`sdk/src/local/index.js`, `exploration.js`,
`observer.js`, `layer.js`, `store.js`), exported from `sdk/src/index.js` ("Nearby — nearest
items, ring by ring"). It is used by the heat worker on the `nearby` surface
(`walk/heat/search.js`, message `SEARCH` → `SEARCH_RESULT`). The word "feed" does not occur
in the SDK.

**Correspondence (paper Algorithm 1 and 2 → code).**
```
run():                                    // = search() of the paper
  if prepare():
     if current.final: stream(); return
     query(); level++
  else: level--; if level == 0: level = layers.length
  run()
search(): limit += options.step; run()   // each call asks for `step` more items
prepare(): identical to the paper line by line (sort by distance; select until
  distance > previous.radius or count ≥ cap·limit; radius; waiting; predicted;
  final; return predicted ≥ limit or radius == first.radius)
stream(): emit min(step, selected.count) items
```
`Layer {radius, indexed, selected, loaded (Store: list + Σ count), final = true, waiting}`.

**Differences from the paper.**
1. `prepare()` is called once per step (the paper's pseudocode calls it twice).
2. `query()` batches: all selected Sets of a collection go in one `network.getSets`
   (one `/sets` request with many locations); a selected element with
   `0 < count ≤ 1000` (or an Item) is read with `network.getRecords(…, 1000)` (`/records`)
   so the last layer holds verified records, not projected cells.
3. Children come from IXB2 rows turned into elements (`blocksToElements`): truncated keys,
   v1 metric positions 2, 3, 4, `_terminal = false` (a projected cell cannot be a final item).
4. Distance: `addLocation` decodes the element's location into segments; overall distance =
   Σ_i segmentDistance(origin_i, segment_i) / ratio_i / dims; direction and distance
   filters per dimension drop elements (paper "Filtering").
5. Multi-collection: the constructor takes `{collection: space}` and seeds one root per
   collection (paper "Cross-Collection Search"); the heat worker uses one collection.
6. Parameters in the heat worker: `cap = 1`, `step` from the request (≥ 1), origin
   `gps(lat, lng)`, filter `[0,0]..[0,360]` (no restriction); `fresh: false` continues the
   same explorer (next batch), otherwise a new one.
7. Cancellation: `options.signal`, `checkRead` at each step.

So: the paper's algorithm is implemented almost verbatim, with batched reads and a records
read at the leaves. The density counters it relies on are the Sums of §1–§3.

---

## 11. Implemented vs documented only

Implemented: everything in §1–§10 above.

Documented only (or not found in code):
- `docs/protocol/query.md` "What the client keeps: frontier, visited, pruned, cursors,
  bounds, results": no such structure in the SDK walk or in `Local`.
- IXB2 `revision` field: "reserved for zone versions"; always written 0, read and unused.
- `docs/heat-pipeline.md`, `docs/layers.md`, `docs/compose.md` are cited by SDK comments but
  exist in neither repository (`find` over `/home/claude/code`).
- `read_mode` / `max_age` are server features the SDK does not use.
- The `via` parameter is parsed by HTTP and passed to `GetSetContext` but not used by `meshGet`.
- The peer `/sets` client (`internal/adapter/peer`): wire-block.md says "The mesh runtime
  has no caller of this client today".

## 12. Docs / code disagreements (code wins)

1. **How owned sums are computed.** query.md "Aggregates", consistency.md and AGG-1 say
   "the written zone folds the delta at once; same-vnode ancestors fold on the next Update,
   in one deepest-first pass". Code: no Sum is kept per zone. A read computes it from the
   store's range sums plus `incoming` (`store.go` comment). A write only queues the boundary.
2. **Keys of a zone, owner side.** query.md: "a compressed tree whose nodes are record
   locations, branches and ownership boundaries … a chain of at most 16 nodes". Code:
   `zonelog.Sum.Only` from the first and last row of a range (`only()`), and
   `Contribution.Exact` for remote children. The 16 survives only as the depth cap of
   `boundaries`.
3. **Poll cadence.** query.md: "Boundary polling runs at a slower one-minute cadence and for
   three consecutive ticks after an authority change". Code: `ReconcileEvery = 5 s` while
   active, doubling to `ReconcileIdleMax = 2 min` when idle, `FullTicksAfterChange = 5`,
   steady-state window `max(4, bits.Len(N))` hosts (SUM-2 matches the code).
4. **SUM-1.** Cited in `internal/summary/tree.go` ("SUM-1, SUM-2"); not defined in
   `docs/protocol/invariants.md` (only SUM-2 and AGG-1 exist).
5. **Count semantics.** Docs speak of record counts (`Count(P) = Direct(P) + Σ children`).
   The served count is the item weight (`round(Weight)`); with plain records it equals the
   record count.
6. read-modes.md: matches the code (32 entries, 16 MiB, 30 s, 8 slots, headers).
7. wire-block.md: matches the encoder. One gap: "Sections appear in the order of the
   requested locations, then by ascending suffixChars" — the sort key also puts fallback
   sections (keys not under their parent) after normal ones of the same location (bit 38).

---

## 13. Things a newcomer must understand, in order

1. A location is a string over 64 characters; each character fixes 6 bits of the zone id
   and, through the Space, `step` binary splits of every coordinate (C1).
2. The Sum (count, metric sums) is abelian: it adds, subtracts, and its count is items.
3. The store answers the Sum of any zone and of its 64 children from range sums, without
   reading records (C2). It also says when all records of a range sit at one location.
4. A `/sets` read of zone z returns at most 65 rows: the records at z, and one row per
   non-empty child, keyed by the child or by its lone location cut 4 characters below z.
5. A zone's owner answers it from the store, corrected by one absolute versioned
   contribution per child held elsewhere. Same-vnode descendants need no message.
6. A write queues the boundary above it; the boundary's absolute value is read at send
   time, coalesced to one send per second, batched by 512, retried with backoff; the parent
   replaces, never adds; it then queues its own boundary.
7. Polls repair lost pushes, on a 5 s to 2 min cadence over a rotating window of hosts.
8. Summary reads are derived and may lag; `refresh=true` or any `read_mode` scans the
   authoritative inventories; `cached`/`stale-if-error` add a per-node result cache.
9. The answer travels as IXB2 Blocks: columns a browser views without copying and uploads
   to the GPU as they are.
10. The client walk descends the zones it holds to the target resolution and names the
    missing child zones; those are its reads. Masses are always Sums from Blocks.
11. Blocks live once on the CPU (budgeted LRU, pinned by the plan) and once on the GPU
    (arena); the pack kernel turns a plan into instances; several collections join on the Cell.
12. The nearby search (Local) is the 2024 algorithm, reading Sets by `/sets` and leaves by
    `/records`, ordered by distance, `step` items per call.

---

## 14. Candidate "Calculations"

### 14.1 Bytes per Block (exact from the encoder)
Rows section bytes = 8 + 12 + pad4(|parent|) + 4·n·(k+1) + 4·n·m (f32),
with k = ceil(6s/32); for f64: + pad to 8 + 8·n·m instead of 4·n·m.
A zone answer is ≤ 65 rows (1 self row with s = 0, k = 0; ≤ 64 child rows with s ∈ 1..4,
k = 1) in ≤ 5 sections, + 16 bytes of header.

Worked: zone `aB3` (|parent| = 3 → 4), m = 4 metrics, f32, all 64 children populated by
many records (keys of 1 character), plus records exactly at `aB3`:
- self section (s = 0, k = 0, n = 1): 8 + 12 + 4 + 4·1·1 + 4·1·4 = 44
- child section (s = 1, k = 1, n = 64): 8 + 12 + 4 + 4·64·2 + 4·64·4 = 24 + 512 + 1024 = 1560
- body: 16 + 44 + 1560 = **1620 bytes** (above the 1400-byte gzip threshold).
Per child row: 8 + 4m bytes in f32 (24 for m = 4), 8 + 8m in f64 (40 for m = 4).
A request of 128 such zones (one SDK chunk): ≤ 16 + 128·(1604) ≈ 205 kB before gzip.

### 14.2 Zones a view reads at a zoom level (2-D Space, step 3)
The deepest slot is R = floor(zoom + resolution) + 1. A zone of depth D carries rows at
resolutions 3D+1 … 3D+3 (its internal binary levels and its child characters). So resolution
R needs the zones of depth D = ceil(R/3) − 1, each covering 2^−3D of each axis, i.e.
2^(R−3D) ∈ {2, 4, 8} cells per axis at resolution R. If the render window spans fractions
w and h of the two axes, the reads at that depth are about ⌈w·2^3D⌉·⌈h·2^3D⌉ zones, plus the
ancestors (held and pinned) — fewer where cells are empty (no rows, no read) or where a
virtual split stands in (§8.3). Worked: zoom 10, resolution 5 → center 15, R = 16, D = 5,
zone width 2^−15 of an axis; the render window is the view × 1.5 per axis (margin 0.25 on
each side). The writer should pick w, h from the map projection; the code gives only the
relation zoom ↔ resolution, not tile pixels.
Per request: ≤ 128 locations per chunk (SDK), ≤ 1024 per `/sets` (server); a reconcile reads
≤ 48 zones in batches of 16.

### 14.3 Freshness bound per ownership level crossed (push path, no loss)
A path from a written zone to the root crosses B ownership boundaries (vnode changes);
same-vnode levels cost nothing, since sums are read from the store at read time. Each
boundary waits ≤ `summaryRemoteWindow` = 1 s before its value is read and sent, then one RPC
(timeout 2 s), then the parent queues its own boundary. So the root's lag after a write is
≤ B·(1 s + RTT) when no message is lost. With balanced vnode ids (JOIN-1: the first
⌈log2 N⌉ bits split the vnodes), every zone of depth p = ⌈log2 N / 6⌉ and below has one owner
(`ownerBelow`), so B ≤ p: N ≤ 64 → B ≤ 1 (≈ 1 s + RTT); N ≤ 4096 → B ≤ 2. This uses an
assumption about the id distribution; state it as such.
With a lost push: repaired by the next poll that reaches the child's host, at most
⌈(N−1)/window⌉ polls with window = max(4, bits.Len(N−1)), spaced 5 s while active and up to
2 min when idle (e.g. N = 16 hosts: 15 remote, window 4, ≤ 4 polls → ≤ 20 s while active).
A failed push retries after 3, 6, 12, 24, 30, 30 … s. The read side adds the client TTL
(`refreshTtlMs` = 5 s) and, for `cached`, `max_age`.
