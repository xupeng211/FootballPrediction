# Single-League Small-Batch pageProps v2 Preflight - Phase 5.21L2T

## 1. Executive summary

- T0C discovered 50 real Ligue 1 2025/2026 candidate targets.
- L2T performed match detail pageProps v2 no-write preflight for manifest candidates only.
- No DB write, no raw_match_data write, no controlled write, and no parser/features/training were executed.

## 2. Current DB baseline

| table                   | rows |
| ----------------------- | ---- |
| matches                 | 10   |
| bookmaker_odds_history  | 2    |
| raw_match_data          | 18   |
| l3_features             | 2    |
| match_features_training | 2    |
| predictions             | 2    |

## 3. Authorization / guardrails

- network_authorization=yes
- match_detail_preflight_authorization=yes
- target_count=50
- concurrency=1
- retry=0
- no browser/proxy
- no DB write
- no controlled write
- no full body/json/pageProps print/save

## 4. Manifest input summary

- manifest path: `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json`
- known_completed_targets=8
- candidate_targets=50
- target_population_status before preflight: `ready_for_no_write_preflight`

## 5. Preflight result

- attempted_target_count=50
- skipped_existing_v2_count=0
- success_count=50
- failed_count=0
- blocked_count=0
- request_count=50
- hash_strategy=stable_pageprops_payload_v1
- target_population_status after preflight: `ready_for_controlled_write_authorization`
- required_next_step: `single_league_small_batch_controlled_pageprops_v2_write_authorization`

## 6. Candidate target preflight summary

