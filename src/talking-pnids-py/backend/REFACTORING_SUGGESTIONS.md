# Refactoring Suggestions

This document outlines suggested improvements for the codebase.

## ✅ Completed Refactorings

### 1. Environment Variables for Universal Deployment
- ✅ Added support for absolute paths via environment variables
- ✅ Environment variables take priority over config.json
- ✅ Created `env.example` template
- ✅ Created `ENV_SETUP.md` documentation

## 🔄 Recommended Refactorings

### 1. Error Handling & Validation

**Current Issue**: Some endpoints don't validate inputs properly.

**Suggested Changes**:
- Add Pydantic models for request/response validation
- Add proper error handling with consistent error response format
- Add input validation for file paths and API keys

**Example**:
```python
from pydantic import BaseModel, Field

class SessionRequest(BaseModel):
    pass  # Currently no body, but ready for future

class SessionResponse(BaseModel):
    success: bool
    message: str
    markdownsLoaded: int
    sessionId: str
```

### 2. Configuration Validation

**Current Issue**: No validation that required config values are present.

**Suggested Changes**:
- Add startup validation to check required environment variables
- Provide clear error messages if API key is missing
- Validate directory paths exist and are accessible

**Example**:
```python
def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate configuration and return list of errors"""
    errors = []
    if not config.get("openai", {}).get("apiKey"):
        errors.append("OPENAI_API_KEY is required")
    # ... more validations
    return errors
```

### 3. Logging Improvements

**Current Issue**: Using `print()` statements instead of proper logging.

**Suggested Changes**:
- Replace all `print()` with proper logging
- Add log levels (DEBUG, INFO, WARNING, ERROR)
- Add structured logging for better debugging

**Example**:
```python
import logging
logger = logging.getLogger(__name__)

# Instead of: print("Session started")
logger.info("Session started", extra={"session_id": session_id})
```

### 4. Path Resolution Simplification

**Current Issue**: `get_project_root()` has complex fallback logic.

**Suggested Changes**:
- Simplify path resolution to prioritize environment variables
- Remove complex fallback logic in favor of explicit configuration
- Make path resolution more predictable

### 5. API Response Consistency

**Current Issue**: Some endpoints return different error formats.

**Suggested Changes**:
- Standardize all API responses
- Use consistent error response format
- Add error codes for better client handling

**Example**:
```python
class APIError(BaseModel):
    error: str
    code: str
    details: Optional[Dict] = None

# Consistent error responses
raise HTTPException(
    status_code=400,
    detail=APIError(
        error="OpenAI API key not found",
        code="MISSING_API_KEY"
    ).dict()
)
```

### 6. Type Hints & Documentation

**Current Issue**: Some functions lack proper type hints and docstrings.

**Suggested Changes**:
- Add comprehensive type hints throughout
- Add docstrings to all public functions
- Use type checking tools (mypy) for validation

### 7. Testing Infrastructure

**Current Issue**: No tests present.

**Suggested Changes**:
- Add unit tests for utility functions
- Add integration tests for API endpoints
- Add tests for path resolution logic
- Set up pytest with coverage

### 8. Dependency Management

**Current Issue**: Some dependencies might be outdated.

**Suggested Changes**:
- Pin exact versions in requirements.txt
- Add requirements-dev.txt for development dependencies
- Consider using poetry or uv for better dependency management

### 9. Code Organization

**Current Issue**: Some files are getting large.

**Suggested Changes**:
- Split large files into smaller modules
- Group related functionality together
- Consider using dependency injection for better testability

### 10. Security Improvements

**Current Issue**: API keys might be logged or exposed.

**Suggested Changes**:
- Never log API keys (mask them in logs)
- Add rate limiting for API endpoints
- Add input sanitization for file paths
- Validate file paths to prevent directory traversal

### 11. Performance Optimizations

**Current Issue**: Markdown cache might not be optimal.

**Suggested Changes**:
- Add caching for API responses
- Optimize markdown loading
- Consider async file I/O operations
- Add connection pooling for external APIs

### 12. Deployment Readiness

**Current Issue**: Some hardcoded values might not work in all environments.

**Suggested Changes**:
- Make all paths configurable
- Add health check endpoint improvements
- Add readiness/liveness probes
- Add metrics endpoint for monitoring

## Priority Order

1. **High Priority** (Do First):
   - Error handling & validation (#1)
   - Configuration validation (#2)
   - Logging improvements (#3)
   - Security improvements (#10)

2. **Medium Priority** (Do Next):
   - API response consistency (#5)
   - Path resolution simplification (#4)
   - Type hints & documentation (#6)

3. **Low Priority** (Nice to Have):
   - Testing infrastructure (#7)
   - Performance optimizations (#11)
   - Code organization (#9)
   - Dependency management (#8)
   - Deployment readiness (#12)

## Implementation Notes

- Start with high-priority items as they improve reliability and security
- Test each refactoring incrementally
- Keep backward compatibility where possible
- Update documentation as you refactor
