# Data model: Upgrade framework

**Spec**: [spec.md](spec.md)

---

## Project classification

| Class | Rule |
|-------|------|
| Wireup | `[tool.scaffold-ca-python].scaffold_version` present; generated at 1.0.0+ |
| Legacy | Key absent; typically scaffold-ca-python ≤ 0.5.0 output |
| Unknown version | Editable install may report `0.0.0+unknown` for **installed** tool only |

---

## Runtime objects (scaffolder)

### `UpgradeAction` (ABC)

| Attribute / method | Purpose |
|--------------------|---------|
| `name: ClassVar[str]` | Stable action id (e.g. `dependency-injector-to-wireup`) |
| `description: ClassVar[str]` | One-line user-facing summary |
| `applies(builder) -> bool` | Content-based gate |
| `up(builder) -> UpgradeResult` | Apply transforms via `ModuleBuilder` |

### `UpgradeResult`

| Field | Type |
|-------|------|
| `applied` | `list[AppliedItem]` |
| `pending` | `list[PendingItem]` |

### `AppliedItem`

| Field | Type |
|-------|------|
| `kind` | `str` |
| `file` | `str` (repo-relative) |
| `description` | `str | None` |

### `PendingItem`

See [contracts/pending-items.md](contracts/pending-items.md).

### `UpgradeReport`

| Field | Type |
|-------|------|
| `actions` | list of per-action results + metadata |
| `automated` | flattened applied items |
| `pending` | flattened pending items |
| `scaffold_version` | declared / installed / guard flags |

---

## Registry

`UPGRADE_ACTIONS: list[type[UpgradeAction]]` — explicit order. Test: `tests/factory/upgrades/test_registry_order.py` compares filename date tokens.

---

## On-disk markers (DI action)

| Signal | Legacy | After migration |
|--------|--------|-----------------|
| `dependency-injector` in pyproject | yes | no (wireup) |
| `*_container.py` under `application/config` | yes | removed |
| `application/config/wiring.py` | absent | present |
| `scaffold_version` in pyproject | absent | set |

---

## Legacy guard message (028 integration)

`_LEGACY_MIGRATION_HINT` in `commands/_shared.py` MUST reference `scaffold up` (not `migrate-di`). FR-020 in 028 updated to exempt `up`.