| external_id | match_id            | home_team           | away_team           | kickoff_time             | status   | http_status | parse_status        | stable_pageprops_hash                                            | preflight_status    | failure_reason |
| ----------- | ------------------- | ------------------- | ------------------- | ------------------------ | -------- | ----------- | ------------------- | ---------------------------------------------------------------- | ------------------- | -------------- |
| 4830466     | 53_20252026_4830466 | Rennes              | Marseille           | 2025-08-15T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b | hash_baseline_ready |                |
| 4830461     | 53_20252026_4830461 | Lens                | Lyon                | 2025-08-16T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | eac411c9c86256df2099bbd8f75f4d86217d598b12d32d68cd67fbddea464767 | hash_baseline_ready |                |
| 4830463     | 53_20252026_4830463 | Monaco              | Le Havre            | 2025-08-16T17:00:00.000Z | finished | 200         | pageprops_v2_parsed | 519a171d16190df970026046d067f8acf10e9489e3d57a1c269278799199ea83 | hash_baseline_ready |                |
| 4830465     | 53_20252026_4830465 | Nice                | Toulouse            | 2025-08-16T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | cec694ea6bf683cf815bfd68bf0db35ce427bd6203dd13031479579ce015ceeb | hash_baseline_ready |                |
| 4830460     | 53_20252026_4830460 | Brest               | Lille               | 2025-08-17T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | 76d5fc82872d5bde2ffae016dd8b292f199501db478090f1d714dd25e08ef98e | hash_baseline_ready |                |
| 4830458     | 53_20252026_4830458 | Angers              | Paris FC            | 2025-08-17T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 14aff4519d38f6f90f428becef08c018dc4b4f98dbb668b36d7cffad48cb8972 | hash_baseline_ready |                |
| 4830459     | 53_20252026_4830459 | Auxerre             | Lorient             | 2025-08-17T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 34fa44344f7abf24ac7a29c646a963ac373853be6d04c55637539f60ebe3c26b | hash_baseline_ready |                |
| 4830462     | 53_20252026_4830462 | Metz                | Strasbourg          | 2025-08-17T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 5089b44e1f5af688cc3930f37b6c09b19c83700592cc3d044e8ba4d42d988a30 | hash_baseline_ready |                |
| 4830464     | 53_20252026_4830464 | Nantes              | Paris Saint-Germain | 2025-08-17T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | 883991364eb632755e018fd4ecd719d2e669134c2fde265f3a470adbd92af905 | hash_baseline_ready |                |
| 4830473     | 53_20252026_4830473 | Paris Saint-Germain | Angers              | 2025-08-22T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | 562ce0e4aba52769b53a5b3848a7aa0ac55175943f20df1e2a59ff64318ebc47 | hash_baseline_ready |                |
| 4830471     | 53_20252026_4830471 | Marseille           | Paris FC            | 2025-08-23T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | 2725352ca86d4254e74601f4b61ff0f6267d226cb9ecfd2cc1f3368192553242 | hash_baseline_ready |                |
| 4830472     | 53_20252026_4830472 | Nice                | Auxerre             | 2025-08-23T17:00:00.000Z | finished | 200         | pageprops_v2_parsed | f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc | hash_baseline_ready |                |
| 4830470     | 53_20252026_4830470 | Lyon                | Metz                | 2025-08-23T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | de53eeb2ffd112577ef70684a998e3c85f5e2f5603550e272c59472691d062c8 | hash_baseline_ready |                |
| 4830469     | 53_20252026_4830469 | Lorient             | Rennes              | 2025-08-24T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | 75b4aaf6e7632842dafee1c946e1422a11179be2fb0c0be19ecd009130f6fc45 | hash_baseline_ready |                |
| 4830467     | 53_20252026_4830467 | Le Havre            | Lens                | 2025-08-24T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | bfc3881169c68bb7b39f29e60278fc34d05b7a838e10602cc2d55991c805d622 | hash_baseline_ready |                |
| 4830474     | 53_20252026_4830474 | Strasbourg          | Nantes              | 2025-08-24T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 6a00d18d740d69eb9a65c593426cad4f956bf9492b0e5be489b75b90d838b6b6 | hash_baseline_ready |                |
| 4830475     | 53_20252026_4830475 | Toulouse            | Brest               | 2025-08-24T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 0e7c1d543e12c112bf6c3e7002d02d49d56afab1283d0fb62f8c81ee78575775 | hash_baseline_ready |                |
| 4830468     | 53_20252026_4830468 | Lille               | Monaco              | 2025-08-24T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5 | hash_baseline_ready |                |
| 4830478     | 53_20252026_4830478 | Lens                | Brest               | 2025-08-29T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | 3d6e522813c63b99f430c4367996385c74196b2b47602560f27ac8441ee1f33c | hash_baseline_ready |                |
| 4830479     | 53_20252026_4830479 | Lorient             | Lille               | 2025-08-30T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | c0a8136ad9a50a19b5a2e70fd8d11aa2be83b2107ad66b63b3ca0dde212c033d | hash_baseline_ready |                |
| 4830482     | 53_20252026_4830482 | Nantes              | Auxerre             | 2025-08-30T17:00:00.000Z | finished | 200         | pageprops_v2_parsed | d1d9c0a32ec75b4f2ce88f56c47f587dd937520bee260167aa7ca8e9d685f1a5 | hash_baseline_ready |                |
| 4830484     | 53_20252026_4830484 | Toulouse            | Paris Saint-Germain | 2025-08-30T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | 594c6ded490ba7f2089dc266edeb30b68d9654f9e0859812035865c197f9c097 | hash_baseline_ready |                |
| 4830476     | 53_20252026_4830476 | Angers              | Rennes              | 2025-08-31T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | b45c4afc5e7a055bc3b60add689b46cd826ec213f12bc6efc37581c11bf5e978 | hash_baseline_ready |                |
| 4830477     | 53_20252026_4830477 | Le Havre            | Nice                | 2025-08-31T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 32fea505aa1fc0bebb9e6336208bf32f7f0cdeacb536f3ecce70823317b7393f | hash_baseline_ready |                |
| 4830481     | 53_20252026_4830481 | Monaco              | Strasbourg          | 2025-08-31T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 3196b8854e54b04ed951883c76463e98c6b92600ed5d7c6e6906e7d12f8fde97 | hash_baseline_ready |                |
| 4830483     | 53_20252026_4830483 | Paris FC            | Metz                | 2025-08-31T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | b3800c9c47ccdb4eb4f485f579f79f5e91916e91ff01b462f2d4241a57a94456 | hash_baseline_ready |                |
| 4830480     | 53_20252026_4830480 | Lyon                | Marseille           | 2025-08-31T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | 782563109844e30585bc814b899bba71fae456c9340ccad6ee0b4693162eb593 | hash_baseline_ready |                |
| 4830488     | 53_20252026_4830488 | Marseille           | Lorient             | 2025-09-12T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | f3e28a11286b14aa3e72435c7472493d7132eb1013ba2e970914d1d25fd7afea | hash_baseline_ready |                |
| 4830490     | 53_20252026_4830490 | Nice                | Nantes              | 2025-09-13T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | 6884afd9685c014f020461d16802af09384f606d4828e99d909818916d1a29ed | hash_baseline_ready |                |
| 4830485     | 53_20252026_4830485 | Auxerre             | Monaco              | 2025-09-13T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | ed8639a0b1f82861d0f991a8d547409b3b88ff35ed1fd127f7fc1623ab675467 | hash_baseline_ready |                |
| 4830487     | 53_20252026_4830487 | Lille               | Toulouse            | 2025-09-14T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | 42728b7c805ca2d929f72f2ac29ed4e663e13a374c7467d0d6f181e2a4b2cd76 | hash_baseline_ready |                |
| 4830486     | 53_20252026_4830486 | Brest               | Paris FC            | 2025-09-14T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 2d4144f8fa562c0520728f51c33e4eb501e61b273705c8d3ecfa082fd3587fa3 | hash_baseline_ready |                |
| 4830489     | 53_20252026_4830489 | Metz                | Angers              | 2025-09-14T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 7d66f6530c38aa538339b894e70928b72fc55dbc408755ad996f44d4e08a2b6e | hash_baseline_ready |                |
| 4830491     | 53_20252026_4830491 | Paris Saint-Germain | Lens                | 2025-09-14T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 67a805fc4db215cb67c60a5f1db9364eab0d0a92d3b0ed6a04d288df0024bdc8 | hash_baseline_ready |                |
| 4830493     | 53_20252026_4830493 | Strasbourg          | Le Havre            | 2025-09-14T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | e0425ed9c188d92e16188ab9d8f45a363942caa7c753c28fdddc6955678ab208 | hash_baseline_ready |                |
| 4830492     | 53_20252026_4830492 | Rennes              | Lyon                | 2025-09-14T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | d5464aa69be9f3706dce73e9f489cf5f6f76a93b15130b24d8b8f6c6ac19968d | hash_baseline_ready |                |
| 4830498     | 53_20252026_4830498 | Lyon                | Angers              | 2025-09-19T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | 3fd2973d716f971bb2062d75d10ae93de600dfa1c7e5f35102acc9695ca17755 | hash_baseline_ready |                |
| 4830501     | 53_20252026_4830501 | Nantes              | Rennes              | 2025-09-20T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | 04fd2fb2e6d47d9e53ab77d5de5ed225ea0cbdd7f27b940e192b58e85bd8953b | hash_baseline_ready |                |
| 4830495     | 53_20252026_4830495 | Brest               | Nice                | 2025-09-20T17:00:00.000Z | finished | 200         | pageprops_v2_parsed | c8ea54f5922827e78c0f748cb0774fa188884f9c9f74be3eebb37be32e1b819b | hash_baseline_ready |                |
| 4830497     | 53_20252026_4830497 | Lens                | Lille               | 2025-09-20T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | b36842dc75def684cc6950cd01699b1746cd2768c4e9bfe6d4dbbc492413961d | hash_baseline_ready |                |
| 4830502     | 53_20252026_4830502 | Paris FC            | Strasbourg          | 2025-09-21T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | aab3e77aaef4c4a0a34c036e06aff64fa8cb7b079465596f2eef91de457edf90 | hash_baseline_ready |                |
| 4830494     | 53_20252026_4830494 | Auxerre             | Toulouse            | 2025-09-21T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | ed99f9e33746a204933da86d0df6ad35b902f7f8ff7e9a2093c4ea0f698d66db | hash_baseline_ready |                |
| 4830496     | 53_20252026_4830496 | Le Havre            | Lorient             | 2025-09-21T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 4aee2a2e2801dbfd4a33cb94fe87182e9165b33a15937dbd70e3783d79f81a6c | hash_baseline_ready |                |
| 4830500     | 53_20252026_4830500 | Monaco              | Metz                | 2025-09-21T15:15:00.000Z | finished | 200         | pageprops_v2_parsed | 9db7a361bdc24349f17ddc64f7eb487883fd87e2f646d3e2889731ce5a323f56 | hash_baseline_ready |                |
| 4830499     | 53_20252026_4830499 | Marseille           | Paris Saint-Germain | 2025-09-22T18:00:00.000Z | finished | 200         | pageprops_v2_parsed | 8ccde7d5658d1148e6c3283efb94510a7b965fdd553b70e7151b5feb4d309666 | hash_baseline_ready |                |
| 4830510     | 53_20252026_4830510 | Strasbourg          | Marseille           | 2025-09-26T18:45:00.000Z | finished | 200         | pageprops_v2_parsed | dae81353108344a1581fb87584fa65ca833a939900173e34ffef843eb38467e4 | hash_baseline_ready |                |
| 4830505     | 53_20252026_4830505 | Lorient             | Monaco              | 2025-09-27T15:00:00.000Z | finished | 200         | pageprops_v2_parsed | 680d9ed7b927e37162a677737848fec7c38841b18f299cea2145bf408da4fe8b | hash_baseline_ready |                |
| 4830511     | 53_20252026_4830511 | Toulouse            | Nantes              | 2025-09-27T17:00:00.000Z | finished | 200         | pageprops_v2_parsed | e6721fc620e526e7d97be1e1545b4b1c3073f284d0b4aa66498724235b0557c8 | hash_baseline_ready |                |
| 4830508     | 53_20252026_4830508 | Paris Saint-Germain | Auxerre             | 2025-09-27T19:05:00.000Z | finished | 200         | pageprops_v2_parsed | e511251e50e701e6d626bd7ff57620556a7654fe587e0828bae02bb36f2a231c | hash_baseline_ready |                |
| 4830507     | 53_20252026_4830507 | Nice                | Paris FC            | 2025-09-28T13:00:00.000Z | finished | 200         | pageprops_v2_parsed | 0c73ba5c6e646e6312de6cbc9f9445c2cd063c56e19c371e01dfa5b5a02da550 | hash_baseline_ready |                |

