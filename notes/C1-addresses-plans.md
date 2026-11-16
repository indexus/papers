# C1 — Addresses and plans: technical note for the paper writer

Scope: `core/internal/tree` (layer 1, address algebra), `core/internal/protocol`
(plans and move order), client side `sdk/src/tree` (Spaces, dimensions, masks,
offsets, cells, locations). Compared with the 2024 paper
`papers2/original/client-algorithm/indexus-search-algorithm-paper.tex`.

All statements below were read from the code (Go `main`, SDK), 2026-11-16.
Where docs and code disagree, the code is stated and the disagreement is listed
in §12. "Wired" means called by the running node (outside tests); "kernel only"
means the function exists and is tested but nothing in the runtime calls it.

Package rule (tree/doc.go): `tree` uses the standard library only, no I/O, no
other internal package. "Plans, capacity and authority build on this package,
never the reverse." `protocol` (doc.go): "No HTTP. No filesystem. No EC2. No
peer.Contact. No global cluster oracle." Invariants named by the packages:
tree: ID-1, OWN-1, TOPO-1. protocol: PLAN-1, HOT-1, HOT-2, REG-1, HND-3, ACT-2,
ZONE-2, AUTO-1, AUTO-2. Normative text: `core/docs/protocol/invariants.md`.

---

## 1. The 96-bit ID

**Definition.** An ID is a 96-bit point of the XOR space `{0,1}^96`. It is *not*
a hash of an item (comment on `type ID`).

**Data structure.** `type ID [12]byte` (tree/id.go). Bit 0 is the MSB of byte 0
(`Bit`, `SetBit`). `Zero` is the all-zero ID.

**Constants.**
- `Size = 12` bytes = 96 bits.
- `Width = Size*8/6 = 16` characters of BASE64: the length of every *name*
  (vnode name, collection name) and of the deepest location.
- `Buckets = Size*8 = 96` (k-buckets of the peer trie, §6).

**Rules (ID-1).**
- `CheckName(s)`: exactly 16 characters of the alphabet (vnode or collection name).
- `CheckLocation(s)`: the root `@`, or 1..16 characters of the alphabet.
- The SDK mirrors both (`checkName`, `checkLocation`, `WIDTH = 16`,
  `KEY_BYTES = 12`, `BITS_PER_CHAR = 6`) in `sdk/src/tree/alphabet.js`.
- A vnode ID is the decoded vnode name (`DecodeName` = BASE64 decode of a
  16-char name, 16×6 = 96 bits exactly). No intermediate hash.
- The zero ID is refused for a vnode (`View.addMember`: "vnode name and id are
  required"; `HotSplitAddress` refuses zero) but is a valid *zone* address
  (ZONE-ID-1).

**Helpers used by plans** (tree/id.go):
- `XORCompare(key,a,b)`: compares `key⊕a` and `key⊕b` byte by byte, big-endian,
  without allocation. `Closer(key,c,i)` = strictly closer.
- `CommonPrefixLen(a,b)` (LCP, 0..96).
- `FirstDiffFrom(a,b,from)`, `SingleDiffBit(a,b)`.
- `Prefix{ID, Bits}`: "closed XOR cell p*", the set of IDs sharing the first
  `Bits` bits; "a control region, not an ownership range". `Contains`.
- `GuardBit`, `HotSplitAddress`, `ForkID` (§10).

## 2. Base alphabets

**Definition.** A `Base` prints and parses bit strings as characters of
`2^k` symbols; the root of every tree is the character `@`.

**Data structure** (tree/codec.go, `type Base`): `rootIdentifier "@"`,
`lengthConfig` (radix), `bitsPerChar = log2(radix)`, `encodeTable =
alphabet[:radix]`, 256-entry `decodeTable`, `idLength = ceil(totalBits /
bitsPerChar)` characters, `idBytes = ceil(totalBits/8)`.

**Constants.**
- Master alphabet: `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_`
  (64 symbols, in this order: digit value = index).
- `BASE64 = NewBase(64, 96)`: 6 bits/char, 16 chars per ID.
- `BASE4  = NewBase(4, 96)`: 2 bits/char, 48 chars per ID, alphabet `0123`
  (the first 4 symbols). Declared, not used by any non-test Go code.
- `-` and `_` are ordinary location characters, never markers (SDK
  `isDirectChild` comment, guarantee "P4").

**Algorithm.**
```
Encode(src, base):            // always idLength chars
  take bitsPerChar bits at a time, MSB first, pad with zero bits at the end
Decode(s):                    // any length
  "@" -> empty; else concatenate bitsPerChar bits per char, right-pad the last byte with 0
Parent(h): "@" -> "" ; len 1 -> "@" ; else h[:len-1]
ChildCandidates(base, p): p+c for each of the radix chars (local targeting only)
IsDirectChild(base, p, c): Parent(c) == p, c != p, c != ""
```
The SDK `encodeFixed`/`decodeFixed`/`parent`/`isDirectChild` are the same
(alphabet.js), "Go Base.Encode".

**Near-name helpers (wired in spawning, not in ownership).**
- `RandomNameNear(target, keepBits)`: random ID sharing the first `keepBits`
  bits with target. Called with 64 bits by the node config
  (`internal/app/node/config.go`, `preferNearBits = 64`) and 20 bits by the
  issuer (`internal/adapter/issuer/server.go`).
- `PreferNearTargets(hot, n)`: `n` clamped to 1..3; keeps `keepBits = 14` bits of
  the hot key and writes the slot index in the next 2 bits. Used by
  `internal/autoscale` and the provisioner.
- SCALE-1 (docs) and `internal/autoscale`: `scaleUpLandingBits = 64`,
  `scaleUpPatience = 3 min`.

## 3. Zone keys: how a zone's ID is built

**Definition.** A zone is `(collection, location)`; its ID is
`id(z) = bits(location) || suffix(collection)` (ID-1).

**Data structures** (tree/id.go):
- `Key{Collection, Location}`: the zone's *identity* ("the unit every phase
  agrees on — what a node owns, transfers, snapshots and delegates").
- `ZoneKey{Collection, Location, ID}`: identity plus XOR address.
  `ZoneKey.Key()` normalizes `""` to `@`.

**Algorithm** (`ZoneKeyID` → `MergeEncodings(BASE64, BASE64, location, collection)`):
```
ZoneKeyID(col, loc):
  if loc == "" then loc := "@"
  CheckName(col); CheckLocation(loc)
  L  := 0 if loc == "@" else 6*len(loc)          // location bits
  lb := Decode(loc); cb := Decode(col)           // cb is 12 bytes
  i  := L div 8 ; r := L mod 8                   // r in {0,6,4,2}
  if r == 0: return lb[:i] || cb[i:]
  else:      return lb[:i] || combine(lb[i], cb[i], r) || cb[i+1:]
combine(x, y, r) = (top r bits of x) || (top 8-r bits of y)   // y >> r
```
SDK `zoneKeyID`/`mergeZoneKey`/`combineBytes` are byte-for-byte the same and
are checked against shared fixtures (`sdk/src/tree/zonekey_fixtures.test.mjs`,
`testdata/zonekey_fixtures.json`).

**Rules.**
- The first `6·len(loc)` bits of `id(z)` are exactly the location's bits, so a
  zone's ID shares its location prefix with every descendant (PREFIX-1;
  `TestID1_ChildSharesParentPrefix`).
