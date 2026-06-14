## Summary

<!-- What does this PR do? Why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature / command
- [ ] Refactor / cleanup
- [ ] Documentation
- [ ] Other: ___

## Checklist

- [ ] Ran `make format` (black)
- [ ] Ran `make lint` (flake8 + mypy)
- [ ] New handler uses `@safe_command` decorator
- [ ] New command added to `command_map.py`
- [ ] New command documented in `docs/COMMANDS.md`
- [ ] No secrets or credentials committed
- [ ] Windows-only imports guarded with `if platform.system() == "Windows":`
- [ ] Heavy imports are inside the handler function (not module-level)

## Testing

<!-- How did you test this? What commands/scenarios did you verify? -->

## Related issues

<!-- Closes #xxx -->
