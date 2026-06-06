## Dev environment tips
- Use uv for Python package management and manage this project as a uv project.
- The `rg` command is installed; use it for quick searching.
- This is a MacOS environment.
- The git server we use is GitHub; the `gh` command is available on this system.
- We're using a "monorepo" approach and avoiding PRs. Push to main upstream. There is only one developer on this project.
- Update README.md with each major commit.
- Don't use README.md as a change log. It's user documentation; they don't go there to look for changes.
- Update SKILLS.md with each change to this repo so future LLMs know how to use the MailChannels Python API correctly.

## Dev rules
- Use Python logging liberally to insert judicious debug, info, warning, and error messages in the code.
- Import logging into each module and set logger = logging.getLogger(__name__). Then use logger for logging in that module.
- In most cases where an error message is called for, you should raise an appropriate exception after logging the error.
- Let exceptions bubble up to the caller unless there is a logical way to handle the exception within the current scope.
- Unless there is no more specific alternative, never catch the base `Exception` class. Always catch the most specific exception you can.
- Commit every change you make and ask the user to push changes when a significant batch of changes has been made.
- Use Python type hints, data classes, Pydantic models, and other strong typing features everywhere.
- Never write a function that has no typing on parameters.
- Write a documentation string for every function and every class.
- Keep functions short and modular. If a function grows longer than 50 rows or so, break it into separate functions that you can compose in a sequence.
- Take the time to keep your code clean, tidy, and readable. Comments should not be required if code is written in a modular, readable manner.
- Always maintain a containerized version of the software using https://github.com/smol-machines/smolvm and run all tests in the SmolVM container. Quick start for SmolVM: `curl -sSL https://smolmachines.com/install.sh | bash && smolvm --help`

## Testing instructions
- Add or update tests for the code you change, even if nobody asked.
- Use pytest and create a harness so the user can just type "uv pytest".
- Always run the full test suite before every commit. Never commit if the test suite fails to pass.