- ZONE-ID-1: identity is `(collection, canonical path)`. The ID is a routing
  address only; a parent and a descendant may have identical IDs. All moves,
  DAG nodes, barriers and proofs are keyed by `tree.Key`, not by ID.
- `Covers(parent, child)` / `IsAncestorOf`: same collection, different path, and
  the parent path is `@` or a strict string prefix of the child path.

**Codec gap (open, code wins).** When `L mod 8 ≠ 0` (location lengths not a
multiple of 4), the partial byte carries the collection's bits
`[8i, 8i+8−r)` (its *high* bits) instead of the documented suffix bits
`[8i+r, 8i+8)`. At most 6 bits of one byte differ from the formula; location bits
and every later collection byte are exact. Docs (`invariants.md` ID-1,
`component-boundaries.md`) record this as an open ID-1 implementation gap, not
fixed because persisted addresses would remap; a versioned address schema is
required. Worked evidence (computed with the SDK, collection `0AABCDEFGH123456`):

| location | id(z) (hex)               | equals documented formula? |
|----------|---------------------------|----------------------------|
| `@`      | 00a28b30d38f4110420c4146  | yes (= collection bits)    |
| `0`      | 00a28b30d38f4110420c4146  | yes (coincidence of bits)  |
| `0A`     | 00aa8b30d38f4110420c4146  | no                         |
| `0AA`    | 00a2a230d38f4110420c4146  | no                         |
| `0AAB`   | 00a28b30d38f4110420c4146  | yes (24 bits, aligned)     |

Note that `@`, `0` and `0AAB` coincide: a location that is a prefix of the
collection's own name has the collection's address (ZONE-ID-1 coincident
addresses). Second example, collection `DvFMV2020idx0001` (bits begin
`001101 111001…`), location `5` (index 5 = `000101`): actual first byte
`00010100`, documented formula would give `00010111`.

## 4. XOR distance and Owner

**Definition.** `owner(z) = argmin_{v ∈ V_active} id(z) ⊕ id(v)` (OWN-1).
The only inputs are the zone ID and the active set; capacity, host, heat,
network and child markers never enter.

Why a total order: IDs of active vnodes are distinct, so for a fixed `z` the map
`v ↦ z⊕v` is injective; the minimum is unique; no tie-breaking is needed.

Key lemma used everywhere (comment on `xor_index.go`, used in `Cell`): for two
vnodes `D ≠ U` with `b = LCP(D,U)`, `z⊕D < z⊕U` iff `z[b] = D[b]`. Bits above
`b` contribute equally, bit `b` decides, all later bits are irrelevant.

## 5. View, Delta and the XOR index

**Definition.** `View` is "the unique source of XOR ownership at a generation".

**Data structure** (tree/topology.go):
- exported: `Generation uint64`, `Active []VNodeDescriptor{ID, Name}`,
  `Digest [32]byte`.
- private: `byName`, `byID`, `retiredIDs map[ID]bool`, `xorIndex []xorNode`
  (immutable, shared by clones until membership changes).
- `Delta{BaseDigest, Add []VNodeDescriptor, Remove []string}`.

**Algorithms.**
```
Digest(gen, Active):  sort Active by (ID bytes, Name)
  SHA-256( gen as 8 bytes big-endian || for each v: ID(12 bytes) || Name || 0x00 )

Apply(old, Δ):                                 // old is never mutated
  if Δ.BaseDigest ≠ 0 and ≠ old.Digest: ErrStaleTopology
  next := clone(old); next.Generation := old.Generation + 1
  remove Δ.Remove by name; add Δ.Add             // refuse duplicate name, duplicate ID,
                                                 // zero ID, empty name, retired ID
  next.Digest := Digest(...); next.xorIndex := build(canonical Active)
Extend(old, adds...) = Apply(old, {old.Digest, adds, ∅})

Owner(z):
  if Active empty: return Zero
  if xorIndex present: return indexedOwner(xorIndex, z)
  best := Active[0]; for v in Active[1:]: if Closer(z, v, best): best := v
```
- `Add`/`Remove` mutate a view in place (no generation bump), recompute the
  digest and drop the index (linear scan afterwards). `NewViewFrom` and
  `Apply` build the index.
