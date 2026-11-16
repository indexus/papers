# C3 — Authority and network: technical note for the paper writer

Sources read: `core/internal/causal`, `core/internal/mesh`, `core/internal/auth`,
`core/internal/replication/{model,journal}`, `core/indexus/{mesh_runtime,membership,node,read,read_policy,write,routing,worker,maintenance,settings}.go`,
`core/internal/storage/{causal_data,causal_zone,permission,apply,receipts,handoff,routing}.go` (the authority
predicate and handoff transactions live there, so they had to be read),
`core/internal/adapter/{meshhttp,issuer,http/p2p,transport}`, `core/quic/meshquic`, `core/gateway/http3server`,
`core/internal/app/node/{main,mesh}.go`, `docs/protocol/*.md` (gossip, write-authority, handoff,
causal-topology, invariants, consistency, ownership, failure-model, distributed-runtime,
cold-reconfiguration, read-modes), `docs/design/replication.md`, and the 2024 paper
`original/p2p-protocol/indexus-p2p-protocol-paper.tex`.

Markers used below: **[impl]** implemented and wired in the node binary; **[test-only]** code
exists but no production caller; **[doc-only]** described in docs, no code; **[DISAGREE]** docs and
code differ (the code is taken as true).

All paths are relative to `/home/claude/code/core/`.

---

## 0. Vocabulary (fix these words once, never change them)

