# Object Field Reference — Groups, Indicators, Cases, Case Artifacts, Tags, Intel Requirements

Consolidated from the customer-provided TQL parameter tables for these resource types. This is authoritative source material (platform documentation), not empirically-guessed syntax like the rest of this skill's TQL notes — treat these field names as correct, but still confirm against the live instance if a query fails unexpectedly (custom instances can vary).

## Identifier / text-search field per resource type — this is NOT consistent across types

This is the single most error-prone thing about TQL. Confirmed per type:

| Resource type | Text-search field | Notes |
|---|---|---|
| `groups` | `summary` | `name` is **not** valid here (confirmed failure). |
| `indicators` | `summary` | The indicator value itself (IP, hash, URL, etc.). |
| `cases` | `name` | Confirmed working — Cases use `name`, unlike groups. |
| `artifacts` (Case Artifacts) | `summary` | Like indicators/groups, not `name`. |
| `tags` | `name` **or** `summary` | Both valid but different semantics: `name` is case-sensitive exact-match-oriented, `summary` is case-insensitive. Confirmed `name CONTAINS` works. |
| `intelRequirements` | `requirement` | The PIR/IR's text (its `requirementText` field is exposed via `requirement` in TQL — confirmed working live 2026-09-17). |

**Don't assume `summary` universally** — check this table before building a query against a new resource type.

## Groups — full field list

`aiLastRetrievalDate`, `aiProvider`, `associatedGroupSource`, `associatedIndicatorSource`, `attackTag`, `attributeNN` (attribute search — see instance-specific attribute types), `createdBy`, `dateAdded`, `documentDateAdded`/`documentFilename`/`documentFilesize`/`documentStatus`/`documentType` (Document groups), `downvoteCount`/`upvoteCount`, `emailDate`/`emailFrom`/`emailScore`/`emailScoreIncludesBody`/`emailSubject` (Email groups), `eventDate`/`eventType` (Event/Incident groups), `externalDateAdded`/`externalDateExpires`/`externalLastModified`, `firstSeen`/`lastSeen`, `generatedReport` (Report groups), `id`, `insights`, `lastModified`, `owner`/`ownerName`, `publishDate` (Report groups), `securityLabel`, `signatureDateAdded`/`signatureFilename`/`signatureType` (Signature groups), `status`, `summary`, `tag`/`tagOwner`/`tagOwnerName` (deprecated shortcuts — prefer `hasTag()`), `taskAssignee`/`taskAssigneePseudo`/`taskDateAdded`/`taskDueDate`/`taskEscalated`/`taskEscalationDate`/`taskLastModified`/`taskOverdue`/`taskReminded`/`taskReminderDate`/`taskStatus` (Task groups), `type`/`typeName`, `victimAsset` (deprecated shortcut — prefer `hasVictimAsset()`).

**Nested queries on groups:** `hasAllTags()`, `hasArtifact()`, `hasAttribute()`, `hasCase()`, `hasCommonGroup()`, `hasCommonVulnerability()`, `hasGroup()`, `hasIndicator()`, `hasIntelQuery()`, `hasIntelRequirement()` — **confirmed working live**, see below, `hasSecurityLabel()`, `hasTag()`, `hasThreatActorProfile()`, `hasVictim()`, `hasVictimAsset()`.

## Indicators — full field list

Common: `id`, `summary`, `type`/`typeName`, `owner`/`ownerName`, `source`, `dateAdded`, `lastModified`, `firstSeen`/`lastSeen`, `lastObserved`, `active`/`activeLocked`, `confidence`, `rating`, `observationCount`, `falsePositiveCount`/`lastFalsePositive`, `privateFlag`, `securityLabel`, `attackTag`, `sameNameAs`, `externalDateAdded`/`externalDateExpires`/`externalLastModified`, `associatedGroup`/`associatedGroupSource`/`associatedIndicatorSource` (deprecated shortcuts), `tag`/`tagOwner`/`tagOwnerName` (deprecated shortcuts).

Enrichment scores: `threatAssessScore`/`threatAssessLastUpdated`, `calScore`/`calLastChecked`, `abuseIpdbConfidenceScore`, `dtLastUpdated`/`dtMalwareScore`/`dtOverallScore`/`dtPhishingScore`/`dtSpamScore`/`dtStatus` (DomainTools), `vtLastUpdated`/`vtMaliciousCount` (VirusTotal). **These filter correctly via TQL but don't come back in the response by default — request `fields=threatassess` (a bundled field, confirmed working) to get the actual `threatAssessScore`/`calScore`/etc. values back.** See `ioc_scoring_and_topic_queries.md`.

Type-specific fields: `address`(EmailAddress), `ip`/`addressASN`/`addressCIDR`/`addressCity`/`addressCountryCode`/`addressCountryName`/`addressIpVal`/`addressIsIpv6`/`addressRegisteringOrg`/`addressState`/`addressTimezone` (Address), `hostName`/`hostDnsActive`/`hostWhoisActive` (Host — **these are the TQL filter names; the JSON response instead shows `dnsActive`/`whoisActive`, confirmed live** — same name-mismatch pattern as elsewhere in this skill), `fileName`/`filePath`/`fileSize` (File), `text` (URL), `value1`/`value2`/`value3` (multi-field custom indicators). Enrichment fields `geoLocation` (Address/Host), `dnsResolution`/`whoIs` (Host, populated only when `hostDnsActive`/`hostWhoisActive` are true) are requested via `fields=`, not returned by default — see `ioc_batch_lookup.md`.