- `ReserveRetired(id)`: lifetime namespace exclusion; a retired ID can never be
  re-added (used by HotSplit to skip retired candidates).

**XOR index** (tree/xor_index.go): a compressed binary trie, "2·N−1 nodes, at
most 96 decisions".
```
xorNode{ child [2]int32, id ID, bit uint8 }      // bit = 96 marks a leaf
build(S sorted by ID):
  if |S| = 1: leaf(S[0])
  b := LCP(S[first], S[last])                    // first bit where the set splits
  pivot := first i with S[i][b] = 1
  node(bit=b, child = [build(S[:pivot]), build(S[pivot:])])
indexedOwner(z): at := root; while not leaf: at := child[z[bit]]; return id
```
Built only when `len(Active) ≥ 16` (below 16 the scan is used).
Correctness: at a node with split bit `b`, all IDs below share bits `< b`; every
ID on the side `z[b]` beats every ID on the other side (lemma §4).

**Rules.**
- OWN-1: `Owner` = argmin XOR; reference oracle `internal/testoracle` computes
  each distance without calling `View.Owner`/`XORCompare`
  (`TestOWN1_OwnerMatchesOracleExhaustive8Bit`, `FuzzViewOwner`).
- TOPO-1: equal active sets give equal owners for every zone; `V_active` never
  empty in the runtime (pinned genesis vnode), no duplicate IDs.

**Complexity.**
- Scan: N comparisons of ≤ 12 bytes, no allocation.
- Index: one bit test per level; depth ≤ min(N−1, 96); for random IDs the
  average leaf depth ≈ log2 N + 0.3 (Calculation B). Memory (2N−1) nodes ×
  24 bytes (8 + 12 + 1, padded to 4).
- Build: sort O(N log N) + recursive split O(N · depth).

## 6. Peer registry trie and k-buckets

**Definition.** `Trie[N]` is "the peer registry: a mutable binary trie over
identifier bits, safe for concurrent use" (tree/trie.go). Unlike the View's
index it holds any payload and is not ownership (NODE-TOPO-1: the registry is
only a route).

**Data structure.** Uncompressed binary trie, one level per bit, `sync.RWMutex`,
`trieNode{children [2]*trieNode, node N}`.

**Algorithms.**
```
nearest(value): descend; at each bit take the matching child, else the other
nearestK(value,k): DFS, matching side first -> leaves arrive in XOR order
Extract(value, routing[96]):  along value's path, at depth i, if the sibling
   subtree exists: routing[i] := nearest(sibling)         // one contact per bucket
ExtractK(value, k, routing[96][]): same with up to k nearest contacts
```
Bucket `i` holds contacts that agree with the target on exactly `i` leading
bits (Kademlia buckets). Wired: `indexus/membership.go` calls
`ExtractK(id, gossipBucketWidth = 20, …)` and `Extract(n.ID(), …)` (gossip,
GOS-1, C3 paper).

## 7. Regions (mask, value) and XOR cells

**Definition.** `Region{Mask, Value ID}` is "a cube of the 96-bit key space.
Unmasked bits are unconstrained. Unlike an inventory of existing rows it also
covers future, empty zones" (tree/region.go).

**Operations.**
```
Valid:      Value & ^Mask == 0
Contains z: z & Mask == Value
Intersect(r, o): fail if (r.V ⊕ o.V) & r.M & o.M ≠ 0; else (r.M|o.M, r.V|o.V)
Subtract(r, o): disjoint cubes for r \ o, one residual cube per bit that o
   constrains and r does not (≤ 96 cubes), no key enumeration
CoversRegions(r, pieces): pending := {r}; for p in pieces: pending := ∪ Subtract(q, p)
   return pending = ∅
Point(id) = (FullMask, id)    // per-zone activation proof
PrefixRegion(zone): mask = first min(6·len(loc), 96) bits, value = id(z) & mask
   (root -> empty mask = whole space)                                 (PREFIX-1)
```
**XOR cell** (`Cell(view, name)`):
```
D := id(name)
for every other U in Active:
   b := first bit where D and U differ
   Mask[b] := 1 ; Value[b] := D[b]
return (Mask, Value)
```
Rule: `z ∈ Cell(D)` ⇔ `View.Owner(z) = D` (lemma §4). The cell is a cube, not
necessarily a prefix: its constrained bits are the distinct values of
`LCP(D,U)`; its size is `2^(96 − k_D)` with `k_D = |{LCP(D,U) : U ≠ D}|`.
The prefix subtree `Prefix{D, g(D)}` (g = guard, §10) is always contained in
`Cell(D)` because all constrained bits are `< g(D)`. The cells of a view
partition the key space.

Wired uses: `internal/mesh` (handoff coverage via `CoversRegions`, prefix
reads via `PrefixRegion`), `internal/causal` (placement, retirement,
authority), protocol `checkGuarantee`.

## 8. Join hint (JOIN-1)

