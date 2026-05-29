# ADG20 Corrected Source Inventory Generation

- Phase: Phase 5.21-ADG20
- proposed_corrected: 0
- rejected_current_reverse: 10
- requires_external_discovery: 32
- suspended_blocked: 8
- raw_write_ready: 0

## Key Finding
From source-controlled artifacts alone, corrected source inventory records cannot be generated for reverse-mapped Ligue 1 targets.
The current source inventory returns the WRONG leg for all double round-robin fixtures.
Corrected records must be acquired from external FotMob L1 API league overview or public page-route discovery.

## Results
| id | generation_status | correction_action |
| --- | --- | --- |
| 4830466 | preserved_suspended_blocked | n/a |
| 4830461 | preserved_suspended_blocked | n/a |
| 4830463 | preserved_suspended_blocked | n/a |
| 4830465 | preserved_suspended_blocked | n/a |
| 4830460 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830458 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830459 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830462 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830464 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830473 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830471 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830472 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830470 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830469 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830467 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830474 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830475 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830468 | rejected_current_reverse_fixture_record | requires_external_discovery_or_evidence_acquisition |
| 4830478 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830479 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830482 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830484 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830476 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830477 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830481 | preserved_suspended_blocked | n/a |
| 4830483 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830480 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830488 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830490 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830485 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830487 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830486 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830489 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830491 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830493 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830492 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830498 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830501 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830495 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830497 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830502 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830494 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830496 | preserved_suspended_blocked | n/a |
| 4830500 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830499 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830510 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830505 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4830511 | preserved_suspended_blocked | n/a |
| 4830508 | preserved_suspended_blocked | n/a |
| 4830507 | requires_external_discovery_or_evidence_acquisition | acquire_oriented_source_inventory_record_from_external_source |
| 4813735 | preserved_positive_control_no_write | n/a |

## Safety
- no live fetch / DB write / raw write / production mutation

## Next

10 targets have reverse-only evidence — confirmed from source-controlled data. 32 additional targets lack any observed evidence. Recommend ADG21: bounded corrected-source discovery using FotMob L1 API league overview or oriented public page-route acquisition. Do NOT raw write.
