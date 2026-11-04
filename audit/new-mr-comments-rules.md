# Additional MR comment coverage (5 screenshots)

| Screenshot comment | Rule ID | Note |
|---|---|---|
| `start` / `end` arguments swapped in `RouteGroupsRepository.findOverlapping` | JAVA-API-001 | Check actual named binding and caller semantics, not just naming |
| Schedule is defined in Tashkent time; remove variable zone logic | JAVA-TIME-002 | Only when business time basis is fixed |
| Inline sender/receiver `if` checks should be validation methods (two screenshots) | JAVA-VALIDATION-001 | Preserve validation semantics |
| Explain specific conflict rather than generic `ConflictException` | JAVA-ERROR-003 | Structured code or safe message is acceptable |

All previous rules retained without ID changes.