`JoinHint(active, rng)` (tree/join_hint.go), wired as the public `/join-hint`
endpoint (`indexus/routing.go`, `internal/adapter/http/p2p`).
```
id := 96 random bits
if active empty: return id
for v in active: depth(v) := 1 + max_{u≠v} LCP(v,u)          // = g(v)
pick v with minimal depth d (ties uniformly at random)
if d ≥ 96: return id
keep v's bits [0, d), flip bit d, keep random bits after d
```
Bit `d` is unconstrained in `Cell(v)`, so the newcomer takes exactly half of
`Cell(v)` and no other vnode loses anything. Comment: "Sequential joins keep
every cell within a factor 2 of every other; random ids leave the largest cell
about ln N times the mean." The hint grants nothing (authority comes from
activation and handoff, C3). Status in `verification.md`: OPERATIONAL.

## 9. Client side: Spaces, dimensions, masks, offsets, cells, locations

Files: `sdk/src/tree/space.js`, `mask.js`, `offset.js`, `collection.js`,
`spherical.js`, `linear.js`, `alphabet.js`, `item.js`, `set.js`, `element.js`.

**Dimension.** A duck-typed object (no base class) giving a distance:
`name, type, ratio, newPoint, pointLength, pointDistance, pointDirection,
newSegment, rootSegment, segmentLength, segmentDistance, segmentDirection,
segmentCenter, segmentExtension, segmentsOverlap, newFilter, filterDistance,
filterDirection`.
- `Spherical(name, [south, north, west, east])`: point `(lat, lon)`,
  `pointLength = 2`, segment `(south, north, west, east)`, distance =
  great-circle in km (`acos` formula × 60 × 1.1515 × 1.609344), direction =
  bearing 0..360°.
- `Linear(name, [start, end])`: scalar point, `pointLength = 1`, distance `|a−b|`.

**Space.** `new Space(dimensions, mask, offset)`:
- `size` = Σ pointLength = number of axes (gps: 2; gps+time: 3).
- `step = BITS_PER_CHAR / size` (= 6/size; gps: 3) — bisections of each axis
  per character; also the number of in-zone levels used by `sdk/src/walk`.
- Root bounds: flat `[min0,max0,min1,max1,…]`, one pair per axis.

**Mask.** `Mask(value[])`, `at(l, n) = value[(l·6 + n) mod len]`: the axis cut
by bit `n` (0..5) of character `l`. A `Collection` builds the identity mask
`[0, 1, …, size−1]`, so axes are cut in round-robin (gps: lat, lon, lat, lon,
lat, lon per character).

**Offset.** `Offset([details])`, `at(l) = details[l mod len]` (0 if empty). A
`Collection`'s offset is its *name* in the alphabet:
`charsToNumbers(name)[i] = alphabet.indexOf(name[i])`, repeated cyclically.

**Cell / location encoding** (`Space._encode`):
```
encode(point, precision):
  if precision = 0: return "@"
  b := root bounds
  for l in 0..precision-1:
     idx := 0
     for n in 0..5:
        a := mask.at(l, n); mid := (b[a].min + b[a].max)/2
        if coord[a] > mid: idx := 2·idx + 1; b[a].min := mid
        else:              idx := 2·idx;     b[a].max := mid
     hash += alphabet[(offset.at(l) + idx) mod 64]
  return hash
decode(hash): idx := (charIndex(hash[l]) − offset.at(l)) mod 64, replay the halvings
xyz(hash): integer cell coordinates per axis and resolution (bits per axis)
bounds(xyz): the cell's segment per axis
```
A point exactly on `mid` goes to the lower half (bit 0). A *location* is the
string `hash`; a *cell* is its bounds. The location is then a zone location:
`zoneKeyID(collection, hash)` is its routing address (§3), so the same
geometric cell of two collections lands at different addresses (different
offset and different collection suffix).

**Worked BASE4 example (the 2024 paper, consistent with the SDK rule).**
The SDK is BASE64-only (hard-coded `% 64` and `l·6+n`); the BASE4 example is the
same rule with 2 bits per character. Alphabet `A B C D` (paper; Go BASE4 uses
`0 1 2 3`), mask `(0,1)` = (lat, lon) cycled, offset `BC` = shifts `[1, 2]`,
ranges lat [−90, 90], lon [−180, 180]. Point lat −60, lon −45:
```
level 0: lat −60 > 0?  no -> 0, lat∈[−90,0];  lon −45 > 0? no -> 0, lon∈[−180,0]
         idx = 00 = 0, char = (shift 1 + 0) mod 4 = 1 -> "B"
level 1: lat −60 > −45? no -> 0, lat∈[−90,−45]; lon −45 > −90? yes -> 1, lon∈[−90,0]
         idx = 01 = 1, char = (shift 2 + 1) mod 4 = 3 -> "D"
location "BD" = bits 0001 ; cell lat [−90,−45] × lon [−90,0]
```
This reproduces the paper's box ("BD = 0001", same cell) and its per-level
tables (first char: A=11, B=00, C=01, D=10; second: A=10, B=11, C=00, D=01).

**Worked BASE64 example (computed with the SDK).** Collection
`DvFMV2020idx0001`, one spherical dimension `gps` [−90,90]×[−180,180];
mask `[0,1]`, offsets `D=13, v=57, F=15, M=22, …`; Paris (48.8566, 2.3522):

| precision | location | lat cell                  | lon cell                   | id(z) hex                |
|-----------|----------|---------------------------|----------------------------|--------------------------|
| 0         | `@`      | [−90, 90]                 | [−180, 180]                | 3793d67c200202c9fb000001 |
| 1         | `5`      | [45, 67.5]                | [0, 45]                    | 1493d67c200202c9fb000001 |
| 2         | `5x`     | [47.8125, 50.625]         | [0, 5.625]                 | 17b9d67c200202c9fb000001 |
| 3         | `5xS`    | [48.515625, 48.8671875]   | [2.109375, 2.8125]         | 17b7357c200202c9fb000001 |
| 4         | `5xS4`   | [48.8232421875, 48.8671875] | [2.28515625, 2.373046875] | 17b7047c200202c9fb000001 |

