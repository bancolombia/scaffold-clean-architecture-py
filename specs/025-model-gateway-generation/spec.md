# Feature Specification: Model Gateway Generation

**Feature Branch**: `feature/model-gateway-generation`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Modify the domain model generation command (`scaffold gm --name <name>` / `scaffold generate-model --name <name>`) so that, in addition to the model, it also generates the model's gateway (repository contract) inside a dedicated per-model package in the domain layer."

## Clarifications

### Session 2026-10-26

- Q: What exact branch name should be created for this feature? → A: `feature/model-gateway-generation`, created from `main` before implementation starts (Constitution Principle VII).
- Q: What should the generated gateway contain? → A: Nothing. The model name comes from the CLI parameter and the CLI cannot know the project's domain, so the gateway is an empty abstract class with no methods. It does not import the model; developers add the operations (and the model import) themselves.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a model together with its gateway (Priority: P1)

A developer working in a generated Clean Architecture project runs `scaffold gm --name paper`. Instead of a single flat model file, the command creates a dedicated `paper` package under `domain/model/` that contains the `Paper` model and a `gateways` sub-package with the `PaperRepository` gateway contract. The developer immediately has the domain-side port that use cases depend on and that driven adapters will later implement, without writing any boilerplate.

Resulting structure inside the generated project:

```text
src/<package>/domain/
└── model/
    └── paper/
        ├── __init__.py
        ├── paper.py
        └── gateways/
            ├── __init__.py
            └── paper_repository.py
```

**Why this priority**: This is the core value of the feature. Every domain model in Clean Architecture needs a gateway contract. Generating both together removes repetitive manual work and enforces a consistent location for gateways across all generated projects.

**Independent Test**: In a freshly scaffolded project, run `scaffold gm --name paper` and verify that the package structure above exists, that the model class `Paper` and the gateway contract `PaperRepository` are present, and that the project's test suite passes.

**Acceptance Scenarios**:

1. **Given** a valid Clean Architecture project with no `paper` model, **When** the developer runs `scaffold gm --name paper`, **Then** the files `domain/model/paper/__init__.py`, `domain/model/paper/paper.py`, `domain/model/paper/gateways/__init__.py`, and `domain/model/paper/gateways/paper_repository.py` are created, and the command exits with code 0.
2. **Given** the command above has run, **When** the developer opens `paper.py`, **Then** it contains the `Paper` domain model with the same content the command generates today.
3. **Given** the command above has run, **When** the developer opens `paper_repository.py`, **Then** it defines an empty abstract gateway contract named `PaperRepository`. The contract declares no methods, has no imports from the model, infrastructure, or application code, and is ready for the developer to add domain-specific operations.
4. **Given** the command above has run, **When** the developer looks under the tests root, **Then** `src/tests/domain/model/paper/test_paper.py` and `src/tests/domain/model/paper/gateways/test_paper_repository.py` exist. The model test imports the model from its new location, and the gateway test verifies that the gateway is an abstract base class.
5. **Given** the command above has run, **When** the developer runs the project's lint, format, and test checks, **Then** all of them pass without manual edits.
6. **Given** the command above has run, **When** the developer runs `scaffold vs`, **Then** no layer violations are reported for the generated model or gateway.
7. **Given** a valid project, **When** the developer runs `scaffold generate-model --name paper` (the long form), **Then** the result is identical to running `scaffold gm --name paper`.

---

### User Story 2 - Multi-word model names produce consistent names (Priority: P1)

A developer generates a model with a multi-word snake_case name, such as `research_paper`. Folder, file, model class, and gateway class names all follow the same naming convention.

**Why this priority**: Multi-word names are common in real domains. Inconsistent naming between the folder, the file, and the classes would break imports and erode trust in the generator.

**Independent Test**: Run `scaffold gm --name research_paper` and verify the folder, file, and class names listed below.

**Acceptance Scenarios**:

1. **Given** a valid project, **When** the developer runs `scaffold gm --name research_paper`, **Then** `domain/model/research_paper/research_paper.py` contains the class `ResearchPaper`, and `domain/model/research_paper/gateways/research_paper_repository.py` contains the gateway contract `ResearchPaperRepository`.
2. **Given** the command above has run, **Then** the mirrored tests exist at `src/tests/domain/model/research_paper/test_research_paper.py` and `src/tests/domain/model/research_paper/gateways/test_research_paper_repository.py`.

---

### User Story 3 - Preview generation with dry-run (Priority: P2)

Before generating anything, a developer runs `scaffold gm --name paper --dry-run` to see exactly which files would be created, including the gateway and its test.

