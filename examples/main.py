import os
import pandas as pd


def main():
    print("hello from sample job")
    df = pd.DataFrame({"value": [1, 2, 3]})
    out_dir = os.environ.get("JOB_OUTPUT_DIR", ".")
    df.to_csv(os.path.join(out_dir, "sample.csv"), index=False)
    print("wrote sample.csv to", out_dir)


if __name__ == "__main__":
    main()