Level 0 bits: lat>0 →1, lon>0 →1, lat>45 →1, lon>90 →0, lat>67.5 →0, lon>45 →0:
`idx = 111000 = 56`; without offset the char would be `u` (index 56); with the
offset 13: `(13+56) mod 64 = 5` → `5`. At precision 4 the cell is about
4.9 km (lat) × 6.5 km (lon) and each axis has resolution 12 bits.

**Elements.** `Item(collection, hash, metrics, id)` with `count() = 1`;
`Set(collection, hash, count, metrics)`; both extend `Element`, which stores
where a read placed them (segments, distances, directions, overall distance).
`abelian.js`: `(count, metrics)` mass, `abelianEqual` with eps 1e-9 and
`abelianCountEqual` (count-only drift test). Sums are the C4 paper.

## 10. Plans

All planners produce a `TopologyPlan` and never mutate `V_active`.

**TopologyPlan** (protocol/plan.go): `BaseDigest, Region tree.Prefix, Donor,
Add []VNodeDescriptor, Remove []string, Changes []ZoneChange, Reason`.
Reasons (persisted in `JoinIntent.Plan`, retired values not reused):
`ReasonNone=0, ReasonMoveHost=1, ReasonHotSplit=2, ReasonRegionalAdd=3,
ReasonColdBalloon=6`. `ZoneStats{Zone, Items, Bytes, WriteFast, WriteSlow, ETA}`.

### 10.1 Validation (PLAN-1)
```
ValidatePlan(V, plan, zones):
  if plan.BaseDigest ≠ 0 and ≠ V.Digest: ErrStalePlan
  V' := Apply(V, (plan.Add, plan.Remove))
  Changes := { z ∈ zones : V.Owner(z) ≠ V'.Owner(z) }   // planner predictions discarded
  checkGuarantee(plan, V, V')
checkGuarantee:
  HOT_SPLIT:   |Add| = 1; b := SingleDiffBit(Donor, J) must exist;
               b ≥ Guard(V, Donor); J = HotSplitAddress(Donor, b);
               allowed := Cell(V, Donor)
  REGIONAL:    Region.Bits ≤ 96; some existing vnode lies in Region;
               allowed := Prefix(Region)
  other reasons: no geometric check (return ok)
  Remove must be empty
  for each added J: Cell(V', J) ⊆ allowed  else ErrExternalSteal
```
The containment check is on the complete key space (cubes), not on the
inventory: "Existing-row checks would miss future zones". Adding vnodes only
moves keys into the new cells, so `Cell(V',J) ⊆ allowed` for every `J` implies
that every key outside `allowed` keeps its owner.

### 10.2 Hot split (HotTrie, HOT-1, HOT-2)

**Guard.** `g(D) = 1 + max_{U≠D} LCP(D,U)` (`GuardBit`; `Guard(view, donor)`).
With no other vnode `g = 0`. Max LCP 95 gives `g = 96`: no legal fork.

**Address.** `J_b = D ⊕ e_b` (`HotSplitAddress`): exactly bit `b` flipped,
`b ≥ g(D)`, `J ≠ 0`.

**Rule (HOT-1).** If `Owner(z,V') ≠ Owner(z,V)` then `Owner(z,V) = D`: zero
external steals. Among the zones owned by `D`, `J_b` captures exactly those
with `z[b] ≠ D[b]`, i.e. exactly half of `Cell(D)` as address space.
Reason: for `U ≠ D`, `LCP(J,U) = LCP(D,U) < g ≤ b` and `J` agrees with `D`
there, so `J` beats `U` exactly where `D` did; between `J` and `D` bit `b`
decides. HOT-1 quantifies over the supplied view only:
`TestHotSplitGuardCannotCertifyAnOmittedCompetitor` shows a local guard 0
versus actual guard 1 when a peer is missing from the local view.

**Planner** (`PlanHotSplit`, protocol/hottrie.go):
```
owned := zones with V.Owner(z) = D
if some owned z is atomic (bytes > AtomicDisk or WriteFast > AtomicWrite): ErrAtomicOverload
writeNeed := WritePressure ≥ TargetWrite and WritePressure > 0; same for disk, items
if no need: empty plan (no Add)
g := Guard(V, D)
sort owned by relief score desc (writes/s per second-to-ready if write need,
     else items per second-to-ready); tie: larger Location string first
for z in owned:
   b := first bit ≥ g where z and D differ; J := D ⊕ e_b    (skip if none)
   while J is a retired ID: b := next differing bit ≥ b+1; J := D ⊕ e_b
   skip if J already tried
   V' := Extend(V, J)
   remaining pressure := pressure − Σ (zones whose V'-owner ≠ D)
   if any active need still above its target: continue
   if only item need and not (0 < remaining items < total items): continue
   return plan{Add: [J], Reason: HOT_SPLIT}
return ErrSafeSplitInsufficient                                  (HOT-2)
```
Relief estimate (`EstimateRelief`): `ρ = WriteFast / DrainRate` (0 if no drain
rate); `TimeToReady = ETA` if given, else `(bytes+1) ms`, divided by `(1−ρ)`
when `0 < ρ < 1`, and `1 h` when `ρ ≥ 1`. Disk weight = `Bytes`, else `Items`.
HOT-2: no legal fork that meets the targets → error, no spawn, no reservation,
no topology write. At most `96 − g` candidate bits per zone.

### 10.3 Load split

