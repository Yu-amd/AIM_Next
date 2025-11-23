# Contributing to AIM.next

Thank you for your interest in contributing to AIM.next! This guide will help you get started.

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd AIM_Next

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Make Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

**Before submitting changes, ensure all tests pass:**

```bash
# GPU Sharing component
cd aim-gpu-sharing
python3 tests/run_tests.py  # Quick validation
pytest tests/ -v            # Full test suite

# Other components (as they're developed)
# Similar commands for aim-guardrails and aim-finetuning
```

### 4. Commit Changes

```bash
git add .
git commit -m "Description of changes"
```

## Testing Requirements

### Unit Tests

- **Required**: All new features must include unit tests
- **Coverage**: Aim for 80%+ code coverage
- **Location**: Place tests in `tests/` directory of each component
- **Naming**: Follow `test_<module_name>.py` convention

### Writing Tests

See component-specific testing guides:
- [GPU Sharing Testing Guide](./aim-gpu-sharing/TESTING.md)

### Test Checklist

Before submitting:
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Tests cover edge cases
- [ ] Tests are well-documented
- [ ] No test warnings or errors

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Document public APIs with docstrings
- Keep functions focused and small

### YAML

- Use 2-space indentation
- Keep line length reasonable
- Add comments for complex configurations

## Documentation

### Required Documentation

- **Code**: Docstrings for all public functions/classes
- **Tests**: Test documentation in component `TESTING.md`
- **README**: Update component README with new features

### Documentation Style

- Use clear, concise language
- Include code examples
- Update as features evolve

## Component-Specific Guidelines

### GPU Sharing (`aim-gpu-sharing/`)

- See [GPU Sharing README](./aim-gpu-sharing/README.md)
- See [GPU Sharing Testing Guide](./aim-gpu-sharing/TESTING.md)
- Follow memory partitioning patterns
- Test with multiple model sizes

### Guardrails (`aim-guardrails/`)

- See [Guardrails README](./aim-guardrails/README.md)
- Test latency requirements (<50ms)
- Validate safety thresholds

### Fine-Tuning (`aim-finetuning/`)

- See [Fine-Tuning README](./aim-finetuning/README.md)
- Test profile generation accuracy
- Validate checkpoint management

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** tests and ensure they pass
6. **Update** documentation
7. **Commit** with clear messages
8. **Push** to your fork
9. **Create** a Pull Request

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No linter errors
- [ ] Commit messages are clear

## Questions?

- Check component-specific documentation
- Review existing code for patterns
- Ask in issues or discussions

## Testing Philosophy

We follow Test-Driven Development (TDD) principles:

1. **Write tests first** (when possible)
2. **Make tests pass**
3. **Refactor** while keeping tests green
4. **Document** test patterns

### Test Categories

- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test full workflows (when applicable)

## Continuous Integration

All PRs are automatically tested. Ensure:

- Tests run in CI environment
- No secrets in test code
- Tests are deterministic
- Fast execution (< 5 minutes for full suite)

---

**Thank you for contributing to AIM.next!** 🚀

