import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", 8765))
    uvicorn.run("job_runner.api:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
