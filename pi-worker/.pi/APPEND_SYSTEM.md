# Githeri Contract Protocol (Autonomous Agent Guidelines)

1. **CONTRACT FIRST**: Before modifying or creating backend routes, inspect active contracts in `.githeri/specs/` and checklists in `.githeri/plans/`. If no plan exists, your very first action MUST be calling the `githeri_plan(prompt=...)` MCP tool or running `githeri plan "<feature>"`. Never alter or delete existing specs unless explicitly instructed.
2. **ZERO SIMPLIFICATIONS**: Never assume, water down, or simplify logic because a file or task seems complex. Implement complete, production-grade logic. Stubs, placeholders (`pass`, `...`), and simplified shortcuts are failures.
3. **RELATIVE PATHS ONLY**: Never output or hardcode absolute user/host paths (`/Users/...`, `/home/...`). Always use repository-relative paths.
4. **NO BLOCKING DAEMONS OR LOG WATCHING**: Never start background dev servers (`uvicorn`, `flask run`) or blocking log watchers (`tail -f`). If an ephemeral server process is started, kill its PID (`kill -9 $PID`) immediately before ending your turn.
5. **CANONICAL CODE STRUCTURE**: Instantiate framework apps (`app = FastAPI(...)`) and database models (`Base = declarative_base()`) at module scope.
6. **COMPLETE IMPORTS**: Ensure every symbol and type hint (`Optional`, `Final`, `AsyncGenerator`) is imported. Check with `ruff check --select F821 <file>`.
7. **VERIFICATION GATE**: Before ending your turn, run `githeri verify`. A task is complete ONLY when `githeri verify` exits with code 0.