| Word | Definition in the code | Type / file |
|---|---|---|
| ID | 96-bit point of the XOR space (`tree.Size = 12` bytes). A vnode ID is the decoded vnode name. | `tree.ID`, `internal/tree/id.go` |
| zone | One `(collection, canonical location)` pair; its `ID` is `bits(location) ‖ suffix(collection)`. Parent and child zones may share an ID, so the zone identity is the pair, not the ID. | `tree.ZoneKey` |
| region | A `(mask, value)` subset of the 96-bit space. `Region{}` is the whole space. | `tree.Region` |
| view | Set of active vnodes `{name, ID}`; `Owner(z) = argmin_v XOR(z.ID, v.ID)`. | `tree.View` |
| cell(v) | The region of IDs whose XOR owner in a view is v. | `tree.Cell(view, name)` |
| holder | `{VNode, Host, Storage}`: vnode name, endpoint URL, durable disk incarnation id. An empty disk restored under the same vnode name is a different holder. | `causal.Holder`, `authority.go` |
| grant | `{Region, Holder}`: "holder is responsible for region". | `causal.Grant` |
| token | `{Certificate digest, Index}`: a reference to one grant (output `Index` of a certificate). The genesis token is `{Hash(genesis), 0}` and denotes the whole space held by the genesis holder. | `causal.Token` |
| certificate | Consumes exactly one previous token and partitions its region into disjoint outputs with complete coverage. | `causal.Certificate` |
| terminal token / leaf | A token with no successor certificate. | `Authority.Leaves` |
| installed token | A token listed in the holder's own disk state `CausalState.Installed`. Only an installed terminal token can authorize an ACK. Receiving a certificate by gossip never installs it. | `storage.CausalState.Installed` |
| zone transfer | Irreversible per-zone flip of authority `From → To` inside a running region handoff; carries `Seq` (the zone's barrier F) and `DataDigest` (seal of frozen records and receipts). | `causal.ZoneTransfer` |
| topology replica | The grow-only, convergent set of facts: intents, activations, retirements, placements, certificates, zone transfers. | `causal.TopologyReplica`, `topology.go` |
| knowledge | `{Root, Genesis, Delta}`; the full certified fact bundle exchanged between nodes. | `mesh.Knowledge`, `service.go` |
| knowledge version | SHA-256 of the JSON encoding of the full knowledge bundle. | `makeKnowledgeFrame`, `knowledge_wire.go` |
| dot | `{Actor, Sequence}`; Actor is the disk incarnation (`Holder.Storage`). | `causal.Dot` |
| frontier | `map[actor]seq`, contiguous prefix of validated dots per actor. | `causal.Frontier` |
| operation | A string identity of one handoff/move/fold, e.g. `handoff:<hash(token,target,region)>`. Retries reuse it. | `service.go` |
| RequestID | Identity of one client write; the retry/dedup key. | `storage.writeRequest` |

`Hash(x) = SHA-256(json.Marshal(x))` everywhere in `internal/causal` (`authority.go: Hash`).

---

## 1. Two kinds of state: routing knowledge vs exclusive write authority

One-line: *routing knowledge converges by union and may be stale; write authority is a single
chain per key, installed on one disk, and checked inside the write transaction.*

| | Routing knowledge | Exclusive write authority |
|---|---|---|
| What | active view, placements, certificate graph, zone transfers, intents, retirements | installed terminal token (or installed zone transfer) on the local disk + no outgoing fence + local vnode active + placement names this disk |
| Where | `TopologyReplica` (in memory, persisted as `CausalState.Delta`) | `CausalState.Installed`, `CausalState.Transfers[*].Zones` on the holder's disk |
| How it changes | `Merge(delta)`: set union, validated atomically; order of arrival irrelevant | local disk transactions only: `CaptureCausal`, `FreezeZones`, `EmitZoneTransfers`, `EmitCausal`, `InstallZones`, `InstallCausal`, `CompleteCausal` |
| Consistency | eventual (CRDT-1, CRDT-2) | at most one writer per zone at any instant (AUTH-1..4, HND-3, ZONE-1) |
| Used for | choosing where to send (Route, HolderOfZone, QueryHolders) | deciding whether to ACK (`causalWritable`) |
| Wrong value consequence | an extra hop or a refusal | never happens: stale knowledge cannot install a token |

Code statements of the split: package comment of `internal/causal` ("separates convergent routing
knowledge from exclusive write authority", `region.go`); `TopologyReplica.Route` ("a routing hint,
never permission to write"); `Authority` ("receiving this graph never grants permission to ACK");
`storage/permission.go` ("This is the sole causal write-permission predicate").

Invariant names: ROUTE-1 (stale knowledge never grants authority), AUTH-3 (only the installed
holder ACKs), HND-3 (single writer despite divergent views).

---

## 2. The topology replica [impl]

### 2.1 Data structure (`internal/causal/topology.go`)

```
TopologyReplica {
  root        VNodeDescriptor          // pinned genesis vnode, never retired
  authority   *Authority               // certificate + zone-transfer graph (section 3)
  intents     map[Digest]JoinIntent
  records     map[Dot]ActivationRecord // activations, grow-only
  retirements map[Dot]RetirementRecord // grow-only, share the dot clock with activations
  moves       map[Digest]PlacementRecord
  ready       map[Dot]bool             // dots that validated (published)
  view        *tree.View               // derived: root + ready activations − ready retirements
  placements  map[name]placementHead   // derived: tip of each vnode's placement chain
}
TopologyDelta { Intents, Placements, Activations, Certificates, ZoneTransfers, Retirements }
```

Copy-on-write: `Merge` validates a draft and swaps maps in; `Clone()` is O(1).

### 2.2 Merge (faithful condensation of `TopologyReplica.Merge`)

```
Merge(delta):
  if every fact of delta is already known (exact digests): return            // idempotent fast path
  A := authority.clone(); A.Merge(delta.Certificates); A.MergeZoneTransfers(delta.ZoneTransfers)
  for r in delta.Activations: reject if actor≠r.Holder.Storage, seq=0, self-dependency,
        same dot with other payload, one ID with two names, one name with two (ID,holder)
  for r in delta.Retirements: reject root, wrong actor, dot reused, two retirements of one name
  repeat until no progress:
     add each pending PlacementRecord whose predecessor is known
     for each unready activation (ordered by sum of its dependency seqs):
        if frontier reaches r.Dependencies:
           cell := Cell(viewAt(r.Dependencies) + r.VNode)
           regions := grants of r.Proof (must name r.Holder) ∪ points of r.ZoneProof (acquired by r.Holder)
           if a proof piece is unknown: stay pending
           require Reaches(cell, regions)            // ACT-1
           require r.VNode.ID not a retired ID
           ready[r.Op] := true; advance frontier
     for each unready retirement: if retirementReady(r): ready, advance frontier
  if placements still pending: return ErrDependency (whole merge refused, state unchanged)
  view := root + ready activations − ready retirements; reserve retired IDs
  keep only intents not yet fulfilled; publish draft
```

Errors: `ErrConflict` (equivocation: refused, never resolved by arrival order) and
`ErrDependency` (missing ancestor: whole batch refused, retried later with full closure).

Rule guaranteed: for compatible histories the merge is commutative, associative, idempotent; a
frontier never acknowledges a hole (A:3 before A:2 does not acknowledge A:2). **CRDT-1**, **CRDT-2**,
**CRDT-3** (`Current()` returns a clone).

### 2.3 Activation (ACT-1)

One-line: an activation publishes a vnode into the active set once it holds at least one
certified grant or transferred zone that meets its XOR cell.

```
ActivationRecord { VNode, Op Dot, Dependencies Frontier, Holder, Proof []Token, ZoneProof []ZoneRef }
```

Producer `mesh.Service.publishActivation` (`service.go`):

```
publishActivation():
  if view has self or an activation of self is known: return
  cell := Cell(view + self, self)
  proof := installed tokens of self whose grant meets cell
  zoneProof := installed zones (of incoming transfers) inside cell
  if not Reaches(cell, proof ∪ zoneProof): return       // nothing yet
  record := {VNode:self, Holder:self, Op:{self.Storage, frontier[self.Storage]+1},
             Dependencies: ∅, Proof, ZoneProof}
  Store.MergeCausal({Activations:[record]}); call Activated hook
```

`Reaches(region, pieces)` = at least one piece, and every piece intersects the region
(`causal/region.go`). Complete coverage is not required: the rest of the cell is acquired while
the vnode already routes. The dependency frontier is deliberately empty: the cell is then computed
against the root alone, which contains the true cell in every view (ADD-1: adding vnodes only
shrinks cells). Consequence noted in invariants.md: the sanity check is weaker (a proof inside the
root-relative cell but outside the true one is accepted); no write permission depends on it.

### 2.4 Join intent

`JoinIntent {Author Holder, Dependencies Frontier, Plan protocol.TopologyPlan}` (`intent.go`)
reserves exact planned vnode identities (written by `Service.Reserve` from autoscale). It grants
neither routing membership nor write authority. Validation: plan has only `Add`, validated by
`protocol.ValidatePlan` against the dependency view. An intent is dropped on every replica when all
its vnodes are activated or retired (`fulfilled`), keeping intents from growing quadratically.

### 2.5 Placement chain (MOVE)

One-line: a vnode keeps its ID and cell while its physical holder changes; the chain of holders
has one successor per predecessor.

```
PlacementRecord { VNode, Operation, Previous Digest, From, To Holder, Dependencies, Proof []Token }
origin(h) = Hash("placement-origin", h)    // tip of a chain before any move
addPlacement(m): require m.From==current tip holder, m.Previous==tip digest
                 (another record with the same Previous ⇒ ErrConflict: two successors)
                 require grants of m.Proof all name m.To and cover Cell(view, m.VNode)
```

Driver `Service.MoveTo` (`service.go`) + `Store.BeginCausalMove/PublishCausalMove`
(`storage/causal_data.go`):

```
MoveTo(target):  BeginCausalMove(target)            // persists Moving; refused if a cold fold or handoff is pending
                 for each installed leaf token of self: handoff(token, whole grant region → target)
                 PublishCausalMove()                 // all transfers installed; proof = their output-0 tokens
                 exchange with target
```

Rule: **MOVE-1** (ownership unchanged), **MOVE-2** (grants move before the unique placement
successor is published; staging alone never makes a second disk writable).

### 2.6 Retirement (logical removal, used only by the cold fold)

```
RetirementRecord { VNode, From Holder, Op Dot, Dependencies, Proof []Token }
retirementReady(r):
  view := dependency view;  require view.ID(r.VNode.Name) == r.VNode.ID
  require current placement of r.VNode == r.From          (else pending)
  require Proof = outputs of certificates issued by r.From, none back to r.VNode,
          covering Cell(view, r.VNode)
  require no terminal grant names r.VNode                  (else pending)
  require no zone (incl. open zone transfers) resolves to r.VNode   (else pending)
```

Retired IDs stay reserved (`view.ReserveRetired`) and cannot be reused; old activation replay
cannot resurrect a vnode. The root cannot retire.

---

## 3. The authority graph and the write-permission predicate [impl]

### 3.1 Authority (`internal/causal/authority.go`)

```
Authority { Genesis{Cluster, Holder}, Certificates map[Digest]Certificate,
            ZoneTransfers map[Digest]ZoneTransfer,
            next map[Token]Digest  (consumed token → its unique successor), closed map[op]bool, byZone, ... }
Certificate { Cluster, Operation, Previous Token, From Holder, Outputs []Grant, Barrier uint64, DataDigest }
```

```
Add(c):
  require c.Cluster == genesis cluster, c.Operation ≠ "", Outputs nonempty
  if Successor(c.Previous) exists: equal digest ⇒ no-op, else ErrConflict      // AUTH-2
  parent := Grant(c.Previous)  (unknown ⇒ ErrDependency)
  require parent.Holder == c.From
  require every output ⊆ parent.Region, outputs pairwise disjoint,
          union of outputs == parent.Region (no gap)                          // AUTH-1
  store c; next[c.Previous] := digest(c); closed[c.Operation] := true
```

```
holderOf(zone):                       // durable authority for forwarding
  leaves := Leaves(Point(zone.ID)); require exactly one
  grant := Grant(leaf)
  if an open (op not closed) ZoneTransfer for this exact zone has From == grant.Holder:
       return transfer.To
  return grant.Holder
```

`Leaves(region)` walks from genesis through `next`, returning terminal tokens meeting `region`.
`holderIndex` (`holder_index.go`) caches the leaves per authority pointer (motivation in the comment:
125 000 zones made an idle inventory count cost about 10 % of a core).

Rule: for every key, including absent keys, certificates form one chain (**AUTH-1**); a token has
at most one successor (**AUTH-2**).

### 3.2 The only write-permission predicate (`internal/storage/permission.go`)

```
writableIn(snapshot, z):                         // evaluated inside the commit transaction
  require self vnode ∈ snapshot.view             else ErrNotReady
  require placement(self).Storage == this disk   else ErrNotOwner
  (holder, token) := replica.HolderOfZone(z)
  require holder == (this vnode, this disk)      else ErrNotOwner
  if outgoingFrozen(state, z): ErrFrozen          // any outgoing transfer fencing z
  if Grant(token).Holder == holder:
       require token ∈ state.Installed            else ErrNotReady
       return ok
  // zone transfer overrides an unconsumed leaf grant:
  if a ZoneTransfer(z, From=grant.Holder, To=holder) has its zone Installed in Transfers[op]: ok
  return ErrNotReady
```

`outgoingFrozen(z)` (`storage/handoff.go`): some outgoing transfer of this disk has zone z
`Frozen && !Transferred`, or the transfer is region-frozen, not emitted, covers z, and z not yet
transferred.

Rule (**AUTH-3**): ACK requires an installed unconsumed grant (or installed zone transfer), an open
fence, active membership, and matching placement. The check runs twice: a read-only preflight
(`ApplyRecordContext` via `peek`) and again inside the group-commit transaction (`applyWrite`).

**AUTH-4**: emitted certificates and fences survive restart; no timeout or newer view reopens a
consumed token.

---

## 4. Knowledge versions and gossip [impl]

### 4.1 Knowledge frame and version (`internal/mesh/knowledge_wire.go`)

```
frame := { version = SHA-256(json(Knowledge{Root, Genesis, Delta = DeltaSince(∅)})), knowledge }
```

The bundle is the **full** proof closure (all certificates, all non-compacted zone transfers, all
activations, retirements, placements, open intents). It is rebuilt only when
`RoutingSnapshot.FactsDigest()` changes; reading the cached frame takes no rebuild lock
(**KNOW-FAST**). Each node remembers up to `knowledgeReceiptLimit = 512` bundle versions it has
verified and merged, and up to `knowledgePeerLimit = 4096` per-peer "acknowledged version" cursors.
Losing a cursor only means resending the full bundle.

### 4.2 Piggybacked exchange (every mesh RPC, not only gossip)

```
exchangeKnowledge(host, r):                     // sender side
  f := knowledgeFrame()
  r.KnowledgeVersion := f.version; r.KnownKnowledge := f.version
  full := (peer cursor[host] ≠ f.version)
  for attempt in 0..1:
     r.Knowledge := full ? f.knowledge : nil
     out := transport.Exchange(host, r)
     if out.NeedKnowledge and not full: full := true; continue    // receiver did not know the version
     verify out.Knowledge hashes to out.KnowledgeVersion, then Merge it
     if out.AcceptedKnowledge == f.version: cursor[host] := f.version
     return out

Handle(r):                                      // receiver side, before any action
  acceptKnowledge: version known ⇒ skip; body present ⇒ check hash, Merge, remember;
                   version only and unknown ⇒ ErrDependency + NeedKnowledge
  ...perform r.Kind...
  defer: out.AcceptedKnowledge := accepted
         if r.Kind=="write" and r.Hops==0 and applied by self: return without knowledge   // KNOW-LAZY
         out.Knowledge := (own version == r.KnownKnowledge) ? ∅ : own full bundle
         out.KnowledgeVersion := own version
```

A merge that fails with `ErrWrongCluster` (different root or genesis) is refused. Knowledge is
returned even with a refusal, so a misrouted request teaches its sender.

Rule: knowledge is a hint over immutable facts; it grants no right. **KNOW-LAZY** (a write applied
on the first hop returns no knowledge; motivation in invariants.md: returning it on every ACK cut
acknowledged writes to about 16 per second in scaling benchmarks).

### 4.3 Partner choice: Kademlia buckets (`internal/mesh/gossip.go`)

```
GossipPeers(self, members, former, round):
  buckets[cpl] := members grouped by CommonPrefixLen(self.ID, m.ID)   // 97 possible buckets (0..96)
  salt := first 8 bytes of self.ID
  for each non-empty bucket i: sort by ID; pick bucket[(round + salt + i) mod |bucket|]
  pick one "former" host: former sorted, former[(round + salt) mod |former|]
  return distinct hosts

GossipTargets(round):
  for each terminal grant: holder active in view ⇒ member; else ⇒ former
  former += genesis host + every certificate donor host (if not current)
  return GossipPeers(...)
```

Rule **GOS-1**: in every round, for every target t, the partner contacted in t's bucket is t or
shares a strictly longer prefix with t. Hence a fact crosses the network in at most `depth`
rounds of successful exchanges, `depth = 1 + longest common prefix of two vnode IDs`. Push-pull,
so both directions. Each member of a bucket is contacted within `|bucket|` rounds (rotation).
Liveness/cost claim only, not safety.

Measured (docs/protocol/gossip.md, test `TestGOS1_BucketGossipCrossesNetworkWithinTrieDepth`):

| Shape | Vnodes | Depth bound | Worst rounds | Messages/round | All-to-all |
|---|---|---|---|---|---|
| random | 64 | 14 | 3 | 406 | 4,032 |
| random | 1,024 | 21 | 4 | 10,589 | 1,047,552 |
| spike | 64 | 41 | 2 | 775 | 4,032 |
| spike | 1,024 | 52 | 3 | 23,578 | 1,047,552 |

### 4.4 Rounds (`indexus/mesh_runtime.go: meshMaintainContext`, `indexus/worker.go`)

```
every Delay() (jobInterval = 10 s in internal/app/node/main.go; 2 s for a spawned node not yet client-ready):
  ctx timeout 30 s
  peers := GossipTargets(gossipRound += 1)
  Sync(peers)          // one "exchange" RPC per peer, sequential loop
  Resume()             // finish persisted handoffs, cold drains, moves
  Rebalance()          // pull any part of my current cell held by someone else
  refresh view; summary Fold
```

What is exchanged in a round: one `Request{Kind:"exchange"}` with the knowledge bundle (full if
the peer's cursor differs, else version only), and the peer's bundle back (full if versions
differ). No data moves by gossip. [doc-only, gossip.md "Not done yet"]: sending a difference
`V → W` instead of the full bundle.

### 4.5 The address book, a separate layer (`indexus/membership.go`)

Not to be confused with the topology replica. It is liveness and contact discovery only
("Registration and discovery are address books, not activation", ownership.md).

```
Observe() (every Delay):
  ping every registered contact: failure ⇒ quarantine 90 s, remove, re-acknowledge as probe
  ping every acknowledged contact: answer ⇒ register
  if nothing known: acknowledge bootstraps
  discover(): ask bits.Len(|known|) random known peers for one Random() contact each ⇒ acknowledge
Neighbors(origin): up to k = gossipBucketWidth = 20 contacts per bucket around origin's ID
routing table: 1 contact per bucket (routingNeighbors)
```

Three tries: `acknowledged` (leads), `registered` (answered for themselves), `routing`. Current
grant holders from the causal view are injected into `registered` by `meshApplyView`.

---

## 5. Write path [impl]

### 5.1 Entry, relay, one hop

Client → any node: `POST` handled by `p2p.Handler.writeItem` (requires client scope `write` when
`RequireAuth`) → `Node.New/Delete` → `meshWrite` → `MeshData` → `mesh.Service.Handle`.

```
meshWrite(item):
  validate key; refuse if node memory full (ErrNodeFull) or autoscale blocks client writes
  requestID := item.RequestID or 16 random bytes in hex
  MeshData({Kind:"write", RequestID, Record, KnownKnowledge: own version})   // timeout 30 s

Handle(write r):
  if r.Hops ≥ MaxWriteHops (64): ErrNotReady
  if CAP-2 rate cap set and exhausted: ErrWriteOverload
  err := Store.ApplyRecordContext(r.RequestID, r.Record)
  if err ∈ {ErrNotOwner, ErrFrozen, ErrNotReady}:
      holder := routing.HolderOfZone(zone(r.Record))      // durable authority as known locally
      if holder == self: return err                       // nobody else to ask: refuse
      r.Hops++; return call(holder.Host, r)               // relay, with piggybacked knowledge
  if ok: out.AppliedBy := self
```

The entry node never pre-routes by the XOR view (comment in `MeshData` and handoff.md): during a
handoff the view already names the receiver while authority is still on the donor, and view
pre-routing bounced writes up to 64 hops. The relay follows **authority** (`HolderOfZone`), not
`Route`. In the steady state the number of network hops is 0 (entry is the holder) or 1.
Rule **FWD-2** / ROUTE-1: forwarding follows authority successors; the hop bound terminates, it
does not guarantee availability.

### 5.2 Redirect

Writes are not redirected; they are relayed server-side. Bulk ingest answers HTTP 421
(Misdirected) on `ErrNotOwner`/`ErrFrozen` (`p2p/bulk.go`). Reads can answer a redirect (section 6).
A write response may carry headers `X-Indexus-Ingress-*` naming the registered contact XOR-closest
to the client's `X-Indexus-Routing-Key` (`RoutingHint`, `p2p/reads.go`) so a sticky client can
migrate its ingress.

### 5.3 Write token

There is no per-write token. "Write authority" is the installed terminal token of section 3 (or
an installed zone transfer), checked in the transaction. Client tokens (section 9) are admission
credentials only and never grant ownership (`auth/doc.go`).

### 5.4 What an ACK means

HTTP 201 means: the current authority's disk committed, in one synchronized group-commit
transaction (batch up to 256 writes, 2 ms window, `internal/app/node/mesh.go`), the record, the
zone sequence `seq+1`, the history entry (for later handoff mirror), the request receipt twice (in
the zone, so it travels with a handoff, and in the node-wide ledger) and the usage counters, after
re-checking `causalWritable` inside that transaction (`storage/apply.go: applyWrite`).
One disk, one copy: there is no replication (failure-model.md: "Permanent loss of current
holder's disk: no automatic takeover or reconstruction of its only copy").
Errors map to: 400 invalid key/too many metrics, 409 `ErrConflict`, otherwise 503 with
`Retry-After: 1` (`p2p.go: writeItem`).

### 5.5 Retries and request IDs

```
replayReceipt(w):                                   // storage/receipts.go, inside the transaction
  old := ledger[w.RequestID]
  if none: apply as new
  if old.Digest ≠ SHA-256(record bytes) or zone differs: refuse ErrConflict
  else return Mutation{RequestID, old.Seq}          // same result, no second effect
```

Rule **MUT-2** (replay idempotent), HND-2 (an ACKed write survives a handoff, receipts included).
The current store keeps every receipt ("today's store keeps every receipt and states no window");
**RETRY-1** with a 262 144-write / 24 h window is zonelog-specific design text (see disagreements).
Caveat for the paper: if the client omits `request_id`, the node generates a fresh random one per
call, so a client-level retry without an ID is not deduplicated.
Transport-level retries: mesh requests are marked idempotent (`Idempotency-Key` header slot set to
nil in `meshhttp.request`), and the QUIC client retries a failed HTTP/3 request once over TCP; both
rely on RequestID/Operation idempotence.

`mesh.Writer` (`internal/mesh/writer.go`) is a client-side writer that caches a replica, routes by
`Route` (XOR view + placement), tries 3 times, refreshes from seeds on transport failure.
**[test-only]**: its only caller is `internal/mesh/service_test.go`.

---

## 6. Read routing [impl]

```
GetSetContext(collection, location, deep, refresh):        // indexus/read.go, 8 read slots
  holder := routing.Route(zone.ID)                         // XOR view + placement (a hint)
  local := holder is this vnode on this disk
  if not deep and not local: return redirect contact       // client follows it
  if local and not refresh: answer from in-memory derived summary
  else: inventory := QueryPrefixMetrics(collection, location); aggregate records

queryLimited(request):                                      // mesh/query.go
  for attempt in 0..7:
     before := routing snapshot
     holders := before.QueryHolders(PrefixRegion(zone))     // terminal grants ∩ region + open zone-transfer receivers
     out := page through each holder, fan-out 4; one failure discards the attempt
     if ErrReadChanged: continue
     if before.AuthorityDigest == after.AuthorityDigest: return out
  return ErrReadChanged
```

The holder side answers an inventory page only if `request.Target == self` and its shards are
current and not frozen (READ-1: "Missing/frozen shards are errors"). Pages carry a watermark; a
changed watermark or non-advancing cursor yields `ErrReadChanged`. Rule **PREFIX-1**: a prefix read
asks only holders of the prefix's XOR subtree.

Read policies (`indexus/read_policy.go`): `fresh` retries `ErrFrozen/ErrNotReady/ErrNotOwner/
ErrDependency` with backoff `min(5 ms·2^min(attempt,5), 100 ms)` within 30 s; `cached` serves a
result younger than `max_age` from a cache of 32 entries / 16 MiB; `stale-if-error` falls back to
the cache. No mode is a linearizable multi-host snapshot. Reads never touch write authority.

---

## 7. Handoff end to end [impl]

### 7.1 Actors and identity

Donor = holder of an installed terminal token whose region meets the receiver's cell. Receiver =
joining vnode (Join), or any vnode whose cell grew (Rebalance), or a new physical host (MoveTo),
or a fold survivor (Compact). Operation id `handoff:<Hash(token, target, part)>` is deterministic,
so every retry joins the same durable operation.

### 7.2 Receiver side: Join (`mesh/service.go: Join`)

```
Join():
  resumeIncoming()                                       // re-ask donors of unfinished incoming transfers
  repeat ≤ 256:
    if self retired: ErrNotOwner
    next := view (+ self via ValidatePlan(ReasonRegionalAdd) if not active)
    cell := Cell(next, self)
    coverage := my installed grants ∪ my installed zones
    if coverage covers cell: publishActivation (if needed); return
    if not active and Reaches(cell, coverage): publishActivation    // route now, keep acquiring
    pending := for each leaf token in Leaves(cell) not held by me:
                 handoff request {Token, Region = grant ∩ cell, Target = me}
    for warm in [true, false]:                           // warm every donor first, then complete all
       in parallel for each request: call donor; while ErrHandoffPending: sleep 1 s, call again
       after each completed (non-warm) donor: publishActivation
```

### 7.3 Donor side (`Handle "handoff"` → `handoffAsync` → `handoffLocked`)

```
Handle(handoff r):
  if r.Operation is new and not a MOVE: require r.Region ⊆ Cell(view + r.TargetVNode, target)
  handoffAsync: one background job per operation (key + "#warm" for warm), job timeout 30 min;
                wait ≤ 20 s, else ErrHandoffPending (wire: not-ready, caller retries)

handoffLocked(r):
  if not warm and another unfinished outgoing transfer consumes the same token: finish it, ErrConflict
  offer := CaptureCausal(op, token, target, region)      // durable intent, source still writable
     // checks: token installed + held by this disk + no successor yet + no other op on token,
     //         region ⊆ grant; outputs = [region → target] + (grant − region) → self
  if not offer.Frozen:                                   // warm convergence, ≤ 4 rounds
     loop: copyAndMirror(offer, known)                   // preload pages ≤ 2000 rows (whole zones),
                                                         // mirror batches ≤ 512 zones
           pending := Σ over zones (unknown zone: 1, else seq − receiver progress)
           converged if pending == 0
                     or (round>0 and pending ≤ lastPending and pending ≤ zones/2)
                     or (round>0 and pending ≤ 256)
     if not converged: ErrRhoDiverged
     if warm: return                                     // receiver has a copy; donor still writable
  transferZones(op)                                      // per-zone wave, below
  FreezeRegion(op)                                       // whole region fenced; no new zone at donor
  transferZones(op)                                      // stragglers created meanwhile
  copyAndMirror(frozen offer)
  call target "stage"   (StageCausal)                    // receiver checks DataDigest, validates cert, stages
  c := EmitCausal(op)                                    // IRREVERSIBLE: token consumed on donor disk
  call target "install" (InstallCausal c)                // receiver mounts stragglers + installs output 0
  CompleteCausal(op)                                     // donor records install; async CollectTransferred
```

Per-zone wave (`transferZones`, leaves first):

```
levels := BuildDAG(moves of untransferred zones).FreezeLevels()   // children before parents (ZONE-2)
for level in levels, chunk of ≤ 64 zones (freezeBatchZones):
   FreezeZones(op, chunk)        // donor: fence each zone + store final snapshot, one transaction
   copyAndMirror(chunk snapshots)
   call target "stage-zone"      // receiver stages and certifies the seal of each zone
   zts := EmitZoneTransfers(op, chunk)   // donor: IRREVERSIBLE, adds ZoneTransfer{Seq=F, DataDigest} to Delta
   call target "install-zone" zts        // receiver: InstallZones (checks zone, Seq, digest == certified seal)
                                         //           then publishActivation
```

### 7.4 Zero-writer window and "never two writers"

Writable state of one zone z during a handoff:

| Phase | Donor `causalWritable(z)` | Receiver `causalWritable(z)` |
|---|---|---|
| Capture, warm copy, mirror | ok (holder=donor, token installed, no fence) | ErrNotOwner/ErrNotReady (HolderOfZone ≠ receiver, or not installed) |
| After `FreezeZones(z)`, before `EmitZoneTransfers(z)` | ErrFrozen | not holder |
| After `EmitZoneTransfers(z)`, before receiver `InstallZones(z)` | ErrNotOwner (donor's own replica: HolderOfZone(z) = To) | ErrNotReady (zone not installed) |
| After `InstallZones(z)` | ErrNotOwner | ok (if active and placed) |
| After `EmitCausal` / `InstallCausal` | residual tokens only; z's grant consumed | token index 0 installed |

So the zero-writer window of z is the interval `FreezeZones(z) → InstallZones(z)` for its chunk
(at most 64 zones share it): one donor transaction, one mirror call, one stage-zone call, one emit
transaction, one install-zone call. It does not include the copy. Sibling zones stay writable.

Why never two writers (argument from code):
1. The receiver becomes writable for z only through `InstallZones` with the exact emitted
   `ZoneTransfer` (or `InstallCausal` with the emitted certificate). Emission happens on the donor's
   disk before the transfer leaves the donor (`EmitZoneTransfers`, `EmitCausal`: "The disk consumes
   the parent before the certificate leaves the sender").
2. Once emitted, the donor's own replica resolves `HolderOfZone(z)` to `To`, and before emission
   the zone is fenced by `Frozen`. Both are checked inside the donor's commit transaction.
3. A token has one successor (`Authority.Add`, `transferOutputs` refuses a second operation on the
   same token), and a zone flips once per operation (`AddZoneTransfer` refuses a second flip of one
   zone in one operation). Restart keeps all of this (AUTH-4).

Invariants: **ZONE-1** (after `ZoneTransfer(z)` only the receiver may ACK z), **ZONE-2** (parent
flips after its MigrationSet children), **HND-4** (freeze partitions the log at F: mutations ≤ F
reach the receiver, > F are not ACKed by the donor), **MUT-1**, **MIG-1** (region certificate and
residual GC only after every zone transferred), **GC-1**, **REC-1**, **HND-1**, **HND-2**,
**HANDOFF-STREAM**, **MIR-1**.

### 7.5 Recovery and reconciliation

`Resume()` (each tick): cold drain first; incoming transfers; for each outgoing transfer, either
`CollectTransferred` (installed) or replay the exact persisted operation (never replanned);
pending MOVE. `Rebalance()` (each tick): for every leaf meeting my current cell not held by me,
request a handoff (non-warm) from its holder; this corrects concurrent ADDs (ADD-1 / PLAN-CRDT-1).

---

## 8. Cold reconfiguration: the pair fold (COLD-2) [impl, on by default]

One-line: an idle vnode folds into one survivor whose post-removal cell contains the source's
whole cell, through ordinary handoffs, then publishes a retirement.

```
Compact(config):                       // mesh/cold.go
  refuse for root vnode
  candidates := view − self sorted by ID; survivor := first candidate c with
       (c is root or c.ID < self.ID) and Cell(view − self, c) ⊇ my cell
  op := "cold:" + Hash(16-byte nonce, self, survivor, view digest, activity)
  BeginColdDrain(op, survivor, limits)  // seals my intake (no new acquisitions, no MOVE)
  pin := call survivor "cold-pin"       // survivor admits if its bytes + mine ≤ 45 % of its capacity
  for each piece (native token): if hot or topology drifted and piece not started: abort (release pin)
                                 handoff(piece → survivor)
  call survivor "cold-check"            // pin still held; heat ignored once all pieces installed
  record := PublishColdRetirement()     // RetirementRecord with outgoing proofs
  call survivor "cold-witness"          // survivor persists retirement + witness
  CompleteColdRetirement()              // source keeps serving as a forwarding endpoint
```

Constants: `DefaultColdCombinedFraction = 0.45`, `DefaultColdHeatBudget = 1024` writes; per
cold-reconfiguration.md: cool rate 10 writes/s for 2 min, interval 5 s, timeout 90 s.
Balloons, the general ADD/MOVE/packing executor and skeleton W1: **[doc-only]** (kernel code
removed 2026-11-13).

---

## 9. Certificates and client tokens (`internal/auth/cert.go`) [impl, optional]

Do not confuse with section 3's authority certificates. These are admission credentials, signed
by a network issuer, independent of membership and authority.

```
NodeCert    { NetworkID, NodeID, PubKey (ed25519, base64), IP, Port, IssuedAt, ExpiresAt, Signature }
ClientToken { NetworkID, ClientID, Scopes []string, IssuedAt, ExpiresAt, Signature }
Signature = Ed25519(issuer private key, JSON of all other fields)
Verify: NetworkID matches, now ≤ ExpiresAt, signature valid (VerifyPeerCert also requires IP ≠ "")
HasScope(s): s ∈ Scopes or "*" ∈ Scopes
```

Issuer (`cmd/issuer`, `internal/adapter/issuer/server.go`): `GET /v1/network/pubkey`,
`POST /v1/issue/node` (assigns a random name, or one near `prefer_near`, signs the cert; node TTL
30 days), `POST /v1/issue/token` (default scopes `["read"]`, TTL 24 h), `GET /v1/cert`.
Node start (`internal/app/node/main.go`): load or create the node Ed25519 key, obtain the cert,
verify it, require `cert.NodeID == node name` and `cert.PubKey == node public key`; fetch a service
token with scopes `read, write` for peer forwarding.
Use on the wire:
- Mesh RPC (`/cluster/mesh`): when `RequireAuth`, header `X-Indexus-Node-Cert` (base64 JSON
  NodeCert) verified by `VerifyPeerCert` (`internal/app/node/mesh.go`).
- Client API: `Authorization: Bearer <base64url JSON ClientToken>`, scope `write` for writes,
  `read` for reads (`p2p.go: requireClientScope`); `Ping` accepts a node cert or a read token.

Observations for the paper (from code, not from docs): the node private key is not used to sign
mesh requests (no `ed25519.Sign` outside `internal/auth`); the node cert is presented as a bearer
credential, so its confidentiality relies on TLS. The issuer endpoints shown perform no caller
authentication. The vnode ID is the decoded vnode name (`indexus/settings.go: DecodeVnodeID`), not a
hash of the public key; the binding name↔key is the issuer's signature.

---

## 10. Replication [delivery 1 and 2 exist as isolated packages; nothing wired]

`grep` shows no non-test importer of `internal/replication`. The running system has one copy per
zone (section 5.4).

### 10.1 Target design (`docs/design/replication.md`, dated 16 Nov 2026) [doc-only]

- Placement group: one primary and two replicas covering several zones and their empty space, one
  shared log with per-zone positions; XOR geometry unchanged; replica placement distinct from the
  logical owner.
- Raft-like consensus (preferably a proven library) for elections and configuration changes.
- Three states: persisted, committed (majority), applied. The client ACK follows commit + local
  apply. Current `ApplyRecordContext` makes state visible after a local commit, so the design
  requires a separate proposal log.
- Authority must be bound to the replicated group and its configuration, and its elected
  representative; "neither HolderOfZone nor the current gossip suffices".
- Handoff becomes: add destination as non-voter, catch up, commit fence F, check destination state
  through F, commit transfer + install, promote with joint majorities.
- Fresh reads need a ReadIndex-like confirmation.
- Six deliveries, 11–18 engineer-weeks.

### 10.2 Invariants REP-1..REP-7 (invariants.md "Réplication (proposé)")

| Name | Statement |
|---|---|
| REP-1 | Majority ACK: every mutation success rests on a committed entry durable on ≥ 2 members of the competent configuration. |
| REP-2 | Prefix kept: every committed entry is in every future primary's log; no two committed entries at one index. |
| REP-3 | Exclusive epoch: only the elected authority commits; an old epoch cannot open a fence or create a competing successor. |
| REP-4 | Exact application: data, receipts and applied index advance atomically; no uncommitted proposal is exposed. |
| REP-5 | Safe promotion: promotion keeps the committed prefix; reconfiguration keeps majority safety. |
| REP-6 | Replicated transfer: fence, barrier, data commit and authority succession survive loss of the primary. |
| REP-7 | Distinct copies: three voters on three machines; an empty replacement rejoins as a new incarnation. |

### 10.3 Delivery 1: bounded executable model (`internal/replication/model/model.go`) [test-only]

State: 4 nodes on 4 disks; voters `{0,1,2}` then `{1,2,3}` after promoting learner 3; persisted
`Term, Vote, Log, Applied, State`; queue ≤ 64 messages with loss, duplication, reorder, partitions,
crash/restart. Commands `Write, Barrier(fence), Transfer, Install, Promote, Noop(seal)`.

```
Commit(leader):                                    // atomic "fresh certificate" abstraction
  live := voters that are up, in leader's term, reachable both ways, holding leader's log as prefix
  require quorum(voters, live) and last entry has the leader's term
  if the new suffix has Promote: require learner 3 holds the log and quorum({1,2,3}, live);
                                 then voters := {1,2,3}; ConfigTerm := term; all leaders step down
  Committed := leader.Log
quorum(set, votes) = |votes ∩ set| > |set|/2
```

Oracle `Check()` after every event: REP-1/2/3/5/6, REP-4 symbolically, REP-7 structural
assumption only. Exploration: seeds 0–3999 × 320 events = 1 280 000 events; three injected faults
(`LocalACK`, `UncheckedElection`, `EarlyPromotion`) are caught with 1-minimal traces of 5, 16 and
30 events (README, validation 16 Nov 2026). Excluded: real messages for commit, leases, ReadIndex,
snapshots, several groups, XOR topology, Byzantine, liveness.

### 10.4 Delivery 2: proposal journal (`internal/replication/journal/journal.go`) [test-only]

Fixed primary = member 0, `Members = 3`, fixed term 1, no election.

```
Propose(c): if not serving: ErrNotPrimary
            if receipt[c.RequestID] exists: same digest ⇒ return it; else ErrRequestMismatch
            if c already in unapplied log or pending: same digest ⇒ wait; else ErrRequestMismatch
            pending += c
Persist():  append pending to disk log with (Term, Index)          // group commit
Append(to): entries after match[to]
HandleAppend(req) (replica): refuse older term, gaps, PrevTerm mismatch, altered digest,
            any rewrite at index ≤ local Commit; persist; reply Match = last index
HandleReply(rep) (primary): newer term ⇒ stale (stop committing, REP-3);
            match[from] := rep.Match; Commit := median(match) = sorted[(3−1)/2]   // 2 of 3 (REP-1)
Apply():    apply committed entries in order; a RequestID with a receipt advances only Applied (REP-4)
Get():      reads applied state only
```

Tested by `journal_test.go` (cut boundaries, majority required, stale term, altered entry, committed
prefix never rewritten, apply exactly once, request mismatch) and `explore_test.go` (seeds 0–999 ×
300 events, checked with the model's oracle). Missing in delivery 2 by its own description: election
and failover (delivery 3), the "commit only current-term entries" rule, snapshots, reconfiguration,
integration with `internal/storage` and the authority graph, bulk path, ReadIndex.

---

## 11. Transport (brief) [impl]

- One RPC: `POST /cluster/mesh` with JSON `{Request}` → `{Response, Failure}`; body ≤ 32 MiB;
  errors carried as codes (`not-owner`, `frozen`, `not-ready`, `handoff-pending`, `dependency`,
  `causal-conflict`, ...) (`internal/adapter/meshhttp/http.go`).
- Connection reuse: one process-wide `http.Client` (timeout 30 s) over a pooled TCP transport
  (`ForceAttemptHTTP2`, `MaxIdleConnsPerHost = MaxConnsPerHost = 128`, idle 50 s, dial 2 s).
- Default node binary: HTTPS over TCP only. The `quic/` module (`quic/meshquic`, `quic/cmd/node`)
  installs hooks into `internal/adapter/transport`: servers answer HTTP/3 over UDP on the same port
  (`gateway/http3server`, `MaxStreams = 4096` concurrent streams per connection, idle 1 min,
  keep-alive 20 s); the client calls `https` peers over HTTP/3 (TLS 1.3, handshake idle 2 s,
  max idle 1 min, keep-alive 20 s) and, on failure, retries the same request over TCP and keeps
  that peer on TCP for `tcpFallbackFor = 5 min`. Rules **NET-1**, **NET-2**. No authority depends
  on the transport.

---

## 12. Implemented vs documented only

| Item | Status |
|---|---|
| Topology replica, activations, intents, retirements, placements | [impl] |
| Certificate graph, zone transfers, permission predicate | [impl] |
| Per-zone bottom-up handoff, region certificate, async GC | [impl] |
| Knowledge piggyback, version cache, KNOW-LAZY, KNOW-FAST | [impl] |
| Kademlia-bucket gossip partners (GOS-1) | [impl] |
| Delta-encoded knowledge (`V → W`) | [doc-only] (gossip.md "Not done yet") |
| Proof/fence garbage collection | [doc-only], "not implemented" (causal-topology.md) |
| Pair fold (COLD-2), retirement | [impl] |
| Balloon planner, general ADD/MOVE/packing, skeleton W1, SoftLeave | [doc-only] / removed |
| MOVE of a host | [impl] (CLI `node move`) |
| Node certs and client tokens | [impl], enforced only when `RequireAuth` |
| Replication model (delivery 1), journal (delivery 2) | [test-only], not wired |
| Elections, failover, replicated authority, ReadIndex (deliveries 3–6) | [doc-only] |
| Automatic takeover after loss of a holder's disk | none, by design (failure-model.md) |
| `mesh.Writer` client router | [test-only] |

## 13. Docs/code disagreements (code wins)

1. **MIR-1 freeze threshold.** invariants.md: freeze when backlog ≤ 256 "or one twentieth of the
   region's zones". Code (`mesh/service.go`): `freezeBacklogDivisor = 2`, i.e. not growing and
   ≤ half the region's zones; or ≤ `freezeBacklogFloor = 256` after the first round; at most 4 rounds.
2. **Storage engine.** failure-model.md, consistency.md, read-modes.md speak of Bolt commits and
   "Bolt stores"; HND-2 and RETRY-1 call zonelog "not wired". Code (`internal/app/node/mesh.go`):
   "only zonelog is left"; replication.md says the same. So RETRY-1's receipt window may or may not
   now apply; the store code read here (`receipts.go`) keeps a ledger entry per RequestID and shows no
   window. Flag to verify in C2.
3. **Activation timing comments.** Comment in `Join` ("activation waits for the complete cell") and
   in `storage.CompleteCausal` ("the receiver's activation waits for every donor to complete") are
   older than the code: activation is published at the first installed grant or zone (ACT-1;
   `install-zone` handler calls `publishActivation`).
4. **ownership.md** says a client writer "sends its frontier with every request". Code
   (`writer.go`) sends `KnownKnowledge`, a digest of a full bundle, not a frontier.
5. **distributed-runtime.md** says `NewSettings` takes "name, port, job delay and delegation
   threshold". Code: `NewSettings(name, port, delay)`; there is no delegation threshold.
6. **HND-1** still names `PREPARED`/`CUTOVER_READY` phases, removed 2026-11-13 (the doc says so);
   handoff.md still uses those words.
7. The issuer's `RandomNameNear(target, 20)` comment says "Keep ~16 bits"; the argument is 20.
   Minor.

## 14. Comparison with the 2024 protocol paper

| 2024 paper | Code today |
|---|---|
| Node address "encoded from the cryptographic public key". | Vnode ID = decoded vnode name, chosen by the issuer (random, near a hot vnode, or `JoinHint` halving one of the largest cells); key↔name bound by an issuer signature. |
| Kademlia routing table, N buckets of k contacts. | Kept in two forms: address book (`Neighbors` k = 20, routing table k = 1) and causal gossip (one partner per non-empty bucket, rotating, GOS-1). |
| Delegation of a set to a node when its child count ≥ D. | No count threshold. Every zone has an XOR owner over the certified active set; load is handled by splitting (HotTrie, regional ADD) and folding (COLD-2). Authority follows certified grants, not counts. |
| Eventual consistency of the data is acceptable. | Only routing knowledge is eventual. Each zone has exactly one writer, checked in the commit transaction; ACKs survive handoffs. |
| "Conflict resolution (already implemented)" after partitions. | Conflicts are refused, not resolved (`ErrConflict` on equivocation). A partitioned zone stays writable only on the side holding its disk; handoffs wait. |
| Synchronization of counts concurrently with routing. | Summaries are derived caches pushed as versioned absolute contributions (AGG-1; C4 scope). |
| Replication "not yet implemented": full copy of a node. | Still not in production. Design: per placement group, primary + 2, majority commit; model and journal exist as tests. |
| Caching: answer an unknown set with a closer contact, optionally cache. | Shallow reads return a redirect; bounded read cache (32 entries, 16 MiB) with explicit modes. |

Content to keep from 2024 (per SERIES2.md): one binary tree for nodes, collections and records;
delegation as a motivating picture; the Kademlia bucket figure (`routing.png`) is still valid for
GOS-1 and the address book.

---

## 15. Things a newcomer must understand, in order

1. A zone is `(collection, location)`; its ID is a 96-bit point; the XOR owner over a view is a
   pure function (`Owner = argmin XOR`).
2. A holder is a vnode on one disk incarnation; a new empty disk is a new holder.
3. The view is derived from a grow-only set of certified facts that every node merges; it is a
   prediction of where to send, nothing more.
4. Write authority is a separate object: a chain of certificates from genesis, each consuming one
   token and partitioning its region; at any time each key has one terminal token.
5. A token is writable only once installed on its holder's disk, and only while no outgoing fence
   covers the zone; the check runs inside the write transaction.
6. Knowing a certificate (by gossip) never installs it. Learning is free; acquiring requires a
   handoff whose donor consumes its token first.
7. A handoff copies warm, then flips authority zone by zone, children first, each flip being
   freeze → stage → emit → install; a zone has no writer only during its own flip.
8. Activation happens after the first installed piece; the rest of the cell is acquired while
   the vnode already routes; misrouted writes are relayed along authority.
9. Every mesh RPC carries the sender's knowledge version and, if needed, the full bundle; gossip
   is just an empty RPC to one partner per Kademlia bucket every 10 s.
10. ACK = one durable local commit with a receipt; retries with the same RequestID are idempotent.
11. There is no replication: losing the only disk of a holder loses its zones' availability; the
    replication design and its two isolated deliveries are the next step.
12. Node certificates and client tokens control admission only.

---

## 16. Candidate "Calculations"

### C1. Gossip rounds to converge vs N

Bound (GOS-1): rounds ≤ depth = 1 + max over pairs of CommonPrefixLen. For N random 96-bit IDs,
`P(max CPL ≥ d) ≤ C(N,2)·2^−d`, so depth ≈ 2·log2 N + O(1).

```
N = 1024: C(N,2) ≈ 5.2e5 ≈ 2^19  ⇒ depth ≈ 20–21   (measured bound 21; worst observed 4 rounds)
N = 64:   C(N,2) = 2016 ≈ 2^11   ⇒ depth ≈ 12–14   (measured bound 14; worst observed 3)
partners per node per round ≈ (non-empty buckets) + 1 former ≈ log2 N + 1
messages per round ≈ N·(log2 N + 1): N=1024 ⇒ 11 264 (measured 10 589) vs N(N−1) = 1 047 552
wall time ≤ depth × 10 s (jobInterval): N=1024 ⇒ ≤ 210 s bound; observed ≈ 4 × 10 = 40 s
```

Bytes (shows the open problem): full bundle ≈ 1.15 KB per vnode (gossip.md). At N = 1024 a bundle
is ≈ 1.2 MB; a node whose partners lag sends ≈ (log2 N + 1) × 1.2 MB ≈ 13 MB per round.

### C2. Probability that a committed write survives (current vs replicated design)

Let p = probability a given disk is lost before repair, independent.

```
today (one copy):                    P(loss) = p
REP-1 worst case (ACK on 2 of 3):    P(loss) = p²                 (only the two acking copies hold it)
after the third copy catches up:     P(loss) = P(≥2 of 3) = 3p² − 2p³
p = 0.01: 1e−2  vs  1e−4  vs  2.98e−4
write availability (need 2 of 3 up, each up with prob q): 3q² − 2q³; q = 0.99 ⇒ 0.999702
```

Writes can continue with one replica down; a 1-vs-2 partition leaves only the pair writable (REP-3).

### C3. Hops per write

Entry node chosen uniformly among N vnodes with equal cells; entry knowledge current:

```
P(entry is holder) = 1/N  ⇒ network hops = 0 with prob 1/N, 1 otherwise
E[hops] = 1 − 1/N     (N = 64 ⇒ 0.984)
```

With stale knowledge each relay piggybacks fresher knowledge back; every extra hop follows one
authority successor; bounded by `MaxWriteHops = 64`. During a zone's flip the write is refused
(503, `Retry-After: 1`) for the zero-writer window: donor `FreezeZones` transaction, optional
mirror RPC, `stage-zone` RPC, donor `EmitZoneTransfers` transaction, `install-zone` RPC and the
receiver's `InstallZones` transaction, shared by a chunk of ≤ 64 zones. (Whether the SDK routes
writes to the XOR owner itself was not checked here; that belongs to C4 / sdk.)