**Why this priority**: The constitution requires dry-run on every command. Developers rely on it to confirm the new, larger set of generated files before writing to disk.

**Independent Test**: Run the command with `--dry-run` and verify that the output lists every file from User Story 1 (sources and tests) and that nothing is written to disk.

**Acceptance Scenarios**:

1. **Given** a valid project, **When** the developer runs `scaffold gm --name paper --dry-run`, **Then** the output lists the model, both package marker files, the gateway, and both test stubs, and no file or folder is created.
2. **Given** a valid project, **When** the developer runs the same command without `--dry-run`, **Then** the files created match exactly the files listed by the dry-run.

---

### User Story 4 - Prevent overwriting existing models (Priority: P2)

A developer accidentally runs `scaffold gm --name paper` for a model that already exists, either in the new package layout or as a flat file created by an earlier version of the tool. The command refuses to continue, explains why, and leaves the project untouched.

**Why this priority**: Overwriting a hand-edited model or gateway would destroy work. Detecting both layouts protects projects created before this feature.

**Independent Test**: Create a `paper` model, run the command again, and verify the exit code, the message, and that no files changed. Repeat with a legacy flat `domain/model/paper.py` file in place.

**Acceptance Scenarios**:

1. **Given** the folder `domain/model/paper/` already exists, **When** the developer runs `scaffold gm --name paper`, **Then** the command exits with code 1, prints a clear message with a resolution hint, and writes no files.
2. **Given** a legacy flat file `domain/model/paper.py` exists, **When** the developer runs `scaffold gm --name paper`, **Then** the command exits with code 1, prints a clear message with a resolution hint, and writes no files.
3. **Given** the tests folder `src/tests/domain/model/paper/` exists but `domain/model/paper/` does not, **When** the developer runs `scaffold gm --name paper`, **Then** the command exits with code 1, prints a clear message with a resolution hint, and writes no files.

---

### User Story 5 - Delete a model generated with the new layout (Priority: P3)

A developer removes a model with the delete-module command. The command finds and removes the whole model package, including its gateway, and the mirrored tests folder. Models generated as flat files by earlier versions can still be deleted.

**Why this priority**: Without this, the delete-module command would silently miss models created with the new layout. It is lower priority because deletion is used less often than generation.

**Independent Test**: Generate `paper` with the new layout, run the delete-module command for `paper`, and verify that `domain/model/paper/` and `src/tests/domain/model/paper/` no longer exist. Repeat with a legacy flat model.

**Acceptance Scenarios**:

1. **Given** a `paper` model generated with the new layout, **When** the developer runs the delete-module command for `paper`, **Then** the folders `domain/model/paper/` and `src/tests/domain/model/paper/` are removed.
2. **Given** a legacy flat model `domain/model/paper.py` with its test `src/tests/domain/model/test_paper.py`, **When** the developer runs the delete-module command for `paper`, **Then** both files are removed, as they are today.
3. **Given** a `paper` model generated with the new layout, **When** the developer runs the delete-module command for `paper` with `--dry-run`, **Then** the output lists the model package and its tests folder, and nothing is removed.

---

### Edge Cases