`LoadSplitForkCandidates(self, ownIDs, weights)` (protocol/load_split.go):
```
total := Σ max(w,0); if total < 2: none
for b in 0..95:
   side := 1 − self[b]
   w := Σ max(weight,1) over ownIDs with id[b] = side
   keep if 0 < w < total and (total − w)·5 ≥ total     // donor keeps ≥ 20%
sort by |w − total/2| ascending, then by lower b
```
**Kernel only and untested**: no Go file other than its own references it (no
caller, no test). It does not apply the guard. The node's
`preferNearsForLoadSplit` (indexus/scale_policy.go) does *not* call it; it calls
`EvaluateMachine` (§10.6).

### 10.4 Regional ADD (REG-1)

**Definition.** A region is a prefix cell `R = p*`. REG-1: a zone outside `R`
keeps its owner. Unlike HotSplit, vnodes other than the donor *inside* `R` may
lose keys.

**Planner** (`PlanRegionalAdd`, protocol/regional.go):
```
owned := zones owned by D; atomic check as in 10.2
z := hottest *leaf* among owned (no owned descendant), by relief score;
     if none, the first owned zone; if no owned zone: ErrSafeSplitInsufficient
b := first bit where D and id(z) differ (from bit 0); none -> ErrAtomicOverload
J := ForkID(D, b, z[b], id(z))      // D's bits < b, then z's bits from b on
                                    // since b = LCP(D,z), J = id(z) exactly
V' := Extend(V, J)
if only item need and the split is not useful: ErrSafeSplitInsufficient
C := Cell(V', J)
bits := number of leading bits 0,1,2,… (< b) that C's mask fixes contiguously
plan{Region: Prefix{D, bits}, Add: [J], Reason: REGIONAL_ADD}
```
So the regional vnode is placed exactly at the hot zone's address, and the
region is widened to the smallest prefix (sharing D's first `bits` bits) that
encloses the whole new cell, "including unobserved keys"; sparse views can
require the root region (`bits = 0`). Validation (§10.1) checks that the region
contains at least one existing vnode and that the new cell lies inside it.

### 10.5 Capacity (CAP-1) and MOVE

`ResourceCounters{Owned, Residual, Staging, ReservedIncoming}`;
`PhysicalLoad = Owned + Residual + Staging + ReservedIncoming`; CAP-1:
`P(m) ≤ C` at every step (enforced in the durable store, C2; the kernel
`Machine` ledger was removed 2026-11-13). `Machine{ID, Capacity C, WriteCap H,
…}`: "Capacity is never an XOR-ownership exception: a full machine refuses
work or MOVE/spawns; it does not rewrite owner()". `MachineID` is a host, never
an XOR identity. `BestDiskOffer`: roomiest `AvailableDisk > 0` among offers with
`Residual = 0`.

MOVE (MOVE-1): same vnode ID, same owner, another machine; `V_active` unchanged.
`pickMove`: load = `Usage.Owned` (else disk pressure); needs a best offer on
another machine with `AvailableDisk ≥ load` and, if `WriteCap > 0`, enough
`AvailableWrite`.

### 10.6 Autoscale decision (AUTO-1, AUTO-2)

`EvaluateMachine(MachineState)` (protocol/autoscale.go), wired from
`indexus/scale_policy.go`:
```
disk  := Pressure.Disk   ≥ TargetDisk  (default 0.90 · Capacity)
write := Pressure.Writes ≥ TargetWrite (default 0.70 · WriteCap)
AUTO-2: if DiskGrowth > 0: disk ||= (C − Disk)/DiskGrowth < 2 · ScaleTime   (default 30 s)
        same for writes with WriteCap
items := Σ Items of zones owned by Donor
itemNeed := (ItemLimit > 0 and items ≥ ItemLimit) or Rebalance
none of the three          -> NONE
disk only and pickMove ok  -> MOVE
HotInput: AtomicDisk = Capacity, AtomicWrite = WriteCap,
          TargetItems = max(1, min(items/2, 0.7·ItemLimit)) when itemNeed
PlanHotSplit ok with an Add      -> HOT_SPLIT
ErrAtomicOverload                -> ATOMIC
other error than SafeSplitInsufficient -> NONE (error)
PlanRegionalAdd ok               -> REGIONAL_ADD
ErrAtomicOverload                -> ATOMIC ; else NONE
```
Constants: `DefaultDiskTrigger = 0.90`, `DefaultWriteTrigger = 0.70`,
`exhaustSafety = 2.0`, default scale time 30 s; `RateEWMA` with default
`α = 0.2` (if α ∉ (0,1)), first observation initializes.
Runtime path (scale_policy.go): `ValidatePlan` on the same detached view;
rejects if the durable view's digest changed; `BuildActivationComponents`;
durable reservation of the plan (`reserveScalePlan`) before any spawn;
`Rebalance = reason ≠ "" and reason ≠ "items"`.

**Wired vs kernel only (code facts).** The node's `planningState` fills
`Capacity, Usage, View, Donor, Zones, Pressure.Disk (= PhysicalLoad),
Pressure.Writes (Σ WriteFast, only if WriteCap > 0), WriteCap, WriteLoad,
ItemLimit, Rebalance`. It never sets `Offers`, `DrainRate`, `DiskGrowth`,
`WriteGrowth`, `ScaleTime`, `TargetDisk`, `TargetWrite`. Hence at runtime:
MOVE is never selected by `EvaluateMachine` (no offers; MOVE exists as the
explicit `-moveFrom` startup), the time-to-exhaustion rule and `RateEWMA` act
only in tests, and `ρ = 0`. No non-test code references `RateEWMA`,
`DrainRate`, `DiskGrowth`, `WriteGrowth`.
Process-level triggers (memory, CPU, disk free, queue) live in
`internal/autoscale` (defaults e.g. `MemLimitPct 40`, `CPULimitPct 70`,
`DiskMinFreePct 35`, `Cooldown 15 s`, `Window 1 min`), outside C1.

## 11. The order of zone moves

### 11.1 Move and handoff DAG (ZONE-2)

`Move{Zone ZoneKey, Donor, Receiver string}` (protocol/handoff.go): one zone
transfer; it does not change `V_active`. `ErrRhoDiverged` = mirror rate `ρ ≥ 1`:
abandon without owner change.

```
BuildDAG(moves):                                  // keyed by tree.Key, not by ID
  node per move
  for each node n: walk loc := Parent(loc) up to "@" (Parent("@") = "")
     first ancestor (same collection) that is also a move -> parent(n)
FreezeLevels():                                   // bottom-up waves
  remaining := all
  repeat: wave := { n ∈ remaining : no child of n in remaining }
          (if empty: dump all remaining as one wave and stop — defensive)
          sort wave by (collection, location); remove wave; emit wave
```
Rule ZONE-2: a parent zone in a MigrationSet freezes and transfers only after
every descendant also in the set is TRANSFERRED; independent leaves and
branches flip in the same wave. The wave is selected before removal so that a
parent cannot enter the same wave as its child. Cost: `BuildDAG` O(n · depth),
depth ≤ 17 path steps (16 characters + root); at most 17 waves per collection.
Wired: `internal/mesh/service.go` builds one DAG per collection, merges waves by
index, freezes each wave in chunks of `freezeBatchZones = 64`. Copy of all
zones may run in parallel; only the authority flip follows the waves
(DAG-1 / ZONE-2 text in invariants.md). Status: ZONE-2 PARTIAL (small trees).

### 11.2 Activation components (ACT-2)

`BuildActivationComponents(old, neu, zones)`: partitions the added vnodes so
that each group can be activated alone.
```
added := neu.AddedSince(old)
if none: one "residual" component (no Add), reconciled on zones
union-find over added:
  union(i,j) if interferes(Ji,Jj) or interferes(Jj,Ji), where
     interferes(a,b) := ∃ z: o_a(z) ≠ o_old(z), o_a(z) ≠ o_full(z), o_ab(z) = o_full(z)
  repairCoupling: repeat until stable: for each group S, if some z has
     owner_{old+S}(z) ∉ {o_old(z), o_full(z)}, union S with the groups of
     o_full(z) and of owner_{old+S}(z)
component = Apply(old, Add = group), ID = sorted names joined by "+",
            Moves = { z : owner changes } via Reconcile
```
Rule ACT-2: `⋃ Changed(C_i) = Changed(Plan)` and activating `C_i` never applies
a transition that belongs to `C_j`. Independent leaves (J1 vs J3) are separate
components; nested IDs (J1 then J2) share one. Note: interference is computed on
the supplied zone inventory (`zones`), not on the full key space. Cost:
O(A² · Z) owner lookups plus O(A²) `Extend` calls for A added vnodes.
Today HotSplit and Regional plans add exactly one vnode, so the runtime sees a
single component per plan.

## 12. Docs versus code (code wins)

1. **ID-1 codec gap.** `invariants.md` states `ID(z) = bits(location) ||
   bits(collection)` and records an open gap; `verification.md` lists ID-1 as
   PROVED (its tests check width, round trip, root and prefix sharing, not the
   suffix). Code: partial-byte suffix uses the collection's high bits (§3).
2. **HotTrie selection rule.** `scaling.md`: "policy prefers the shallowest
   candidate where both sides retain at least 20% of the donor". Code
   (`PlanHotSplit`): ranks zones by relief per time-to-ready and returns the
   first fork `b = FirstDiffFrom(D, z, g)` that brings every active pressure
   under target; no 20% rule and no shallowest preference. A 20% rule exists
   only in the uncalled `LoadSplitForkCandidates`, and there only for the
   donor's kept share, ordered by closeness to ½, not by depth.
3. **Spec references.** `capacity.go` cites `docs/protocol/04-protocol-spec.md
   C1–C3`; `id.go` cites `docs/protocol/02-id-xor-model.md`. Neither file exists;
   the rule is CAP-1 in `invariants.md`.
4. **JoinHint "largest cells".** Code picks the vnode with the smallest
   `g(v) = 1 + max LCP`, not the largest cell by size (`2^(96−k_v)`, §7). The
   split is an exact half of that vnode's cell either way.
5. **Autoscale MOVE and AUTO-2.** Docs present MOVE first and time to exhaustion
   as decision rules; the code implements both, but the runtime state never
   carries offers or growth rates (§10.6).
6. **SDK** `Space.signature()` calls `mask.signature()`, which `Mask` does not
   define (would throw); no caller exists. SDK `SETS_PRECISION = 32`
   (api/wire.js, cited in offset.js) exceeds the 16-character maximum location
   accepted by `checkLocation`; it is not referenced elsewhere.
   `sdk/src/tree/index.js` cites `docs/layers.md` and alphabet.js cites
   "go-indexus-core protocol.Base": the Base now lives in `internal/tree`.
7. `protocol/tree_aliases.go`: deprecated aliases of tree types kept only for
   `internal/storage` ("Nothing else may use them").
8. HND-3 is listed in protocol/doc.go, but the package only checks one
   geometric owner per view (`TestHND3_SingleWriteLeader`); the single-writer
   rule itself is enforced by durable authority (C3).

## 13. Kept from 2024 / changed

**Kept.**
- One binary tree for node addresses, collection IDs, sets and item locations
  ("materialized by the leaves of the tree") — now literally: vnode IDs and
  zone IDs live in the same 96-bit space and ownership is XOR in that tree.
- Dimension = distance function (+ filter + direction); Space = ranges + mask +
  offset; mask maps bits to dimensions; offset shifts each character to spread
  collections. The encoding rule (bit = upper half, char = (offset + idx) mod
  radix) is unchanged; the paper's BASE4 example still decodes the same way.
- BASE64 with 6 bisections per character as the working base.
- Sets as partitions with counts (Abelian mass); items with ID and coordinates.

**Changed.**
- Fixed widths: 96-bit IDs, names of exactly 16 characters, locations of at
  most 16 characters (paper: unbounded layers).
- Offset: the paper hashes the collection's definition into an identifier used
  as offset; the SDK uses the collection *name's* characters directly, and the
  name is also the collection suffix of every zone ID.
- Mask: paper lets the collection choose the mask to fit data distribution; the
  SDK `Collection` always builds the identity round-robin mask (custom masks
  are possible only by constructing `Mask` directly).
- Placement: paper says sets "live within the closest node" and delegate past a
  threshold; now "closest" is exactly `argmin XOR` over the certified active
  view, and data moves only by validated plans (HotSplit, Regional ADD) and
  ordered handoffs (DAG), never by a node's own threshold decision.
- Alphabet: paper BASE4 uses `ABCD`; code BASE4 uses `0123`.
- New since 2024: XOR cells as cubes, guard bit, donor-only split, regional
  prefix closure, activation components, bottom-up freeze waves, join hint.
- The search algorithm itself (layers, radius, Cap × Batch) is the C4 topic
  (`sdk/src/walk`), not covered here.

## 14. What a newcomer must understand, in order

1. The 96-bit space and its printing: bits, BASE64 (6 bits/char), 16-char
   names, `@` root, parent = drop last char.
2. Space encoding on the client: dimensions, bisection, mask, offset →
   location string → cell (BASE4 example first, then BASE64).
3. Zone = (collection, location); `id(z) = location bits || collection bits`;
   identity is the path, the ID is only an address (coincident addresses; the
   codec gap as a footnote).
4. XOR distance and the one-bit lemma (first differing bit decides).
5. View and Owner: `owner(z) = argmin XOR`, generation, digest, Delta/Apply.
6. The compressed XOR trie: why one bit test per level suffices; cost.
7. Regions (mask, value) and the XOR cell of a vnode as a cube; cells
   partition the space; containment proofs on the full key space.
8. Joining: the join hint halves a cell.
9. Plans are proposals: ValidatePlan recomputes changes (PLAN-1).
10. Guard bit and the donor-only hot split `J = D ⊕ e_b` (HOT-1); when it is
    impossible (HOT-2); atomic zones.
11. Regional ADD: a new vnode at the hot zone's address inside the smallest
    enclosing prefix (REG-1).
12. Capacity is never an ownership exception (CAP-1, MOVE).
13. The decision order (AUTO-1) and time to exhaustion (AUTO-2).
14. Executing a plan: activation components (ACT-2), then bottom-up freeze
    waves of zone moves (ZONE-2).
15. Peer registry trie and k-buckets as routes, not ownership (bridge to C3).

## 15. Candidate "Calculations"

**A. Load imbalance with N random IDs vs join hints.** A vnode's address share
is `|Cell(D)|/2^96 = 2^(−k_D)`, `k_D` = number of distinct `LCP(D,U)`. Mean
share is `1/N` (cells partition the space). Simulation (64-bit IDs, exact cell
sizes, Python, seed 1; 20 trials, 5 for N = 1024):

| N    | max/mean | min/mean | max/min | ln N |
|------|----------|----------|---------|------|
| 16   | 2.60     | 0.356    | 10      | 2.77 |
| 64   | 3.70     | 0.212    | 19      | 4.16 |
| 256  | 3.90     | 0.141    | 30      | 5.55 |
| 1024 | 4.80     | 0.081    | 77      | 6.93 |

With sequential join hints (same simulation of `JoinHint`), N a power of two
gives max/mean = 1.00 (a complete trie); in general cells differ by at most a
factor 2 (JOIN-1). The docs report, on 16 real processes, the busiest node at
1.05× the mean with hints versus 2.05× to 4× with random names. Short code:
```
cell(D) = 2 ** -len({lcp(D,U) for U in ids if U != D})
```

**B. Cost of an Owner lookup.** Linear scan: N comparisons of 12 bytes. Indexed
(N ≥ 16): one bit test per compressed-trie level. Measured average leaf depth
for random IDs: 4.31 (N=16), 6.31 (64), 8.33 (256), 10.34 (1024), i.e.
≈ log2 N + 0.3; maximum depth ≈ 1.4 log2 N (5.7, 8.3, 10.9, 13.8); bound 96.
Memory 24·(2N−1) bytes: about 0.5 MB for N = 10 000. Example: N = 1024 →
≈ 10 bit tests versus 1024 twelve-byte comparisons.

**C. Room for donor-only splits and move waves.** The guard of a random vnode
averages log2 N + 1.3 (5.28, 7.33, 9.30, 11.36 for N = 16…1024), so a donor
has about `96 − g ≈ 85` legal fork bits at N = 1024; each split raises the
donor's and the newcomer's guard to at least `b + 1`, so at most `96 − g`
successive splits of one lineage, fewer if forks are deep (the reason docs warn
against forks near bit 95). Each plan transfers its zones in at most 17
bottom-up waves per collection (root + 16 depths), each frozen in chunks of 64
zones.
