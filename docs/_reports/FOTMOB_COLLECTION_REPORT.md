# FOTMOB Collection Report

- Generated at: 2026-04-27T04:30:20.044Z
- Compliance mode: disabled
- Database status: available

## Collection Health

- Total matches: 3873
- Raw JSON rows: 2501
- Raw coverage: 64.58%
- Pending: 1372
- Harvested: 2501
- Failed: 0
- RECON linked: 0
- Average raw size: 205773 bytes
- Last collected at: Sun Apr 26 2026 17:38:16 GMT+0800 (China Standard Time)

## Failure Reasons

- No persisted failure reason column was available, or no failed rows were found.

## Schema Diff

- Samples inspected: 10
- Samples with changes: 10

### Added Keys

- general.awayTeam: 10
- general.awayTeam.name: 10
- general.homeTeam: 10
- general.homeTeam.name: 10
- general.leagueId: 10
- general.leagueName: 10
- general.matchId: 10
- general.matchTimeUTCDateTime: 10
- general.parentLeagueName: 10
- header.status: 10

### Removed Keys

- away: 10
- details: 10
- home: 10
- lineup: 10
- matchId: 10
- nav: 10
- stats: 10
- teams: 10

## Notes

- This report reads raw_match_data first and does not call FotMob or any live network endpoint.
- Schema diff is structural only: it compares key paths, not business values.