## 7. Coverage / shape summary

- pageProps_found_count=50
- raw_data_shape_valid_count=50
- has_meta_count=50
- has_matchId_count=50
- has_pageProps_count=50
- module coverage: `{"content.matchFacts":50,"content.lineup":50,"content.liveticker":50,"content.playerStats":50,"content.shotmap":50,"content.stats":50,"content.h2h":50,"content.table":50,"content.momentum":50,"content.topPlayers":0,"content.insights":0,"content.highlights":0,"seo":50,"seo.eventJSONLD":50,"seo.breadcrumbJSONLD":50,"translations":50,"fallback":50,"nav":50,"ongoing":50,"ssr":50}`
- suspicious small payloads: `none`
- block/captcha markers: `none`

## 8. Manifest update result

- manifest updated: yes
- candidate_targets count: 50
- baseline_hash populated count: 50
- preflight_status distribution: `{"hash_baseline_ready":50}`
- target_population_status: `ready_for_controlled_write_authorization`
- required_next_step: `single_league_small_batch_controlled_pageprops_v2_write_authorization`

## 9. DB safety result

- matches=10
- raw_match_data=18
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2
- row counts unchanged: true

## 10. Verification results

- small-batch pageProps v2 preflight tests: passed (`node --test tests/unit/single_league_small_batch_pageprops_v2_preflight.test.js`)
- related pageProps/source inventory/manifest/canonical tests: passed
- `npm test`: passed
- `npm run test:coverage`: passed (`lines=89.44`, `branches=80.02`, `functions=84.61`)
- `git diff --check`: passed
- ESLint: passed for `FotMobRawDetailFetcher`, the new preflight script, and the new test file
- Prettier: passed
- DB row counts unchanged: matches=10, raw_match_data=18, bookmaker_odds_history=2, l3_features=2, match_features_training=2, predictions=2
- l1-config residue absent
- `docs/_staging_preview` absent
- PR CI: pending before PR creation
- main push CI: pending until PR merge

## 11. Recommended next phase

- Phase 5.21L2U: single-league small-batch controlled pageProps v2 write authorization / planning.
- Any future write requires explicit final DB-write authorization, baseline hash gates, a controlled transaction, and no parser/features/training.

## 12. Explicit non-execution

- no DB writes
- no raw_match_data writes
- no bookmaker_odds_history writes
- no controlled write
- no schema migration
- no matches writes
- no parser implementation
- no feature extraction
- no l3_features write
- no match_features_training write
- no training/prediction
- no browser/proxy/captcha bypass
- no retry
- no full raw_data/pageProps/source body print/save
- no file deletion
- no invented external_id / fake target data
