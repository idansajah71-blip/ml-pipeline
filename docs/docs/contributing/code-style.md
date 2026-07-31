---
sidebar_position: 3
title: Code Style
---

# Code Style Guide

Coding conventions for the ML Pipeline project.

## Python (Backend)

### Formatting

- **Formatter**: Black
- **Line length**: 88 characters
- **Import sorting**: isort

```bash
# Format code
black app/
isort app/
```

### Naming

| Type | Convention | Example |
|------|-----------|---------|
| Functions | snake_case | `get_user_by_id()` |
| Classes | PascalCase | `DataProcessor` |
| Constants | UPPER_SNAKE | `MAX_FILE_SIZE` |
| Variables | snake_case | `user_count` |
| Files | snake_case | `security_middleware.py` |

### Type Hints

Always use type hints:

```python
def process_data(df: pd.DataFrame, target: str) -> Tuple[pd.DataFrame, pd.Series]:
    ...

async def get_user(user_id: UUID, db: AsyncSession) -> User | None:
    ...
```

### Error Handling

```python
try:
    result = await some_operation()
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## TypeScript (Frontend)

### Formatting

- **Formatter**: Prettier
- **Linter**: ESLint
- **Line length**: 100 characters

```bash
npm run lint
```

### Naming

| Type | Convention | Example |
|------|-----------|---------|
| Components | PascalCase | `StatsCard.tsx` |
| Functions | camelCase | `fetchData()` |
| Variables | camelCase | `isLoading` |
| Types | PascalCase | `MLModel` |
| Files | PascalCase | `StatsCard.tsx` |

### Component Style

```tsx
// Functional components with explicit types
interface Props {
  title: string;
  value: number;
}

export default function StatsCard({ title, value }: Props) {
  return (
    <div>
      <h2>{title}</h2>
      <p>{value}</p>
    </div>
  );
}
```

## Git Commits

### Format

```
<type>: <description>

[optional body]
```

### Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation |
| test | Adding tests |
| refactor | Code refactor |
| chore | Maintenance |
| deps | Dependency update |

### Examples

```
feat: add model versioning
fix: resolve dataset upload timeout
docs: update API authentication guide
test: add ML pipeline unit tests
refactor: replace useState with SWR hooks
```

## Pull Requests

### Title

Use the same format as commits:
```
feat: add A/B testing dashboard
```

### Description

Include:
1. What changed
2. Why it changed
3. How to test
4. Screenshots (for UI changes)
