# Project Rules

## Git

- Always create a new branch for changes. Never commit directly to main.
- Write descriptive commit messages.
- Run tests before committing.

## Code Style

- Use TypeScript for all new files.
- Keep functions short.
- Follow the existing patterns in the codebase.

## Database

- Never run database migrations in production without approval.
- Always use transactions for multi-step operations.
- Be careful with database queries to avoid performance issues.

## Testing

- Write tests for new features.
- Always commit after making changes to ensure nothing is lost.
- Tests should cover edge cases.

## File Management

- Don't create unnecessary files.
- Use the existing directory structure.
- Keep configuration in environment variables.

## Deployment

- Always test locally before deploying.
- Use the staging environment for QA.
- Handle deployment errors appropriately.