**Nested queries on indicators:** `hasAllTags()`, `hasArtifact()`, `hasAttribute()`, `hasCase()`, `hasCustomAssociation()`, `hasGroup()`, `hasIndicator()`, `hasIntelRequirement()`, `hasSecurityLabel()`, `hasTag()`, `hasVictim()`, `hasVictimAsset()`.

## Cases — full field list

`assignedToUserOrGroup`, `assigneeName`, `attackTag`, `attribute`, `calScore`, `caseCloseDate`/`caseCloseTime`/`caseCloseUser`, `caseDetectionTime`/`caseDetectionUser`, `caseOccurrenceTime`/`caseOccurrenceUser`, `caseOpenDate`/`caseOpenTime`/`caseOpenUser`, `createdBy`/`createdById`, `dateAdded`, `description`, `detectionDue`/`detectionOverdue`, `id`/`idAsString`, `lastUpdated`, `missingArtifactCount`, `name` (confirmed working), `owner`/`ownerName`, `resolution`, `responseDue`/`responseOverdue`, `severity`, `status`, `tag`, `targetId`/`targetType`, `threatAssessScore`, `timeToDetect`/`timeToRespond`, `typeName`, `xid`.

**Nested queries on cases:** `hasAllTags()`, `hasArtifact()`, `hasCase()`, `hasGroup()`, `hasIndicator()`, `hasNote()`, `hasTag()`, `hasTask()`, `hasWorkflowTemplate()`.

**Useful for triage/investigation-status queries:** `status`, `severity`, `detectionOverdue`/`responseOverdue` (booleans — direct SLA-breach flags), `missingArtifactCount` (incomplete evidence collection), `assigneeName`/`targetType`, `timeToDetect`/`timeToRespond` (seconds). E.g. "what's overdue and needs attention" → `responseOverdue = true OR detectionOverdue = true`.

## Case Artifacts — full field list

`analyticsScore`, `caseId`, `dateAdded`, `id`, `indicatorActive`, `noteId`, `source`, `summary`, `taskId`, `type`/`typeName`.

**Nested queries on artifacts:** `hasCase()`, `hasGroup()`, `hasIndicator()`, `hasNote()`, `hasTask()`.

**Artifact Types** (the type-definition object, separate from Artifact instances): `active`, `dataType`, `description`, `id`, `intelType`, `managed`, `name` (Artifact Types use `name`, not `summary`).

## Tags — full field list

`active` (false for some deprecated ATT&CK tags), `associatedCase`/`associatedGroup`/`associatedIndicator`/`associatedVictim` (deprecated shortcuts), `caseId`, `description`, `financialRisk` (ATT&CK-tag-specific RQ financial-impact rating), `id`, `lastUsed`, `name` (case-sensitive), `normalized`, `owner`/`ownerName`, `securityCoverage` (ATT&CK-tag-specific), `summary` (case-insensitive), `techniqueId` (MITRE technique ID, e.g. `T1566`, for ATT&CK tags — null otherwise).

**Nested queries on tags:** `hasCase()`, `hasGroup()`, `hasIndicator()`, `hasVictim()`.

**Useful:** `techniqueId` lets you query tags by ATT&CK technique directly, e.g. finding the Tag object for T1566, then `hasTag()` from groups/indicators to that tag ID for a TTP-driven search.

## Intelligence Requirements (PIRs/IRs) — full field list

`category`, `dateAdded`, `id`, `lastModified`, `owner`/`ownerName`, `requirement` (the IR's text, maps to `requirementText` — confirmed working), `subtype`, `tag`, `uniqueId` (the human-facing ID like `PIR-1015`).

**Nested queries on intelRequirements:** `hasArtifact()`, `hasCase()`, `hasGroup()`, `hasIndicator()`, `hasTag()`, `hasVictim()`, `hasVictimAsset()`.

## Intelligence Requirement Results — special, v3-API/dashboard only

This object type is **not browsable/searchable the normal way** — per platform docs, it's only queryable via dashboard Query cards or the v3 API directly (not the Legacy Browse screen, not generic object-type search). It is **not in the MCP `tc_resources` list** either (confirmed).

Fields: `archivedDate`, `dateAdded`, `id`, `intelId` (the ID of the matched object), `intelReqId` (the PIR/IR's ID — **only valid here**, confirmed NOT valid as a `groups`/`indicators` TQL field), `intelType` (e.g. Address, Host, Adversary, Campaign), `isArchived`, `isAssociated`, `isDeleted`, `isFalsePositive`, `isLocal`, `lastMatchedDate`, `owner`/`ownerName`, `score` (relevancy weighting — UI-only, not visible elsewhere), `summary`.

**This carries triage/workflow metadata that plain group/indicator queries don't have** — `isFalsePositive`, `isArchived`, `score`, `lastMatchedDate`. It also carries the platform's *actual* PIR match set — the nested query `hasIntelRequirement(id=X)` on `groups`/`indicators` looks like a shortcut to this, but only returns objects an analyst has manually associated to the PIR (rare in practice, per the customer), so it badly under-reports real matches. See `association_traversal.md` for the corrected approach: prefer direct API access to this object when available, and a keyword-replication approximation over MCP-only.