- **Invalid names**: names that are not valid snake_case module names, such as `Paper`, `my-paper`, or `1paper`, exit with code 1 and the existing validation message. Nothing is written.
- **Outside a project**: running the command outside a Clean Architecture project root exits with code 1 and the existing message.
- **No arguments**: running `scaffold gm` with no arguments shows help and exits with code 0.
- **Partial leftovers**: if the tests folder `src/tests/domain/model/<name>/` already exists, even when the source package does not, the command treats it as a conflict: it exits with code 1 and a resolution hint, and writes nothing.
- **Name collides with a gateway file name**: names ending in `_repository`, such as `paper_repository`, are accepted. They produce `paper_repository/gateways/paper_repository_repository.py`. No special handling is required.
- **Other model packages**: generating `paper` never modifies files that belong to other models, such as `research_paper`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generate-model command (`gm` / `generate-model`) MUST create a per-model package folder `domain/model/<name>/` containing a package marker file and the model module `<name>.py`.
- **FR-002**: The model module content MUST be unchanged from the current generated model: a Pydantic v2 domain model class named in PascalCase after `<name>`.
- **FR-003**: The command MUST create a `gateways` sub-package at `domain/model/<name>/gateways/` containing a package marker file and the gateway module `<name>_repository.py`.
- **FR-004**: The gateway module MUST define an empty abstract contract named `<ClassName>Repository` (for example, `PaperRepository`) that declares no methods and contains no implementation.
- **FR-005**: The gateway module MUST NOT import the model or anything from the infrastructure or application layers.
- **FR-006**: The command MUST create a model test stub at `src/tests/domain/model/<name>/test_<name>.py` that imports the model from its new location.
- **FR-007**: The command MUST create a gateway test stub at `src/tests/domain/model/<name>/gateways/test_<name>_repository.py` that verifies the gateway is an abstract base class.
- **FR-008**: The command MUST derive folder, file, and class names consistently from the snake_case name, including multi-word names.
- **FR-009**: The command MUST keep its current name validation, project-root detection, and no-argument help behavior, including exit codes and messages.
- **FR-010**: `--dry-run` MUST list every file the command would create, including the gateway, the package marker files, and both test stubs, and MUST write nothing.
- **FR-011**: The success message MUST report the model class name and the total number of files created.
- **FR-012**: The command MUST exit with code 1, with a clear message and a resolution hint, if `domain/model/<name>/`, a legacy flat file `domain/model/<name>.py`, or the tests folder `src/tests/domain/model/<name>/` already exists. In that case it MUST write no files or folders (all-or-nothing).
- **FR-013**: The delete-module command and module lookup MUST recognize a model generated with the new layout and remove the whole `domain/model/<name>/` package and its mirrored tests folder `src/tests/domain/model/<name>/`.
- **FR-014**: The delete-module command and module lookup MUST continue to recognize and remove legacy flat models (`domain/model/<name>.py` and `src/tests/domain/model/test_<name>.py`).
- **FR-015**: All generated files MUST come from versioned templates, and every new or changed template MUST have rendering tests (Constitution Principle II).
- **FR-016**: Code generated by the command MUST pass the generated project's lint, format, type-check, and test checks without manual edits.
- **FR-017**: The command's help text and the project README MUST describe the new generated structure, including the gateway.

### Key Entities

- **Domain Model**: The business entity, a pure data class, generated in `domain/model/<name>/<name>.py`. Its name is the PascalCase form of `<name>`.
- **Gateway (Repository Contract)**: An abstract port in `domain/model/<name>/gateways/<name>_repository.py`, named `<ClassName>Repository`. It belongs to the domain layer and is generated empty. Developers add the operations their domain needs, and driven adapters in the infrastructure layer later implement it.
- **Model Package**: The folder `domain/model/<name>/` that groups a Domain Model with its gateways. It is the unit that is created by generation and removed by deletion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One invocation of the generate-model command produces 6 source and test artifacts (model, gateway, 2 package markers, 2 test stubs) in the structure described in User Story 1.
- **SC-002**: In 100% of freshly scaffolded projects, the generated project's test suite, lint, format, and type-check checks pass immediately after generating a model, with no manual edits.
- **SC-003**: The structure validation command reports 0 violations for any model and gateway produced by the command.
- **SC-004**: The files listed by `--dry-run` match the files actually created in 100% of runs.
- **SC-005**: Re-running the command for an existing model, in either layout, never modifies or deletes an existing file. It is verified for both the new and the legacy layout.
- **SC-006**: Deleting a model generated with the new layout leaves no leftover model, gateway, or test files for that model.
- **SC-007**: The CLI's own test suite covers gateway generation, dry-run output, conflict detection for both layouts, multi-word names, and deletion of both layouts, and stays at or above the 80% coverage gate.

## Assumptions

- The gateway contract is created empty, with no predefined operations such as `save` or `find_by_id`, because the CLI cannot know the project's domain. Developers add the operations their domain needs.
- The gateway contract is expressed as an abstract base class that driven adapters will subclass. Because it has no abstract methods yet, it can technically be instantiated until the developer adds the first one. The generated test therefore checks that it is an abstract base class, not that instantiation fails.
- The gateway is always generated. No flag to skip or rename it is provided.
- Package marker files are generated for both the model package and the `gateways` sub-package so that the new import path resolves consistently with the rest of the generated project.
- The existing structure validation already classifies everything under `domain/model/` as the domain model layer, including nested folders. Gateways therefore fall under the same dependency rules as models without new validation rules.
- Use-case and driven-adapter generation are not changed by this feature. Wiring a gateway into a use case or adapter remains a manual step.
- All work for this feature MUST happen on the branch `feature/model-gateway-generation`, created from `main` before any implementation change, following the `feature/<kebab-case-name>` convention of Constitution Principle VII. The plan MUST include creating this branch as its first step.

### Out of Scope

- Generating concrete driven-adapter implementations of the gateway.
- CLI flags to skip, rename, or customize the gateway.
- Migrating existing flat models in user projects to the new package layout.
